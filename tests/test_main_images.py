import hashlib
import io
import json

from PIL import Image
import pytest

from vlmbench.datasets.candidates import candidate
from vlmbench.io_utils import read_manifest, write_json, sha256_file
from vlmbench.main_images import materialize_repope, check_asset_url, load_image_index, PROVIDER_REVISION, MainImageClient
from vlmbench.datasets.repope import SourceError


def jpeg(color):
    b=io.BytesIO();Image.new('RGB',(12,8),color=color).save(b,format='JPEG');return b.getvalue()


@pytest.fixture
def images_project(tmp_path):
    rows=[candidate(dataset='repope',split='annotations',revision='a'*40,row_id=str(i),
        record={'synthetic_test_only':i},namespace='coco',image_id=f'{i:012}',image_ref=f'COCO_val2014_{i:012}.jpg',
        task='object_existence',category='random',question='synthetic_test_only?',truth='yes' if i==1 else 'no') for i in (1,2)]
    path=tmp_path/'selection.jsonl';path.write_text(''.join(r.model_dump_json()+'\n' for r in rows))
    write_json(tmp_path/'data/pilot/image_exclusions.json',{'images':[]})
    cache=tmp_path/'cache'
    idx={r.image_id:{'url':f'https://datasets-server.huggingface.co/assets/--/{PROVIDER_REVISION}/--/{i}.jpg',
                       'viewer_row_idx':i} for i,r in enumerate(rows)}
    write_json(cache/'image_index.json',idx)
    write_json(cache/'image_index.receipt.json',{'revision':PROVIDER_REVISION,
        'wanted_image_ids':sorted(idx),'sha256':sha256_file(cache/'image_index.json')})
    class FakeClient:
        downloaded_bytes=0
        calls=0
        def get(self,url):
            self.calls+=1
            content=jpeg('red' if url.endswith('0.jpg') else 'blue')
            self.downloaded_bytes+=len(content)
            return content
    options=dict(root=tmp_path,selection_path=path,cache=cache,manifest_output=tmp_path/'draft.csv',
                 client=FakeClient(),source_rows=rows)
    return rows,options


def test_partial_then_resume_fetches_only_missing_images_and_preserves_labels(images_project):
    rows,opts=images_project
    first=materialize_repope(**opts,limit_images=1)
    assert not first['complete'] and not opts['manifest_output'].exists()
    complete=materialize_repope(**opts,limit_images=2)
    assert complete['complete'] and opts['client'].calls==2
    actual=read_manifest(opts['manifest_output'])
    assert [r.ground_truth for r in actual]==[r.ground_truth for r in rows]
    assert all(r.qa_status=='pending' and r.translation_status=='missing' and not r.is_pilot for r in actual)
    before=opts['manifest_output'].read_bytes()
    assert materialize_repope(**opts,limit_images=2,offline=True)['complete']
    assert opts['client'].calls==2 and opts['manifest_output'].read_bytes()==before


def test_pilot_id_overlap_fails_before_network(images_project):
    rows,opts=images_project
    write_json(opts['root']/'data/pilot/image_exclusions.json',{'images':[{
        'image_namespace':'coco','image_id':rows[0].image_id,'image_sha256':'0'*64}]})
    with pytest.raises(ValueError,match='Pilot image ID'):materialize_repope(**opts)
    assert opts['client'].calls==0


def test_pilot_byte_overlap_never_published(images_project):
    _,opts=images_project
    write_json(opts['root']/'data/pilot/image_exclusions.json',{'images':[{
        'image_namespace':'other','image_id':'synthetic','image_sha256':hashlib.sha256(jpeg('red')).hexdigest()}]})
    with pytest.raises(ValueError,match='pilot checksum'):materialize_repope(**opts)
    assert not (opts['cache']/'images/000000000001.jpg').exists()
    assert not opts['manifest_output'].exists()


def test_changed_source_label_rejected(images_project):
    rows,opts=images_project
    changed=[rows[0].model_copy(update={'ground_truth':'no'}),rows[1]]
    opts['selection_path'].write_text(''.join(r.model_dump_json()+'\n' for r in changed))
    with pytest.raises(ValueError,match='pinned source'):materialize_repope(**opts)
    assert opts['client'].calls==0


def test_corrupt_cached_image_stops_without_redownload(images_project):
    _,opts=images_project
    materialize_repope(**opts,limit_images=1)
    (opts['cache']/'images/000000000001.jpg').write_bytes(b'synthetic_corruption')
    with pytest.raises(ValueError):materialize_repope(**opts,limit_images=2)
    assert opts['client'].calls==1


def test_offline_missing_photo_stays_incomplete(images_project):
    _,opts=images_project
    with pytest.raises(SourceError,match='not cached'):materialize_repope(**opts,offline=True)
    assert opts['client'].calls==0


def test_draft_output_must_stay_inside_project(images_project):
    _,opts=images_project
    opts['manifest_output']=opts['root'].parent/'outside_synthetic_test_only.csv'
    with pytest.raises(ValueError,match='inside project'):materialize_repope(**opts)
    assert opts['client'].calls==0


@pytest.mark.parametrize('url',[
    'http://datasets-server.huggingface.co/--/'+PROVIDER_REVISION+'/--/image.jpg',
    'https://example.com/--/'+PROVIDER_REVISION+'/--/image.jpg',
    'https://datasets-server.huggingface.co/--/'+'b'*40+'/--/image.jpg'])
def test_wrong_host_or_revision_never_used(url):
    with pytest.raises(SourceError):check_asset_url(url,PROVIDER_REVISION)


def test_revision_drift_blocks_index_without_guessing_new_pin(tmp_path):
    class Drift:
        def json(self,url):return {'sha':'b'*40}
    with pytest.raises(SourceError,match='HEAD differs'):
        load_image_index({'000000000001'},cache=tmp_path,client=Drift())


def test_interrupted_index_reuses_completed_pages(tmp_path):
    from urllib.parse import parse_qs,urlsplit
    class Pages:
        def __init__(self,first):self.first=first;self.offsets=[]
        def json(self,url):
            if '/api/' in url:return {'sha':PROVIDER_REVISION}
            offset=int(parse_qs(urlsplit(url).query)['offset'][0]);self.offsets.append(offset)
            if self.first and offset==100:raise SourceError('synthetic interrupted source')
            n=1 if offset==0 else 2
            return {'num_rows_total':200,'rows':[{'row_idx':offset,'row':{'image_id':f'{n:012}',
                'image':{'src':f'https://datasets-server.huggingface.co/assets/--/{PROVIDER_REVISION}/--/{n}.jpg'}}}]}
    wanted={'000000000001','000000000002'}
    with pytest.raises(SourceError):load_image_index(wanted,cache=tmp_path,client=Pages(True))
    assert (tmp_path/'pages/00000.json').exists()
    second=Pages(False)
    index,_=load_image_index(wanted,cache=tmp_path,client=second)
    assert set(index)==wanted and second.offsets==[100]


def test_metadata_429_stops_without_rapid_retry(monkeypatch):
    import urllib.error
    calls=[]
    def limited(*args,**kwargs):
        calls.append(1)
        raise urllib.error.HTTPError('https://datasets-server.huggingface.co/rows',429,'limited',{'Retry-After':'60'},None)
    monkeypatch.setattr('urllib.request.urlopen',limited)
    with pytest.raises(SourceError,match='Retry-After=60'):
        MainImageClient(1000).get('https://datasets-server.huggingface.co/rows?synthetic_test_only=1')
    assert len(calls)==1
