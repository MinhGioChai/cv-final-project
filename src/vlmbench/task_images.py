"""Selected official images only; bounded acquisition never creates human approvals."""
import hashlib
import io
import json
import logging
import re
import tarfile
import gzip
import time
import urllib.request
from urllib.parse import urlsplit

from PIL import Image

from .datasets.candidates import Candidate
from .datasets.repope import BoundedClient
from .io_utils import atomic_bytes, manifest_bytes, read_manifest, sha256_file, write_json
from .qa import preflight_image
from .schemas import ManifestRow

PET_URL = 'https://thor.robots.ox.ac.uk/pets/images.tar.gz'
LOG = logging.getLogger(__name__)


def persist_receipt(path, value):
    """Windows scanners may briefly hold a receipt; retain atomic replacement."""
    for attempt in range(3):
        try:
            write_json(path,value)
            return
        except PermissionError:
            if attempt==2:raise
            time.sleep(0.25*2**attempt)


def selected_source(root, dataset):
    if dataset not in {'vsr', 'tallyqa', 'oxford_pet'}:
        raise ValueError('Unsupported task dataset')
    path = root / f'data/main/preparation_v2/{dataset}_candidates.jsonl'
    inventory = json.loads((root/'reports/stage1/v8/main_inventory_v2.json').read_text())['datasets'][dataset]
    frame = root / inventory['frame_path']
    if sha256_file(frame) != inventory['frame_sha256']:
        raise ValueError('Pinned source frame checksum differs')
    source = {r.sample_id: r for r in (Candidate.model_validate_json(s) for s in frame.read_text(encoding='utf-8').splitlines())}
    rows = [Candidate.model_validate_json(s) for s in path.read_text(encoding='utf-8').splitlines()]
    if not rows or len({r.sample_id for r in rows}) != len(rows):
        raise ValueError('Empty/duplicate selection')
    if any(r.source_dataset != dataset or source.get(r.sample_id) != r for r in rows):
        raise ValueError('Selection differs from pinned source')
    expected = 160 if dataset == 'oxford_pet' else 120
    if len(rows) != expected or len({r.image_id for r in rows}) != expected:
        raise ValueError('Selection quota/unique images differs')
    return rows, path


def image_url(row):
    if row.source_dataset == 'vsr':
        part = urlsplit(row.source_image_ref)
        if (part.hostname != 'images.cocodataset.org' or
                not re.fullmatch(r'/train2017/[0-9]{12}\.jpg|/val2017/[0-9]{12}\.jpg', part.path)
                or part.path.split('/')[-1] != row.image_id+'.jpg'):
            raise ValueError('Unexpected COCO source identity')
        return 'https://s3.amazonaws.com/images.cocodataset.org'+part.path
    if row.source_dataset == 'tallyqa':
        if not re.fullmatch(r'VG_100K(?:_2)?/[1-9][0-9]*\.jpg', row.source_image_ref):
            raise ValueError('Unexpected Visual Genome source path')
        if row.source_image_ref.split('/')[-1] != row.image_id+'.jpg':
            raise ValueError('Visual Genome identity differs')
        return 'https://cs.stanford.edu/people/rak248/'+row.source_image_ref
    raise ValueError('Pet images require the official archive')


def jpeg_info(content):
    if len(content) > 10*1024**2:
        raise ValueError('Selected image exceeds 10 MiB')
    with Image.open(io.BytesIO(content)) as image:
        image.verify()
    with Image.open(io.BytesIO(content)) as image:
        image.load()
        if image.format != 'JPEG':
            raise ValueError('Expected original JPEG bytes')
        return {'width':image.width, 'height':image.height, 'format':image.format,
                'bytes':len(content), 'sha256':hashlib.sha256(content).hexdigest()}


class BoundedStream:
    def __init__(self, stream, limit):
        self.stream, self.limit, self.count, self.digest = stream, limit, 0, hashlib.sha256()

    def read(self, size=-1):
        # Never permit an unbounded allocation through a stream consumer.
        size = min(size if size >= 0 else 1024**2, self.limit-self.count+1)
        data = self.stream.read(size)
        self.count += len(data)
        if self.count > self.limit:
            raise ValueError('Archive download budget exceeded')
        self.digest.update(data)
        return data


def consume_pet(stream, *, wanted, save):
    """Do not extract archive paths; pass only exact selected regular JPEG members."""
    found = set()
    with gzip.GzipFile(fileobj=stream) as uncompressed:
        with tarfile.open(fileobj=uncompressed, mode='r|') as archive:
            for member in archive:
                image_id = member.name.removeprefix('images/').removesuffix('.jpg')
                if member.name != f'images/{image_id}.jpg' or image_id not in wanted:
                    continue
                if not member.isfile() or not 0 < member.size <= 10*1024**2 or image_id in found:
                    raise ValueError('Unexpected selected archive member type/size/duplicate')
                content = archive.extractfile(member).read(10*1024**2+1)
                if len(content) != member.size:
                    raise ValueError('Truncated archive member')
                save(image_id, content, PET_URL+'#'+member.name)
                found.add(image_id)
        # Validate gzip trailer/CRC, even if tar stopped at the end markers.
        while uncompressed.read(1024**2):
            pass
    while stream.read(1024**2):
        pass
    if found != wanted:
        raise ValueError('Official Pet archive is missing selected images')


def materialize(root, dataset, *, offline=False, budget_mb=250):
    root = root.resolve()
    rows, selection = selected_source(root, dataset)
    cache = root/f'data/raw/task_images_v1/{dataset}'
    target = root/f'data/main/preparation_v3/{dataset}_image_draft.csv'
    receipt_path = cache/'receipt.json'
    binding = {'dataset':dataset, 'selection_sha256':sha256_file(selection), 'policy':'official_selected_original_jpeg_v1'}
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'binding':binding,'images':{}}
    wanted = {r.image_id for r in rows}
    if receipt['binding'] != binding or not set(receipt['images']).issubset(wanted):
        raise ValueError('Cache binding differs')
    registry = json.loads((root/'data/pilot/image_exclusions.json').read_text())['images']
    blocked_ids = {(r['image_namespace'], r['image_id']) for r in registry}
    blocked_hashes = {r['image_sha256'] for r in registry}
    for row in rows:
        if (row.image_namespace,row.image_id) in blocked_ids:
            raise ValueError('Pilot image ID in main')
    # Also check previous main tasks, so differently named copies cannot slip in.
    other_hashes = {r.image_sha256 for r in read_manifest(root/'data/main/preparation_v2/repope_bilingual_draft_manifest.csv')}
    for other in {'vsr','tallyqa','oxford_pet'}-{dataset}:
        other_receipt = root/f'data/raw/task_images_v1/{other}/receipt.json'
        if other_receipt.exists():
            other_hashes.update(r['sha256'] for r in json.loads(other_receipt.read_text())['images'].values())
    seen = set()
    for image_id, item in receipt['images'].items():
        path = (root/item['path']).resolve()
        if not path.is_relative_to(cache) or preflight_image(path)['sha256'] != item['sha256']:
            raise ValueError('Cached image path/checksum differs')
        if item['sha256'] in blocked_hashes | other_hashes | seen:
            raise ValueError('Cached image duplicates pilot/main bytes')
        seen.add(item['sha256'])

    def save(image_id, content, url):
        info = jpeg_info(content)
        if image_id in receipt['images']:
            if receipt['images'][image_id]['sha256'] != info['sha256']:
                raise ValueError('Official archive changed cached image bytes')
            return
        if info['sha256'] in blocked_hashes | other_hashes | seen:
            raise ValueError('Downloaded image duplicates pilot/main bytes')
        path = cache/'images'/f'{image_id}.jpg'
        if path.exists():
            # A previous receipt replacement can fail after the JPEG was committed.
            # Recover only after reacquiring identical official bytes; never overwrite.
            if preflight_image(path)['sha256'] != info['sha256']:
                raise ValueError('Unreceipted image differs from reacquired official bytes; preserve and inspect')
            LOG.info('Recovered identical official JPEG after interrupted receipt: %s',image_id)
        else:
            atomic_bytes(path, content)
        receipt['images'][image_id] = {**info,'path':path.relative_to(root).as_posix(),'url':url}
        seen.add(info['sha256'])
        persist_receipt(receipt_path,receipt)
        LOG.info('%s verified %s/%s',dataset,len(receipt['images']),len(wanted))

    downloaded = 0
    complete = set(receipt['images']) == wanted
    if dataset == 'oxford_pet':
        complete = complete and 'archive' in receipt
    if not complete:
        if offline:
            raise ValueError('Image cache incomplete; online acquisition required')
        if dataset == 'oxford_pet':
            request = urllib.request.Request(PET_URL,headers={'User-Agent':'vlmbench/0.1'})
            with urllib.request.urlopen(request,timeout=60) as response:
                if urlsplit(response.url).hostname != 'thor.robots.ox.ac.uk':
                    raise ValueError('Unexpected archive redirect')
                length = int(response.headers['Content-Length'])
                if length > budget_mb*1024**2:
                    raise ValueError('Official archive exceeds explicit download budget')
                etag = response.headers.get('ETag')
                stream = BoundedStream(response,budget_mb*1024**2)
                consume_pet(stream,wanted=wanted,save=save)
                if stream.count != length:
                    raise ValueError('Archive length differs')
                receipt['archive'] = {'url':PET_URL,'etag':etag,'bytes':stream.count,'sha256':stream.digest.hexdigest(),
                    'hash_scope':'observed full acquisition; not an independently published checksum'}
                downloaded = stream.count
                persist_receipt(receipt_path,receipt)
        else:
            client = BoundedClient(budget_mb*1024**2,allowed_hosts={'s3.amazonaws.com','cs.stanford.edu'})
            for row in rows:
                if row.image_id not in receipt['images']:
                    save(row.image_id,client.get(image_url(row)),image_url(row))
            downloaded = client.downloaded_bytes
    drafts = []
    for row in rows:
        item = receipt['images'][row.image_id]
        drafts.append(ManifestRow(sample_id=row.sample_id,source_dataset=row.source_dataset,
            source_split=row.source_split,source_row_id=row.source_row_id,image_id=row.image_id,
            image_path=item['path'],image_sha256=item['sha256'],task=row.task,category=row.category,
            question_en=row.question_en,question_vi='',ground_truth=row.ground_truth,
            ground_truth_source=row.source_dataset+':'+row.source_revision,qa_status='pending',
            translation_status='missing',is_pilot=False,sampling_seed=42,
            metadata={**row.metadata,'image_namespace':row.image_namespace,'source_revision':row.source_revision,
                'source_record_sha256':row.source_record_sha256,'image_provider':item['url'],
                'image_width':item['width'],'image_height':item['height'],'stage':'unfrozen_main_draft'}))
    payload = manifest_bytes(drafts)
    if target.exists() and target.read_bytes() != payload:
        raise ValueError('Draft differs; use new output version')
    if not target.exists():
        atomic_bytes(target,payload)
    return {'dataset':dataset,'rows':len(rows),'verified_images':len(receipt['images']),
        'downloaded_bytes_this_run':downloaded,'image_bytes':sum(r['bytes'] for r in receipt['images'].values()),
        'manifest':target.relative_to(root).as_posix(),'manifest_sha256':sha256_file(target),
        'receipt_sha256':sha256_file(receipt_path),'qa_status':'pending','translation_status':'missing',
        'frozen':False,'new_human_approvals':0,'pilot_id_overlap':0,'pilot_sha256_overlap':0,'other_main_sha256_overlap':0}
