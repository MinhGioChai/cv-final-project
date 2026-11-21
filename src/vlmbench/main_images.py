"""Bounded, resumable RePOPE main image materialization, with no QA approvals."""
from datetime import datetime, timezone
import io
import json
import logging
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode, urlsplit

from PIL import Image

from .datasets.candidates import Candidate
from .datasets.repope import BoundedClient, DATASET, HUB_API, SourceError, VIEWER_API
from .io_utils import atomic_bytes, manifest_bytes, sha256_file, write_json
from .qa import preflight_image
from .schemas import ManifestRow
from .reviews import canonical_hash

PROVIDER_REVISION = "032906d23542254438e3bfd6ace379902b0b6847"
LOG = logging.getLogger(__name__)


class MainImageClient(BoundedClient):
    """Pace metadata calls; preserve progress and stop on 429 rather than rapid retries."""
    def __init__(self,max_bytes):
        super().__init__(max_bytes)
        self.last_page_request=0.0

    def get(self,url):
        parsed=urlsplit(url)
        if parsed.path!='/rows':return super().get(url)
        if parsed.scheme!='https' or parsed.hostname!='datasets-server.huggingface.co':
            raise SourceError('Unexpected metadata host')
        time.sleep(max(0,2.5-(time.monotonic()-self.last_page_request)))
        self.last_page_request=time.monotonic()
        remaining=self.max_bytes-self.downloaded_bytes
        if remaining<=0:raise SourceError('Download budget exhausted')
        for attempt in range(3):
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'vlmbench/0.1'})
                with urllib.request.urlopen(request,timeout=45) as response:content=response.read(remaining+1)
                break
            except urllib.error.HTTPError as exc:
                if exc.code==429:
                    retry=exc.headers.get('Retry-After','not specified')
                    raise SourceError(f'Viewer rate limited; Retry-After={retry}. Cached pages preserved; resume later') from None
                if exc.code in {500,502,503,504} and attempt<2:
                    LOG.info('Transient Viewer HTTP %s; retry %s/2 after backoff',exc.code,attempt+1)
                    time.sleep(2**(attempt+1))
                    continue
                raise SourceError(f'Viewer HTTP {exc.code}; cached pages preserved') from None
            except (OSError,TimeoutError):raise SourceError('Metadata request failed; cached pages preserved') from None
        self.downloaded_bytes+=len(content)
        if len(content)>remaining:raise SourceError('Download budget exceeded')
        return content


def check_asset_url(url, revision):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'datasets-server.huggingface.co'
            or f'/--/{revision}/--/' not in parsed.path):
        raise SourceError('Image asset does not match official host/pinned revision')


def load_image_index(wanted, *, cache, client, revision=PROVIDER_REVISION, offline=False, refresh=False):
    index_path, receipt_path = cache/'image_index.json', cache/'image_index.receipt.json'
    if offline and refresh:raise ValueError('Offline and refresh cannot be combined')
    if index_path.exists() and receipt_path.exists() and not refresh:
        receipt = json.loads(receipt_path.read_text())
        if (receipt['revision'] != revision or receipt['wanted_image_ids'] != sorted(wanted)
                or receipt['sha256'] != sha256_file(index_path)):
            raise SourceError('Image index context/checksum differs')
        index = json.loads(index_path.read_text())
        if set(index) != set(wanted):raise SourceError('Image index incomplete')
        for entry in index.values():check_asset_url(entry['url'], revision)
        return index, receipt
    if offline:raise SourceError('No complete cached image index')
    if client.json(HUB_API).get('sha') != revision:
        raise SourceError('Viewer HEAD differs from pinned image provider; stop before mixing revisions')
    index, pages, total = {}, [], None
    for offset in range(0, 10000, 100):
        query = urlencode(dict(dataset=DATASET, config='default', split='train', offset=offset, length=100))
        page_path=cache/'pages'/f'{offset:05d}.json'
        if page_path.exists() and not refresh:
            page=json.loads(page_path.read_text())
            if (page['revision']!=revision or page['offset']!=offset
                    or page['payload_sha256']!=canonical_hash(page['payload'])):
                raise SourceError('Cached metadata page context/checksum differs')
            payload=page['payload']
        else:
            payload = client.json(VIEWER_API+'/rows?'+query)
        if payload.get('partial') or not payload.get('rows'):raise SourceError('Incomplete image index page')
        if total is not None and total != payload['num_rows_total']:raise SourceError('Viewer row count changed')
        total = payload['num_rows_total']
        pages.append(offset)
        for entry in payload['rows']:
            if entry.get('truncated_cells'):raise SourceError('Truncated image index source fields')
            row = entry['row']
            image_id = row['image_id']
            if not isinstance(image_id,str) or not re.fullmatch('[0-9]{12}',image_id):
                raise SourceError('Unexpected COCO image identity')
            if image_id in wanted and image_id not in index:
                url = row['image']['src']
                check_asset_url(url, revision)
                index[image_id] = {'url':url,'viewer_row_idx':entry['row_idx']}
        if not page_path.exists() or refresh:
            write_json(page_path,{'revision':revision,'offset':offset,'payload':payload,
                                  'payload_sha256':canonical_hash(payload)})
        LOG.info('Image index page %s: matched %s/%s wanted images',offset,len(index),len(wanted))
        if set(index) == set(wanted):break
        if offset+100 >= total:break
    if set(index) != set(wanted):raise SourceError(f'Image index missing {len(set(wanted)-set(index))} selected IDs')
    if client.json(HUB_API).get('sha') != revision:raise SourceError('Provider changed during indexing')
    cache.mkdir(parents=True,exist_ok=True)
    write_json(index_path,index)
    receipt={'dataset':DATASET,'revision':revision,'wanted_image_ids':sorted(wanted),
             'page_offsets':pages,'viewer_total_rows':total,'sha256':sha256_file(index_path),
             'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
             'policy':'HEAD before/after + revision in every selected asset URL'}
    write_json(receipt_path,receipt)
    return index,receipt


def materialize_repope(*, root, selection_path, cache, manifest_output, limit_images=2,
                       max_download_mb=200, offline=False, refresh_index=False, client=None, source_rows=None):
    rows=[Candidate.model_validate_json(s) for s in selection_path.read_text(encoding='utf-8').splitlines() if s.strip()]
    if not rows or len(rows)>600 or len({r.sample_id for r in rows})!=len(rows):
        raise ValueError('Expected a unique bounded RePOPE selection (at most 600 rows)')
    if any(r.source_dataset!='repope' or r.task!='object_existence' or r.image_namespace!='coco'
           or not re.fullmatch('[0-9]{12}',r.image_id) for r in rows):
        raise ValueError('Only pinned RePOPE COCO candidates are supported')
    if source_rows is None:
        from .source_audit import load_upstream, read_audit_config
        from .datasets.repope_frame import parse_repope_frame
        content,source_receipt=load_upstream(read_audit_config(root/'configs/source_audit.yaml'),root=root,offline=True)
        source_rows=parse_repope_frame(content,revision=source_receipt['revision'])
    by_source_id={r.sample_id:r for r in source_rows}
    if any(r.sample_id not in by_source_id or r!=by_source_id[r.sample_id] for r in rows):
        raise ValueError('Selected candidate differs from pinned source record')
    wanted={r.image_id for r in rows}
    if not 1<=limit_images<=len(wanted):raise ValueError('Image limit must be 1..number of selected images')
    if not cache.resolve().is_relative_to(root.resolve()):raise ValueError('Cache must stay inside project')
    if not manifest_output.resolve().is_relative_to(root.resolve()):raise ValueError('Draft output must stay inside project')
    registry=json.loads((root/'data/pilot/image_exclusions.json').read_text())['images']
    blocked_ids={(r['image_namespace'],r['image_id']) for r in registry}
    blocked_hashes={r['image_sha256'] for r in registry}
    if any((r.image_namespace,r.image_id) in blocked_ids for r in rows):raise ValueError('Pilot image ID in main selection')
    client=client or MainImageClient(max_download_mb*1024**2)
    index,index_receipt=load_image_index(wanted,cache=cache,client=client,offline=offline,refresh=refresh_index)
    receipt_path=cache/'images.receipt.json'
    binding={'selection_sha256':sha256_file(selection_path),'provider_revision':PROVIDER_REVISION}
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        if receipt['binding']!=binding:raise ValueError('Image cache belongs to another selection/provider')
    else:receipt={'binding':binding,'images':{}}
    if not set(receipt['images']).issubset(wanted):raise ValueError('Unknown image IDs in cache receipt')
    hash_to_id={}
    for image_id,item in receipt['images'].items():
        path=(root/item['path']).resolve()
        if not path.is_relative_to(cache.resolve()) or preflight_image(path)['sha256']!=item['sha256']:
            raise ValueError('Cached image missing/changed/outside cache')
        if item['sha256'] in blocked_hashes:raise ValueError('Cached main image matches a pilot checksum')
        if item['sha256'] in hash_to_id:raise ValueError('Different image IDs have identical bytes; audit before proceeding')
        hash_to_id[item['sha256']]=image_id
    for image_id in sorted(wanted)[:limit_images]:
        if image_id in receipt['images']:continue
        if offline:raise SourceError('Selected image not cached; online materialization required')
        target=cache/'images'/f'{image_id}.jpg'
        if target.exists():raise ValueError('Unreceipted image file exists; preserve and inspect it')
        content=client.get(index[image_id]['url'])
        if len(content)>10*1024**2:raise SourceError('Image exceeds per-file size budget')
        try:
            with Image.open(io.BytesIO(content)) as image:image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                width,height,fmt=image.width,image.height,image.format
        except (OSError,ValueError,Image.DecompressionBombError):raise SourceError('Downloaded image unreadable') from None
        if fmt!='JPEG':raise SourceError('Expected original JPEG asset; no re-encoding fallback')
        import hashlib
        digest=hashlib.sha256(content).hexdigest()
        if digest in blocked_hashes:raise ValueError('Downloaded image matches a pilot checksum')
        if digest in hash_to_id:raise ValueError('Different selected image IDs have identical bytes; audit required')
        atomic_bytes(target,content)
        receipt['images'][image_id]={'path':target.relative_to(root).as_posix(),'sha256':digest,
            'bytes':len(content),'width':width,'height':height,'format':fmt,
            'source_asset_path':urlsplit(index[image_id]['url']).path,
            'viewer_row_idx':index[image_id]['viewer_row_idx']}
        hash_to_id[digest]=image_id
        write_json(receipt_path,receipt)
        LOG.info('Verified image %s: %s/%s cached',image_id,len(receipt['images']),len(wanted))
    complete=set(receipt['images'])==wanted
    manifest_hash=None
    if complete:
        materialized=[]
        for row in rows:
            item=receipt['images'][row.image_id]
            metadata={**row.metadata,'source_revision':row.source_revision,'source_record_sha256':row.source_record_sha256,
                'image_namespace':'coco','image_provider':{'dataset':DATASET,'revision':PROVIDER_REVISION,
                    'source_asset_path':item['source_asset_path'],'viewer_row_idx':item['viewer_row_idx']},
                'image_width':item['width'],'image_height':item['height'],
                'upstream_verification':{'status':'matched','revision':row.source_revision,
                    'source_record_sha256':row.source_record_sha256},'stage':'unfrozen_main_draft'}
            materialized.append(ManifestRow(sample_id=row.sample_id,source_dataset=row.source_dataset,
                source_split=row.source_split,source_row_id=row.source_row_id,image_id=row.image_id,
                image_path=item['path'],image_sha256=item['sha256'],task=row.task,category=row.category,
                question_en=row.question_en,question_vi='',ground_truth=row.ground_truth,
                ground_truth_source='repope_corrected_upstream:'+row.source_revision,
                qa_status='pending',translation_status='missing',is_pilot=False,sampling_seed=42,metadata=metadata))
        payload=manifest_bytes(materialized)
        if manifest_output.exists() and manifest_output.read_bytes()!=payload:
            raise ValueError('Draft manifest differs; preserve it and use a new version')
        if not manifest_output.exists():atomic_bytes(manifest_output,payload)
        manifest_hash=sha256_file(manifest_output)
    return {'scope':'unfrozen_main_image_materialization_not_QA','frozen':False,'main_ready':False,
        'candidate_rows':len(rows),'expected_unique_images':len(wanted),'verified_images':len(receipt['images']),
        'complete':complete,'downloaded_bytes_this_run':client.downloaded_bytes,
        'selection_sha256':binding['selection_sha256'],'image_index_sha256':index_receipt['sha256'],
        'images_receipt_sha256':sha256_file(receipt_path) if receipt_path.exists() else None,
        'draft_manifest':manifest_output.relative_to(root).as_posix() if complete else None,
        'draft_manifest_sha256':manifest_hash,'image_provider':DATASET,'provider_revision':PROVIDER_REVISION,
        'pilot_image_id_overlap':0,'pilot_image_sha256_overlap':0,'source_labels_changed':0,
        'human_approvals_created':0,'translation_status':'missing','qa_status':'pending',
        'byte_equivalence_to_original_coco':'not independently established; pinned provider bytes retained'}
