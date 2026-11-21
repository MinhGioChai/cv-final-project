"""Data QA, bounded pilot inference, and paired analysis of saved predictions."""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import sys

from pydantic import ValidationError

from .datasets.repope import BoundedClient, SourceError, load_pool, materialize
from .io_utils import atomic_bytes, manifest_bytes, read_config, read_manifest, sha256_file, write_json, write_manifest
from .qa import preflight_image, validate_manifest
from .sampling import SamplingError, stratified_sample
from .reviews import export_review, import_review, write_review_preview
from .source_audit import audit_rows, load_upstream, read_audit_config
from .environment import inspect_environment
from .pilot_runtime import run_pilot
from .portable import build_pilot_bundle
from .evaluate import evaluate_run, read_evaluation, read_predictions, seal_report
from .statistics import statistics_for_evaluation

LOG = logging.getLogger(__name__)


def _show(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _reserve_pilot_images(root: Path, rows: list) -> None:
    path = root / "data/pilot/image_exclusions.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"images": []}
    registry = {(item["image_namespace"], item["image_id"], item["image_sha256"]): item for item in previous["images"]}
    for row in rows:
        key = (row.metadata.get("image_namespace", row.source_dataset), row.image_id, row.image_sha256)
        registry[key] = {"image_namespace": key[0], "image_id": key[1], "image_sha256": key[2]}
    write_json(path, {"purpose": "Exclude every image ever used in pilot/preflight from final", "images": [registry[key] for key in sorted(registry)]})


def _prepare(args: argparse.Namespace, root: Path) -> int:
    config = read_config(root / args.config)
    report_dir = root / config.report_dir
    client = BoundedClient(config.max_download_mb * 1024 * 1024)
    pool, receipt = load_pool(config, root=root, client=client, offline=args.offline, refresh=args.refresh)
    retained = read_manifest(root / args.retain_manifest) if args.retain_manifest else []
    if args.retain_manifest and not retained:
        raise ValueError("Retained manifest cannot be empty")
    if retained:
        if len({row.sample_id for row in retained}) != len(retained) or len({row.source_row_id for row in retained}) != len(retained):
            raise ValueError("Retained manifest has duplicate sample/source row IDs")
        pool_by_id = {row["source_row_id"]: row for row in pool}
        for row in retained:
            candidate = pool_by_id.get(row.source_row_id)
            if (not candidate or row.source_dataset != "repope" or not row.is_pilot
                    or row.metadata.get("source_revision") != config.source_revision
                    or (row.image_id, row.question_en, row.ground_truth, row.category) != (
                        candidate["image_id"], candidate["question"], candidate["answer"], candidate["category"])):
                raise ValueError("Retained manifest does not match pinned RePOPE candidate pool")
    try:
        selected, sampling = stratified_sample(pool, size=config.sample_size, seed=config.seed, max_rows_per_image=config.max_rows_per_image,
                                               retained_source_ids={row.source_row_id for row in retained} if args.retain_manifest else None)
    except SamplingError as exc:
        write_json(report_dir / "sampling_feasibility_report.json", exc.report)
        raise
    retained_by_id = {row.source_row_id: row for row in retained}
    new_rows = materialize([row for row in selected if row["source_row_id"] not in retained_by_id], config, root=root, client=client, offline=args.offline)
    by_id = {row.source_row_id: row for row in retained + new_rows}
    rows = [by_id[candidate["source_row_id"]] for candidate in selected]
    if args.retain_manifest:
        sampling["retained_manifest"] = args.retain_manifest
        sampling["retained_manifest_sha256"] = sha256_file(root / args.retain_manifest)
    manifest_path = root / config.manifest
    if manifest_path.exists() and read_manifest(manifest_path) != rows:
        raise ValueError("Existing manifest differs from regenerated data; preserving it. Use a new manifest/report path for a new pilot version")
    validation = validate_manifest(rows, root=root, mode="pilot")
    write_json(report_dir / "validation_report.json", validation)
    if not validation["valid"]:
        raise ValueError(f"Pilot validation failed; see {config.report_dir}/validation_report.json")
    # Reserve before publishing a manifest so a later rerun never forgets exposed images.
    _reserve_pilot_images(root, rows)
    write_manifest(root / config.manifest, rows)
    write_json(report_dir / "source_report.json", receipt)
    write_json(report_dir / "sampling_report.json", sampling)
    review = io.StringIO(newline="")
    fields = ["sample_id", "image_id", "image_path", "category", "question_en", "ground_truth", "question_vi", "reviewer_1_status", "reviewer_2_status", "notes", "final_status"]
    writer = csv.DictWriter(review, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({"sample_id": row.sample_id, "image_id": row.image_id, "image_path": row.image_path,
                         "category": row.category, "question_en": row.question_en, "ground_truth": row.ground_truth,
                         "question_vi": row.question_vi, "reviewer_1_status": "pending", "reviewer_2_status": "pending", "final_status": "pending"})
    review_path = report_dir / "sample_review.csv"
    # Human edits must survive technical reruns. Never silently replace a review sheet.
    if not review_path.exists():
        atomic_bytes(review_path, review.getvalue().encode("utf-8-sig"))
    else:
        LOG.info("Preserving existing sample_review.csv; compare sample IDs if config changed")
    sample_lines = [
        "# Mẫu RePOPE thực — pilot/preflight", "",
        "Nhãn dưới đây là nhãn nguồn. Xem trạng thái dịch/QA trong manifest; bảng này không phải kết quả model.", "",
        "| Image ID | Nhóm | Câu hỏi EN | Nhãn nguồn | Ảnh local |", "|---|---|---|---|---|",
    ]
    for row in rows:
        link = Path(os.path.relpath(root / row.image_path, report_dir)).as_posix()
        question = row.question_en.replace("|", "\\|")
        sample_lines.append(f"| `{row.image_id}` | {row.category} | {question} | {row.ground_truth} | [Mở ảnh]({link}) |")
    sample_lines += ["", "Ảnh nằm trong `data/raw/` đã gitignore. Chạy lại `prepare-pilot` theo README để tải ở máy khác.",
                     "", "Bảng review: [sample_review.csv](sample_review.csv)."]
    atomic_bytes(report_dir / "samples.md", ("\n".join(sample_lines) + "\n").encode("utf-8"))
    _show({"stage": config.purpose, "manifest": config.manifest, "manifest_sha256": sha256_file(root / config.manifest),
           "sampling": sampling["selected"], "validation_valid": validation["valid"],
           "downloaded_bytes_this_run": client.downloaded_bytes,
           "translation_status": dict(Counter(row.translation_status for row in rows)),
           "qa_status": dict(Counter(row.qa_status for row in rows))})
    return 0


def _inspect(args: argparse.Namespace, root: Path) -> int:
    config = read_config(root / args.config)
    path = root / (args.manifest or config.manifest)
    if not path.exists():
        raise ValueError("No pilot manifest. Run: python -m vlmbench.cli prepare-pilot --config configs/pilot.yaml")
    rows = read_manifest(path)
    validation = validate_manifest(rows, root=root, mode="pilot")
    _show({"dataset": args.dataset, "n_rows": len(rows), "n_unique_images": validation["n_unique_images"],
           "image_preflight_valid": validation["valid"],
           "rows": [{"sample_id": row.sample_id, "image_id": row.image_id, "category": row.category,
                     "question_en": row.question_en, "ground_truth": row.ground_truth, "image_path": row.image_path} for row in rows[:args.limit]],
           "issues": validation["issues"]})
    return 0 if validation["valid"] else 1


def _validate(args: argparse.Namespace, root: Path) -> int:
    rows = read_manifest(root / args.manifest)
    pilot = read_manifest(root / args.pilot_manifest) if args.pilot_manifest else None
    report = validate_manifest(rows, root=root, mode=args.mode, pilot=pilot)
    if args.mode == "main":
        registry_path = root / "data/pilot/image_exclusions.json"
        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))["images"]
            ids = {(item["image_namespace"], item["image_id"]) for item in registry}
            hashes = {item["image_sha256"] for item in registry}
            for row in rows:
                if (row.metadata.get("image_namespace", row.source_dataset), row.image_id) in ids or row.image_sha256 in hashes:
                    report["issues"].append({"sample_id": row.sample_id, "code": "PILOT_REGISTRY_OVERLAP"})
            report["valid"] = not report["issues"]
    if args.output:
        write_json(root / args.output, report)
    _show(report)
    return 0 if report["valid"] else 1


def _distinct_paths(*paths: Path) -> None:
    resolved = [path.resolve() for path in paths]
    if len(resolved) != len(set(resolved)):
        raise ValueError("Input, output, report and audit paths must be distinct")


def _preserve_manifest(path: Path, rows: list) -> None:
    if path.exists() and path.read_bytes() != manifest_bytes(rows):
        raise ValueError("Existing output manifest differs; preserving it. Use a new output version/path")


def _audit_source(args: argparse.Namespace, root: Path) -> int:
    manifest, output, report_path = root / args.manifest, root / args.output, root / args.report
    _distinct_paths(manifest, output, report_path)
    rows = read_manifest(manifest)
    config = read_audit_config(root / args.config)
    content, receipt = load_upstream(config, root=root, offline=args.offline)
    verified, report = audit_rows(rows, content, receipt)
    report["input_manifest_sha256"] = sha256_file(manifest)
    if report["all_matched"]:
        _preserve_manifest(output, verified)
        write_manifest(output, verified)
        report["output_manifest_sha256"] = sha256_file(output)
    write_json(report_path, report)
    _show({key: report[key] for key in ("all_matched", "n_rows", "status_counts", "upstream_revision", "upstream_annotation_rows")})
    return 0 if report["all_matched"] else 1


def _export_review(args: argparse.Namespace, root: Path) -> int:
    manifest, dictionary = root / args.manifest, root / args.dictionary
    output, report = root / args.output, root / args.report
    _distinct_paths(manifest, dictionary, output, output.with_suffix(".context.json"), report)
    rows = read_manifest(manifest)
    summary = export_review(rows, manifest_path=manifest, dictionary_path=dictionary, output=output)
    write_review_preview(rows, review_path=output, output=report.with_name("translation_preview.md"), root=root)
    write_json(report, summary)
    _show(summary)
    return 0


def _import_review(args: argparse.Namespace, root: Path) -> int:
    manifest, review = root / args.manifest, root / args.review
    output, audit_path = root / args.output, root / args.audit
    _distinct_paths(manifest, review, review.with_suffix(".context.json"), output, audit_path)
    source_rows = read_manifest(manifest)
    for row in source_rows:
        if preflight_image(root / row.image_path)["sha256"] != row.image_sha256:
            raise ValueError(f"Image changed since review export for {row.sample_id}; restore original image or create a new reviewed version")
    updated, audit = import_review(source_rows, manifest_path=manifest, review_path=review, operator=args.operator)
    audit["output_manifest_sha256"] = hashlib.sha256(manifest_bytes(updated)).hexdigest()
    _preserve_manifest(output, updated)
    if audit_path.exists():
        existing = json.loads(audit_path.read_text(encoding="utf-8"))
        if (existing.get("run_key") != audit["run_key"] or existing.get("events") != audit["events"]
                or existing.get("output_manifest_sha256") != audit["output_manifest_sha256"]):
            raise ValueError("Existing audit differs; preserve history and use a new audit/output version")
        audit = existing
    if not args.dry_run:
        # Persist the expected output hash and full decisions before publishing the manifest.
        # A retry can finish a missing manifest while reusing this immutable audit receipt.
        if not audit_path.exists():
            write_json(audit_path, audit)
        write_manifest(output, updated)
    _show({"dry_run": args.dry_run, "run_key": audit["run_key"], "n_rows": audit["n_rows"],
           "translation_status": audit["translation_status"], "qa_status": audit["qa_status"],
           "output_manifest_sha256": audit["output_manifest_sha256"]})
    return 0


def _doctor(args: argparse.Namespace, root: Path) -> int:
    report = inspect_environment()
    if args.output:
        write_json(root / args.output, report)
    _show(report)
    return 0


def _infer_pilot(args: argparse.Namespace, root: Path) -> int:
    output = root / (args.output or f"results/pilot/{args.platform}/{args.model}.jsonl")
    summary = run_pilot(root=root, config_path=root / args.config, alias=args.model, platform_name=args.platform,
                        output=output, limit=args.limit, languages=tuple(args.languages), dry_run=args.dry_run,
                        resume=args.resume, retry_failed=args.retry_failed)
    _show(summary)
    return 1 if summary.get("failed") or summary.get("missing") else 0


def _package_pilot(args: argparse.Namespace, root: Path) -> int:
    _show(build_pilot_bundle(root, root / args.output, args.manifest))
    return 0


def _infer_gemma_trace(args: argparse.Namespace, root: Path) -> int:
    from .gemma_diagnostic import run_gemma_pilot
    summary = run_gemma_pilot(root=root, config_path=root / args.config, output=root / args.output,
                              limit=args.limit, platform_name=args.platform, dry_run=args.dry_run,
                              resume=args.resume, retry_failed=args.retry_failed, offline=not args.online)
    _show(summary)
    return 1 if summary.get("failed") or summary.get("missing") or summary.get("invalid") else 0


def _export_label_qa(args: argparse.Namespace, root: Path) -> int:
    from .label_qa import export_label_qa
    manifest, output, html = root / args.manifest, root / args.output, root / args.html
    _distinct_paths(manifest, output, html)
    if output.suffix != ".json" or html.suffix != ".html":
        raise ValueError("Use .json review and .html view outputs")
    _show(export_label_qa(read_manifest(manifest), manifest_path=manifest, root=root,
                          output=output, html_path=html))
    return 0


def _import_label_qa(args: argparse.Namespace, root: Path) -> int:
    from .label_qa import import_label_qa
    manifest, review, output, audit_path = (root / args.manifest, root / args.review,
                                           root / args.output, root / args.audit)
    _distinct_paths(manifest, review, output, audit_path)
    if output.suffix != ".csv" or audit_path.suffix != ".json":
        raise ValueError("Use .csv manifest output and .json audit")
    updated, audit = import_label_qa(read_manifest(manifest), manifest_path=manifest,
                                     root=root, review_path=review, operator=args.operator)
    audit["output_manifest_sha256"] = hashlib.sha256(manifest_bytes(updated)).hexdigest()
    _preserve_manifest(output, updated)
    if audit_path.exists():
        old = json.loads(audit_path.read_text(encoding="utf-8"))
        if (old.get("run_key") != audit["run_key"] or old.get("events") != audit["events"]
                or old.get("output_manifest_sha256") != audit["output_manifest_sha256"]):
            raise ValueError("Existing QA audit differs; use new output/audit versions")
        audit = old
    if not args.dry_run:
        if not audit_path.exists():
            write_json(audit_path, audit)
        write_manifest(output, updated)
    _show({"dry_run": args.dry_run, "run_key": audit["run_key"],
           "qa_status": audit["qa_status"], "translation_status": audit["translation_status"]})
    return 0


def _write_analysis_outputs(outputs: list[tuple[Path, bytes]]) -> None:
    for path, content in outputs:
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f"Analysis output already exists with different content: {path.name}. Use a new output version")
    for path, content in outputs:
        if not path.exists():
            atomic_bytes(path, content)


def _analysis_json(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _format_percent(value: float | None) -> str:
    return f"{100 * value:.2f}%" if value is not None else "undefined"


def _evaluate_saved(args: argparse.Namespace, root: Path) -> int:
    manifest, predictions, output = root / args.manifest, root / args.predictions, root / args.output
    selection_path = root / args.selection if args.selection else None
    markdown = root / args.report if args.report else None
    paths = [manifest, predictions, output] + ([selection_path] if selection_path else []) + ([markdown] if markdown else [])
    _distinct_paths(*paths)
    if output.suffix != ".json" or markdown and markdown.suffix != ".md":
        raise ValueError("Use a .json analysis output and a .md optional report")
    rows = read_manifest(manifest)
    records = read_predictions(predictions)
    selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path else None
    if selection is not None and not isinstance(selection, dict):
        raise ValueError("Selection must be a JSON object")
    report = evaluate_run(rows, records, selection)
    report["inputs"] = {"manifest": args.manifest, "manifest_sha256": sha256_file(manifest),
                        "predictions": args.predictions, "predictions_sha256": sha256_file(predictions),
                        "selection": args.selection, "selection_sha256": sha256_file(selection_path) if selection_path else None}
    report["implementation"] = {name: sha256_file(Path(__file__).parent / name)
                                for name in ("evaluate.py", "parse.py")}
    report = seal_report(report)
    outputs = [(output, _analysis_json(report))]
    if markdown:
        lines = ["# Paired evaluation of saved predictions", "", f"Evaluation scope is {report['scope']}.",
                 "", f"Selected rows {report['n_selected_rows']}. Expected inferences {report['expected_inferences']}. Raw attempts {report['total_raw_attempts']}.",
                 "", "| Dataset | Task | EN accuracy | VI accuracy | Jointly valid pairs | Disagreement |",
                 "|---|---|---|---|---|---|"]
        for group in report["groups"]:
            lines.append(f"| {group['dataset']} | {group['task']} | {_format_percent(group['languages']['en']['accuracy'])} | "
                         f"{_format_percent(group['languages']['vi']['accuracy'])} | {group['paired']['jointly_valid']} | "
                         f"{_format_percent(group['paired']['disagreement_rate'])} |")
        primary = report["primary_repope"]
        lines += ["", "## RePOPE jointly valid negatives", "",
                  f"Eligible pairs {primary['jointly_valid_negative_pairs']}. Image clusters {primary['complete_case_image_clusters']}. Excluded pairs {primary['excluded_negative_pairs']}.",
                  "", f"FPR EN {_format_percent(primary['fpr_en'])}. FPR VI {_format_percent(primary['fpr_vi'])}.",
                  "", f"Delta FPR VI minus EN is {primary['delta_fpr_pp']} percentage points.",
                  "", "Accuracy uses all expected rows and scores invalid, failed and missing predictions as incorrect.",
                  "", "Image QA and translation status counts are recorded in the JSON report.",
                  "", "Each paired row records its selected raw source line and attempt for auditing."]
        outputs.append((markdown, ("\n".join(lines) + "\n").encode("utf-8")))
    _write_analysis_outputs(outputs)
    _show({"output": args.output, "scope": report["scope"], "selected_rows": report["n_selected_rows"],
           "expected_inferences": report["expected_inferences"], "primary_repope": report["primary_repope"]})
    return 0


def _statistics_saved(args: argparse.Namespace, root: Path) -> int:
    source, output = root / args.evaluation, root / args.output
    _distinct_paths(source, output)
    if output.suffix != ".json":
        raise ValueError("Statistics output must use .json")
    evaluation = read_evaluation(source)
    report = statistics_for_evaluation(evaluation, n_resamples=args.resamples, seed=args.seed)
    report["inputs"] = {"evaluation": args.evaluation, "evaluation_file_sha256": sha256_file(source),
                        "statistics_implementation_sha256": sha256_file(Path(__file__).with_name("statistics.py"))}
    _write_analysis_outputs([(output, _analysis_json(report))])
    _show({"output": args.output, "scope": report["scope"], "primary_repope": report["primary_repope"]})
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="VLM EN/VI data/QA tools and bounded local/Colab/Kaggle GPU pilot")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root (default: current directory)")
    parser.add_argument("--verbose", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-pilot", help="Fetch bounded RePOPE metadata and prepare a tiny engineering manifest")
    prepare.add_argument("--config", default="configs/pilot.yaml")
    prepare.add_argument("--offline", action="store_true", help="Use a complete local snapshot; never access network")
    prepare.add_argument("--refresh", action="store_true", help="Refresh source metadata/temporary image URLs, enforcing pinned revision")
    prepare.add_argument("--retain-manifest", help="Keep every row in an existing pilot and fill remaining target strata without replacing it")
    prepare.set_defaults(func=_prepare)
    inspect = commands.add_parser("inspect", help="Inspect cached pilot rows and verify all referenced images")
    inspect.add_argument("--dataset", choices=["repope"], default="repope")
    inspect.add_argument("--config", default="configs/pilot.yaml")
    inspect.add_argument("--manifest")
    inspect.add_argument("--limit", type=int, default=10)
    inspect.set_defaults(func=_inspect)
    validate = commands.add_parser("validate", help="Validate schema/images and pilot/main QA/leakage gates")
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--mode", choices=["pilot", "main"], default="pilot")
    validate.add_argument("--pilot-manifest", help="Mandatory explicit pilot manifest for main leakage checks")
    validate.add_argument("--output", help="Write a JSON validation report")
    validate.set_defaults(func=_validate)
    audit = commands.add_parser("audit-source", help="Compare manifest questions/labels with pinned upstream RePOPE JSONL")
    audit.add_argument("--manifest", required=True)
    audit.add_argument("--config", default="configs/source_audit.yaml")
    audit.add_argument("--output", required=True, help="New source-verified manifest; never modifies source labels")
    audit.add_argument("--report", required=True)
    audit.add_argument("--offline", action="store_true")
    audit.set_defaults(func=_audit_source)
    export = commands.add_parser("export-translation-review", help="Generate pending template drafts and a bound human review CSV")
    export.add_argument("--manifest", required=True)
    export.add_argument("--dictionary", default="data/dictionaries/object_en_vi.csv")
    export.add_argument("--output", required=True)
    export.add_argument("--report", required=True)
    export.set_defaults(func=_export_review)
    review = commands.add_parser("import-translation-review", help="Validate explicit review decisions and create a versioned manifest + audit receipt")
    review.add_argument("--manifest", required=True, help="Exact original manifest used to export this review sheet")
    review.add_argument("--review", required=True)
    review.add_argument("--output", required=True)
    review.add_argument("--audit", required=True)
    review.add_argument("--operator", required=True, help="Import operator ID; does not confer reviewer approval")
    review.add_argument("--dry-run", action="store_true", help="Validate and summarize; write no output/audit")
    review.set_defaults(func=_import_review)
    doctor = commands.add_parser("doctor", help="Inventory GPU driver and Python packages without downloading or loading models")
    doctor.add_argument("--output", help="Write an environment inventory JSON")
    doctor.set_defaults(func=_doctor)
    infer = commands.add_parser("infer-pilot", help="Bounded real inference, 1–30 pilot rows, same config on local/Colab/Kaggle")
    infer.add_argument("--model", choices=["qwen", "gemma"], required=True)
    infer.add_argument("--platform", choices=["local", "colab", "kaggle"], required=True)
    infer.add_argument("--config", default="configs/inference/pilot_4bit.yaml")
    infer.add_argument("--output")
    infer.add_argument("--limit", type=int, default=2, help="Number of shared image/question rows; 2 languages by default")
    infer.add_argument("--languages", nargs="+", choices=["en", "vi"], default=["en", "vi"])
    infer.add_argument("--dry-run", action="store_true", help="Validate and show queue without loading/downloading models or writing predictions")
    infer.add_argument("--resume", action="store_true")
    infer.add_argument("--retry-failed", action="store_true")
    infer.set_defaults(func=_infer_pilot)
    trace = commands.add_parser("infer-gemma-trace", help="Gemma NF4/BF16 pilot with token/raw-logit traces; cached files only by default")
    trace.add_argument("--platform", choices=["local", "colab", "kaggle"], default="local")
    trace.add_argument("--config", default="configs/inference/gemma_bf16_trace_v1.yaml")
    trace.add_argument("--output", required=True)
    trace.add_argument("--limit", type=int, default=2)
    trace.add_argument("--dry-run", action="store_true")
    trace.add_argument("--resume", action="store_true")
    trace.add_argument("--retry-failed", action="store_true")
    trace.add_argument("--online", action="store_true", help="Allow Hub downloads; otherwise local cache only")
    trace.set_defaults(func=_infer_gemma_trace)
    label_export = commands.add_parser("export-label-qa", help="Create offline image/label QA view without changing translation approvals")
    label_export.add_argument("--manifest", required=True)
    label_export.add_argument("--output", required=True, help="Pending review .json")
    label_export.add_argument("--html", required=True, help="Self-contained image review .html")
    label_export.set_defaults(func=_export_label_qa)
    label_import = commands.add_parser("import-label-qa", help="Validate explicit human image/label decisions into a new manifest/audit")
    label_import.add_argument("--manifest", required=True)
    label_import.add_argument("--review", required=True)
    label_import.add_argument("--output", required=True)
    label_import.add_argument("--audit", required=True)
    label_import.add_argument("--operator", required=True)
    label_import.add_argument("--dry-run", action="store_true")
    label_import.set_defaults(func=_import_label_qa)
    bundle = commands.add_parser("package-pilot", help="Create a local ZIP with code, notebooks, manifest and 30 images for private team use")
    bundle.add_argument("--manifest", default="data/pilot/stage1_v3/pilot_manifest.csv")
    bundle.add_argument("--output", default="exports/vlmbench_pilot.zip")
    bundle.set_defaults(func=_package_pilot)
    evaluate = commands.add_parser("evaluate", help="Evaluate one saved run against an explicit expected EN/VI grid")
    evaluate.add_argument("--manifest", required=True)
    evaluate.add_argument("--predictions", required=True, help="One existing pilot JSONL run including retry history")
    evaluate.add_argument("--selection", help="JSON plan/summary with sample_ids; default evaluates every manifest row")
    evaluate.add_argument("--output", required=True, help="New evaluation .json report")
    evaluate.add_argument("--report", help="Optional .md summary")
    evaluate.set_defaults(func=_evaluate_saved)
    stats = commands.add_parser("statistics", help="Paired image-cluster percentile bootstrap from a saved evaluation")
    stats.add_argument("--evaluation", required=True)
    stats.add_argument("--output", required=True)
    stats.add_argument("--resamples", type=int, default=5000)
    stats.add_argument("--seed", type=int, default=42)
    stats.set_defaults(func=_statistics_saved)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    if args.command == "inspect" and args.limit < 1:
        parser.error("--limit must be positive")
    try:
        return args.func(args, args.root.resolve())
    except (SourceError, SamplingError, ValueError, ValidationError, OSError, KeyError) as exc:
        LOG.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
