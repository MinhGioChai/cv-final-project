"""Offline source inventory/feasibility, never an image-ready main manifest or freeze."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import yaml

from vlmbench.datasets.oxford_pet import parse_oxford_pet, read_pet_list
from vlmbench.datasets.repope_frame import parse_repope_frame
from vlmbench.datasets.tallyqa import parse_tallyqa
from vlmbench.datasets.vsr import parse_vsr
from vlmbench.io_utils import atomic_bytes, sha256_file, write_json
from vlmbench.sampling import SamplingError, stratified_sample
from vlmbench.source_audit import load_upstream, read_audit_config


def summarize(rows):
    image_counts = Counter((r.image_namespace, r.image_id) for r in rows)
    content = Counter((r.image_namespace, r.image_id, r.question_en, str(r.ground_truth)) for r in rows)
    within_category = Counter((r.category, r.image_namespace, r.image_id, r.question_en, str(r.ground_truth)) for r in rows)
    return {"rows": len(rows), "unique_image_refs": len(image_counts),
            "max_rows_per_image": max(image_counts.values(), default=0),
            "label_counts": dict(Counter(str(r.ground_truth) for r in rows)),
            "categories": dict(sorted(Counter(r.category for r in rows).items())),
            "duplicate_image_question_label_rows": sum(n - 1 for n in content.values()),
            "duplicate_within_category_rows": sum(n - 1 for n in within_category.values())}


def prepare(root: Path, *, config: Path, output: Path):
    proposal = yaml.safe_load(config.read_text(encoding="utf-8"))
    if proposal["frozen"] is not False:
        raise ValueError("Inventory requires an unfrozen proposal; does not authorize main inference")
    cache = root / "data/raw/main_metadata_v1"
    receipt_path = cache / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    source_pins = yaml.safe_load((root / "configs/data_sources_v1.yaml").read_text())['sources']
    if set(source_pins) != set(receipt['files']):raise ValueError("Source receipt differs from pinned source set")
    for key, item in receipt["files"].items():
        if any(item[field] != source_pins[key][field] for field in ('url', 'revision', 'sha256')):
            raise ValueError("Metadata receipt differs from source pins")
        if sha256_file(cache / item["file"]) != item["sha256"]:
            raise ValueError("Source archive/annotation checksum differs")
    for name, item in receipt["extracted"].items():
        if sha256_file(cache / name) != item["sha256"]:
            raise ValueError("Extracted metadata checksum differs")
    content, rep_receipt = load_upstream(read_audit_config(root / "configs/source_audit.yaml"), root=root, offline=True)
    variant = proposal["vsr_variant"]
    if variant not in {"random", "zeroshot"}:raise ValueError("Choose a VSR variant explicitly")
    frames = {
        "repope": parse_repope_frame(content, revision=rep_receipt["revision"]),
        "vsr": parse_vsr((cache / f"vsr_{variant}_test.jsonl").read_bytes(), variant=variant,
                         revision=receipt["files"][f"vsr_{variant}_test"]["revision"]),
        "tallyqa": parse_tallyqa((cache / "tallyqa_test.json").read_bytes(),
                                 revision=receipt["files"]["tallyqa_archive"]["revision"]),
        "oxford_pet": parse_oxford_pet((cache / "pet_test.txt").read_bytes(),
            revision="sha256:" + receipt["files"]["pet_annotations"]["sha256"], breeds=proposal["pet_breeds_proposed"])}
    registry_path = root / "data/pilot/image_exclusions.json"
    exclusions = json.loads(registry_path.read_text())["images"]
    excluded_ids = {(x["image_namespace"], x["image_id"]) for x in exclusions}
    inventory = {}
    for dataset, rows in frames.items():
        kept = [r for r in rows if (r.image_namespace, r.image_id) not in excluded_ids]
        path = cache / "candidate_frames" / f"{dataset}.jsonl"
        payload = ("".join(r.model_dump_json() + "\n" for r in kept)).encode("utf-8")
        if path.exists() and path.read_bytes() != payload:
            raise ValueError("Existing candidate frame differs; use a new acquisition/config version")
        if not path.exists():atomic_bytes(path, payload)
        inventory[dataset] = {"before_exclusions": summarize(rows), "after_exclusions": summarize(kept),
            "pilot_rows_excluded_by_image_id": len(rows) - len(kept),
            "frame_path": path.relative_to(root).as_posix(), "frame_sha256": sha256_file(path),
            "target_rows_proposed": proposal["targets"][dataset], "source_split": kept[0].source_split}
    rep = [r for r in frames["repope"] if (r.image_namespace, r.image_id) not in excluded_ids]
    pool = [{"source_row_id": r.source_row_id, "image_id": r.image_id, "category": r.category,
             "answer": r.ground_truth} for r in rep]
    caps = {}
    for cap in (1, 2):
        try:
            selected, report = stratified_sample(pool, size=proposal["targets"]["repope"], seed=proposal["seed"],
                                                  max_rows_per_image=cap)
            caps[str(cap)] = {"status": "feasible_for_this_seed_and_greedy_sampler", "image_cap": cap,
                             "selected": report["selected"], "quotas": report["quotas"],
                             "selected_source_ids_sha256": hashlib.sha256(json.dumps(
                                 [r['source_row_id'] for r in selected]).encode()).hexdigest()}
            selected_ids = {r['source_row_id'] for r in selected}
            caps[str(cap)]['selected_content_summary'] = summarize([r for r in rep if r.source_row_id in selected_ids])
        except SamplingError as e:
            caps[str(cap)] = {"status": "infeasible_for_this_sampler", "image_cap": cap,
                             "image_capacity_upper_bound": len({r.image_id for r in rep}) * cap,
                             "target": proposal["targets"]["repope"], "failed_stratum": e.report["failed_stratum"]}
    pet_test = read_pet_list((cache / "pet_test.txt").read_bytes())
    pet_train = read_pet_list((cache / "pet_trainval.txt").read_bytes())
    if {r['image'] for r in pet_test} & {r['image'] for r in pet_train}:
        raise ValueError("Pet official trainval/test overlap")
    extra_vsr = parse_vsr((cache / 'vsr_zeroshot_test.jsonl').read_bytes(), variant='zeroshot',
                         revision=receipt['files']['vsr_zeroshot_test']['revision'])
    result = {"schema_version": "main_inventory_v1", "frozen": False, "main_ready": False,
        "scope": "metadata feasibility only; not a sampled/materialized/QA-approved main manifest",
        "proposal_sha256": sha256_file(config), "source_receipt_sha256": sha256_file(receipt_path),
        "pilot_registry_sha256": sha256_file(registry_path), "pilot_images_excluded": len(excluded_ids),
        "datasets": inventory, "repope_image_cap_feasibility": caps,
        "pet_class_map_proposed": dict(zip(proposal['pet_breeds_proposed'], 'ABCDEFGH')),
        "pet_official_test_rows": len(pet_test), "pet_official_trainval_rows": len(pet_train),
        "pet_test_trainval_overlap": 0, "vsr_zeroshot_rows_observed": len(extra_vsr),
        "outstanding": ["Group confirms RePOPE image cap, VSR split and eight Pet classes before sampling/freeze",
            "Resolve/download only selected image references; verify SHA256 against pilot exclusions too",
            "Human image/label QA and EN-VI translation review", "Baseline metadata and main runner/freeze"],
        "human_approvals_created": 0, "images_materialized": 0, "inferences_run": 0}
    if output.exists() and json.loads(output.read_text()) != result:
        raise ValueError("Inventory output differs; use a new report version")
    if not output.exists():write_json(output, result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="configs/main_preparation_v1.yaml")
    p.add_argument("--output", default="reports/stage1/v8/main_inventory_v2.json")
    args = p.parse_args()
    report = prepare(Path.cwd(), config=Path(args.config), output=Path(args.output))
    print(json.dumps({"frozen": False, "datasets": {k:v['after_exclusions'] for k,v in report['datasets'].items()},
                      "repope_caps": report['repope_image_cap_feasibility']},indent=2))
