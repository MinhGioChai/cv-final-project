"""Observe the new MAIN image helper feeding pinned real processors on approved PILOT images, CPU only."""
import importlib.metadata
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))


def main():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    from transformers import AutoProcessor
    import torch
    from vlmbench.baseline_contract import BaselineConfig,PromptSet,render_prompt
    from vlmbench.baseline_runtime import prepare_main_image
    from vlmbench.image_ab import ObservedProcessor
    from vlmbench.io_utils import read_manifest,sha256_file,write_json
    import yaml
    assert importlib.metadata.version('transformers')=='4.57.1'
    torch.set_num_threads(1)
    cfg=BaselineConfig.model_validate(yaml.safe_load((ROOT/'configs/baseline_v3_option_b_v1.yaml').read_text(encoding='utf-8')))
    prompts=PromptSet.model_validate(yaml.safe_load((ROOT/cfg.prompts).read_text(encoding='utf-8')))
    rows=sorted(read_manifest(ROOT/cfg.pilot_manifest),key=lambda r:r.sample_id)[:2]
    assert all(r.is_pilot and r.qa_status==r.translation_status=='approved' for r in rows)
    audit=json.loads((ROOT/'reports/audits/2026-11-24/processor_configs.json').read_text())['models']
    records=[];configs={}
    for alias,spec in cfg.models.items():
        path=ROOT/'.cache/huggingface/hub'/('models--'+spec.model_id.replace('/','--'))/'snapshots'/spec.revision
        digest=sha256_file(path/'preprocessor_config.json')
        assert digest==audit[alias]['preprocessor_config_sha256']
        kwargs=({'min_pixels':cfg.preprocess.qwen_min_pixels,'max_pixels':cfg.preprocess.qwen_max_pixels}
                if alias=='qwen' else {'do_pan_and_scan':False,'use_fast':False})
        processor=AutoProcessor.from_pretrained(str(path),local_files_only=True,trust_remote_code=False,**kwargs)
        observer=ObservedProcessor(processor)
        configs[alias]={'revision':spec.processor_revision,'processor_class':type(processor).__name__,
            'image_processor_class':type(processor.image_processor).__name__,
            'image_processor_settings':processor.image_processor.to_dict(),
            'preprocessor_config_sha256':digest,'passed_kwargs':kwargs}
        for row in rows:
            image,wh=prepare_main_image(ROOT/row.image_path,cfg.preprocess)
            received=list(image.size)
            prompt=render_prompt(row,'en',prompts)
            text=observer.apply_chat_template([{'role':'user','content':[{'type':'image'},{'type':'text','text':prompt}]}],
                tokenize=False,add_generation_prompt=True)
            observer(text=[text],images=[image],return_tensors='pt',add_special_tokens=False)
            assert received==wh
            records.append({'model':alias,'sample_id':row.sample_id,'is_approved_pilot':True,
                'source_sha256':row.image_sha256,'original_wh':wh,'processor_received_wh':received,
                'policy_id':cfg.preprocess.policy_id,'mode':image.mode,**observer.last})
    write_json(Path(__file__).with_name('processor_input_evidence.json'),{
        'scope':'Real CPU processors fed by the new MAIN preprocessing helper on approved PILOT images; not M3/GPU inference',
        'model_weights_loaded':False,'new_model_generations':0,'configs':configs,'records':records})
    print(json.dumps({'CPU_processor_observations':len(records),'records':records},indent=2))


if __name__=='__main__':main()
