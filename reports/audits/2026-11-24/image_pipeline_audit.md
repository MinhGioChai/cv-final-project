# Audit image pipeline và kế hoạch so sánh chính sách ảnh

Ngày 24/11/2026, đối chiếu code tại commit `c215d3c` và dữ liệu local.
**512 px là bước tiền xử lý thực sự trước VLM.** Review HTML nhúng nguyên
bytes ảnh lưu trong manifest; JSON review tải về không chứa ảnh. Gemma còn
resize thành 896×896 bên trong processor, nên pipeline không giữ tỷ lệ xuyên
suốt. Cấu hình main vẫn `frozen=false`, `freeze_receipt=null`; không có model
inference mới hoặc thay đổi runtime/config/QA trong audit này.

## 1 JSON review và ảnh trong HTML

| Thành phần | Nội dung ảnh thực tế |
|---|---|
| JSON review main v2 | `context` và `decisions`: IDs, manifest/template/row hashes, câu VI, hai lượt quyết định và history. Không có base64, ảnh resize hay `image_path` trực tiếp. |
| CSV cùng gói | `image_path` và `image_sha256` cùng provenance/labels; đây là nơi trỏ đến file ảnh local. |
| HTML main v2 | JSON payload nội bộ có `review` và `cards`; `cards[].image` là data URL base64 của `image.read_bytes()`. Bytes JPEG nguyên vẹn, không thumbnail hoặc re-encode khi xuất review. |
| Nút Tải JSON | Chỉ `JSON.stringify(review)`, không stringify toàn bộ payload/cards. JSON nhận diện mẫu qua IDs/hash, importer đối chiếu manifest rồi đọc ảnh local. |
| Pilot label QA và main v1 lịch sử | Cùng nguyên tắc: HTML có ảnh, JSON quyết định không có ảnh. Không sửa các artifacts cũ. |

Đã giải mã và đối chiếu SHA256 **1.000/1.000 cards main v2**, thêm 1.000 cards
main v1 và 30 cards pilot lịch sử với ảnh được manifest tham chiếu. Đã kiểm
46 JSON đang có: 22 main v1, 22 main v2 và 2 pilot; không có image data URL.
JSON mới do reviewer gửi vẫn cần qua importer, không coi mọi JSON bất kỳ là
đã được kiểm chỉ vì cùng đuôi file.

Nguồn: [exporter v2](../../../src/vlmbench/main_review_v2.py),
[template v2](../../../src/vlmbench/main_review_v2_template.html),
[main v1](../../../src/vlmbench/main_review.py),
[pilot QA](../../../src/vlmbench/label_qa.py).

## 2 Các nhánh xử lý ảnh

```text
Ảnh JPEG được manifest tham chiếu, có SHA256
  ├─ Review: đọc nguyên bytes → base64 trong HTML → CSS object-fit:contain
  │           → tải JSON chỉ gồm context và quyết định
  └─ Inference: Image.open → convert RGB → thumbnail max edge 512 LANCZOS
                → model processor → tensor CUDA → generate
```

Cả `pilot_runtime.run_pilot`, `gemma_diagnostic.run_gemma_pilot` và
`baseline_runtime.run_main` đều tạo ảnh RGB trong RAM rồi gọi
`thumbnail((image_max_edge, image_max_edge), LANCZOS)`. Các configs đang dùng
đặt `image_max_edge=512`. Ảnh nhỏ hơn giới hạn không bị phóng to ở bước này;
ảnh lớn bị thu theo tỷ lệ, có sai số làm tròn số pixel. Ảnh này được truyền
trực tiếp vào `adapter.generate`, rồi `processor(images=[image], ...)`.
Notebooks local/cloud dùng launcher/adapters này, không có pipeline ảnh riêng
để bỏ bước 512. Main mới là code/draft CPU-tested, chưa có main inference thật.

Nguồn: [pilot runtime](../../../src/vlmbench/pilot_runtime.py),
[Gemma runtime](../../../src/vlmbench/gemma_diagnostic.py),
[main runtime](../../../src/vlmbench/baseline_runtime.py),
[draft config](../../../configs/baseline_v3_draft.yaml).

Ở đây “ảnh gốc” là **bytes asset đã lấy từ provider và lưu local**. RePOPE
dùng JPEG asset của mirror, VSR dùng COCO, TallyQA dùng Visual Genome và Pet
dùng JPEG từ archive chính thức. Audit không khẳng định provider chưa resize
ảnh trước khi phân phối hoặc đó là độ phân giải máy ảnh ban đầu.

## 3 Kích thước đã ghi nhận

Đã đọc 1.030 dòng manifest: 30 pilot và 1.000 main, tương ứng **813 ảnh khác
nhau**. Mỗi dòng trong [image_dimensions.jsonl](image_dimensions.jsonl) ghi
sample ID, path/hash, kích thước JPEG, kích thước intrinsic trong review,
CSS hiển thị, EXIF orientation và kích thước RGB ngay trước processor.

Khoảng W và H dưới đây là min–max riêng từng chiều, không phải hai ảnh cụ
thể ở hai đầu khoảng. Số ảnh giảm kích thước tính theo ảnh khác nhau, không
theo số câu trên cùng ảnh.

| Tập | Ảnh | W gốc | H gốc | W trước processor | H trước processor | Ảnh giảm bởi 512 |
|---|---:|---|---|---|---|---:|
| Pilot RePOPE | 30 | 369–640 | 333–640 | 363–512 | 314–512 | 27 |
| Main RePOPE | 383 | 333–640 | 234–640 | 288–512 | 187–512 | 325 |
| Main VSR | 120 | 335–640 | 334–640 | 335–512 | 287–512 | 106 |
| Main TallyQA | 120 | 256–1024 | 256–768 | 256–512 | 256–500 | 3 |
| Main Pet | 160 | 258–500 | 225–500 | 258–500 | 225–500 | 0 |

**Kích thước review intrinsic bằng kích thước JPEG gốc ở mọi card đã kiểm.**
Kích thước vẽ trên màn hình không cố định: main có `width:100%`,
`max-height:650px`, `object-fit:contain`; pilot giới hạn cao 660 CSS px.
Modal dùng lại cùng data URL, với `max-height:85vh`. Kích thước còn phụ thuộc
viewport/panel/zoom, không phải ảnh đã được tạo lại ở 512 px. `contain` giữ
toàn bộ ảnh và tỷ lệ bên trong ô; khoảng trống của ô không phải padding được
ghi vào file ảnh. Chưa đo layout browser thực tế trong phiên này, nên không
gán số CSS px cụ thể cho từng ảnh.

Ví dụ chuỗi W×H đã đo bằng CPU:

| Trường hợp | JPEG và review intrinsic | Trước processor A | Sau Qwen processor A | Sau Gemma processor A |
|---|---|---|---|---|
| Pilot `repope_adversarial_104803044cb7c965` | 640×480 | 512×384 | 532×392 | 896×896 |
| Cùng ảnh, bỏ thumbnail ở policy B | 640×480 | 640×480 | 644×476 | 896×896 |

### Processor Qwen

Trong môi trường `transformers==4.57.1` hiện tại, đường AutoImageProcessor
chọn `Qwen2VLImageProcessorFast` khi không truyền `use_fast`; adapter không
pin rõ cờ này. Đã đối chiếu Qwen2.5 processor dùng AutoImageProcessor và không
thêm override resize khi gọi xử lý ảnh. Cần ghi class/cấu hình thực tế cho run
mới; không suy ngược class đã dùng trong run lịch sử nếu metadata thiếu.

Qwen dùng `smart_resize`: hai chiều là bội của 28 (patch 14 × merge 2), với
min/max pixel đang override là 200.704 / 401.408. Tỷ lệ được giữ xấp xỉ, có
thay đổi do lượng tử hóa kích thước theo patch. Điều này **có thể phóng to lại
thumbnail**: 512×384 có 196.608 pixel, dưới min, nên thành 532×392. 512 không
phải giới hạn cạnh của tensor cuối. Tensor Qwen là chuỗi patch, không phải
tensor vuông `[1,3,512,512]`.

Checkpoint mặc định có min/max 3.136 / 12.845.056, khác override hiện tại.
Vì vậy “ảnh gốc + mặc định” thay cả thumbnail và ngân sách processor; phải
tách nó khỏi phép so sánh chỉ bỏ thumbnail. `to_dict().size` của fast class
có thể còn chứa defaults; cần đọc cả min/max và grid thực đo, không chỉ `size`.

### Processor Gemma

Adapter bật `use_fast=False`, `do_pan_and_scan=False`. Cached preprocessor
đúng revision đặt `do_resize=true`, `size={height:896,width:896}`, bilinear.
Gemma processor mặc định cũng tắt pan-and-scan trong đường gọi hiện tại.
Ảnh không vuông được resize trực tiếp về **896×896**, làm méo tỷ lệ. Không có
center crop hoặc letterbox để giữ tỷ lệ trong đường này. Cả A và B cho tensor
`[1,3,896,896]`, nhưng shape giống nhau không có nghĩa pixels giống nhau.

CPU probe đã chạy image processor trên 30 pilot ×2 model ×3 policies =
**180 bản ghi**, không load weights/tokenizer và không gọi generate. Ở cả
hai model, tensor A và B khác ở **27/30 ảnh**, trùng ở 3 ảnh vốn không bị
thumbnail giảm. Gemma có `num_crops=0` trên mọi probe. Đây là bằng chứng về
tiền xử lý, chưa phải prediction flip, performance, VRAM hoặc latency GPU.

Xem [processor_dimensions.jsonl](processor_dimensions.jsonl),
[processor_configs.json](processor_configs.json) và [summary.json](summary.json).
Code processor đối chiếu từ package local 4.57.1: Qwen `smart_resize/_preprocess`,
Gemma `preprocess` và `Gemma3ProcessorKwargs`. Config checkpoint được đọc offline
theo exact revisions trong baseline draft; receipt ghi SHA256 config.

## 4 Crop padding tỷ lệ và việc giữ ảnh gốc

| Kiểm tra | Kết quả và phạm vi |
|---|---|
| Center crop | Không có trong code pipeline của repo hoặc đường processor đang kích hoạt. |
| Crop khác | Gemma có code pan-and-scan trong thư viện nhưng repo tắt; CPU probe không tạo crop. |
| Padding ảnh | Không thấy spatial padding/letterbox trong đường hiện tại. Qwen lặp frame tĩnh để đủ temporal patch là xử lý trục thời gian, không phải viền đen quanh ảnh. Text padding không phải padding ảnh. |
| Tỷ lệ trước processor | PIL thumbnail giữ tỷ lệ tới sai số làm tròn; không ép vuông, không upscale. |
| Tỷ lệ sau processor | Qwen thay đổi nhẹ theo grid; Gemma ép 896×896, có méo đối với ảnh không vuông. |
| EXIF | Repo không gọi exif_transpose. Cả 813 ảnh đang dùng không có orientation khác 1 cần xử lý; ảnh bổ sung sau này phải kiểm lại. |
| Ghi đè JPEG | Các runner/review chỉ đọc và biến đổi trong RAM, không gọi image.save. Materializers ghi bytes nhận từ nguồn, có cache/checksum guards; không re-encode ảnh cho review/model. |
| Bảo toàn trong phiên | 813 ảnh khớp manifest SHA256; tổng 1.296 file đầu vào được so hash trước/sau audit, gồm code/config/data theo Git, ảnh, review HTML, pilot raw và ZIP local. |

Metadata `image_variant=original` hiện chỉ nhận diện variant nguồn không bị
thay thế theo RQ4. Nó **không có nghĩa bỏ thumbnail hoặc đưa nguyên kích
thước vào vision encoder**. `image_sha256` là hash bytes JPEG nguồn;
`image_preprocess` mới mô tả biến đổi. Tensor hashes trong probe ghi nhận
khác biệt pixels sau processor, không thay thế source hash.

Nguồn giữ bytes: [main RePOPE images](../../../src/vlmbench/main_images.py),
[task images](../../../src/vlmbench/task_images.py),
[pilot materializer](../../../src/vlmbench/datasets/repope.py).

## 5 Đề xuất so sánh trên 30 ảnh pilot

### Dữ liệu và ba chính sách

Dùng **đúng 30 ảnh RePOPE pilot đã được QA**, giữ exclusions main, IDs, nhãn,
EN/VI và prompts. Đây là sensitivity kỹ thuật trên pilot, không phải kết quả
RQ2 bốn task và không đủ để kết luận generalization. Chọn đủ 30 trước outputs,
không chọn theo ảnh model trả lời tốt/xấu. Có thể giảm xuống 24 theo sáu nhóm
category×label, 4 ảnh/nhóm, nếu nhóm quyết định và ghi danh sách trước run.

| Policy | Ảnh trước processor | Processor | Ý nghĩa |
|---|---|---|---|
| A 512 hiện tại | RGB → thumbnail max edge 512 LANCZOS | Overrides hiện tại | Baseline kỹ thuật để đối chiếu |
| B ảnh gốc cùng processor | RGB, bỏ thumbnail | Giữ nguyên mọi kwargs/class của A | Cô lập ảnh hưởng của bước 512 |
| C ảnh gốc mặc định checkpoint | RGB, bỏ thumbnail | Bỏ override pixel của Qwen; dùng defaults ảnh, pin cùng class/version; Gemma mặc định no pan-and-scan | Nhánh bổ sung, đo thay cả chính sách processor |

**Ưu tiên A–B:** 30 ảnh ×2 ngôn ngữ ×2 model ×2 policies = **240 cells**.
Nếu thêm C thì 360 cells tổng, chưa tính warm-up/repeats. B và C có thể giống
nhau trên nhiều ảnh, riêng Gemma cùng cách resize; không coi là ba phép đo độc
lập. Không gọi C là mặc định mọi thứ nếu vẫn giữ class/precision/generation để
kiểm soát các yếu tố ngoài ảnh.

Giữ cùng model/revision, Qwen NF4/FP16 và Gemma NF4/BF16, seed, greedy,
batch=1, max_new_tokens=8, attention, parser và prompt bytes giữa policies.
Không sửa prompt để cải thiện accuracy khi đang so ảnh. Existing team launcher
giới hạn 10 mẫu và legacy Gemma cũng giới hạn 10: run 30 ảnh cần harness
diagnostic riêng được nhóm duyệt, **không tăng giới hạn pilot cũ hoặc bật main**.

### Đo dự đoán

Giữ raw và parsed output của mọi lượt. Báo từng model/ngôn ngữ: số jointly
valid, prediction flip A↔B, đúng→sai, sai→đúng, invalid/failed/OOM/missing và
accuracy/negative-only FPR cùng denominator. Báo thay đổi EN–VI disagreement
và ΔFPR giữa policies; tập mẫu nhỏ chỉ phân tích mô tả, không chọn policy
bằng cách lấy main accuracy tốt nhất. Tensor khác chưa chứng minh dự đoán khác.

### Đo VRAM và thời gian

Một GPU/model mỗi lần, cùng môi trường và batch. Load model ngoài thời gian
đo; warm-up 2 lượt/model/policy với IDs pilot ghi rõ, không tính vào số đo.
Chạy A/B xen kẽ AB–BA theo danh sách seed cố định, từng image/language/model
là một cặp. Đề xuất 3 repeats/cell: **720 measured generations cho A–B**, cộng
warm-up; nếu cần rút gọn, quyết định trước và báo rõ chỉ một repeat. Repeats
không tạo thêm ảnh độc lập và không được chọn lần có prediction đẹp nhất.

Ghi riêng thời gian đọc/decode/RGB/thumbnail, processor CPU, H2D, generate
và decode output; có tổng end-to-end. Dùng perf_counter và CUDA synchronize
ở ranh giới GPU để tránh chỉ đo thời gian enqueue. Log số input/visual/output
tokens, tensor shapes/grid và peak memory theo từng cell. Timer `elapsed_ms`
trong adapters hiện tại bỏ qua PIL/thumbnail; Qwen và Gemma còn khác ranh giới
decode/logit-trace, nên không dùng nó một mình để kết luận tốc độ giữa model.

Sau warm-up, synchronize, ghi allocated/reserved baseline lúc model đã load,
reset peak stats rồi ghi **peak allocated, peak reserved và phần tăng so với
baseline**. Chụp cả GPU model, VRAM capacity, package/dtype và các tiến trình
GPU khác. Đây là bộ nhớ do PyTorch quản lý, không tự gọi nó tổng VRAM hệ
thống; nếu dùng NVML thêm, ghi riêng cadence/định nghĩa. Báo median/p95 latency
và paired delta/ratio, peak MiB/max và OOM; không xóa OOM hoặc tự giảm ảnh/token.

Gemma A/B có cùng tensor shape nên có thể không giảm đáng kể vision VRAM khi
giữ bước 512; đó là giả thuyết cần đo. Qwen B/C có thể có nhiều visual tokens
hơn và tốn VRAM hơn. Không ghi con số ms/MiB dự đoán thành kết quả thực.

### Artifacts và điều kiện quyết định

Run riêng dưới namespace `results/pilot/image_policy_comparison_v1/` mới,
lưu config snapshot, source/preprocessor hashes, code/environment, IDs,
policy/class/kwargs, kích thước từng giai đoạn, raw/parsed, attempts, token
counts, timing/memory và summary. Không ghi vào outputs pilot lịch sử hoặc
results/main, không tái sử dụng checkpoint giữa các policies khác hash.

Sau khi nhóm duyệt kế hoạch, mới xây harness CPU-tested rồi xác nhận bounded
GPU run. Trước khi quyết định main policy, xem prediction flips/invalid/OOM,
tài nguyên, tổn thất do resize và giới hạn pilot. Nếu đổi policy, tạo config/
protocol version và receipt mới theo quy trình; không sửa âm thầm config
draft hoặc lịch sử. Main vẫn cần đầy đủ review A/B, final protocol/freeze
receipt và explicit execute, kể cả khi pilot comparison thành công.

## 6 Tái kiểm và trạng thái

Chạy từ root sau khi restore đủ ảnh/HTML local; script chỉ ghi audit evidence
trong thư mục này. Trên máy mới thiếu cached processors, CPU probe phải báo
thiếu dữ liệu/cache, không tự tải weights hoặc truy cập token.

```powershell
.venv/Scripts/python.exe reports/audits/2026-11-24/audit_image_pipeline.py
.venv-infer/Scripts/python.exe reports/audits/2026-11-24/audit_image_pipeline.py --processor-probe
```

Lệnh thứ hai chỉ chạy image processors offline trên CPU, không gọi model.
Lần probe đầu dùng return_tensors=np bị fast Qwen từ chối; đã sửa audit helper
để dùng pt giống runner rồi probe đủ 180 records đạt. Đây không phải thay
runtime hoặc một lần software-suite/model-run. 396 tests ở completion v30
vẫn là lần v13 ngày 22/11, không được tính là test mới của audit.

Đã thực hiện inventory/hash verification và CPU processor probe. Chưa chạy
so sánh dự đoán/VRAM/thời gian GPU. Main configs/prompts, runtime, human review,
freeze gate, ảnh, raw pilot và các ZIP giữ nguyên. Bước tiếp là nhóm chốt có
thực hiện A–B (và C tùy chọn) với số repeats nào trước khi thay main policy.
