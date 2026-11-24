# Baseline contract and main runner v1

**Cập nhật24/11:** main CLI mặc định candidate Option B tại
`configs/baseline_v3_option_b_v1.yaml`, policy `original_rgb_processor_v1`.
Chưa freeze. [Method/checklist M3 hiện hành](MAIN_OPTION_B_V1.md) và
[evidence v14](../../reports/stage1/v14/completion.md). Config draft A cũ vẫn
đọc được qua --config; bảng/thiết kế gốc22/11 bên dưới ghi cả lựa chọn lịch sử.

Ngày 22/11/2026. Hợp đồng này bổ sung metadata và runner bốn task cho RQ1/RQ2,
để phát triển bằng CPU trong lúc nhóm review. Manifest hiện tại vẫn là draft;
configs baseline và prompts mới chưa frozen. Không thay schema/bytes pilot cũ.

## Cách kiểm kế hoạch bằng CPU

Chạy từ root bằng môi trường CPU đã cài theo hướng dẫn nhóm:

```powershell
.venv/Scripts/python.exe scripts/run_main.py plan
.venv/Scripts/python.exe scripts/run_main.py plan --report results/main/preflight_v1/plan.json --grid-output results/main/preflight_v1/grid.jsonl
.venv/Scripts/python.exe scripts/run_main.py run --model qwen --dry-run
.venv/Scripts/python.exe scripts/run_main.py run --model gemma --dry-run
```

Report/grid phải là đường dẫn mới. Full grid chứa 4.000 cells nên nằm trong
results, ngoài Git; summary nhỏ có thể lưu làm evidence. Lệnh plan là mặc định,
không import torch/transformers, không tải weights và không gọi model.
Mỗi dry-run model riêng có 2.000 cells và giữ đầy đủ 1.000 sample IDs.

Config A lịch sử `configs/baseline_v3_draft.yaml` và candidate B mới tham chiếu cùng bốn manifest hiện tại,
source selection 1.000 IDs, pilot approved manifest và exclusion registry.
Queue sắp theo alias model, sample ID, rồi EN/VI; không lấy mẫu lại hoặc đổi seed.
Ảnh không có trong Git: nếu clone chưa restore dữ liệu, plan báo lỗi preflight
ảnh và vẫn cho xem lưới dự kiến. Nhận/restore workspace ZIP theo hướng dẫn nhóm
để kiểm bytes thật. Trạng thái pending/frozen=false là blocker dự kiến.

## Config và prompt đã triển khai

| Thành phần | Hợp đồng v1 |
|---|---|
| Schema | baseline_v1, Pydantic strict, extra fields bị từ chối |
| Dữ liệu | Cùng 600 RePOPE +120 VSR +120 TallyQA +160 Pet; source labels/fields giữ nguyên |
| Cặp EN–VI | Cùng row/ảnh/ground truth, cùng config trong mỗi model |
| Models | Qwen2.5-VL-3B-Instruct và Gemma 3 4B IT, exact revision 40 ký tự |
| Processor/tokenizer | Pin rõ revision; adapters hiện yêu cầu cùng revision với model |
| Precision | Qwen NF4/FP16; Gemma NF4/BF16, không fallback |
| Generation | Greedy, batch=1, seed=42; max_new_tokens hiện là 8, chưa final freeze |
| Ảnh | Main B: RGB kích thước nguồn, không manual resize; A lịch sử: thumbnail LANCZOS max512. Cùng Qwen min/max pixels; Gemma no pan-and-scan/slow processor |
| Prompt variants | baseline; image_variant=original; không mở RQ3/RQ4 |

Prompt mới tại `configs/prompts_baseline_v1.yaml`. Mỗi task/ngôn ngữ phải giữ
`{question}`; Pet thêm cùng danh sách tám giống `{candidates}` cho EN/VI.
Pet không làm rơi câu VI của manifest như một template chỉ chứa danh sách lớp.
RePOPE yêu cầu YES/NO; VSR yêu cầu TRUE/FALSE; counting yêu cầu số nguyên không
âm; Pet yêu cầu A–H. Parser hiện có chuẩn hóa TRUE→yes, FALSE→no, không đảo
nhãn vì phát biểu có vẻ sai. Prompt không nhận ground truth làm placeholder.

Đây là candidate settings cho baseline, không phải kết quả thực nghiệm hoặc
quyết định freeze cuối. Pilot vẫn dùng configs/prompts lịch sử của chính run.

Audit trước quyết định B ngày24/11 xác nhận đường A đưa thumbnail512 vào processor; review
HTML dùng nguyên JPEG. Processor Gemma tiếp tục resize về 896×896, có méo tỷ
lệ với ảnh không vuông; Qwen resize theo grid/pixel budget nên có thể phóng
to thumbnail trở lại. `image_variant=original` chỉ variant nguồn, không có
nghĩa giữ nguyên pixels/kích thước vào encoder. Xem [audit và kế hoạch so sánh
pilot](../../reports/audits/2026-11-24/image_pipeline_audit.md) trước quyết định
final preprocessing. Config/runtime/freeze gate chưa thay đổi.

## Metadata và tên trường

Không rename CSV hiện có theo sơ đồ minh họa V3. Alias khi đọc contract:
dataset=source_dataset, source_item_id=source_row_id, task_type=task và
annotation_status=qa_status. Source revision/record hashes vẫn từ metadata
manifest, decision/audit notes vẫn trong review proof đã import.

Mỗi run có JSONL, `.meta.json`, `.summary.json`, và `.load_error.json` nếu
model load thất bại. Một file chỉ thuộc một model/platform/run ID/fingerprint.

| Nhóm | Metadata/record bắt buộc |
|---|---|
| Định danh | schema_version, experiment_id, run_id, cell_id, sample_id, language |
| Nguồn | source_dataset/split/row_id/revision/record_sha256, task, image_namespace/id/sha256, source_row_sha256, ground_truth/source |
| Model | model_alias/id/revision, processor_revision, tokenizer_revision |
| Điều kiện | precision, dtype, quantization_config NF4/double quant, device, platform, generation_config, image_preprocess/processor policy |
| Prompt | prompt_version, prompt_variant, image_variant, prompt_text, prompt_hash |
| Tái lập | protocol_hash, run_config_hash, code_commit, code_dirty, metadata environment/package/GPU inventory, implementation/source hashes |
| Kết quả | attempt, recorded_at_utc, raw_response, parsed_prediction, run_status, parse_status/reason, valid, invalid_reason, used_alias |
| Đo/lỗi | elapsed_ms, peak_allocated_mib, generation_trace nếu có, sanitized error |
| QA/scope | qa_status, translation_status, main_baseline hoặc synthetic_test_only |

Metadata lưu generation/preprocess/quantization settings đã truyền cho adapter;
hardware inventory và Gemma trace bổ sung quan sát runtime khi chạy thật.
Không có `.git` thì code_commit/code_dirty là null, không bịa commit. Có Git
thì ghi HEAD thật và dirty flag; protocol còn bind hashes của 14 source modules.
Không đưa token/environment secrets vào metadata. Synthetic test adapter có
scope và device riêng, không được ghi như CUDA inference thật.

protocol_hash bind config bytes, prompts, manifests, candidate selection,
pilot/exclusions, source implementations và toàn bộ grid. Freeze receipt
tham chiếu hash này; không tự nhúng receipt bytes vào protocol gây vòng lặp.
run_config_hash còn bind model/platform/run ID, môi trường, code state và
freeze receipt hash. Không chia checkpoint giữa các fingerprint khác nhau.

## Gate trước chạy model

Runner dựng lại preflight từ file ngay trước execute, không tin một plan object
đã bị sửa trong bộ nhớ. Chỉ vào runtime/model khi tất cả điều kiện dưới đạt:

1. Source IDs bằng đúng full selection; counts đúng targets; source EN/labels,
   provenance và mapping Pet A–H không đổi; không trùng image bytes giữa IDs.
2. Ảnh đọc được/hash đúng, không overlap pilot theo namespace/ID hoặc SHA256,
   kiểm cả pilot manifest và registry.
3. Tất cả main translation/QA approved, có proof v2 với hai ID khác nhau cùng
   approved cả dịch và ảnh/nhãn trên bản VI cuối; chỉ đổi cột approved chưa đủ.
4. Config frozen=true và freeze receipt hợp lệ, được người có trách nhiệm
   ghi nhận với đúng protocol_hash, approved_by, approved_at có timezone, notes.
5. Người chạy gọi rõ `run --execute`; CUDA và native BF16 cho Gemma đạt trước Hub access.

Hiện chưa có reviewed final manifest hoặc freeze receipt thật. Chưa thêm lệnh
tự freeze/approve: sau khi nhận JSON review, cần tổng hợp, đối soát, chốt configs
và được xác nhận trước main inference. Không bật frozen=true để vượt QA.
Schema freeze receipt là baseline_freeze_v1; mẫu tổng hợp trong tests chỉ là
synthetic fixtures, không tái sử dụng làm approvals cho dữ liệu thật.

## Resume và lỗi

Sau khi có config final/freeze hợp lệ, runner hỗ trợ `--max-cells N` để giới
hạn một đợt nhưng expected grid luôn giữ đủ 2.000 cells/model. `--resume` tiếp
tục đúng run/output; failed chỉ retry khi có `--retry-failed`. Một generation
thành công nhưng parser invalid được giữ nguyên, không tự chạy lại để chọn đáp
án đẹp hơn. Attempt tăng liên tiếp; không có attempt sau success cho cùng cell.

Metadata và mỗi checkpoint JSONL được ghi atomic. Ctrl+C giữa generation để
cell đó missing, các records đã commit trước còn nguyên. JSONL truncated,
duplicate attempt, prompt/label/parse bị sửa hoặc metadata khác sẽ bị chặn;
giữ file để đối soát, không tự bỏ dòng. OOM ghi failed rồi dừng, phần còn lại
missing; không đổi precision/image size/model ngầm. Lỗi load có report riêng,
không bịa prediction cho các cells chưa chạy. Raw text/trace hợp lệ được giữ
khi generation thất bại; JSON không ghi NaN/Inf hoặc diagnostic hỏng.

Runner dùng lại adapters đã có: Qwen HuggingFaceAdapter, GemmaTraceAdapter
BF16 với model-declared terminal EOS handling. Không đổi giới hạn/chức năng
pilot cũ; entry point main mới là scripts/run_main.py. Môi trường inference
cần được chọn riêng, ví dụ gọi bằng `.venv-infer/Scripts/python.exe`; script
không tự đổi interpreter. Cache-only là mặc định; --online chỉ cho tải khi
đã execute qua gates. Credential dùng secret/environment của người chạy.

## Tích hợp evaluation

JSONL mới giữ các field tương thích evaluator hiện có. Evaluate riêng từng
model với manifest hợp nhất đúng của run và `.summary.json` làm selection.
Manifest hợp nhất phải được kiểm đủ IDs/source và lưu version mới sau review;
runner không tự tạo một main approved manifest từ các bản nháp.

```powershell
.venv/Scripts/python.exe -m vlmbench.cli evaluate --manifest data/main/final_v1/main_manifest.csv --predictions results/main/local/RUN_ID/qwen.jsonl --selection results/main/local/RUN_ID/qwen.summary.json --output results/analysis/RUN_ID_qwen_eval.json --report results/analysis/RUN_ID_qwen_eval.md
.venv/Scripts/python.exe -m vlmbench.cli statistics --evaluation results/analysis/RUN_ID_qwen_eval.json --output results/analysis/RUN_ID_qwen_ci.json --resamples 5000 --seed 42
```

Các đường dẫn final/RUN_ID ở trên là ví dụ cho giai đoạn sau, chưa tồn tại
như artifact đã freeze. Metrics/CI không viết lại: tests đã đưa fake outputs
cả hai model qua bốn nhóm task, paired negative ΔFPR và image-cluster bootstrap.
Điều đó chứng minh tích hợp phần mềm, không đo performance thật của main.

## Trạng thái và bước tiếp theo

Contract/planner/runtime v1 đã có CPU tests; actual main GPU generation và
cloud execution chưa được xác minh. Full tests mới và dry-run thật ghi tại
[Stage 1 v13](../../reports/stage1/v13/completion.md).
Ưu tiên tiếp theo: nhận/import review A/B, tổng hợp main final, xử lý mẫu nghi
vấn, chốt/freeze configs rồi xác nhận một run nhỏ bốn task trước full run.
RQ3/RQ4 vẫn có gate riêng; không thêm negation, training hoặc model mới.
