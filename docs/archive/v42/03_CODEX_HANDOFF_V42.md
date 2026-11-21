# CODEX HANDOFF — TRIỂN KHAI VLM BENCHMARK V4.2

> **ĐỌC FILE NÀY TRƯỚC KHI CODE.** Đây là specification/acceptance criteria để triển khai từ đầu. Đọc thêm:
> - `01_RESEARCH_OUTLINE_V42.md`: câu hỏi nghiên cứu, giả thuyết, số mẫu, nguồn, metrics và giới hạn.
> - `02_DRAFT_CONG_VIEC_V42.md`: công việc, phụ thuộc, timeline và tiêu chí nghiệm thu.
> - `project_topics.md`: yêu cầu gốc của thầy — **Topic #14 Probing vision–language models**.
>
> **Không gán nhiệm vụ theo tên thành viên.** Nhóm có 5 người nhưng sẽ tự phân công sau.

## 1. Mục tiêu sản phẩm (không được tự diễn giải sai)

Xây dựng **reproducible, zero-shot, paired English–Vietnamese evaluation framework** cho **hai open-weight generative VLM**: `Qwen/Qwen2.5-VL-3B-Instruct` và `google/gemma-3-4b-it`.

**Không train/fine-tune model.** Mỗi mẫu có cùng ảnh, câu hỏi gốc EN, bản VI tương đương và nhãn gốc. Chạy inference độc lập EN/VI cho từng model; lưu raw predictions; chuẩn hóa về nhãn; tính task-specific metrics + paired statistics; dựng figures; hỗ trợ tập Visual Contrast và Negation. Không gộp các tác vụ khác nhau thành một hallucination metric.

**Tổng sample chính mục tiêu = 1.000 ROW**, gồm:

| Task | Dataset | Row target | Rule |
|---|---|---:|---|
| Object existence | `MM-Hallu/RePOPE` | 600 | 200/category × 3; mục tiêu 100 yes/100 no/category nếu khả thi; lưu unique image count |
| Spatial relation | VSR official | 120 | 60 TRUE/60 FALSE, chọn một official test split cố định |
| Counting | TallyQA official | 120 | 60 `issimple=true`, 60 `false`; ground truth integer |
| Fine-grained | Oxford-IIIT Pet official | 160 | 8 dog breeds × 20 test images; candidate labels fixed |
| TOTAL | | **1000** | **4.000 inference chính = 1000 × 2 languages × 2 models** |

**Tập phụ riêng:** `visual_contrast` 30–40 **image pairs**; `negation` 40 base examples × 2 polarity statements; `paraphrase` optional 20–30 base examples. Không dùng các tập này thay thế cho 4 bộ dữ liệu chính. **Fallback** nếu QA/time quá tải: 600/80/80/120 = 880 row; chỉ sử dụng khi nhóm đồng ý, log lý do.

**RQ1 chính:** đối chiếu **RePOPE FPR trên negative-only rows** EN vs VI, ΔFPR theo từng model; **RQ2:** visual evidence contrast (behavioral diagnostic, exploratory); **RQ3:** spatial/counting/fine-grained gaps; **RQ4:** negation logical consistency.

**Không được tự bịa benchmark results, Accuracy, p-value, VRAM hoặc runtime.** Tài liệu nêu mục tiêu và giao thức, không có kết quả chạy thật.

## 2. Chỉ dẫn quan trọng cho Codex

1. **Làm theo từng giai đoạn**, ưu tiên runnable prototype và tests trước full inference; sau mỗi stage cập nhật README, còn thiếu gì và lệnh chạy.
2. **Không tự động tải toàn bộ COCO/VG hàng chục GB**, không thuê GPU, không gọi API trả phí, không push public repo và không tiêu quota GPU lâu khi chưa được nhóm xác nhận. Cho phép tiny preflight và pilot trước.
3. **Không tự động dùng VLM benchmark làm máy gán nhãn** hoặc thay nhãn gốc theo output. Chỉ dùng nhãn gốc và QA người được ghi lại.
4. **Không sử dụng final test để sửa prompt**. Pilot và final tách theo `image_id` và cố định config trước final.
5. **Không tự xem câu nào VLM sai rồi loại khỏi benchmark**; mọi loại trừ vì dữ liệu hỏng/nhãn mơ hồ phải được quyết định trước khi thấy kết quả final và lưu audit trail.
6. **Không tự dịch bằng dịch vụ tốn tiền.** Hỗ trợ template/dictionary cho POPE và xuất review queue cho VSR/TallyQA; phần dịch và xác minh còn lại để nhóm làm. Có thể hỗ trợ import CSV đã dịch.
7. **Không coi 1.000 row là 1.000 ảnh duy nhất.** RePOPE có ~8.185 questions trên ~500 images; cần `n_unique_images`, `rows_per_image`, cluster-aware stats.
8. **Không tạo tuyên bố nhân quả nội tại.** Pair-image analysis kiểm tra behavior, không chứng minh attention/training-data gây lỗi.
9. **Bảo mật:** không lưu HF access token vào repo hay log; Gemma cần chấp nhận license trên Hugging Face.

## 3. Links nguồn chính (trang gốc ưu tiên)

- Assignment: `project_topics.md` trong thư mục tài liệu dự án.
- RePOPE packaged images: https://huggingface.co/datasets/MM-Hallu/RePOPE ; upstream annotations: https://github.com/YanNeu/RePOPE . Cần xác minh dữ liệu HF và citation/license/revision cụ thể.
- VSR source: https://github.com/cambridgeltl/visual-spatial-reasoning ; image references COCO tải riêng; zero-shot/random splits khác nhau.
- TallyQA: https://github.com/manoja328/TallyQA_dataset ; QA JSON có `image`,`image_id`,`issimple`,`data_source`; images từ COCO/VG tải riêng.
- Oxford Pet official: https://www.robots.ox.ac.uk/~vgg/data/pets/ ; HF: https://huggingface.co/datasets/timm/oxford-iiit-pet ; use test split and class label names.
- Model A: https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct .
- Model B: https://huggingface.co/google/gemma-3-4b-it ; documentation: https://huggingface.co/docs/transformers/model_doc/gemma3 .
- Prior work: https://aclanthology.org/2025.acl-long.640/ ; NegBench (reference only): https://negbench.github.io/ .

## 4. Kiến trúc repo cần có

```text
vlm-en-vi-grounding/
├── README.md
├── pyproject.toml                  # hoặc requirements + phiên bản được khóa
├── .gitignore
├── configs/
│   ├── pilot.yaml
│   ├── main.yaml
│   ├── models.yaml
│   └── prompts.yaml
├── docs/
│   ├── data_sources.md
│   ├── sampling_protocol.md
│   ├── translation_guidelines.md
│   ├── experiment_protocol.md
│   └── limitations.md
├── data/
│   ├── raw/                       # tải về, KHÔNG commit ảnh thô
│   ├── external_images/           # COCO/VG nếu có; gitignored
│   ├── pilot/
│   ├── processed/
│   │   ├── main_manifest.parquet
│   │   ├── visual_contrast.parquet
│   │   ├── negation.parquet
│   │   └── optional_paraphrase.parquet
│   ├── dictionaries/
│   │   └── object_en_vi.csv
│   └── reviews/
│       ├── translation_review.csv
│       ├── contrast_review.csv
│       └── issues.csv
├── src/vlmbench/
│   ├── __init__.py
│   ├── cli.py
│   ├── schemas.py
│   ├── io_utils.py
│   ├── datasets/
│   │   ├── repope.py
│   │   ├── vsr.py
│   │   ├── tallyqa.py
│   │   └── oxford_pet.py
│   ├── sampling.py
│   ├── translate.py
│   ├── qa.py
│   ├── prompts.py
│   ├── models/
│   │   ├── base.py
│   │   ├── qwen25_vl.py
│   │   └── gemma3.py
│   ├── inference.py
│   ├── parse.py
│   ├── evaluate.py
│   ├── statistics.py
│   ├── contrast.py
│   ├── negation.py
│   └── plot.py
├── tests/
│   ├── fixtures/                 # ảnh nhỏ/tiny synthetic manifests
│   ├── test_sampling.py
│   ├── test_schema.py
│   ├── test_parser.py
│   ├── test_leakage.py
│   ├── test_metrics.py
│   ├── test_negation.py
│   └── test_contrast.py
├── results/
│   ├── predictions/              # .jsonl per model/dataset/language
│   ├── parsed/
│   ├── metrics/
│   └── figures/
└── reports/
    ├── proposal.md
    ├── milestone.md
    └── final.md
```

## 5. Data contract chính (phải type-check)

Mọi row chính trong manifest có các trường sau (có thể thêm tùy task nhưng KHÔNG bỏ trường bắt buộc):

```json
{
  "sample_id": "repope_random_000123",
  "source_dataset": "repope",
  "source_split": "train",
  "source_row_id": "...",
  "image_id": "000000310196",
  "image_path": "data/raw/repope/images/000000310196.jpg",
  "image_sha256": "...",
  "task": "object_existence",
  "category": "random",
  "question_en": "Is there a dog in the image?",
  "question_vi": "Trong ảnh có con chó nào không?",
  "ground_truth": "yes",
  "ground_truth_source": "repope_original_label",
  "qa_status": "approved",
  "translation_status": "approved",
  "is_pilot": false,
  "sampling_seed": 42,
  "metadata": {"object_name_en": "dog", "object_name_vi": "chó"}
}
```

**Tùy task:** VSR có `relation`, TallyQA có `issimple`, `count_answer`, Oxford Pet có `breed_id`, `candidate_ids_and_names`; image-pair contrast có `pair_id`, `image_id_a`, `image_id_b`, `target_object`, `truth_a=yes`, `truth_b=no`, `pair_qa_status`; negation có `base_id`,`polarity`,`truth_value` và câu A/B.

**Bản ghi inference** (một row cho **sample × language × model**):

```json
{
  "experiment_id": "v42_main_frozen_v1",
  "sample_id": "repope_random_000123",
  "source_dataset": "repope",
  "task": "object_existence",
  "image_id": "000000310196",
  "language": "vi",
  "model_id": "Qwen/Qwen2.5-VL-3B-Instruct",
  "model_revision": "<exact commit/hash>",
  "processor_revision": "<exact commit/hash>",
  "prompt_version": "v1",
  "prompt_text": "...",
  "ground_truth": "yes",
  "raw_response": "YES",
  "parsed_prediction": "yes",
  "parse_status": "valid",
  "elapsed_ms": 1234.5,
  "precision": "bf16_or_fp16_or_4bit_actual",
  "image_preprocess": {"policy_id": "qwen_default_v1"},
  "run_config_hash": "...",
  "error": null
}
```

`parsed_prediction` phải null khi không parse được, `parse_status` = invalid. Nếu OOM/exception, `run_status=failed`, lưu lỗi và hỗ trợ retry; **không âm thầm drop row**. Hoàn toàn có thể thêm các trường version/VRAM/seed/device để audit.

## 6. Quy tắc sampling (KHÔNG dùng model outputs để lựa chọn)

**Pilot:** chọn 30–50 RePOPE row, cố gắng đa dạng category và label; **ghi image IDs pilot để loại tất cả record có cùng ảnh khỏi final**; `seed=42` hoặc một seed đã chốt. Pilot để thử data/translation/inference/QA, không phải evidence cho kết luận.

**Main RePOPE:** mục tiêu 200 sample mỗi category, 100 yes/100 no nếu khả thi; ưu tiên đa dạng image IDs; dùng stratified sampling với seed cố định, cap per-image *mềm* (được nới có log khi không đủ); report chính xác số unique images, median/max rows per image và tỷ lệ mỗi strata.

**VSR:** chọn test split **duy nhất** theo official repo (mặc định đề xuất `cambridgeltl/vsr_random` test, nếu có ảnh); True/False 60/60; đa dạng relation và image IDs. Không tin rằng HF viewer luôn đọc được image bytes.

**TallyQA:** test JSON, 60 simple/60 complex; kiểm tra ảnh tồn tại và parse label; đa dạng answer counts (0, 1, 2, >=3) theo khả dụng; ghi rõ COCO hay VG; không cố tải hàng trăm GB tự động.

**Oxford-IIIT Pet:** test split, cố định 8 classes từ bộ có sẵn (chọn dựa vào taxonomy và ảnh, KHÔNG dựa vào kết quả VLM), 20 ảnh mỗi class, same candidate list/order for EN/VI; label output `A`–`H` hoặc ID từ 0–7 để tránh alias/parsing bias; chú thích tên riêng giống thường không thể dịch thuần Việt.

**Nếu không đạt target:** tạo `sampling_feasibility_report.json` (available counts, image counts, missing images, conflicts); xin nhóm quyết định giảm theo **fallback 880**; không sửa ngầm target hay report sample ảo.

## 7. Translate & QA (đặc biệt quan trọng)

- RePOPE thường có mẫu `Is there a [object] in the image?`; tách object theo template **chỉ khi chắc chắn match**, dùng `object_en_vi.csv`; object ngoài từ điển hoặc câu không match → `REQUIRES_REVIEW`, không tự đoán nghĩa.
- VSR và TallyQA: file `translation_review.csv` gồm `sample_id,en,vi,reviewer_1_status,reviewer_2_status,notes,final_status`; toàn bộ 240 câu được review ở mức phù hợp. Không tự động duyệt bản dịch máy.
- Negation: xác nhận label mệnh đề âm/khẳng **đối lập chính xác**, ví dụ ảnh có chó → “Có chó” TRUE, “Không có chó” FALSE; ảnh không có chó thì ngược lại. Dùng nhãn hiện hữu đã kiểm chứng.
- Contrast: mọi cặp ảnh có target class như nhau, truth A/B đối lập, pair_id ổn định, QC hai người; không gọi cặp ảnh bất kỳ là “controlled” nếu thiếu tương đồng bối cảnh.
- Chỉ các row `qa_status=approved && translation_status=approved` mới được chạy main. Bản mẫu unreviewed chỉ dùng pilot/mock.

## 8. Prompts & parsing

**Đối chứng EN/VI phải giữ nghĩa như nhau.** Thay instruction language mà vẫn yêu cầu **canonical output chung** để hạn chế parser bias. Định nghĩa prompts bằng YAML có `prompt_version`; không sửa sau freeze. `do_sample=false` cho cả hai; kiểm tra generation config model riêng; không dùng conversation history.

Các task:
- `object_existence`: question binary -> `YES`/`NO`.
- `spatial`: mệnh đề true/false -> `YES`/`NO` tương ứng true/false (định nghĩa rõ).
- `counting`: integer answer duy nhất; regex chỉ nhận integer đơn giản trong output hợp lệ, không lấy bừa chữ số đầu của giải thích dài.
- `fine_grained`: candidate 8 breeds được cố định; trả `A..H` hoặc mã lớp; tránh EN/VI candidate set khác nhau.
- `negation`: paired affirmative/negative -> `YES`/`NO` tính truthfulness.

**Parser policy:** có nhánh phân tích `yes`,`no`,`true`,`false`, `có`,`không` nếu model không theo canonical output; phải log. Với câu chứa cả YES và NO hoặc câu dài mâu thuẫn: `INVALID_AMBIGUOUS` thay vì đoán. Unit tests cho case Vietnamese diacritics, leading/trailing punctuation, unparseable, negation and digits.

## 9. Model adapters & inference (không code giả)

**Qwen:** model `Qwen2_5_VLForConditionalGeneration` hoặc API Transformers chính thức tương ứng checkpoint; `AutoProcessor`, `qwen-vl-utils` nếu cần; ảnh ở định dạng được hỗ trợ; kiểm soát image resolution/pixel bounds có ghi log. Model revision fixed.

**Gemma:** dùng **chính xác** API `Gemma3ForConditionalGeneration` hoặc `AutoModelForImageTextToText`/pipeline phù hợp phiên bản đã cài; không dùng class không tương thích do copy ví dụ lỗi thời. Model card yêu cầu HF license; không đưa token vào source. Gemma 3 4B vision-capable.

GPU: dùng Colab/Kaggle nếu được cấp; RTX 3060 laptop 6GB rất dễ OOM ở FP16 đầy đủ; thử 4-bit khi cần và report config. Adapter phải `load_model`, `generate(image,prompt)`, `unload_model`; chạy **một model một lần** để không đồng thời giữ hai weights trong GPU. Nếu môi trường không có GPU, mock tests vẫn chạy được, CLI in actionable warning thay vì cố tải weights nặng.

`inference.py` phải hỗ trợ:
- Atomic append per output JSONL / SQLite or Parquet checkpoints, deterministic work queue.
- `resume=true`: bỏ qua `model_id × language × sample_id × config_hash` đã thành công; retry các lỗi nếu người dùng cho phép.
- `--limit`, `--dataset`, `--language`, `--model`, `--config`, `--output`, `--dry-run`.
- Validate expected count: 1.000 × 2 × 2 = 4.000; đếm thực tế success/invalid/failed và unique sample keys, report missing.
- Ghi latency và (nếu có) peak VRAM; không in chi phí GPU giả định khi chưa đo.

## 10. Metrics & tests (đây là phần có giá trị học thuật)

**Main per model/language/task:** accuracy, valid/invalid rate, sample count, unique images. For RePOPE: confusion matrix, FPR on negatives, FNR on positives, precision/recall/F1, balanced accuracy and strategy-level breakdown; **ΔFPR = VI − EN**.

**Spatial:** binary accuracy; **Counting:** exact match and MAE, invalid separate; **Pet:** 8-way top-1 accuracy, confusion matrix; **Contrast:** pair accuracy and correct-flip (each pair as resampling unit); **Negation:** correct statements and logical consistency.

**Statistical tests:** 95% **cluster bootstrap by image_id** for main RePOPE paired EN/VI differences; exact McNemar for jointly valid paired predictions (report n excluded invalid); consider Holm across two model H1 tests. CIs for contrast bootstrap by pair ID. No model comparison false significance with correlated questions as if independent.

**Unit tests tối thiểu:**

1. `test_parser`: YES/NO, True/False, tiếng Việt, integer, breed class, ambiguous/invalid.
2. `test_sampling`: target counts, repeatability with seed, no duplicated `sample_id`, approximate strata, unique image counts.
3. `test_leakage`: same image (even different question) cannot appear pilot vs final in same source, detect collisions if identical images across different datasets when hashes available.
4. `test_negation`: the two proposition labels have opposite truth values; pair accuracy consistency.
5. `test_contrast`: A/B labels oppose, pair_id, no scene pairs with unapproved QC.
6. `test_metrics`: hand-calculated FPR, FNR, accuracy, counting MAE, top-1, disagreement; invalid policy preserved.
7. `test_statistics`: when EN=VI identical outputs, estimated Δ=0; bootstrap deterministic with seed; paired counts correct.
8. `test_resume`: running inference twice does not duplicate completed records.
9. `test_dataset_preflight`: unreadable/missing image, wrong label, absent translation raise or put in validation report.

## 11. CLI contract (mỗi lệnh có `--help` và config file)

```bash
# Chưa gọi model nặng: kiểm tra dữ liệu/tiny sample
python -m vlmbench.cli inspect --dataset repope --limit 10
python -m vlmbench.cli prepare-pilot --config configs/pilot.yaml
python -m vlmbench.cli validate --manifest data/pilot/pilot_manifest.csv

# Sau khi nhóm kiểm tra pilot và dịch thuật
python -m vlmbench.cli prepare-main --config configs/main.yaml
python -m vlmbench.cli export-translation-review --manifest data/processed/main_manifest.csv
python -m vlmbench.cli validate --manifest data/processed/main_manifest.csv

# Inference: chạy trên GPU có quyền, --limit 10 để smoke test trước
python -m vlmbench.cli infer --model qwen --config configs/pilot.yaml --limit 10
python -m vlmbench.cli infer --model gemma --config configs/pilot.yaml --limit 10

# Khi đã được duyệt full-run
python -m vlmbench.cli infer --model qwen --config configs/main.yaml --resume
python -m vlmbench.cli infer --model gemma --config configs/main.yaml --resume
python -m vlmbench.cli evaluate --config configs/main.yaml
python -m vlmbench.cli statistics --config configs/main.yaml
python -m vlmbench.cli plot --config configs/main.yaml

pytest -q
```

Nếu data chưa có hoặc auth chưa xong: in hướng dẫn xử lý cụ thể. **Không tự tạo bản ghi inference fake trong `results`**. Có thể dùng mock cho unit tests với thư mục `tests/fixtures` được đánh dấu `synthetic_test_only`.

## 12. Các giai đoạn giao Codex (ưu tiên theo thứ tự; đừng cố làm tất cả trong một lượt)

### Stage 0 — Foundation / kiểm chứng nguồn dữ liệu (đề xuất làm NGAY)
- Tạo cấu trúc repo, README, pyproject requirements, logging, schemas, sample configs, CI `pytest` cơ bản.
- Adapter đọc RePOPE 5–10 record (ảnh kèm), preflight image, metadata report. Tạo pilot manifest với seed, không require dịch hết dataset.
- Viết `test_parser`, `test_sampling`, `test_leakage` với fixtures. Xuất **một bảng sample có image_id/question/ground truth**; chứng minh ảnh mở được.
- Chỉ tiếp tục Stage 1 sau khi `pytest` xanh và pilot manifest hợp lệ.

### Stage 1 — Bilingual pilot & model adapters
- Template translation RePOPE, export review table, 30–50 mẫu pilot đã QA.
- Chạy smoke test Qwen 10 mẫu, Gemma 10 mẫu khi có GPU; ghi lỗi cài đặt/env/VRAM thực tế.
- Export prediction schema; pipeline FPR/Accuracy/disagreement với mock outputs và real pilot outputs.
- Tạo `docs/pilot_findings.md` phân biệt **số liệu pilot thực** với mục tiêu dự kiến.

### Stage 2 — Full dataset + main benchmark (chỉ sau khi nhóm đồng ý)
- Adapter VSR/TallyQA/Pet; preflight ảnh; 1.000 main rows/quality freeze; upload/review translation files thủ công.
- Full inference + resume/checkpoint; report 4.000 expected vs actual.
- Metrics, cluster bootstrap, McNemar, plots; test reproduction from results files.

### Stage 3 — Contrasts/negation/report
- Form/CSV cho review cặp ảnh, paired contrast generator, negation manifest & consistency tests.
- Error case export; result figures; markdown tables for 6–8 page paper and presentation.
- Optional paraphrase only if core completed.

## 13. Definition of Done

**Stage 0 Done:** `pip install -e .` hoạt động; `pytest -q` xanh; chạy `inspect repope --limit 10`; có 10 ảnh mở được và output hợp lệ; có pilot manifest; không đòi GPU/Google token.

**Pilot Done:** 2 VLM (nếu có hardware) xử lý cùng tối thiểu 10–30 row × EN/VI; raw output + parser report + latency/VRAM đo thật; có invalid audit; mọi blocker được ghi.

**Main Done:** manifest QA-approved/frozen; đúng target hoặc fallback được phê duyệt; không leak pilot; 4.000 expected runs được đối chiếu success/invalid/failed; metrics + CIs được kiểm tra; có chart và examples đủ để báo cáo.

**Final Done:** contrast và negation đã QA; github repo reproducible, docs/license/source citations, report 6–8 trang, 15-minute slides, video demo dự phòng; không có thống kê/claim bịa.

---

## Prompt khởi động có thể dán thẳng vào Codex

> Hãy đọc toàn bộ `03_CODEX_HANDOFF_V42.md`, `01_RESEARCH_OUTLINE_V42.md`, `02_DRAFT_CONG_VIEC_V42.md` và `project_topics.md`. Đây là một dự án Computer Vision Topic #14: benchmark đối chứng Anh–Việt cho object hallucination và visual grounding bằng Qwen2.5-VL-3B & Gemma 3 4B, không fine-tuning. **Trước mắt chỉ thực hiện Stage 0**: tạo repo/pipeline ETL RePOPE 10 records có ảnh, schema, preflight ảnh, manifest pilot có phân tầng/seed, parser cơ bản, pytest và README với lệnh chạy. Tuyệt đối không tự chạy full 4.000 inference, không tự dịch 1.000 câu, không sửa nhãn nguồn, không dùng API trả phí hoặc tải nguyên bộ COCO/VG. Khi xong Stage 0 hãy báo các file đã tạo, lệnh test, kết quả thực tế, blockers, và đề xuất Stage 1. Những gì chưa kiểm chứng thì ghi rõ chưa kiểm chứng.
