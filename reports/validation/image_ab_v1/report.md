# GPU A B validation cho image preprocessing

Ngày 24/11/2026. Ngày thuyết trình do người dùng xác nhận: **03/12/2026**.
**Trạng thái: BLOCKED_TASK_COVERAGE; chưa hoàn thành GPU A/B validation.**
Không có prediction A/B mới. GPU đã qua kiểm tra kernel FP16/BF16 thật,
nhưng 30 pilot hiện tại chỉ có RePOPE. Điều kiện người dùng yêu cầu đủ bốn
task trước run 240 cells chưa đạt, nên không load model hoặc gọi generate.

## Trạng thái xác minh và kế hoạch tối thiểu

Đã đọc completion v31, stage v13, audit commit `5fd8345`, handoff/protocol/
implementation plan V3 và configs/adapters hiện tại. Đây là validation kỹ
thuật trước freeze, không mở RQ mới. Thay đổi chỉ thêm một module, một CLI,
tests và report/evidence; tái sử dụng MainAdapter, Qwen FP16/Gemma BF16 loaders,
parser, prompt renderer và gates/provenance utilities hiện có.

| Kiểm tra thật | Kết quả |
|---|---|
| Pilot đã QA | 30/30 dịch và ảnh/nhãn approved; 30 RePOPE, 0 VSR, 0 TallyQA, 0 Pet |
| GPU | RTX 3060 Laptop, 6.144 MiB, compute capability 8.6, driver 616.87 |
| Runtime | Torch 2.7.1+cu126, CUDA 12.6, Transformers 4.57.1, Pillow 12.3.0 |
| CUDA thật | Kernel matmul 32×32 FP16 và BF16 đạt, mỗi kernel sum=32768; không phải VLM inference hoặc memory benchmark |
| Execute Qwen/Gemma | Cả hai lệnh exit 2 do thiếu ba task; không tạo run directory, không load adapter/model |
| Main | 1.000 MAIN_QA_NOT_APPROVED, BASELINE_NOT_FROZEN, FREEZE_RECEIPT_REQUIRED |
| Inference mới | 0 measured A/B cells; 0 warm-up VLM; 0 main |

Bằng chứng: [hardware/kernel preflight](gpu_kernel_preflight.json),
[pilot plan](preflight_final.json), [execute bị chặn](blocked_execute.json),
[main gates](main_gates.json). Model access/NF4 load/peak memory của full
model chưa được kiểm lại ở phiên này; kernel nhỏ thành công không chứng minh
Gemma hoặc Qwen chạy được mọi input trong 6 GB.

## Bổ sung coverage mà không dùng main outputs

Đề xuất một **manifest validation mới gồm 30 ảnh**:

| Dataset | Số mẫu | Thiết kế | Trạng thái |
|---|---:|---|---|
| RePOPE | 6 | Một mẫu cho mỗi random/popular/adversarial × yes/no | Chọn từ 30 pilot đã QA, giữ nguyên câu/nhãn/metadata |
| VSR | 8 | 4 TRUE, 4 FALSE | Metadata candidate; chưa có ảnh/VI/human QA |
| TallyQA | 8 | 4 simple, 4 complex | Metadata candidate; chưa có ảnh/VI/human QA |
| Oxford Pet | 8 | Một ảnh mỗi lớp A–H hiện có | Metadata candidate; chưa có ảnh/human QA |

Đã chọn IDs cụ thể bằng thứ tự SHA256 với seed label cố định, từ candidate
frames đã pin của ba dataset hiện có. Không thêm model/dataset hoặc nhánh C.
Danh sách [subset_proposal.json](subset_proposal.json) và
[24 candidates](supplement_candidates.jsonl) là **đề xuất metadata**, không
phải manifest được duyệt. Đã loại sample IDs main và mọi image namespace/ID
main/pilot; byte/checksum exclusions vẫn **pending** vì ảnh chưa materialize.
Không chọn candidates bằng predictions hoặc độ đúng/sai của model.

Để hợp lệ: lấy JPEG gốc vào thư mục pilot mới ngoài main, ghi checksum và
kiểm với 813 ảnh hiện có; kiểm source labels, dịch tương đương và review thật
cả dịch/ảnh theo A/B cho 24 mẫu mới. Giữ source revision/record hashes và
review proof khi tạo manifest pilot mới, không sửa pilot cũ hoặc main.
Harness từ chối supplement chỉ gắn cờ approved mà thiếu proof/source binding.
Các task mới dùng đúng prompts baseline draft, cùng prompt bytes giữa A/B
trong từng language/model; không dùng output để chỉnh prompt.

## Hai nhánh và logging đã triển khai

- A: JPEG nguồn → RGB → thumbnail LANCZOS cạnh tối đa 512 → processor hiện tại.
- B: JPEG nguồn → RGB → cùng processor, bỏ duy nhất thumbnail.

Dùng một model/processor instance cho hai nhánh; cùng revisions, NF4/dtype,
seed, batch=1, greedy/max_new_tokens=8, attention và prompt. Chạy AB/BA xen kẽ
theo thứ tự IDs/language cố định. Mỗi model có 2 warm-up/nhánh, thực hiện
trước measured cells và lưu riêng; run ban đầu một repeat như người dùng yêu
cầu: **240 measured cells +8 warm-up generations** nếu coverage/QA đủ.

`ObservedProcessor` chỉ quan sát shape/grid/token count và thời gian CPU,
trả nguyên đối tượng processor cho adapter; không đổi kwargs/tensor.
`measure` log IDs/task/model/language/branch, kích thước JPEG và trước
processor, processor shape/grid, raw/parsed, ground truth/correctness,
invalid reason, error/OOM, prompt/config/runtime fingerprints, timing và
VRAM. Config fingerprint bind inputs/source/implementation; runtime fingerprint
thêm environment/GPU/code state. `processor.json` lưu class/kwargs thực tế.

`latency_ms` đo chung từ verify hash + đọc/decode/RGB/thumbnail qua adapter,
decode/diagnostic đến CUDA synchronize; model loading, warm-up và checkpoint
write nằm ngoài timer. Có image_prepare_ms, processor_cpu_ms và adapter timer
để giải thích; không giả vờ có timing H2D/generate tách riêng khi reused
adapters không cung cấp. Chỉ so A/B trong cùng model; adapter Gemma có logits
diagnostics nên không dùng số này để xếp tốc độ hai model.

VRAM ghi baseline allocated/reserved, peak allocated/reserved và incremental
peaks. Đây là stats allocator PyTorch, không phải tổng VRAM hệ thống. Model
load loại khỏi timing; allocator cache còn tồn tại giữa cells, nên reserved
peak có thể phụ thuộc warm-up/order. Có checkpoint mỗi measured cell; OOM
được ghi rồi dừng model, giữ các cells còn lại missing, không đổi policy/dtype.
Ctrl+C/load error ghi stop.json. Không resume/retry tự động: dùng run directory
mới để tránh trộn fingerprints hoặc chọn lại lần trả lời tốt hơn.

## Bảng so sánh hiện tại và cách tính

[metrics.json](metrics.json) có nhóm **model × task × language × branch**,
A/B transitions và consistency. Hiện recorded=0, missing=240 trên tập pilot
đang có; các nhóm ba task còn thiếu có expected=0, không được coi là covered.
Accuracy, latency, VRAM đều null; các count flip=0 với denominator=0 chỉ là
bộ đếm chưa có observation, không phải bằng chứng hai nhánh tương đương.

| Metric | Qwen A/B | Gemma A/B |
|---|---|---|
| Prediction flips, correct→incorrect, incorrect→correct | Chưa đo | Chưa đo |
| Thay đổi EN–VI disagreement | Chưa đo | Chưa đo |
| Invalid/failed/OOM của model | Chưa chạy; không có model attempts | Chưa chạy; không có model attempts |
| Latency p50/p95 | null | null |
| Peak allocated/reserved VRAM | null | null |

Sau run, flips/correct transitions chỉ dùng A/B đều valid trên cùng ID và
language. Invalid/failed/OOM/missing báo riêng; all-expected accuracy có đủ
denominator. Thay đổi EN–VI disagreement dùng **cùng tập four-way-valid**
EN-A, VI-A, EN-B, VI-B, không so hai denominator khác nhau. Percentile nội suy
tuyến tính trên các generation thành công, kể cả response invalid; failed
không lẫn vào latency thành công. Giữ per-cell latency/error để xem failed.

## Phân bố độ phân giải của 813 ảnh

Tái tổng hợp từ audit kích thước, không chạy model trên main:

| Cạnh dài JPEG local | Số ảnh |
|---|---:|
| ≤512 | 352 |
| 513–640 | 458 |
| >640 | 3 |
| Tổng | 813 |

461 ảnh bị bước thumbnail giảm, gồm 27 pilot và 434 main. Pet main 160 ảnh
đều không bị giảm ở bước này; TallyQA chỉ 3/120. RePOPE/VSR ảnh hưởng nhiều
hơn. Xem [resolution_distribution.json](resolution_distribution.json) và
[kích thước từng ảnh](../../audits/2026-11-24/image_dimensions.jsonl).

Audit CPU trước đó thấy tensor A/B khác 27/30 pilot ở mỗi processor. Đây
không phải prediction flips, accuracy gain, latency hoặc VRAM evidence.
Gemma vẫn ép 896×896 ở cả A/B: B tránh một lần downsample nhưng **không sửa
méo tỷ lệ** của processor. Qwen B có thể tạo nhiều patch hơn trong cùng pixel
bounds; chưa đo tính ổn định trên GPU. Không chọn policy bằng cách tối đa
hóa accuracy pilot, không dùng main test outputs hoặc claim significance từ
30 ảnh; mỗi task chỉ 6–8 ảnh sau bổ sung, giới hạn suy rộng rất lớn.

## Recommendation và gates M1 đến M3

**Recommendation hiện tại: tạm giữ A trong draft, chưa phê duyệt freeze.**
Lý do là A đã có engineering pilot lịch sử, trong khi chưa có GPU comparison
đa task để chứng minh B ổn định/khả thi trong 6 GB. Đây không phải kết luận
A chính xác hơn, nhanh hơn hoặc tốt hơn về thị giác. B có lợi thế hợp lý là
giữ chi tiết nguồn lâu hơn và tránh resampling dư, nhưng cần đo tokens,
invalid/OOM/VRAM/latency thật trước đổi policy. Nếu B chạy ổn, giữ toàn ảnh
và chi phí chấp nhận được, nhóm có thể ưu tiên B kể cả accuracy pilot không
cao hơn. Không sửa config chỉ từ tensor difference hoặc pilot accuracy.

| Gate | Trạng thái sau kiểm tra | Điều còn thiếu |
|---|---|---|
| M1 main data QA | IN_PROGRESS | 1.000 main chưa được human A/B approve/import đầy đủ |
| M2 final protocol/freeze | PENDING | Nhóm chốt preprocessing; frozen=false, không có freeze receipt |
| M3 main GPU smoke | NOT_RUN | Chưa qua M1/M2. Pilot A/B là diagnostic trước freeze riêng, hiện blocked coverage; kernel smoke không thay M3 |

Nếu nhóm chọn B, chỉ đề xuất tạo policy ID/config/protocol version mới và
hash/receipt sau phê duyệt; không sửa historical config, main manifests hoặc
gate. Chưa mở full main 4.000 cells, RQ3/RQ4 hoặc C. Ưu tiên trước 03/12 là
QA 24 mẫu bổ sung và một run 240 cells, không thêm repeats/thí nghiệm phụ.

## Lệnh tái lập

Từ root, dùng đường output mới nếu artifact đã tồn tại:

```powershell
.venv/Scripts/python.exe scripts/validate_image_ab.py plan --output reports/validation/image_ab_v1/preflight_rerun.json
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py hardware --output reports/validation/image_ab_v1/hardware_rerun.json
.venv/Scripts/python.exe reports/validation/image_ab_v1/propose_subset.py
.venv/Scripts/python.exe reports/validation/image_ab_v1/collect_evidence.py
.venv/Scripts/python.exe -m pytest tests/test_image_ab.py -q
.venv/Scripts/python.exe -m pytest -q
```

Sau khi có manifest pilot mới đủ coverage/QA/exclusions và đã kiểm plan:

```powershell
$env:HF_HOME = "$PWD/.cache/huggingface"
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --manifest data/pilot/image_ab_reviewed_v1/pilot_manifest.csv --model qwen --output results/pilot/image_ab_v1/run_001/qwen --execute
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --manifest data/pilot/image_ab_reviewed_v1/pilot_manifest.csv --model gemma --output results/pilot/image_ab_v1/run_001/gemma --execute
.venv/Scripts/python.exe scripts/validate_image_ab.py analyze --manifest data/pilot/image_ab_reviewed_v1/pilot_manifest.csv --inputs results/pilot/image_ab_v1/run_001/qwen results/pilot/image_ab_v1/run_001/gemma --output reports/validation/image_ab_v1/metrics_run_001.json
```

Đường manifest reviewed là **đầu ra cần chuẩn bị, hiện chưa có**. Lệnh run
offline dùng cache/revisions hiện có, không tự tải weights hoặc fallback.
Không dùng --execute để bỏ gate; mọi blocker vẫn bị chặn trước adapter load.

## Files và kiểm thử

- `src/vlmbench/image_ab.py`: plan, độc lập pilot gates, A/B, quan sát processor,
  timing/memory/checkpoint và metrics.
- `scripts/validate_image_ab.py`: hardware/plan/run/analyze.
- `tests/test_image_ab.py`: synthetic unit tests cho gates, không đổi ảnh,
  processor passthrough, OOM, pairing/denominators, tamper và orchestration.
- Thư mục report này: proposals, evidence hardware/gates và NOT-RUN metrics;
  scripts tạo lại proposal/evidence. Không có ảnh, weights hoặc simulated
  predictions trong report.
- README/docs/reports navigation và completion: trạng thái hiện tại, ngày
  thuyết trình, bước tiếp. Không sửa configs, parser, adapters/runners cũ,
  source JPEG, main/pilot manifest cũ, human decisions hoặc audit cũ.

Full suite thực: **416 passed/20,77 s**, gồm **20 tests mới** cho A/B. Xem
[software_checks.json](software_checks.json). Các lần targeted ban đầu phát
hiện thiếu source fixture khi không có proof và đọc UTF-8 bằng codec Windows;
đã sửa fail-closed planner/test fixture trước suite cuối.

Unit tests dùng fake torch/adapter trong thư mục pytest tạm, có nhãn synthetic;
không sao chép outputs giả thành evidence. Harness đã CPU-tested, actual
model generation/latency/memory instrumentation vẫn chưa GPU-validated do
coverage gate. Test receipt ghi kết quả suite thực, tách khỏi kernel thật.

[Preservation receipt](preservation.json): 813 JPEG khớp hash audit; 416 file
Git cũ ngoài năm docs được cập nhật giữ nguyên nội dung Git, 103 local links
đạt. Hai notebooks có khác biệt LF/CRLF so với blob Git, không có thay đổi
nội dung Git; không stage chúng. Runtime/config/main manifests/review JSON
cũ không đổi. Chi tiết file mới và hash code nằm trong receipt/thư mục này.
