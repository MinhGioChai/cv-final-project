# Project completion log — context bàn giao

**Phiên bản nhật ký:** v21 · **Cập nhật:** 20/11/2026 (Asia/Saigon).
**Đặc tả hiện hành:** [Codex Handoff V3](../docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md),
do người dùng cung cấp. [Mục lục docs](../docs/README.md), [reports](README.md).

**Nhắc pilot Gemma theo yêu cầu người dùng:** đã hoàn tất pilot kỹ thuật
ngày 19/11, NF4/BF16 trên cùng 10 mẫu Qwen: 20/20 valid, không failed/invalid/
missing/nonfinite, resume giữ checksum và đã có metrics/CI. Không còn nhắc
setup/Gemma pilot như việc chưa làm. QA ảnh/nhãn 30 mẫu đã approved theo
JSON người dùng và import ngày 20/11 tại v10; Stage 1
toàn bộ và main benchmark chưa hoàn tất. [Bằng chứng v7](stage1/v7/completion.md).
**Việc mới nhất:** [v8](stage1/v8/completion.md) có QA packet 30 mẫu, metadata
adapters/frame bốn task và RePOPE selection 600 câu/383 ảnh. Người dùng chốt
cap2; bản dịch vẫn approved 30, QA vẫn pending 30. Chờ review thật, không tự approve.
**Tiếp tục v20:** [v9](stage1/v9/completion.md) chọn đủ 1.000 candidate/783 mã
ảnh và đã có 383 ảnh + bilingual draft cho 600 RePOPE. VI main vẫn requires_review,
QA pending; 400 mẫu task khác còn thiếu ảnh/VI. Không có model inference mới.
**Mới nhất v21:** [v10](stage1/v10/completion.md) đã import human QA pilot 30/30;
main có đủ 783 ảnh và 1.000 bilingual draft, toàn bộ main vẫn requires_review/
QA pending. Đã xuất [22 gói review main](stage1/v10/main_review/index.html).
Không inference mới, chưa metadata/runner/freeze hoặc full-run.

## Đọc trước khi tiếp tục

1. File này và [completion data/QA gần nhất](stage1/v10/completion.md).
   [V9](stage1/v9/completion.md) giữ selection 1000 và draft RePOPE ban đầu.
   [V8](stage1/v8/completion.md) giữ QA packet/inventory và quyết định cap2.
   Model generation gần nhất vẫn là [Gemma v7](stage1/v7/completion.md).
   [V6](stage1/v6/completion.md) giữ lịch sử FP16 rỗng trước khi sửa.
   Evaluation implementation ở [v5](stage1/v5/completion.md), Qwen ở [v4](stage1/v4/completion.md).
2. [Handoff V3](../docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md).
3. [Protocol V3](../docs/research/RESEARCH_PROTOCOL_V3.md),
   [kế hoạch/checklist](../docs/research/IMPLEMENTATION_PLAN_V3.md) và
   [audit 12/11](audits/2026-11-12/repository_audit_v3.md).

V3 mới hơn theo chỉ dẫn người dùng, dù số khác chuỗi V4.2. Giữ báo cáo và
evidence cũ; cập nhật trạng thái thật, quyết định, việc còn lại và concrete next
action sau meaningful work. Append lịch sử có ngày; không biến test cũ thành
lần chạy mới, kế hoạch thành kết quả hoặc acceptance ngôn ngữ thành image QA.

## Scope được cập nhật theo V3

- Zero-shot paired EN–VI; Qwen2.5-VL-3B và Gemma 3 4B IT; không training/LoRA.
- **P0 RQ1:** negative-only RePOPE ΔFPR = VI − EN, riêng từng model,
  paired image-cluster CI; không mặc định VI kém hơn.
- **P0 RQ2:** gaps/disagreement/invalid trong RePOPE, VSR, TallyQA và Pet.
- Main dự kiến 600/120/120/160 = 1.000 row, 4.000 inference. Row khác unique
  image; target/config chưa freeze; không tự giảm scope/thay model.
- **P1 RQ3:** paraphrase khoảng 40 mẫu × 2 variants/language, có điều kiện.
- **P1 RQ4:** visual evidence khoảng 30 image pairs, có điều kiện.
- **P2:** negation riêng, attention/activation và mở rộng model/dataset.
  Không nâng P1/P2 thành P0; không có RQ3/RQ4 vẫn đủ nghiệm thu main theo V3.

Giữ source labels, human review thật, image exclusions và staged scope. Không
gán người, chỉ workstreams. Sau audit 12/11, ngày 16/11 người dùng yêu cầu
triển khai bước tiếp theo. P0 paired evaluation/metrics/bootstrap đã thực hiện.
Full-run và conditional diagnostics vẫn theo các gate V3.

## Trạng thái có bằng chứng

| Hạng mục | Trạng thái |
|---|---|
| Foundation | Schema/CLI/atomic I O, RePOPE ETL, sampler, source audit, QA/review, parser, leakage/resume có thể tái sử dụng |
| Pilot data | 30 row/30 ảnh; source audit 30/30 matched; giữ 10 mẫu ban đầu và thêm 20 |
| Language/image QA | Pilot 30 translation approved giữ nguyên; 20/11 import JSON người dùng, 30 QA approved vào stage1_qa_v1. Không bịa reviewer thứ hai |
| Local Qwen | Run v4 ngày 10/11: 10 mẫu × EN/VI = 20 lượt thật; failed/invalid/missing=0 |
| Timing/VRAM | Median processor+generation 492,13 ms; PyTorch peak allocated 2483,91 MiB, không phải tổng device VRAM hoặc tải/load |
| Environment | .venv-infer/CUDA matmul đã chạy ở v4 trên RTX 3060 Laptop 6144 MiB; torch 2.7.1+cu126 |
| Software tests | Full suite thực phiên v21 ngày 20/11 đạt 302 passed/4,13 s trong .venv, thêm 33 tests image/VI/main review so với v9 |
| Gemma | 19/11 NF4/BF16, 10 mẫu/20 lượt thật valid, failed/invalid/missing/nonfinite=0; resume giữ raw hash. Median 10208,95 ms có trace, peak allocated 5720,93 MiB |
| Colab/Kaggle | Notebooks/bundle/dry-run có; chưa real generation trên cloud |
| Evaluation | evaluate/statistics CLI và image-cluster percentile bootstrap. Actual Qwen ở v5 và Gemma ở v7; các task khác mới toy tests |
| QA tooling | Pilot đã import human review thật; main có 22 gói offline/source-bound import, hai reviewer dịch và QA riêng, chưa main approvals |
| Main | Đủ 1.000 rows/783 ảnh có SHA256 và EN–VI draft; source fields giữ nguyên, ID/byte leakage check đạt. 1.000 requires_review/QA pending; baseline chưa freeze |
| Reports | Word 2 trang và context 11 trang ngày 11/11 giữ nguyên theo V4.2; chưa có xác nhận đã nộp/proposal mới |
| V3 audit | Đã đọc đặc tả, mapping/gaps/checklist và mục lục; chưa triển khai major runtime changes |
| Kiểm tra 12/11 | 118 file bảo toàn checksum; 280 links hợp lệ; 6 dry-run plans và temporary packaging pass; không gọi model |
| Analysis 16/11 | EN accuracy 100%, VI 90%, disagreement 10%. Primary 5 negative ảnh cho ΔFPR +20 pp, empirical CI 95% từ 0 đến 60 |
| Gemma analysis 19/11 | EN 90%, VI 100%, disagreement 10%; FPR 20%/0%, ΔFPR −20 pp, CI −60 đến 0; năm negative ảnh, QA pending |

[Báo cáo thực nghiệm v4](stage1/v4/completion.md),
[Qwen measurements](stage1/v4/qwen_local_report.json),
[10 cases](stage1/v4/local_cases.md). Source-label matches EN 10/10 và VI 9/10
được tính lại qua evaluator v1, cùng paired analysis và CI. Image/label QA
pending, scope engineering pilot. Năm negative images giới hạn diễn giải CI.
[Completion analysis v5](stage1/v5/completion.md).

Pilot pool ba trang metadata không phải main sampling frame. Exclusions
giữ đủ 30 ảnh. Main cần QA nguồn/ảnh/dịch thật, không sửa nhãn theo model.

## Tài liệu và tổ chức file

- Current: docs/handoffs và docs/research; entry points README/START_HERE.
- [Archive V4.2](../docs/archive/README.md): ba nguồn gốc giữ bytes; root
  filenames là chuyển tiếp. Snapshots trước sửa navigation/guides cũng giữ.
- [Proposal index](proposal/README.md): hai Word và bản V3 người dùng nguyên
  văn; Word v1 chưa theo RQ/priority V3, không tự sửa lịch sử.
- Reports stage, code/configs, data paths, raw results, notebooks và ZIP cũ giữ.
  ZIP cũ chưa chứa đợt cập nhật docs V3; khi cần build output path mới.
- [Organization receipt](audits/2026-11-12/organization_receipt.json) và
  [verification](audits/2026-11-12/verification.json) ghi checksums/kiểm tra.

## Hành động kế tiếp

### QA và data main — ưu tiên hiện tại

**Cập nhật sau khi resume:** người dùng giao assistant chọn phương án chuẩn
bị phù hợp. Config main_preparation_v3.yaml giữ VSR random/test 60T/60F,
TallyQA 60 simple/60 complex với count-bin policy, tám giống Pet 20/lớp,
seed42 và frozen=false. Selection đủ 1.000/783 mã ảnh, RePOPE v8 giữ bytes.
V10 đã hoàn tất ảnh/bilingual draft cả bốn task: 1.000 row/783 ảnh; main chưa human QA.
Xem [guide review hiện tại](../docs/research/MAIN_REVIEW_V1.md) và
[readiness](stage1/v10/readiness.json). Các lựa chọn preparation không phải
approval cho freeze hoặc 4.000 inference.

1. Pilot QA đã xong: JSON người dùng đủ 30 approved, dry-run/import hợp lệ,
   manifest mới `data/pilot/stage1_qa_v1/pilot_manifest.csv`. Không review/chạy
   lại pilot. Mở [mục lục main](stage1/v10/main_review/index.html), làm từng gói,
   tải `<packet>_reviewed.json` và lưu `data/reviews/main_review_v1/`. Dùng
   [workflow main](../docs/research/MAIN_REVIEW_V1.md) cho hai reviewer dịch và
   QA ảnh/nhãn riêng; source labels giữ nguyên. Chưa có main human approvals.
2. Người dùng đã chốt **600 RePOPE, tối đa 2 câu/ảnh** trong câu trả lời async
   ngày 19/11. Config mới main_preparation_v2.yaml ghi lựa chọn, frozen=false.
   Source còn 470 ảnh sau loại pilot nên cap1 không thể đạt 600. Feasibility
   cũ cap2 có 379 ảnh/21 nội dung lặp giữa category. Selection mới đề xuất
   tránh trùng nội dung toàn cục: 600 câu/383 ảnh/0 trùng, 100 YES/100 NO mỗi
   category, seed42. Đây là trạng thái v8; v9 người dùng đã ủy quyền chọn
   phương án VSR/TallyQA/Pet, nhưng baseline content/protocol vẫn chưa freeze.
   [Sampling](stage1/v8/repope_sampling_v1.json), [data guide](../docs/research/MAIN_DATA_PREPARATION_V1.md).
3. Đã chọn các mẫu VSR/TallyQA/Pet theo phương án được người dùng ủy quyền.
   V10 đã materialize đủ 400 JPEG và VI draft, offline replay/hash và kiểm
   leakage tổng hợp đạt. Tiếp theo review toàn bộ main và hoàn
   thiện metadata/runner/freeze trước xác nhận full-run. Main vẫn 1.000 row/
   4.000 inference dự kiến, chưa tự giảm scope hoặc chạy model.

Stage 1 đang IN_PROGRESS. Pilot QA 30 đã approved; main QA/translation chưa approved.
Browser visual QA chưa làm được vì Computer Use tự dừng khi không xác định
chắc URL đủ để thực thi policy; không retry/bypass. JS syntax và backend
workflow tests đã pass, không ghi là đã kiểm giao diện trực quan.

### Checklist nhắc pilot Gemma

**Trạng thái hiện tại 19/11:** pilot kỹ thuật hoàn tất. Runner Gemma riêng
NF4/BF16 + token/logit trace khắc phục NaN FP16 và terminal EOS còn sót khi
decode. Cùng 10 mẫu Qwen, 20/20 valid, không OOM, raw/summary resume giữ hash.
Metrics/CI đã chạy; xem [completion v7](stage1/v7/completion.md),
[runtime report](stage1/v7/gemma_local_report.json). Không sửa parser,
legacy runtime hoặc source labels. Human QA 30 đã import thật tại v10 ngày
20/11. Bước tiếp theo là review main, baseline metadata/runner/freeze.

**Blocker trước sửa, đã khắc phục tại v7:** load thành công, generation success=4 nhưng
raw_response="" và INVALID_EMPTY=4. Parser đúng, chưa có output hợp lệ.
Evaluation/statistics từ raw đã lưu ở [v6](stage1/v6/completion.md), FPR/Delta
FPR undefined vì không có jointly valid pairs. GPU có hỗ trợ BF16; checkpoint
gốc dùng BF16, adapter hiện ép FP16. Giả thuyết bất ổn số học cần kiểm bằng
diagnostic NF4/BF16 có token/logit trace, output mới. Tại phiên v17 chưa đổi
code/config hoặc chạy diagnostic. V7 đã thực hiện và xác nhận nguyên nhân;
raw v1 vẫn giữ nguyên, không resume vào đó.

**Blocker cũ ngày 18/11, không tái diễn ở run 19/11:** lỗi
thực là `The paging file is too small ... (os error 1455)` khi load. Snapshot
chỉ đọc: RAM trống 1,63/15,69 GiB, pagefile tự động trên C 14.408 MiB, C trống
2,03 GiB và F trống 37,94 GiB. Hai weights shards có đủ file/kích thước, chưa
hash integrity. Tại snapshot cũ chưa có `gemma_smoke_v1.jsonl`. Khuyến nghị khi đó là lưu việc,
giải phóng RAM/dung lượng C và bổ sung pagefile F theo guide, restart rồi
chạy lại smoke 2 mẫu. Không yêu cầu tạo token mới để chữa lỗi 1455.
[Evidence chẩn đoán](diagnostics/2026-11-18/gemma_load_v1/diagnosis.json),
[bản sao load error](diagnostics/2026-11-18/gemma_load_v1/load_error.json).
Chưa sửa hệ thống/reboot hoặc khởi chạy model mới trong phiên chẩn đoán.

Đã có [hướng dẫn setup từng bước](../docs/setup_gemma.md) ngày 18/11.
Kiểm tra mới: `.venv-infer` dùng Python 3.12.10, torch 2.7.1+cu126,
Transformers 4.57.1, bitsandbytes 0.48.2, huggingface_hub 0.36.0; CUDA True
và nhận RTX 3060 Laptop GPU. Dry-run Gemma 2 mẫu đạt, không load/tải weights.
Không suy từ đó ra quyền truy cập hoặc khả năng fit VRAM.

- [x] Truy cập/load hoạt động theo run thật người dùng 19/11; không lưu token
  hoặc suy diễn xác nhận điều khoản ngoài bằng chứng hội thoại.
- [x] Người dùng đã nhập token qua prompt ẩn của helper theo log cung cấp 18/11;
  không lưu/đọc giá trị token, quyền remote chưa kiểm chứng độc lập.
- [x] Smoke BF16 2 mẫu valid rồi mở rộng cùng 10 mẫu EN–VI Qwen, lưu raw/token/
  logits/timing/VRAM và kiểm resume. Run cuối gemma_bf16_trace_v2.jsonl.
- [x] Tính metrics/CI Gemma và cập nhật completion v7 theo real evidence.
- [x] QA ảnh/nhãn 30 mẫu đã approved từ JSON người dùng, import v10 ngày 20/11.

Yêu cầu nhắc Gemma cho đến khi có kết quả và completion đã được đáp ứng.
Các phiên sau đọc v7 và ưu tiên việc còn lại, không yêu cầu setup lại Gemma.

Người dùng trả lời câu hỏi quyền Gemma bằng “Chưa, tiếp tục evaluation trước”.
Đây là lựa chọn ngày 16/11; ngày 18/11 yêu cầu mới là hướng dẫn setup Gemma.
Chưa có xác nhận đã chấp nhận license/cấu hình token. Hành động cụ thể tiếp
theo ở đầu phiên setup là cấp quyền/token. Cập nhật sau lỗi load 18/11:
token đã được nhập, weights có trong cache; ưu tiên xử lý pagefile/RAM như
blocker lúc 18/11 rồi chạy lại. Ngày 19/11 đã load được nhưng output rỗng;
hành động khi đó là diagnostic NF4/BF16 có version trước 10 mẫu. Sau người
dùng xác nhận triển khai, phiên v18 đã hoàn tất diagnostic + 10 mẫu/20 lượt.
P0 metrics/bootstrap v1 đã triển khai,
có 175 tests đạt trong phiên v12 và report từ raw pilot cũ. Bước tiếp theo là
rà soát scoring/CI v5 cho main protocol, human image QA và chuẩn bị dữ liệu
main. Hành động tiếp theo hiện tại là human image/label QA rồi data main;
Gemma pilot kỹ thuật đã hoàn tất, toàn bộ Stage 1 chưa hoàn tất.
Approval bản dịch hiện có đã được ghi nhận.

Method v1 dùng accuracy trên expected grid (invalid/failed/missing tính sai),
complete-case primary, sensitivity bounds cho unknown và percentile cluster
bootstrap B=5000/seed42 với pooled row weighting. Đây là lựa chọn triển khai
pilot do assistant chốt và ghi trong method report để nhóm rà soát trước main.
[Evaluation guide](../docs/research/EVALUATION_V1.md).

Ngày 23:59 11/11 là hạn proposal người dùng từng cung cấp và đã qua ở thời
điểm audit 12/11. Chưa biết đã nộp hay chưa; không ghi là đã nộp hoặc nhắc như
deadline tương lai. Kế hoạch bốn tuần V3 chưa được gán ngày bắt đầu/kết thúc;
06/12 từ V4.2 chỉ là mục tiêu nội bộ cũ. Không tự đổi lịch chính thức.

## Lịch sử phiên bản

### v1 — 09/11/2026: Hoàn thành Stage 0

Foundation và preflight 10 ảnh thật hoàn tất, 75 tests đạt, offline replay thành
công. Báo cáo gốc: [stage0/completion.md](stage0/completion.md).
Sửa tên file đề bài và phép tính contrast 240–320 inference.

### v2 — 09/11/2026: Chuẩn hóa bàn giao và kế hoạch Stage 1

Theo yêu cầu người dùng, giữ báo cáo completion và theo dõi qua các phiên bản.
Thêm nhật ký tổng này cùng hướng dẫn đọc ở `AGENTS.md`, liên kết từ README;
chốt thứ tự Stage 1 và ưu tiên proposal. Chỉ cập nhật tài liệu, không có dữ liệu,
QA, model inference hoặc kết quả test mới trong phiên này.

### v3 — 09/11/2026: Stage 1 v1 source audit và translation/review tooling

10/10 mẫu khớp annotations gốc; tải 1.002.905 bytes JSONL pinned, không tải
weights/ảnh mới. Tạo dictionary/template và 10 VI draft, export sheet có context,
import có audit/ảnh checksum/anti-stale/source-field checks. 119 tests đạt;
source replay offline và import idempotence đã kiểm tra. Stage 0 artifacts giữ
nguyên. Không có human approval hoặc inference mới. Chi tiết:
[Stage 1 v1 completion](stage1/v1/completion.md).

### v4 — 09/11/2026: Sửa classifiers theo phản hồi và mở rộng pilot

Người dùng đã xem 10 bản dịch v1 và yêu cầu bổ sung từ chỉ loại. Ghi lại phản
hồi thật, sửa 9 câu/giữ person; template v2 dùng dictionary có classifier_vi.
Giữ toàn bộ 10 mẫu cũ, chọn thêm 20 để đạt 30 ảnh, 5 YES/5 NO mỗi category;
30/30 audit nguồn khớp, 30 draft đầy đủ, exclusions tích lũy. 132 tests đạt,
offline/replay giữ artifacts. Kiểm kê GPU thật RTX 3060 Laptop 6 GB; chưa có
torch/transformers/accelerate trong venv, chưa chạy CUDA/model. Không tạo QA
người thứ hai hay ảnh/nhãn từ nhận xét ngôn ngữ. Chi tiết:
[Stage 1 v2 completion](stage1/v2/completion.md).

### v5 — 09/11/2026: Người dùng chấp nhận bản dịch; chuẩn bị local/Colab/Kaggle

Ghi nhận chấp nhận thật về bản dịch hiện tại, tạo manifest v3 approved về ngôn
ngữ, giữ QA ảnh/nhãn pending. Thêm adapters Qwen/Gemma, runner pilot chung,
pin revisions/runtime, raw records/resume/OOM/error redaction, 2 notebooks,
local scripts và private bundle. 144 tests đạt; 6 dry-run plans dùng cùng
protocol theo model. Chưa cài runtime inference, tải weights hoặc chạy GPU
thật; không có metrics model. Chi tiết [completion v3](stage1/v3/completion.md).

### v6 — 10/11/2026: Qwen đã chạy thật trên RTX 3060 trước Colab

Theo yêu cầu người dùng, cài inference venv, CUDA matmul và 144 tests đều đạt.
Tải Qwen weights và chạy NF4/FP16: 4 lượt đầu, resume thành 20 lượt trên 10
mẫu, không failed/invalid/missing, resume không trùng. Median 492,13 ms,
peak allocated 2483,91 MiB. Mô tả nhãn nguồn: EN 10/10, VI 9/10, một bất đồng;
chỉ là pilot nhỏ, chưa QA ảnh/nhãn/final. Gemma anonymous 401 và chưa có token.
[Completion v4](stage1/v4/completion.md).

### v7 — Khoảng 01:00 ngày 10/11/2026: Kiểm tra tiến độ và đính chính lịch

Người dùng xác nhận tiếp tục lúc 08:00 cùng ngày 10/11; đính chính mốc 11/11
assistant đã suy diễn trước đó. Đối chiếu timeline/artifacts: foundation và
Qwen pilot có bằng chứng thực; Gemma access, QA và proposal còn việc. Ưu tiên
proposal bản đầu buổi sáng và gỡ Gemma, giới hạn thời gian troubleshooting cloud.
Không chạy lại tests/inference trong phiên đánh giá. Xem
[progress review](progress_2026-11-10.md).

### v8 — 10/11/2026: Bổ sung giờ hạn proposal theo người dùng

Người dùng xác nhận có thể làm đến **23:59 ngày 11/11**. Đính chính đánh giá
v7: từ phiên 08:00 ngày 10/11 còn gần 40 giờ đến hạn, không cần coi đầu ngày
11/11 là hạn nộp. Kế hoạch: ngày 10/11 tiếp tục pilot/QA và có proposal nháp;
ngày 11/11 rà soát/chỉnh sửa, chừa thời gian nộp. Tiến độ hiện có dư địa hợp lý,
nhưng Gemma, QA và proposal vẫn chưa hoàn tất. Chỉ cập nhật lịch/tài liệu;
không có test, inference hoặc QA mới.

### v9 — 11/11/2026: Hoàn thành bản proposal Word v1 để nhóm rà soát

Theo yêu cầu người dùng, soạn tiếng Việt với bốn heading Problems, Related
Work, Proposed Method, Discussion. Giữ thiết kế 1.000 row/4.000 lượt dự kiến,
primary ΔFPR, cluster bootstrap, QA/exclusions, contrast/negation và giới hạn;
chỉ dùng bằng chứng Qwen thật từ v4. Đối chiếu 8 nguồn primary trên web, gắn
hyperlink trong bibliography. Proposal đề xuất primary trên cặp EN–VI cùng
valid, kèm exclusions/invalid sensitivity; cần đưa quyết định này vào protocol
freeze, chưa phải metric code đã triển khai hoặc kết quả đã tính.

Tạo Word, Markdown, bibliography và script dựng lại. Word/PDF xác nhận 2 trang;
đã xem cả hai PNG cuối và sửa font/đường viền tiêu đề. Renderer chuẩn thiếu
LibreOffice trong managed runtime Windows; dùng Word PDF export rồi rasterize
qua renderer của skill, không dùng LibreOffice desktop. Chưa có human approval
hoặc nộp bài; không chạy lại unit tests, inference hoặc QA ảnh/nhãn. Xem
[completion proposal](proposal/completion.md).

### v10 — 11/11/2026: Hồ sơ chi tiết để explore và soạn proposal bằng ChatGPT

Người dùng yêu cầu thêm Word chi tiết về đã, đang, sẽ làm và context cho ChatGPT.
Tạo hồ sơ 11 trang: mục tiêu/assignment, RQ gốc và related work, main data,
dịch/QA/protocol, implementation/runtime, toàn bộ 10 cases thật, blocker và
lệnh đang có, metrics/statistics/diagnostics, roadmap/câu hỏi mở, sources/
evidence paths và hai prompt để nghiên cứu/viết proposal. Giữ prototype CLI
khác contract dự kiến; main/QA/statistical tests chưa được ghi thành hoàn tất.

Đọc lại 30 row manifest: translation approved=30, image QA pending=30; raw
Qwen có 20 records và checksum khớp report v4. Không inference hoặc unit-test
run mới. Word PDF export và renderer skill cho 11 trang, đã xem từng PNG cuối;
không sửa proposal hai trang trước. Lưu nguồn Markdown/builder/verification.
Đây là hồ sơ bàn giao, chưa tự upload sang ChatGPT hay nộp bài. Xem
[completion hồ sơ](proposal/research_context_completion_v1.md).

### v11 — 12/11/2026: Tiếp nhận Handoff V3 và audit tổ chức repository

Đọc nguyên văn V3 mới, đối chiếu code/config/tests/data/reports; RQ1/RQ2 là
P0, RQ3 paraphrase/RQ4 visual evidence có điều kiện, negation riêng P2. Lập
audit, schema/output mappings, gaps, file plan, checklist bốn trạng thái và
gates mở rộng. Không gán cá nhân dù handoff có role gợi ý.

Tổ chức current handoff/protocol/plan và mục lục docs/reports/proposal. Ba
nguồn V4.2 được chuyển archive với checksum, root giữ chuyển tiếp; snapshots
trước sửa được giữ. File V3 người dùng và hai DOCX/nguồn v1 không bị ghi đè.
Guides sửa các câu trạng thái cũ gây nhầm và phân biệt lịch sử/pilot/final.

Kiểm tra mới: pilot validate đạt 30 row/30 ảnh, approval states giữ nguyên;
raw Qwen vẫn 20 records/hash cũ; 6 dry-run plans giữ đúng protocol/subset v4;
temporary bundle có V3 docs và checksum đúng, ZIP cũ không đổi. 280 local
links qua 41 Markdown files không lỗi; 118 protected files và 3 V4.2 sources/
12 snapshots được giữ nguyên. Đây không phải chạy lại 144 unit tests.

Đọc lại artifacts và kiểm tra offline theo verification riêng; không tải
dữ liệu/weights, chạy model, nâng QA, đổi runtime config hoặc tạo baseline/
diagnostic code. Suite 144 là lịch sử v4; kiểm tra audit mới ghi riêng. Latest
stage inference vẫn v4, Stage 1 nghiên cứu/full benchmark chưa hoàn tất.

### v12 — 16/11/2026: Triển khai paired evaluation metrics và bootstrap P0

Theo yêu cầu tiếp tục của người dùng, thêm evaluate.py/statistics.py và CLI
evaluate/statistics. Expected EN–VI grid dựa manifest/explicit selection,
phân biệt valid/invalid/failed/missing, kiểm tra provenance/parser/retry,
metrics bốn task, category breakdown, complete-case primary ΔFPR và unknown
sensitivity. Report có raw source lines, attempt, checksums và replay.

Bootstrap percentile theo namespace/image ID, pooled row weighting, B=5000,
seed42. Thêm 31 toy/provenance/CLI/statistics tests. Full suite mới đạt 175
passed trong .venv. Tính từ raw Qwen ngày 10/11 được EN 100%, VI 90%, 1/10
disagreement. Primary 5 negatives cho FPR 0%/20%, ΔFPR +20 pp, CI 0–60 pp.
Accuracy gap −10 pp, CI −30–0. Image QA vẫn pending, scope engineering pilot.

Đã kiểm tra token local và known HF caches chưa có Gemma; hỏi trạng thái chuẩn
bị quyền từ người dùng. Không có model generation hoặc human QA mới trong
phiên này. Báo cáo v4/dữ liệu pilot/exclusions tiếp tục truy vết qua checksums.
Method/scoring choices, limitations, verification và lệnh chạy ghi trong
[Stage 1 v5 completion](stage1/v5/completion.md). Stage 1 hai model và main
benchmark còn việc, P1/P2 giữ priority V3.

### v13 — 16/11/2026: Ghi nhận ưu tiên evaluation trước Gemma

Người dùng phản hồi câu hỏi async rằng chưa chuẩn bị quyền/token Gemma và
muốn tiếp tục evaluation trước. Ghi quyết định vào hành động kế tiếp và plan.
Evaluation/metrics/bootstrap và 175 tests đã hoàn tất trong phiên v12, report
v5 là kết quả hiện có. Phiên ghi nhận này chỉ cập nhật tài liệu, không phát
sinh test run, model inference hoặc human QA mới.

### v14 — 16/11/2026: Lưu nhắc pilot Gemma cho các phiên sau

Người dùng yêu cầu nhắc lại pilot Gemma ở những lần tiếp tục làm việc. Thêm
nhắc nổi bật và checklist quyền/token, smoke test, subset chung 10 mẫu, raw/
timing/VRAM/resume và evaluation. Bổ sung quy tắc đọc nhắc vào AGENTS và kế
hoạch V3. Ưu tiên evaluation trước vẫn được giữ theo phản hồi người dùng.
Phiên này cập nhật context và tài liệu, chưa có kết quả chạy mới.

### v15 — 18/11/2026: Hướng dẫn setup Gemma theo project hiện có

Theo yêu cầu người dùng, thêm docs/setup_gemma.md với license/token Read,
terminal nhập ẩn qua helper, tái sử dụng .venv-infer, smoke 2 mẫu rồi resume
cùng 10 mẫu Qwen, lỗi access/CUDA/OOM và đường dẫn cloud. Liên kết từ README,
docs index và hướng dẫn đa nền tảng. Đối chiếu model card/tài liệu token chính
thức với script thực tế; không dùng lệnh cài mới hoặc thay dependency pins.

Kiểm tra mới trên máy: Python 3.12.10, torch 2.7.1+cu126, Transformers 4.57.1,
bitsandbytes 0.48.2, huggingface_hub 0.36.0, CUDA True, RTX 3060 Laptop GPU.
Dry-run Gemma 2 mẫu/4 lượt expected đạt, revision/precision đúng config.
Dry-run 10 mẫu cũng đạt và sample IDs đúng thứ tự subset Qwen; 76 local
links trong sáu tài liệu hiện hành không thiếu, git diff --check đạt.
Không kiểm tra token/license, tải weights hoặc model generation, không chạy
lại unit tests hoặc thực hiện human QA. Pilot Gemma vẫn chưa hoàn thành;
nhắc qua các phiên tiếp tục được giữ.

### v16 — 18/11/2026: Chẩn đoán Gemma load thất bại do Windows pagefile

Người dùng báo traceback khi loading checkpoint shards. Đọc sanitized report
xác định OSError 1455: paging file quá nhỏ, không phải bằng chứng lỗi license
hoặc CUDA OOM. Hai shards 4.961.251.752 và 3.639.026.128 bytes đã có trong
cache; mới kiểm tồn tại/kích thước, chưa kiểm checksum weights. Chưa có raw
prediction Gemma. Bảo toàn bản sao load_error và snapshot chỉ đọc tại
reports/diagnostics/2026-11-18/gemma_load_v1 trước khi thử lại.

CIM ngoài sandbox đọc được RAM tổng/trống 15,69/1,63 GiB, pagefile tự động C
14.408 MiB, C trống 2,03 GiB, F trống 37,94 GiB. Lượt CIM trong sandbox bị
Access denied, các giá trị 0/null từ lượt đó bị loại, không dùng làm evidence.
Đối chiếu Microsoft, bổ sung guide giải phóng bộ nhớ/dung lượng và thêm
pagefile F 16–24 GiB trong khi giữ C system managed, sau đó restart thủ công.
Đây là đề xuất cấu hình thử theo snapshot, chưa chứng minh Gemma fit VRAM.
Chưa đổi Windows settings, xóa/move cache, reboot, chạy model hoặc unit tests
trong phiên này; không sửa runner/config/dependency pins. Pilot Gemma vẫn chờ.

### v17 — 19/11/2026: Gemma load được, phát hiện raw rỗng 4/4

Người dùng chạy lại smoke 2 mẫu và cung cấp summary. Đọc actual raw xác nhận
4 lượt success đều raw_response rỗng, parser INVALID_EMPTY; failed/missing=0.
Median processor+generation 2281,63 ms, peak allocated 5200,24 MiB. Không
đánh dấu pilot hoàn tất hoặc coi success là prediction valid. Giữ run/error
cũ và hashes, tính evaluation/statistics tại stage1/v6. Primary không đủ cặp
valid, Delta FPR/CI undefined, n_resamples_used=0 cho primary.

Kiểm GPU mới: CUDA/BF16 support True. Checkpoint config gốc BF16 còn adapter
đang ép FP16; đối chiếu maintainer Transformers cho thấy đây là giả thuyết
ưu tiên cần kiểm, chưa có token/logit trace hoặc BF16 run để xác nhận. Hành
động cụ thể kế tiếp là diagnostic NF4/BF16 có version trên 2 mẫu, rồi mới
10 mẫu và metrics/CI. Phiên này chỉ phân tích outputs và kiểm khả năng GPU,
không đổi code/config, không inference hoặc human QA/unit-test run mới.

### v18 — 19/11/2026: Hoàn tất Gemma NF4/BF16 pilot và evaluation

Người dùng xác nhận triển khai. Thêm runner Gemma riêng/CLI/helper và hai
configs để giữ nguyên hash runtime Qwen/FP16 cũ. Raw token/logit trace xác
nhận FP16 toàn NaN, sinh tám PAD ID 0, decode rỗng. BF16 logits hữu hạn;
runtime slow tokenizer không coi EOS 106 là special nên adapter tách đúng
một terminal EOS theo model config, giữ full trace; parser không đổi.

Smoke BF16 cuối 4/4 valid, resume mở rộng lên cùng 10 mẫu Qwen: 20/20 valid,
failed/invalid/missing/nonfinite=0, không OOM. Replay resume không load model,
raw/summary hash không đổi, first four records giữ byte-for-byte. EN accuracy
90%, VI 100%, disagreement 10%; negative FPR 20%/0%, ΔFPR −20 pp, empirical
cluster CI −60 đến 0 trên năm ảnh âm. Accuracy gap +10 pp, CI 0–30.
Median có instrumentation 10208,95 ms, peak allocated 5720,93 MiB; không
so timing trực tiếp với Qwen không trace hoặc tổng device memory.

Thêm 22 tests, full suite mới 197 passed/3,13 s trong .venv. Phiên này có
28 generation mới: 4 BF16 development, 4 FP16 diagnostic và 20 BF16 cuối
(bao gồm smoke, thêm 16 khi mở rộng). Giữ outputs/snapshot development,
không cộng lặp ảnh hoặc gộp diagnostics vào main. Qwen raw/protocol và tám
protected files v6 giữ hash. Không đổi nhãn/QA, Windows settings, dependency
pins hoặc chạy main/P1/P2. Offline cache-only, không tải weights mới.

[Completion v7](stage1/v7/completion.md) có metrics/statistics/cases/evidence,
README và setup guide cập nhật lệnh mới. Pilot kỹ thuật hai model đã hoàn
tất; nhắc Gemma pending được đóng theo yêu cầu người dùng. Tiếp theo QA
ảnh/nhãn 30 mẫu và data main/metadata/freeze; toàn Stage 1 vẫn còn việc.

Kiểm tra cuối phiên v18: analysis CLI replay giữ bytes báo cáo, metadata run
Gemma khớp source hash cuối, 150 local links trong 12 tài liệu không thiếu,
git diff --check đạt (chỉ cảnh báo LF/CRLF lịch sử). QA vẫn 30 pending và
translation approved 30. [Verification v7](stage1/v7/verification.json).

### v19 — 19/11/2026: QA ảnh/nhãn riêng và metadata main bốn task

Người dùng yêu cầu bắt đầu các việc còn lại. Thêm label QA export/import
độc lập để giữ bản dịch đã approved, HTML offline nhúng 30 ảnh nguyên bytes,
không model outputs, Save/JSON/restore/identity/timestamps và context/hash
guards. Packet tạo 30 pending, không reviewer IDs hoặc human approval.
Dry-run pending giữ translation approved=30 và QA pending=30, không output
manifest/audit thật. Computer Use dừng tự động vì URL browser chưa xác định
chắc; visual QA chưa được xác nhận. Node syntax check pass, không dùng tool
khác để bypass browser policy.

Tải metadata official 25.919.368 bytes có commit/SHA256 pins, không photo
archives hoặc inference. Thêm strict Candidate schema và adapters VSR,
TallyQA, Pet, RePOPE full frame từ pinned upstream cache. Sau loại đủ 30 ảnh
pilot: RePOPE 7680 rows/470 ảnh refs, VSR random/test 2194/1873, TallyQA test
38589/26451 (toàn VG), Pet tám lớp đề xuất 799/799. Metadata không có image
hash/approval, không coi như main manifest. Ghi actual zeroshot rows=1222
khác README 616, Pet rights note khác giữa archive và site; cần review.

Người dùng chốt async giữ 600 RePOPE/tối đa 2 câu mỗi ảnh. Lưu config v2,
frozen=false; sampler mới đề xuất tránh lặp nội dung, cho 600 câu/383 ảnh,
0 trùng nội dung, sáu quota 100, source fields không đổi. So với feasibility
379 ảnh/21 nội dung lặp, không âm thầm gộp/xóa source-category rows hoặc
thay label; chọn các candidates khác theo policy có ghi nhận, chờ freeze.
User chưa chốt các lựa chọn VSR/Pet/content policy còn lại.

Full suite thực 241 passed/3,49 s, thêm 44 tests. Offline inventory/selection
replay giữ bytes; source pins/ảnh pilot/checksums/v7 evidence và raw hai
model giữ nguyên, không inference/QA người/Windows settings mới. Chỉ CLI
trong source list v7 được mở rộng có chủ đích; portable/package thêm template.
Docs/README cập nhật workflow, [completion v8](stage1/v8/completion.md) ghi
bằng chứng. Tiếp theo nhận QA JSON thật rồi data materialization/translation/
review/baseline freeze; toàn Stage 1 và main vẫn chưa hoàn tất.

### v20 — 19/11/2026: Selection 1.000 mẫu và RePOPE draft có ảnh/VI

Tiếp tục từ v8, chưa có QA JSON mới nên không import/approve. Người dùng
trả lời giao assistant chọn phương án phù hợp cho phần main còn lại. Chốt
preparation config v3: VSR random/test 120 (60T/60F, relation diversity),
TallyQA 120 (60 simple/60 complex, count bins min1 + proportional remainder),
Pet tám giống đã nêu ×20, seed42/frozen=false. Selection metadata đủ 1000
rows/783 mã ảnh, không overlap IDs giữa task/pilot, RePOPE cũ giữ bytes.

Thêm materializer RePOPE bounded/offline/resume. COCO HTTPS trực tiếp lỗi
hostname certificate; dùng cùng image provider HF pinned như pilot, không
tắt TLS. Viewer HEAD trước/sau, revision asset paths, pages/checksum cache,
429 stop và 5xx backoff. Các attempt 429/502 và correction thiếu page-cache
ban đầu ghi trong source checks. Đã có 383 JPEG/19.484.714 bytes cho 600
rows, readability/hash/ID và byte-level pilot exclusions đạt, không đổi label
nguồn. Draft manifest mới is_pilot=false, QA pending, không freeze/inference.
Byte-equivalence với COCO gốc chưa được kiểm chứng độc lập.

Giữ dictionary pilot, thêm 53 noun phrases draft để phủ 72 object names.
Tạo 600 VI proposals rồi bilingual draft 600 rows, toàn bộ requires_review,
QA vẫn pending, risk notes cho thuật ngữ khó. Không coi approval từ vựng/
pilot là approval câu main mới. Source/image/translation offline replay giữ
bytes; hai ảnh smoke giữ nguyên khi mở rộng. Main gate chặn 600 rows bằng
MAIN_QA_NOT_APPROVED; không có image/pilot-overlap issue khác trong check này.

Full suite mới 269 passed/7,31 s, thêm 28 tests. Không human approvals,
inference/training, Windows settings hoặc thay dependencies mới. UI visual
QA chưa được kiểm chứng ở v8 vẫn giữ đúng trạng thái; không bypass policy.
Xem [completion v9](stage1/v9/completion.md). Tiếp theo human QA pilot JSON,
ảnh/VI 400 mẫu còn lại, QA toàn main và baseline metadata/runner/freeze;
Stage 1 tiếp tục IN_PROGRESS.

### v21 — 20/11/2026: Import QA pilot và hoàn tất main drafts bốn task

Nhận `label_qa_reviewed_v1.json` người dùng gửi: đủ 30 IDs/context/fingerprints,
quan sát approved khớp nhãn và reviewer/timezone hợp lệ. Dry-run rồi import
vào stage1_qa_v1 mới, QA approved 30 và translation approved 30; source fields,
ảnh, manifest lịch sử và raw model outputs giữ nguyên. Không tạo human
decision thay người dùng. A06 DONE, toàn Stage 1 chưa hoàn tất.

Giữ selection v9 1000/783, tải 120 VSR JPEG qua COCO S3 HTTPS, 120 TallyQA JPEG
Stanford, 160 Pet JPEG từ official gzip/tar stream. Pet đọc 791.918.971 bytes,
chỉ lưu selected JPEG; kiểm CRC/length/full-download SHA. 400 ảnh mới tổng
55.531.311 bytes. TallyQA gặp WinError 5 khi atomic receipt replacement sau
110 ảnh; bổ sung bounded retry, khôi phục orphan 2354629 sau khi reacquire
official bytes khớp SHA, không overwrite ảnh cũ hoặc sửa Windows/ACL. Hoàn
tất cả 400; offline replay không tải thêm và giữ draft hashes.

Tạo 400 VI proposals/bilingual drafts requires_review, giữ classifiers và
source predicate/labels; ghi risk notes cho quan hệ/thuật ngữ mơ hồ. Main đủ
1000 EN–VI draft/783 ảnh và SHA khác nhau, không pilot ID/hash overlap hoặc
source changes, không technical issues khác. Gate MAIN_QA_NOT_APPROVED=1000,
main_ready=false. Xuất 22 gói tối đa 50 row, fixed CSV/pending JSON/HTML offline;
hai người review bản dịch, QA riêng, source/ảnh hashes và chống stale approval.
Giao diện mới chưa visual browser QA; không bypass stop cũ. Không model outputs
trong review packets. [Completion v10](stage1/v10/completion.md).

Full suite thực 302 passed/4,13 s, thêm 33 tests; JS syntax/backend đạt. Không
inference/training/cloud generation mới, model runtime/parser/Windows settings
giữ nguyên. Tiếp theo người review làm từng gói main và gửi JSON để assistant
dry-run/import, tổng hợp QA rồi metadata/runner/freeze trước xác nhận full-run.
