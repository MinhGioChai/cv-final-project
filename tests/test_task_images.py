import gzip
import io
import json
import tarfile

from PIL import Image
import pytest

from vlmbench.datasets.candidates import candidate
from vlmbench.io_utils import write_json
from vlmbench import task_images as module


def row(dataset='vsr', image_id='000000012704'):
    return candidate(dataset=dataset,split='test',revision='a'*40,row_id='1',record={},
        namespace='coco' if dataset=='vsr' else 'visual_genome',image_id=image_id,
        image_ref=f'http://images.cocodataset.org/train2017/{image_id}.jpg' if dataset=='vsr' else f'VG_100K/{image_id}.jpg',
        task='spatial' if dataset=='vsr' else 'counting',category='x',question='Source question',
        truth='yes' if dataset=='vsr' else 1)


def jpeg(color='red'):
    output=io.BytesIO()
    Image.new('RGB',(3,4),color).save(output,'JPEG')
    return output.getvalue()


def test_source_urls_preserve_split_and_identity():
    assert module.image_url(row()).endswith('/images.cocodataset.org/train2017/000000012704.jpg')
    assert module.image_url(row('tallyqa','2360718'))=='https://cs.stanford.edu/people/rak248/VG_100K/2360718.jpg'
    changed=row().model_copy(update={'source_image_ref':'http://evil.example/train2017/000000012704.jpg'})
    with pytest.raises(ValueError):module.image_url(changed)
    with pytest.raises(ValueError):module.image_url(row().model_copy(update={'image_id':'other'}))


def test_bounded_stream_fails_before_unbounded_read():
    stream=module.BoundedStream(io.BytesIO(b'abcde'),3)
    with pytest.raises(ValueError,match='budget'):stream.read()


def archive(members):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz') as target:
        for name,content,kind in members:
            info=tarfile.TarInfo(name);info.size=len(content);info.type=kind
            target.addfile(info,io.BytesIO(content))
    return buf.getvalue()


def test_pet_only_exact_selected_members_and_full_stream_hash():
    payload=archive([('../escape.jpg',jpeg(),tarfile.REGTYPE),('images/wanted.jpg',jpeg(),tarfile.REGTYPE),
                     ('images/other.jpg',jpeg('blue'),tarfile.REGTYPE)])
    stream=module.BoundedStream(io.BytesIO(payload),len(payload))
    saved=[]
    module.consume_pet(stream,wanted={'wanted'},save=lambda *args:saved.append(args))
    assert len(saved)==1 and saved[0][0]=='wanted'
    assert stream.count==len(payload)
    assert saved[0][1]==jpeg()


def test_pet_missing_selected_member_rejected():
    payload=archive([('../wanted.jpg',jpeg(),tarfile.REGTYPE)])
    with pytest.raises(ValueError,match='missing'):
        module.consume_pet(module.BoundedStream(io.BytesIO(payload),len(payload)),wanted={'wanted'},save=lambda *a:None)


def test_pet_link_rejected():
    payload=archive([('images/wanted.jpg',b'',tarfile.SYMTYPE)])
    with pytest.raises(ValueError,match='member'):
        module.consume_pet(module.BoundedStream(io.BytesIO(payload),len(payload)),wanted={'wanted'},save=lambda *a:None)


def test_pet_duplicate_member_rejected():
    payload=archive([('images/wanted.jpg',jpeg(),tarfile.REGTYPE)]*2)
    with pytest.raises(ValueError,match='duplicate'):
        module.consume_pet(module.BoundedStream(io.BytesIO(payload),len(payload)),wanted={'wanted'},save=lambda *a:None)


def test_pet_gzip_crc_checked():
    payload=bytearray(archive([('images/wanted.jpg',jpeg(),tarfile.REGTYPE)]))
    payload[-8]^=1
    with pytest.raises((OSError,tarfile.ReadError)):
        module.consume_pet(module.BoundedStream(io.BytesIO(payload),len(payload)),wanted={'wanted'},save=lambda *a:None)


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    selection=tmp_path/'selection.jsonl';selection.write_text('fixed source')
    monkeypatch.setattr(module,'selected_source',lambda *a:([row()],selection))
    monkeypatch.setattr(module,'read_manifest',lambda *a:[])
    write_json(tmp_path/'data/pilot/image_exclusions.json',{'images':[]})
    class Client:
        def __init__(self,*a,**kw):self.downloaded_bytes=0
        def get(self,url):self.downloaded_bytes+=len(jpeg());return jpeg()
    monkeypatch.setattr(module,'BoundedClient',Client)
    return tmp_path


def test_materialize_resume_keeps_bytes_and_pending(prepared):
    first=module.materialize(prepared,'vsr')
    second=module.materialize(prepared,'vsr',offline=True)
    assert first['manifest_sha256']==second['manifest_sha256']
    assert second['downloaded_bytes_this_run']==0
    assert second['qa_status']=='pending' and second['new_human_approvals']==0


def test_offline_incomplete_rejected(prepared):
    with pytest.raises(ValueError,match='incomplete'):module.materialize(prepared,'vsr',offline=True)


def test_corrupt_cache_rejected(prepared):
    module.materialize(prepared,'vsr')
    path=prepared/'data/raw/task_images_v1/vsr/images/000000012704.jpg'
    path.write_bytes(jpeg('blue'))
    with pytest.raises(ValueError,match='checksum'):module.materialize(prepared,'vsr',offline=True)


def test_pilot_byte_overlap_rejected(prepared):
    write_json(prepared/'data/pilot/image_exclusions.json',{'images':[{'image_namespace':'other',
        'image_id':'other','image_sha256':module.jpeg_info(jpeg())['sha256']}]})
    with pytest.raises(ValueError,match='duplicates'):module.materialize(prepared,'vsr')


def test_unreceipted_image_not_overwritten(prepared):
    image=prepared/'data/raw/task_images_v1/vsr/images/000000012704.jpg'
    image.parent.mkdir(parents=True);image.write_bytes(b'keep me')
    with pytest.raises(ValueError):module.materialize(prepared,'vsr')
    assert image.read_bytes()==b'keep me'


def test_identical_orphan_after_receipt_failure_recovered(prepared):
    image=prepared/'data/raw/task_images_v1/vsr/images/000000012704.jpg'
    image.parent.mkdir(parents=True);image.write_bytes(jpeg())
    before=image.read_bytes()
    result=module.materialize(prepared,'vsr')
    assert result['verified_images']==1 and image.read_bytes()==before


def test_receipt_permission_failure_has_bounded_retry(tmp_path,monkeypatch):
    calls=[];real=module.write_json
    def failing(path,value):
        calls.append(1)
        if len(calls)<3:raise PermissionError('synthetic_test_only transient lock')
        real(path,value)
    monkeypatch.setattr(module,'write_json',failing);monkeypatch.setattr(module.time,'sleep',lambda *a:None)
    target=tmp_path/'receipt.json';module.persist_receipt(target,{'safe':True})
    assert len(calls)==3 and json.loads(target.read_text())=={'safe':True}
