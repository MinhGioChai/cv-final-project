"""Read-only image audit; optional offline image-processor CPU probe, no weights/GPU.

Run with .venv/Scripts/python.exe for inventory. Use .venv-infer/Scripts/python.exe
and --processor-probe to measure pinned cached image processors on 30 pilot images.
Outputs are new audit evidence; existing inputs/configs/HTML/reviews are never written.
"""
import argparse
import base64
from collections import Counter
import csv
import hashlib
import io
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess

from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--processor-probe', action='store_true')
    args = parser.parse_args()
    cfg = yaml.safe_load((ROOT/'configs/baseline_v3_draft.yaml').read_text(encoding='utf-8'))
    pilot = load_rows(ROOT/'data/pilot/stage1_qa_v1/pilot_manifest.csv')
    main_rows = [row for path in cfg['manifests'] for row in load_rows(ROOT/path)]
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    protected = {ROOT/p for p in tracked if p and not p.startswith('reports/audits/2026-11-24/')}
    protected.update(ROOT/r['image_path'] for r in pilot+main_rows)
    protected.update((ROOT/'results/pilot/local').glob('*'))
    protected.update((ROOT/'exports').glob('*.zip'))
    protected.update((ROOT/'reports/stage1/v12/main_review').glob('*.html'))
    protected.update((ROOT/'reports/stage1/v10/main_review').glob('*.html'))
    protected.add(ROOT/'reports/stage1/v8/label_qa_review.html')
    protected = sorted(p for p in protected if p.is_file())
    before = {p: sha(p) for p in protected}
    inventory = []
    for scope, rows in [('pilot', pilot), ('main', main_rows)]:
        for row in rows:
            path = ROOT/row['image_path']
            digest = sha(path)
            assert digest == row['image_sha256'], row['sample_id']
            with Image.open(path) as original:
                size = original.size
                fmt, mode = original.format, original.mode
                orientation = original.getexif().get(274)
                image = original.convert('RGB')
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            inventory.append({'scope': scope, 'sample_id': row['sample_id'],
                'dataset': row['source_dataset'], 'image_path': row['image_path'],
                'image_sha256': digest, 'original_wh': list(size), 'format': fmt, 'mode': mode,
                'exif_orientation': orientation, 'review_intrinsic_wh': list(size),
                'review_css': 'width:100%;max-height:650px;object-fit:contain' if scope=='main'
                              else 'width:100%;max-height:660px;object-fit:contain',
                'pre_processor_wh': list(image.size), 'pre_processor_mode': image.mode,
                'resized_by_512': size != image.size,
                'pre_processor_rgb_sha256': hashlib.sha256(image.tobytes()).hexdigest()})

    packets = json.loads((ROOT/'reports/stage1/v12/main_review/packets.json').read_text())['packets']
    originals = {r['sample_id']: r for r in main_rows}
    html_verified = 0
    for packet in packets:
        html = (ROOT/packet['html']).read_text(encoding='utf-8')
        payload = json.loads(re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>', html, re.S)[1])
        assert len(payload['cards']) == packet['rows']
        for card in payload['cards']:
            content = base64.b64decode(card['image'].split(',', 1)[1], validate=True)
            assert hashlib.sha256(content).hexdigest() == originals[card['sample_id']]['image_sha256']
            with Image.open(io.BytesIO(content)) as im:
                assert list(im.size) == next(r['original_wh'] for r in inventory if r['sample_id']==card['sample_id'])
            html_verified += 1
    legacy_verified = Counter()
    known = {r['sample_id']:r for r in pilot+main_rows}
    legacy_html = list((ROOT/'reports/stage1/v10/main_review').glob('*.html'))
    legacy_html.append(ROOT/'reports/stage1/v8/label_qa_review.html')
    for path in legacy_html:
        html=path.read_text(encoding='utf-8')
        match=re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>',html,re.S)
        if match is None:
            assert path.name=='index.html'
            continue
        payload=json.loads(match[1])
        for card in payload['cards']:
            content=base64.b64decode(card['image'].split(',',1)[1],validate=True)
            assert hashlib.sha256(content).hexdigest()==known[card['sample_id']]['image_sha256']
            legacy_verified['pilot' if 'label_qa' in path.name else 'main_v1']+=1
    json_stats = []
    for folder in ['data/reviews/main_review_v1', 'data/reviews/main_review_v2', 'data/reviews/pilot_label_qa_v1']:
        files = list((ROOT/folder).glob('*.json'))
        data_urls = sum('data:image/' in p.read_text(encoding='utf-8') for p in files)
        assert data_urls == 0
        json_stats.append({'folder': folder, 'files_checked': len(files), 'with_image_data_url': data_urls})
    summaries = {}
    for scope in ['pilot','main']:
        for dataset in sorted({r['dataset'] for r in inventory if r['scope']==scope}):
            records = [r for r in inventory if r['scope']==scope and r['dataset']==dataset]
            unique = {r['image_sha256']: r for r in records}.values()
            summaries[f'{scope}/{dataset}'] = {'rows':len(records), 'images':len(unique),
                'original_width_range':[min(r['original_wh'][0] for r in unique),max(r['original_wh'][0] for r in unique)],
                'original_height_range':[min(r['original_wh'][1] for r in unique),max(r['original_wh'][1] for r in unique)],
                'pre_processor_width_range':[min(r['pre_processor_wh'][0] for r in unique),max(r['pre_processor_wh'][0] for r in unique)],
                'pre_processor_height_range':[min(r['pre_processor_wh'][1] for r in unique),max(r['pre_processor_wh'][1] for r in unique)],
                'images_downscaled_512':sum(r['resized_by_512'] for r in unique),
                'nontrivial_exif_orientation':sum(r['exif_orientation'] not in (None,1) for r in unique)}
    (OUT/'image_dimensions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in inventory),encoding='utf-8')
    audit = {'date_local':'2026-11-24','code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        'scope':'read_only_cpu_image_inventory_not_inference','summaries':summaries,
        'main_html_cards_byte_verified':html_verified, 'review_json':json_stats,
        'legacy_html_cards_byte_verified':dict(legacy_verified),
        'Pillow':importlib.metadata.version('Pillow'),
        'originals_match_manifest':True, 'input_files_hash_verified_unchanged':len(protected),
        'display_size':'intrinsic measured; rendered CSS size depends on viewport; no browser layout measurement',
        'dimension_records':len(inventory), 'frozen':cfg['frozen'], 'freeze_receipt':cfg['freeze_receipt']}
    if args.processor_probe:
        # Local directories only. No Hub lookups, tokens, model/tokenizer loads or GPU use.
        os.environ['HF_HUB_OFFLINE']='1'
        os.environ['TRANSFORMERS_OFFLINE']='1'
        from transformers import AutoImageProcessor
        import transformers
        import torch
        torch.set_num_threads(1)
        probes=[]
        policies={}
        for alias, model in cfg['models'].items():
            snapshot=ROOT/'.cache/huggingface/hub'/('models--'+model['model_id'].replace('/','--'))/'snapshots'/model['revision']
            extra={'min_pixels':200704,'max_pixels':401408} if alias=='qwen' else {'do_pan_and_scan':False,'use_fast':False}
            current=AutoImageProcessor.from_pretrained(str(snapshot),local_files_only=True,**extra)
            default=AutoImageProcessor.from_pretrained(str(snapshot),local_files_only=True,**({'use_fast':False} if alias=='gemma' else {}))
            policies[alias]={'current_class':type(current).__name__,'current':current.to_dict(),
                'checkpoint_default_class':type(default).__name__,'checkpoint_default':default.to_dict(),
                'revision':model['revision'], 'preprocessor_config_sha256':sha(snapshot/'preprocessor_config.json')}
            for row in sorted(pilot,key=lambda r:r['sample_id']):
                with Image.open(ROOT/row['image_path']) as im:original=im.convert('RGB')
                thumb=original.copy();thumb.thumbnail((512,512),Image.Resampling.LANCZOS)
                for policy,image,processor in [('A_512_current',thumb,current),('B_original_same_processor',original,current),('C_original_checkpoint_default',original,default)]:
                    inputs=processor(images=[image],return_tensors='pt')
                    result={'sample_id':row['sample_id'],'model':alias,'policy':policy,'input_wh':list(image.size),
                        'pixel_values_shape':list(inputs['pixel_values'].shape)}
                    if 'image_grid_thw' in inputs:
                        grid=inputs['image_grid_thw'].tolist();result['image_grid_thw']=grid
                        result['processor_output_wh']=[grid[0][2]*processor.patch_size,grid[0][1]*processor.patch_size]
                    else:
                        result['processor_output_wh']=list(reversed(inputs['pixel_values'].shape[-2:]))
                        result['num_crops']=inputs['num_crops'].tolist() if hasattr(inputs['num_crops'],'tolist') else inputs['num_crops']
                    result['processed_tensor_sha256']=hashlib.sha256(inputs['pixel_values'].numpy().tobytes()).hexdigest()
                    probes.append(result)
        (OUT/'processor_dimensions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in probes),encoding='utf-8')
        dump(OUT/'processor_configs.json',{'transformers':transformers.__version__,'models':policies})
        audit['processor_probe']={'scope':'CPU_image_processors_only_no_weights_no_predictions',
                                  'pilot_rows':len(pilot),'records':len(probes),'policies':sorted({p['policy'] for p in probes})}
    assert all(sha(p)==value for p,value in before.items()), 'An input changed during the audit'
    dump(OUT/'summary.json',audit)
    print(json.dumps(audit,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
