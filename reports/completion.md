# Completion — trạng thái và context hiện tại

**v30 · 22/11/2026 (Asia/Saigon).** Điểm vào: [hướng dẫn nhóm](../HUONG_DAN_NHOM.md),
[README](../README.md). Lịch sử **v1–v21 được giữ nguyên bytes** tại
[completion_history.md](completion_history.md); không bị xóa khi rút gọn file này.

Đọc thêm [stage data/QA gần nhất](stage1/v10/completion.md),
[pilot tooling](stage1/v11/completion.md),
[review tooling A/B mới nhất](stage1/v12/completion.md),
[baseline contract/runner mới nhất](stage1/v13/completion.md),
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
  tạo reviewer/approval. Theo yêu cầu mới ngày 22/11, đã chia 5 vai trò TV1–TV5
  tại [report phân công](../docs/research/TEAM_PROGRESS_AND_ASSIGNMENT_V1.md);
  nhóm điền tên thật sau, không gán lại tác giả các commit đã có.

## Đã hoàn thành có bằng chứng

| Hạng mục | Trạng thái thật |
|---|---|
| Foundation | Schema/CLI, atomic I/O, dataset adapters, sampler, parser, resume/leakage và review tooling |
| Qwen pilot | 10 ảnh × EN/VI =20 lượt thật, NF4/FP16, valid 20/20; [v4](stage1/v4/completion.md) |
| Gemma pilot | Cùng 10 ảnh/20 lượt, NF4/BF16, valid 20/20, resume giữ hash; [v7](stage1/v7/completion.md) |
| Pilot QA | 30 translation approved; JSON người dùng được import ngày 20/11, 30 image/label QA approved; `data/pilot/stage1_qa_v1/pilot_manifest.csv` |
| Main drafts | Đủ ảnh/EN–VI nháp cho 1.000 row, 783 JPEG/hash khác nhau; source và ID/byte leakage checks đạt; tất cả main requires_review/QA pending |
| Review main | 22 gói v2 tối đa 50 câu; A/B mỗi người kiểm dịch và ảnh/nhãn, một JSON cuối/gói; chưa có main human import |
| Evaluation/statistics | Metrics bốn task, expected pairing/invalid/missing và image-cluster bootstrap; thực tế đã phân tích hai pilot; các task khác mới synthetic tests |
| Baseline main v1 | Metadata/config/record schemas, prompt routing bốn task, CPU grid 4.000 cells và gated runner/resume/error đã có; adapters reuse, chưa main GPU inference/freeze |
| Tests | Ngày 22/11 full suite 396 passed/18,91 s, thêm 37 baseline tests; fake outputs hai model qua evaluator/CI. Chưa main GPU hoặc visual browser QA |
| Git/team handoff | Đã push riêng 6 phần foundation/data/eval/pilot/review/docs lên origin/main; commit audit ghi đủ SHAs và receipts. Ảnh/HTML sinh/ZIP/env/weights ở ngoài Git; xem release log |
| Rerun pilot | Launcher chung local/Colab/Kaggle, configs team QA approved, default 2/max10; Qwen NF4/FP16, Gemma NF4/BF16; ZIP pilot riêng |
| Hướng dẫn/structure | HUONG_DAN_NHOM.md; root commands 10 sau thêm run_main.py, data/8 và legacy/2. Data/config/runtime paths cũ giữ nguyên |

**Gemma reminder đã đóng:** setup và engineering pilot đã hoàn tất, không
nhắc như việc pending. Lỗi FP16 NaN/PAD được khắc phục bằng runner BF16 tại
v7; giữ diagnostics/raw cũ. V11 đã đồng bộ notebooks Gemma BF16 qua launcher
chung và GPU guard; cloud Colab/Kaggle vẫn chưa có actual generation được xác minh.

Raw hai run valid được copy nguyên bytes vào [pilot_outputs](pilot_outputs/README.md)
để nhóm phân tích CPU; bản gốc vẫn trong results local. Các metrics/CI chỉ từ
10 ảnh/model, năm negative; không suy thành kết luận main hoặc language gap.
QA nhập sau không làm thay đổi scope/bytes của raw và báo cáo lịch sử.

## Việc tiếp theo

0. Nhóm đọc [report tiến độ và phân công 5 người](../docs/research/TEAM_PROGRESS_AND_ASSIGNMENT_V1.md),
   điền tên TV1–TV5 và ghi nhận gói đang review. Bắt đầu các đầu ra làm ngay
   của từng vai trò; bảng chia 400 lượt kiểm mẫu/người là đề xuất cho gói chưa chốt.
1. Người dùng báo nhóm đang review. Gửi kèm hướng dẫn HTML chi tiết
   `exports/HUONG_DAN_REVIEW_V2.html` với main_review_v2.zip; nhóm thử lưu/mở lại
   vài mẫu rồi tiếp tục theo đúng A/B. Chưa import thêm human QA trong phiên này.
2. Review main theo [workflow v2](../docs/research/MAIN_REVIEW_V2.md): mở
   `reports/stage1/v12/main_review/index.html` sau khi nhận ZIP; tải JSON và
   lưu `data/reviews/main_review_v2/<packet>_reviewed_v2.json`. Không làm lại pilot.
3. Dry-run/import các JSON thật vào version mới; xử lý rejected/uncertain,
   tổng hợp đúng 1.000 IDs, đối soát source/ảnh/leakage trước final.
4. Engineering baseline v1 đã có; dùng `scripts/run_main.py plan` để kiểm CPU.
   Sau review, chốt final manifest/configs/prompts và freeze receipt đúng protocol,
   rồi xác nhận bounded main smoke bốn task trên GPU trước full-run. Config draft
   hiện frozen=false, execution_ready=false; không tự bật để vượt QA.
5. Sau run được duyệt: paired metrics/CI, error analysis, Results–Discussion,
   report/slides V3. Word v1 ngày 11/11 giữ scope V4.2, chưa revise V3 hoặc có
   bằng chứng đã nộp. RQ3/RQ4 chỉ xét sau core ổn định và gate riêng.

**Stage 1 vẫn IN_PROGRESS.** Main QA/final freeze và kiểm main GPU còn thiếu, không
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

### v27 — 21/11/2026: Hai người A/B kiểm cả dịch và ảnh/nhãn

Người dùng chọn rõ A làm cả hai, B kiểm lại cả hai; không dùng single reviewer.
Tạo backend/template v2 và 22 gói mới, CLI mặc định v2 với --version v1 để xử lý
lịch sử. Mỗi người dùng cùng ID cho hai quyết định; cả hai ID khác nhau phải
approve bản cuối/quan sát khớp nguồn. Thay VI giữ lượt cũ trong history và yêu
cầu duyệt lại, không tự biến QA v1 một người thành hai người.

Full suite mới 359 passed/8,74 s; JS mock-DOM → backend và CLI dry-run/import
synthetic đạt. Đối chiếu 1.000 ảnh nhúng, 22 pending packets/783 ảnh và 225
protected hashes đạt; main vẫn pending và readiness=false. Đóng gói riêng
exports/main_review_v2.zip (~83,4 MiB); hai ZIP cũ giữ nguyên. Cập nhật guide,
protocol, README; công bố thay đổi bằng một commit review riêng theo yêu cầu
push từng việc. Không model run, download hoặc human approval mới. Chi tiết
và giới hạn kiểm chứng tại [v12](stage1/v12/completion.md). Bước tiếp: chia sẻ
ZIP v2, thử lưu/tải/mở lại vài mẫu rồi A → B → import JSON thật.

### v28 — 21/11/2026: Hướng dẫn chi tiết cho reviewer và việc làm song song

Hoàn tất yêu cầu hướng dẫn đang dở: mở rộng MAIN_REVIEW_V2.md tại chỗ thành
14 mục cho người review và giữ phụ lục operator, thêm bản HTML độc lập ở
exports/HUONG_DAN_REVIEW_V2.html để gửi cùng ZIP. Bao gồm cách mở gói, đúng
tên nút, A/B nối tiếp, checklist dịch, QA bốn task/mapping Pet, trạng thái,
sửa VI/history, tải/khôi phục JSON, bộ đếm và lỗi/bàn giao. README và guide
trỏ vào tài liệu hiện có, không tạo thêm entry point Markdown trùng lặp.

Đã đối chiếu labels/UI/schema, kiểm cấu trúc HTML/14 mục/anchors, Git links
và diff; HTML không scripts/assets từ mạng. Không visual browser QA, không
chạy lại suite: 359 tests vẫn là kết quả v27. Không đổi code, template review,
manifests, JSON quyết định hoặc nội dung ZIP; không inference/human approval mới.
Khi kiểm bàn giao, main_review_v2.zip không còn ở exports; đã đóng lại từ bộ
HTML hiện có, bytes/SHA256 khớp hoàn toàn receipt v12 (755e18f4…). Hai ZIP cũ
giữ hash; không ghi đè ZIP có sẵn hoặc sửa receipt lịch sử.
Người dùng hỏi việc làm khi nhóm đang review: ưu tiên metadata contract →
full-runner CPU dry-run 4.000 ô → tích hợp evaluation/CI, chuẩn bị Method/khung
Results song song. Đây là kế hoạch, không nâng trạng thái A12/A13 thành DONE.

### v29 — 22/11/2026: Baseline metadata và runner main v1 bằng CPU

Người dùng cho phép triển khai tiếp trong lúc nhóm review và sẽ gửi JSON sau.
Thêm baseline_contract.py/baseline_runtime.py, run_main.py và hai config/prompt
draft mới. Strict fields/revisions, nguồn/ảnh/prompt/code/env hashes, raw/valid/
invalid/error/attempt, source IDs, model dtype/NF4 và bốn task đều có contract.
VSR dùng TRUE/FALSE normalize yes/no; Pet giữ manifest question và map A–H.
Không đổi pilot runtime/parser/configs, review v2, data/labels/exclusions hoặc raw.

CPU dry-run thật đủ 1.000 row/783 ảnh, 4.000 cells, 2.000/model; sáu platform-label
plans cùng IDs/protocol. Fake adapters kiểm resume, explicit retry, invalid,
Ctrl+C, OOM, corrupted metadata/JSONL và đưa output hai model qua evaluator/CI cũ.
Full suite mới 396 passed/18,91 s, thêm 37 tests. Old data/config/core/stage files
so với Git blobs đạt 289 files; raw snapshots giữ bytes. A12 DONE ở phạm vi
engineering contract; A13 IN_PROGRESS vì final QA/freeze/main GPU còn chờ.

Execution draft bị chặn trước runtime/model load. Chưa tạo freeze receipt thật,
main human approvals, model downloads hoặc actual main generation. Initial 3
targeted-test failures do synthetic VI routing/Windows encoding đã sửa trong
fixture, rồi suite đạt; không giả lập chúng thành dữ liệu/thí nghiệm thật.
Chi tiết tại [v13](stage1/v13/completion.md) và [contract](../docs/research/BASELINE_V1.md).
Bước tiếp cụ thể: nhận/import JSON A/B, tổng hợp main final, chốt/freeze và
xác nhận GPU smoke; không cần chạy lại pilot hoặc viết lại evaluator.

### v30 — 22/11/2026: Report tiến độ và phân công 5 người

Người dùng yêu cầu chia công việc còn lại cho đủ 5 người và tạo report để
xin góp ý ChatGPT. Đây là yêu cầu mới cho phép phân công theo 5 ký hiệu:
TV1 dữ liệu/QA cuối, TV2 inference/GPU, TV3 định lượng, TV4 phân tích lỗi/
Related Work, TV5 báo cáo/tái lập. Mỗi phần ghi việc làm ngay và việc phụ
thuộc QA/raw, đầu ra, điều kiện hoàn tất, phần viết và branch/PR/commit.
Không gán tên thật, tạo approval hoặc đổi tác giả/lịch sử Git.

Report có tổng quan V3, dữ liệu/metrics, bằng chứng tiến độ, gates M1–M5,
giới hạn và 6 câu hỏi phản biện cho ChatGPT. Đối chiếu đủ 22 gói/1.000 mẫu:
hai lượt A/B tạo 2.000 lượt kiểm mẫu, cân bằng 400/người; giữ công việc đang
làm nếu đã nhận gói. A và B vẫn phải là hai người thật, mỗi người duyệt cả
dịch và ảnh/nhãn trong cùng JSON. Đây là kế hoạch, không phải review đã xong.

Nguồn canonical là docs/research/TEAM_PROGRESS_AND_ASSIGNMENT_V1.md, đã link
từ README/docs index/hướng dẫn nhóm. Bản gửi ChatGPT ở exports:
EN_VI_VLM_Tien_do_va_Phan_cong_5_nguoi_v1.pdf và .md. PDF 11 trang đã render
và kiểm bố cục từng trang, glyph tiếng Việt và text; Markdown export khớp
nguồn. Word không xuất do canonical renderer thiếu LibreOffice; không bàn
giao DOCX chưa kiểm. Artifacts/QA local giữ ngoài Git.

Phiên này chỉ tài liệu và kiểm report; không chạy lại software suite, GPU,
download, import human QA hoặc freeze. 396 tests/18,91 s vẫn là lần v13,
không phải test run v30. Main chưa có kết quả, Stage 1 IN_PROGRESS và RQ3/RQ4
vẫn conditional P1. Bước tiếp: nhóm thống nhất TV1–TV5, tiếp tục A/B và làm
đầu ra song song; nhận JSON thật để tổng hợp main trước freeze/GPU smoke.
