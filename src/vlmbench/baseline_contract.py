"""Versioned P0 baseline contract; historical manifests and pilot schemas stay intact."""
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from string import Formatter
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
import yaml

from .datasets.candidates import Candidate
from .io_utils import read_manifest, sha256_file
from .main_review_v2 import MainDecision, POLICY, SLOTS, _validate_round
from .qa import validate_manifest
from .reviews import canonical_hash, row_hash
from .schemas import ManifestRow
from .translate import require_review_identity

Hex40 = Annotated[str, Field(pattern=r'^[0-9a-f]{40}$')]
Hex64 = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
TASKS = {'repope': 'object_existence', 'vsr': 'spatial', 'tallyqa': 'counting', 'oxford_pet': 'fine_grained'}
MODEL_IDS = {'qwen': 'Qwen/Qwen2.5-VL-3B-Instruct', 'gemma': 'google/gemma-3-4b-it'}
PET_LABELS = dict(zip('ABCDEFGH', ['American Bulldog', 'American Pit Bull Terrier', 'Basset Hound',
    'Beagle', 'Boxer', 'Chihuahua', 'English Cocker Spaniel', 'English Setter']))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)


class ModelSpec(StrictModel):
    model_id: str = Field(min_length=1)
    revision: Hex40
    processor_revision: Hex40
    tokenizer_revision: Hex40
    precision: Literal['nf4_fp16', 'nf4_bf16']
    attention: Literal['eager', 'sdpa'] = 'eager'

    @model_validator(mode='after')
    def revisions(self) -> Self:
        if len({self.revision, self.processor_revision, self.tokenizer_revision}) != 1:
            raise ValueError('Current adapters require model/processor/tokenizer at the same pinned revision')
        return self


class Generation(StrictModel):
    do_sample: Literal[False] = False
    batch_size: Literal[1] = 1
    max_new_tokens: int = Field(default=8, ge=1, le=32)


class Preprocess(StrictModel):
    policy_id: Literal['rgb_thumbnail_lanczos_v1'] = 'rgb_thumbnail_lanczos_v1'
    image_max_edge: int = Field(default=512, ge=224, le=1024)
    qwen_min_pixels: int = Field(default=200704, ge=784)
    qwen_max_pixels: int = Field(default=401408, ge=784)

    @model_validator(mode='after')
    def bounds(self) -> Self:
        if self.qwen_min_pixels > self.qwen_max_pixels:
            raise ValueError('Invalid Qwen pixel bounds')
        return self


class BaselineConfig(StrictModel):
    schema_version: Literal['baseline_v1']
    experiment_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    frozen: bool = False
    freeze_receipt: str | None = None
    seed: Literal[42] = 42
    manifests: list[str] = Field(min_length=1)
    source_selection: str
    pilot_manifest: str
    pilot_exclusions: str
    prompts: str
    targets: dict[str, StrictInt]
    languages: list[Literal['en', 'vi']]
    models: dict[str, ModelSpec]
    generation: Generation = Field(default_factory=Generation)
    preprocess: Preprocess = Field(default_factory=Preprocess)

    @model_validator(mode='after')
    def scope(self) -> Self:
        if self.languages != ['en', 'vi'] or set(self.models) != {'qwen', 'gemma'}:
            raise ValueError('P0 baseline requires paired en/vi and both qwen/gemma')
        if set(self.targets) != set(TASKS) or any(v < 1 for v in self.targets.values()):
            raise ValueError('Positive targets required for exactly the four P0 datasets')
        if len(self.manifests) != len(set(self.manifests)):
            raise ValueError('Manifest paths must be distinct')
        for alias, spec in self.models.items():
            if spec.model_id != MODEL_IDS[alias] or spec.precision != ('nf4_fp16' if alias == 'qwen' else 'nf4_bf16'):
                raise ValueError('Keep the approved model families and explicit per-model precision')
        return self


class FreezeReceipt(StrictModel):
    schema_version: Literal['baseline_freeze_v1']
    protocol_hash: Hex64
    approved_by: str
    approved_at: str
    notes: str = Field(min_length=1)


class PromptSet(StrictModel):
    prompt_version: str = Field(min_length=1)
    tasks: dict[str, dict[str, str]]

    @model_validator(mode='after')
    def templates(self) -> Self:
        if set(self.tasks) != set(TASKS.values()):
            raise ValueError('Prompts must cover exactly the four P0 tasks')
        for task, languages in self.tasks.items():
            if set(languages) != {'en', 'vi'}:
                raise ValueError('Each task needs en/vi templates')
            for template in languages.values():
                fields = []
                for _, name, fmt, conversion in Formatter().parse(template):
                    if name is not None:
                        if name not in {'question', 'candidates'} or fmt or conversion:
                            raise ValueError('Only plain question/candidates placeholders are supported')
                        fields.append(name)
                if 'question' not in fields or (task == 'fine_grained' and 'candidates' not in fields):
                    raise ValueError('Preserve the manifest question, and Pet candidate labels, in both languages')
        return self


class Cell(StrictModel):
    cell_id: Hex64
    sample_id: str
    model: Literal['qwen', 'gemma']
    language: Literal['en', 'vi']
    prompt_variant: Literal['baseline'] = 'baseline'
    image_variant: Literal['original'] = 'original'
    prompt_text: str
    prompt_hash: Hex64
    source_row_sha256: Hex64


def inside(root, path):
    root = root.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Paths must stay inside the project')
    return target


def render_prompt(row, language, prompts):
    if row.source_dataset not in TASKS or row.task != TASKS[row.source_dataset]:
        raise ValueError('Dataset/task routing is outside P0')
    labels = row.metadata.get('candidate_labels', {})
    if row.task == 'fine_grained' and labels != PET_LABELS:
        raise ValueError('Pet must retain the fixed eight-breed A-H mapping')
    return prompts.tasks[row.task][language].format(question=getattr(row, 'question_' + language),
        candidates='; '.join(f'{k}: {v}' for k, v in PET_LABELS.items()))


def review_proof(row):
    proof = row.metadata.get('main_review', {})
    if proof.get('schema_version') != 'main_review_v2' or proof.get('policy') != POLICY:
        return False
    try:
        decision = MainDecision.model_validate(proof['decision'])
        if decision.sample_id != row.sample_id or decision.question_vi != row.question_vi:
            return False
        owners = [_validate_round(row, getattr(decision, s), row.question_vi) for s in SLOTS]
        return bool(owners[0] and owners[1] and owners[0] != owners[1] and all(
            getattr(decision, s).translation.status == getattr(decision, s).image_qa.status == 'approved' for s in SLOTS))
    except (ValueError, KeyError, TypeError):
        return False


@dataclass
class BaselinePlan:
    root: Path
    config_path: Path
    config: BaselineConfig
    rows: list[ManifestRow]
    cells: list[Cell]
    protocol: dict
    protocol_hash: str
    issues: list[dict]
    freeze_sha256: str | None

    def summary(self):
        return {'schema_version': 'baseline_plan_v1', 'scope': 'main_baseline_preflight_not_inference',
            'protocol_hash': self.protocol_hash, 'frozen': self.config.frozen,
            'execution_ready': not self.issues, 'selected_rows': len(self.rows),
            'unique_images': len({(r.metadata.get('image_namespace', r.source_dataset), r.image_id) for r in self.rows}),
            'expected_inferences': len(self.cells), 'expected_per_model': dict(Counter(c.model for c in self.cells)),
            'datasets': dict(Counter(r.source_dataset for r in self.rows)),
            'qa_status': dict(Counter(r.qa_status for r in self.rows)),
            'translation_status': dict(Counter(r.translation_status for r in self.rows)),
            'blocking_counts': dict(Counter(i['code'] for i in self.issues)),
            'grid_sha256': canonical_hash([c.model_dump() for c in self.cells]),
            'inputs_sha256': self.protocol['inputs_sha256'], 'freeze_sha256': self.freeze_sha256,
            'model_inferences': 0, 'new_human_approvals': 0}


def build_plan(root, config_path):
    root = root.resolve()
    config_path = inside(root, config_path)
    config = BaselineConfig.model_validate(yaml.safe_load(config_path.read_text(encoding='utf-8')))
    paths = [inside(root, p) for p in config.manifests]
    rows = sorted([row for path in paths for row in read_manifest(path)], key=lambda r: r.sample_id)
    if not rows or len({r.sample_id for r in rows}) != len(rows):
        raise ValueError('Nonempty unique main sample IDs required')
    if dict(Counter(r.source_dataset for r in rows)) != config.targets:
        raise ValueError('Manifest counts differ from declared dataset targets')
    source_path = inside(root, config.source_selection)
    candidates = [Candidate.model_validate_json(s) for s in source_path.read_text(encoding='utf-8').splitlines() if s.strip()]
    source = {r.sample_id: r for r in candidates}
    if len(source) != len(candidates) or set(source) != {r.sample_id for r in rows}:
        raise ValueError('Main IDs must equal the complete pinned source selection')
    identities, digests = {}, {}
    for row in rows:
        original = source[row.sample_id]
        for field in ['source_dataset', 'source_split', 'source_row_id', 'image_id', 'task', 'category', 'question_en', 'ground_truth']:
            if type(getattr(row, field)) is not type(getattr(original, field)) or getattr(row, field) != getattr(original, field):
                raise ValueError('Protected source field changed: ' + field)
        if any(row.metadata.get(k) != getattr(original, k) for k in ['source_revision', 'source_record_sha256', 'image_namespace']):
            raise ValueError('Source provenance changed')
        inside(root, row.image_path)
        identity = (original.image_namespace, original.image_id)
        if identity in identities and identities[identity] != row.image_sha256:
            raise ValueError('One image identity has multiple byte versions')
        if row.image_sha256 in digests and digests[row.image_sha256] != identity:
            raise ValueError('Different image identities share duplicate bytes')
        identities[identity] = row.image_sha256
        digests[row.image_sha256] = identity
    pilot_path = inside(root, config.pilot_manifest)
    exclusions_path = inside(root, config.pilot_exclusions)
    pilot = read_manifest(pilot_path)
    issues = validate_manifest(rows, root=root, mode='main', pilot=pilot)['issues']
    exclusions = json.loads(exclusions_path.read_text(encoding='utf-8'))['images']
    excluded_ids = {(i['image_namespace'], i['image_id']) for i in exclusions}
    excluded_hashes = {i['image_sha256'] for i in exclusions}
    for row in rows:
        if (row.metadata['image_namespace'], row.image_id) in excluded_ids or row.image_sha256 in excluded_hashes:
            issues.append({'sample_id': row.sample_id, 'code': 'PILOT_REGISTRY_OVERLAP'})
        if row.qa_status == row.translation_status == 'approved' and not review_proof(row):
            issues.append({'sample_id': row.sample_id, 'code': 'TWO_REVIEWER_PROOF_REQUIRED'})
    prompts_path = inside(root, config.prompts)
    prompts = PromptSet.model_validate(yaml.safe_load(prompts_path.read_text(encoding='utf-8')))
    cells = []
    for model in sorted(config.models):
        for row in rows:
            for language in config.languages:
                prompt = render_prompt(row, language, prompts)
                identity = dict(sample_id=row.sample_id, model=model, language=language,
                                prompt_variant='baseline', image_variant='original')
                cells.append(Cell(**identity, cell_id=canonical_hash(identity), prompt_text=prompt,
                    prompt_hash=hashlib.sha256(prompt.encode('utf-8')).hexdigest(), source_row_sha256=row_hash(row)))
    inputs = paths + [config_path, source_path, pilot_path, exclusions_path, prompts_path]
    source_files = [Path(__file__).with_name(name + '.py') for name in (
        'baseline_contract', 'baseline_runtime', 'parse', 'pilot_runtime', 'gemma_diagnostic',
        'main_review_v2', 'main_review', 'translate', 'qa', 'schemas', 'io_utils', 'reviews',
        'environment', 'pilot_launcher')]
    protocol = {'schema_version': 'baseline_protocol_v1', 'settings': config.model_dump(),
        'prompt_version': prompts.prompt_version, 'inputs_sha256': {p.relative_to(root).as_posix(): sha256_file(p) for p in inputs},
        'implementation_sha256': {p.name: sha256_file(p) for p in source_files},
        'grid_sha256': canonical_hash([c.model_dump() for c in cells]),
        'external_labels': {'object_existence': ['YES', 'NO'], 'spatial': ['TRUE', 'FALSE'],
                            'counting': 'nonnegative_integer', 'fine_grained': PET_LABELS},
        'processor_policy': {'qwen': {'min_pixels': config.preprocess.qwen_min_pixels,
                                      'max_pixels': config.preprocess.qwen_max_pixels, 'use_fast': 'checkpoint_default'},
                             'gemma': {'do_pan_and_scan': False, 'use_fast': False}},
        'stored_binary_labels': {'TRUE': 'yes', 'FALSE': 'no'}}
    protocol_hash = canonical_hash(protocol)
    freeze_hash = None
    if not config.frozen:
        issues.append({'code': 'BASELINE_NOT_FROZEN'})
    if not config.freeze_receipt:
        issues.append({'code': 'FREEZE_RECEIPT_REQUIRED'})
    else:
        freeze_path = inside(root, config.freeze_receipt)
        try:
            receipt = FreezeReceipt.model_validate_json(freeze_path.read_text(encoding='utf-8'))
            require_review_identity(receipt.approved_by, receipt.approved_at, field='baseline freeze')
            if receipt.protocol_hash != protocol_hash:
                raise ValueError('Freeze belongs to another protocol')
            freeze_hash = sha256_file(freeze_path)
        except (ValueError, OSError):
            issues.append({'code': 'FREEZE_RECEIPT_INVALID_OR_MISSING'})
    return BaselinePlan(root, config_path, config, rows, cells, protocol, protocol_hash, issues, freeze_hash)
