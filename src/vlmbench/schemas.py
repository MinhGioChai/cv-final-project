"""Strict manifest contract; unreviewed translations are allowed only in pilot mode."""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

NonEmpty = Annotated[str, Field(min_length=1)]
Task = Literal["object_existence", "spatial", "counting", "fine_grained", "negation"]
ReviewStatus = Literal["pending", "approved", "rejected"]
TranslationStatus = Literal["missing", "requires_review", "approved", "rejected"]


class ManifestRow(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sample_id: NonEmpty
    source_dataset: NonEmpty
    source_split: NonEmpty
    source_row_id: NonEmpty
    image_id: NonEmpty
    image_path: NonEmpty
    image_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    task: Task
    category: NonEmpty
    question_en: NonEmpty
    question_vi: str
    ground_truth: str | StrictInt
    ground_truth_source: NonEmpty
    qa_status: ReviewStatus
    translation_status: TranslationStatus
    is_pilot: bool
    sampling_seed: int
    metadata: dict[str, Any]

    @model_validator(mode="after")
    def check_semantics(self) -> Self:
        if not self.question_en.strip():
            raise ValueError("question_en cannot be blank")
        if self.translation_status in {"requires_review", "approved"} and not self.question_vi.strip():
            raise ValueError("translation status requires a nonempty question_vi")
        if self.translation_status == "missing" and self.question_vi:
            raise ValueError("nonempty question_vi must be marked requires_review or approved")
        if self.task in {"object_existence", "spatial", "negation"}:
            if self.ground_truth not in {"yes", "no"}:
                raise ValueError("binary ground_truth must be yes/no")
        elif self.task == "counting":
            if type(self.ground_truth) is not int or self.ground_truth < 0:
                raise ValueError("counting ground_truth must be a nonnegative integer")
        elif self.task == "fine_grained" and self.ground_truth not in tuple("ABCDEFGH"):
            raise ValueError("fine_grained ground_truth must be A–H")
        return self


class PilotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    experiment_id: NonEmpty
    purpose: Literal["stage0_engineering_preflight", "bilingual_pilot"] = "stage0_engineering_preflight"
    dataset: Literal["repope"]
    source_revision: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    source_split: Literal["train"]
    pool_rows_per_page: int = Field(ge=10, le=100, default=100)
    pool_page_offsets: Annotated[list[Annotated[int, Field(ge=0)]], Field(min_length=1, max_length=6)]
    sample_size: int = Field(ge=6, le=50, default=10)
    seed: int = 42
    max_rows_per_image: int = Field(ge=1, le=10, default=1)
    max_download_mb: int = Field(ge=1, le=50, default=20)
    cache_dir: NonEmpty
    manifest: NonEmpty
    report_dir: NonEmpty
    require_approved: Literal[False] = False
