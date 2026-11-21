# Completion — trạng thái và context hiện tại

**v26 · 21/11/2026 (Asia/Saigon).** Điểm vào: [hướng dẫn nhóm](../HUONG_DAN_NHOM.md),
[README](../README.md). Lịch sử **v1–v21 được giữ nguyên bytes** tại
[completion_history.md](completion_history.md); không bị xóa khi rút gọn file này.

Đọc thêm [stage data/QA gần nhất](stage1/v10/completion.md),
[pilot tooling mới nhất](stage1/v11/completion.md),
[công bố GitHub và kiểm chứng tái lập](releases/2026-11-21/README.md),
[Handoff V3](../docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md),
[protocol](../docs/research/RESEARCH_PROTOCOL_V3.md) và
[checklist](../docs/research/IMPLEMENTATION_PLAN_V3.md) trước khi triển khai tiếp.

## Scope và các quyết định cần giữ

- Zero-shot paired EN–VI, cùng ảnh/nghĩa/ground truth trong mỗi cặp. Qwen2.5-VL-3B
  và Gemma 3 4B IT; không training/LoRA/paid inference hoặc tự đổi model.
- V3 supersedes V4.2: RQ1 RePOPE negative-only ΔFPR và RQ2 bốn task là P0.
  RQ3 paraphrase/RQ4 visual evidence là conditional P1, chưa triển khai;
  negation riêng là future work. Người dùng hỏi tiến độ có tính RQ3/RQ4,
  chưa có quyết định mới chạy hai mở rộng này.
- Main 600 RePOPE +120 VSR +120 TallyQA +160 Pet =1.000 row, 783 ảnh.
  RePOPE cap2/ảnh được người dùng chốt; các task khác cap1, seed42,
  split/classes/count-bin policy ghi trong `configs/main_preparation_v3.yaml`.
- Main **frozen=false**; 4.000 inference chính chưa chạy/chưa được xác nhận
  full-run. Không tự giảm scope, thay labels hoặc loại theo output của model.
- Source labels/provenance và pilot ID/SHA exclusions giữ nguyên. Không
  tạo reviewer/approval hoặc gán công việc theo tên thành viên.

## Đã hoàn thành có bằng chứng

| Hạng mục | Trạng thái thật |
|---|---|
| Foundation | Schema/CLI, atomic I/O, dataset adapters, sampler, parser, resume/leakage và review tooling |
| Qwen pilot | 10 ảnh × EN/VI =20 lượt thật, NF4/FP16, valid 20/20; [v4](stage1/v4/completion.md) |
| Gemma pilot | Cùng 10 ảnh/20 lượt, NF4/BF16, valid 20/20, resume giữ hash; [v7](stage1/v7/completion.md) |
| Pilot QA | 30 translation approved; JSON người dùng được import ngày 20/11, 30 image/label QA approved; `data/pilot/stage1_qa_v1/pilot_manifest.csv` |
| Main drafts | Đủ ảnh/EN–VI nháp cho 1.000 row, 783 JPEG/hash khác nhau; source và ID/byte leakage checks đạt; tất cả main requires_review/QA pending |
| Review main | 22 gói tối đa 50 câu, offline HTML + fixed CSV/JSON; hai reviewer dịch, QA riêng; chưa có main human import |
| Evaluation/statistics | Metrics bốn task, expected pairing/invalid/missing và image-cluster bootstrap; thực tế đã phân tích hai pilot; các task khác mới synthetic tests |
| Tests | Ngày 21/11: 334 passed/5,56 s trên đúng Git tree phần tài liệu (8033908); từng phần trước cũng được kiểm từ cây Git riêng. Không phải inference/QA mới |
| Git/team handoff | Đã push riêng 6 phần foundation/data/eval/pilot/review/docs lên origin/main; commit audit ghi đủ SHAs và receipts. Ảnh/HTML sinh/ZIP/env/weights ở ngoài Git; xem release log |
| Rerun pilot | Launcher chung local/Colab/Kaggle, configs team QA approved, default 2/max10; Qwen NF4/FP16, Gemma NF4/BF16; ZIP pilot riêng |
| Hướng dẫn/structure | Một HUONG_DAN_NHOM.md từ mục tiêu đến push; root scripts 19→9, data/8 và legacy/2. Data/config/runtime paths giữ nguyên |

**Gemma reminder đã đóng:** setup và engineering pilot đã hoàn tất, không
nhắc như việc pending. Lỗi FP16 NaN/PAD được khắc phục bằng runner BF16 tại
v7; giữ diagnostics/raw cũ. V11 đã đồng bộ notebooks Gemma BF16 qua launcher
chung và GPU guard; cloud Colab/Kaggle vẫn chưa có actual generation được xác minh.

Raw hai run valid được copy nguyên bytes vào [pilot_outputs](pilot_outputs/README.md)
để nhóm phân tích CPU; bản gốc vẫn trong results local. Các metrics/CI chỉ từ
10 ảnh/model, năm negative; không suy thành kết luận main hoặc language gap.
QA nhập sau không làm thay đổi scope/bytes của raw và báo cáo lịch sử.

## Việc tiếp theo

1. Nhóm clone repo đã push, nhận riêng ZIP workspace từ người giữ project và
   làm thử một gói review/lưu/mở lại JSON trước khi triển khai rộng. ZIP không
   được upload/chia sẻ tự động trong phiên này.
2. Review main theo [workflow](../docs/research/MAIN_REVIEW_V1.md): mở
   `reports/stage1/v10/main_review/index.html` sau khi nhận ZIP; tải JSON và
   lưu `data/reviews/main_review_v1/<packet>_reviewed.json`. Không làm lại pilot.
3. Dry-run/import các JSON thật vào version mới; xử lý rejected/uncertain,
   tổng hợp đúng 1.000 IDs, đối soát source/ảnh/leakage trước final.
4. Song song review, hoàn thiện metadata/schema baseline và full runner;
   sau gates chốt configs/protocol,
   freeze sau gates rồi xin xác nhận full-run. Không coi pilot runner là main runner.
5. Sau run được duyệt: paired metrics/CI, error analysis, Results–Discussion,
   report/slides V3. Word v1 ngày 11/11 giữ scope V4.2, chưa revise V3 hoặc có
   bằng chứng đã nộp. RQ3/RQ4 chỉ xét sau core ổn định và gate riêng.

**Stage 1 vẫn IN_PROGRESS.** Main QA/metadata/runner/freeze còn thiếu, không
đánh dấu xong stage vì đã có đủ ảnh/draft. Giao diện review đã kiểm cú pháp JS
và backend tests; chưa visual browser QA. Không retry/bypass Computer Use stop cũ.

Các maintenance reports/Word/snapshots được nhắc trong lịch sử dưới đây chỉ
giữ local trên máy gốc, ngoài Git; stage evidence nhỏ và completion history
v1–v21 vẫn được đưa vào repo. Trạng thái cũ được giữ đúng thời điểm ghi.

## Nhật ký phiên bản mới

### v22 — 20/11/2026: Rút gọn để đưa nhóm lên GitHub

Người dùng yêu cầu sắp xếp/cập nhật/xóa phần dư và đóng gói cho first push.
Đã rút gọn README/START_HERE/completion; lưu nguyên lịch sử v1–v21, giữ
stage reports, nguồn/ảnh/review/raw/Word và configs cũ. Cập nhật protocol có
trạng thái QA/data đúng, bổ sung CONTRIBUTING, file maps và pilot outputs nhỏ.
Loại generated review HTML/Word previews và artifacts local khỏi Git; thêm
kiểm tập file Git/credential patterns, team ZIP build/restore có hash/conflict
guards, CPU CI và kiểm tra handoff. Chỉ dọn Python bytecode được sinh lại;
không xóa venv, weights hoặc cache dataset. Không inference/human QA mới.

Chi tiết, số lượng file và bằng chứng checks ở
[maintenance completion](maintenance/2026-11-20/completion.md). Các phiên sau
tiếp tục cập nhật phần trạng thái và thêm dated version entry; không sửa lịch
sử như thể test/QA/inference cũ là một lần chạy mới.

### v23 — 20/11/2026: Cập nhật pilot cho thành viên chạy khi cần

Người dùng yêu cầu cập nhật pilot và tiếp tục phần đang dở. Thêm launcher
team dùng configs mới/manifest pilot QA approved, giữ nguyên core runtime/
parser/configs và raw lịch sử. Helper cũ chuyển thành aliases an toàn; output
team_v1 mới, native BF16 guard cho Gemma trước download, token/offline/resume
rõ ràng. Regenerate hai notebooks output-free và hướng dẫn ngắn; tạo pilot
ZIP nhỏ cho cloud, khác ZIP main workspace. Lưu nguồn helper/notebook/docs cũ.

Full suite thực 334 passed/5,15 s, thêm 16 tests; 12 dry-run local CPU với
platform labels local/colab/kaggle đều đạt, image QA approved và subset giống
nhau, hai aliases route Gemma BF16. Không inference, tải weights hoặc human
QA mới; cloud runtime chưa được chạy thật. Xem [completion v11](stage1/v11/completion.md)
và receipts/checks. Khi cần rerun, dùng `scripts/run_pilot.py`, run name/output
mới và guide; không bắt buộc chạy lại pilot để tiếp tục main human review.

### v24 — 20/11/2026: Một hướng dẫn tổng hợp và chia nhóm scripts

Người dùng yêu cầu tiếp tục đơn giản hóa structure và một file đủ để thành
viên hiểu/tham gia/push. Tạo HUONG_DAN_NHOM.md; README, CONTRIBUTING,
START_HERE và folder maps rút gọn thành điều hướng, không giữ bộ setup/Git
commands trùng nhau. Guide bao gồm scope/RQ, trạng thái, CPU/GPU, ZIP/review,
pilot/analysis, file/config đúng và first push/PR workflow.

Di chuyển 8 data-preparation scripts vào scripts/data/ giữ nguyên bytes,
2 Word v1 builders vào scripts/legacy/ và chỉ sửa ROOT vì sâu thêm một cấp;
nguồn trước sửa được snapshot. Tầng scripts chính còn 9 file. Cập nhật paths
trong guides hiện hành và future pilot bundles kèm hướng dẫn nhóm. Giữ nguyên
source/data/config/runtime, reviews, raw/model reports và hai ZIP đã chia sẻ.

Full suite thực 334 passed/5,42 s; 8 --help checks và 2 legacy ROOT checks
đạt, không thực thi Word builders. Kiểm mirror/ZIP và bằng chứng giữ file
ở [maintenance guide report](maintenance/2026-11-20/team_guide/completion.md).
Không model inference, download weights hoặc human QA mới, chưa stage/commit/
push. Tiếp theo nhóm dùng hướng dẫn tổng hợp để first push và main human review.

### v25 — 20/11/2026: Làm rõ nghiên cứu, tiến độ và các mốc cộng tác

Theo yêu cầu người dùng, mở rộng mục 1–3 HUONG_DAN_NHOM.md: mục đích/giá trị,
RQ1–RQ4 và giới hạn diễn giải, dataset/task/metrics, paired controls và ảnh
so với số câu. Tiến độ phân biệt real inference/pilot QA/main draft/software;
ghi rõ repo chưa first-push để nhóm bắt đầu chia review, chưa có main JSON
review được nhận/import tại thời điểm kiểm. Có bảng 22 gói/1.000 câu.

Kế hoạch tiếp theo có mốc A–F, deliverables và điều kiện qua gate, workstreams
không gán người, review và metadata/runner làm song song; RQ3/RQ4 vẫn conditional.
Đã lưu bản guide trước sửa và kiểm links/script paths/Git readiness/evidence
hashes trong [research brief report](maintenance/2026-11-20/research_brief/completion.md).
Đây là docs-only: không chạy lại suite, inference, acquisition hoặc human QA;
không stage/commit/push/upload hoặc thay code/config/data/ZIP.

### v26 — 21/11/2026: Công bố GitHub từng phần để nhóm tái lập

Theo yêu cầu người dùng, công bố từng phần với commit body nêu mục đích,
hoàn thành và kiểm chứng; không gom một bulk commit hoặc ghi lùi ngày.
Sáu phần đã push và đối chiếu remote HEAD: foundation 78 tests, data 166,
evaluation 178, pilot 309, review 334 và tài liệu 334 (5,56 s). Tất cả chạy từ cây Git riêng của
chính phần đó, không mượn file chưa commit trong workspace. Phần 6 là protocol,
hướng dẫn nhóm và evidence nhỏ; audit cuối chỉ docs/receipts, không lặp suite.
Khôi phục ZIP từ tree phần 5: 861 file, đủ 1.000 row/783 ảnh, sinh lại 22 gói/23
HTML giống bytes, main_ready=false đúng gate. Build/cài wheel offline vào target
riêng đạt, đủ 2 HTML templates/CLI và 15 CPU pins. Xem release log/manifest cho
SHA, receipts, lỗi temp/cache permissions đã xử lý và giới hạn kiểm chứng.

Git giữ nguồn/template/generator cho 22 gói, không chứa HTML nhúng ảnh hoặc
ZIP/model/env. Các dữ liệu/runner/config/raw lịch sử và lịch sử completion
không đổi. Main vẫn pending review, Stage 1 IN_PROGRESS; không inference,
download model hay tạo human approval. Bước tiếp là chia sẻ ZIP riêng và review.
