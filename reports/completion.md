# Completion — trạng thái và context hiện tại

**v47 · 27/11/2026 (Asia/Saigon).** Đọc [hướng dẫn nhóm](../HUONG_DAN_NHOM.md),
[Handoff V3](../docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md),
[protocol](../docs/research/RESEARCH_PROTOCOL_V3.md),
[implementation plan](../docs/research/IMPLEMENTATION_PLAN_V3.md) và
[stage mới nhất v25](stage1/v25/completion.md) trước khi làm tiếp.
Giữ nguyên lịch sử v1–v21 trong completion_history.md và nhật ký v22–v46 bên dưới.

## Phạm vi và dữ liệu đã chốt

- Zero-shot paired EN–VI, Qwen2.5-VL-3B và Gemma 3 4B; RQ1/RQ2 là P0.
  Không training hoặc tự mở RQ3/RQ4. Hạn thuyết trình 03/12/2026.
- Main: 1.000 mẫu / 783 ảnh / 4.000 cells; 600 RePOPE, 120 VSR,
  120 TallyQA, 160 Pet. Giữ pilot exclusions, source hashes và review history.
- Option B: JPEG gốc → RGB giữ kích thước → pinned processor; không thumbnail 512.
- Pet dùng ngoại lệ đã được người dùng chấp thuận: duyệt dịch/chất lượng ảnh,
  giống kế thừa official source labels/mapping; không bịa reviewer B hoặc nhận diện giống.
- TallyQA: 112 QA nguyên bản + 5 câu hỏi nguồn có nhãn sửa + 3 QA viết lại,
  category 61 simple / 59 complex. Ba QA mới có hai proof thật; donut dùng “phủ socola”.
  Sensitivity 117 loại ba QA viết lại, vẫn giữ năm nhãn sửa; chưa có main results.
- RePOPE 294 yes / 306 no sau adjudication; không ép cân bằng hoặc đổi ground truth.
  A và B khác ID duyệt cả dịch và ảnh/nhãn, trừ ngoại lệ Pet; giữ raw JSON nguyên bytes.

## Trạng thái đã kiểm chứng

| Hạng mục | Trạng thái |
|---|---|
| Engineering pilot | Hai model đã chạy thật; Gemma pilot đã hoàn tất, không nhắc lại như pending |
| Pilot QA | 30/30 approved, không làm lại |
| Image diagnostic | RePOPE-only 30 ảnh / 240 measured GPU cells, không phải validation bốn task hoặc M3 |
| Main QA / M1 | **DONE**, 1.000/1.000 đạt; [adjudication v22](stage1/v22/completion.md) |
| Local freeze / M2 | **DONE v1**, protocol hash `74353c78c3bbed176b75fd1bae6792bc8cf7c8eebaac4383829ac4cdc0cc9d69` |
| Main smoke / M3 | **PARTIAL_QWEN_ONLY**: 16/16 valid, 0 invalid/failed/OOM/missing trên RTX 3060 Laptop 6 GB; [v23](stage1/v23/completion.md) |
| Team handoff | **Phase A**: bốn configs, bốn hướng dẫn cá nhân, Git/PR ownership, hai notebook starter, một master private và bốn ZIP nhỏ tham chiếu chung |
| Software checks | Đợt publish: **527 passed / 41,46s** trên đúng public tree, tách WIP; đợt v24 full local có 567 passed. Không suy ra GPU/cloud passed |
| Sharding / cloud main | **Chưa triển khai/kiểm chứng đầy đủ**: core chưa có `--language`; PR của TV1–TV4 còn chờ |
| Full main / metrics | **NOT RUN**; chưa được phép tự chạy 4.000 cells, Gemma main smoke hoặc các shard |

Frozen config `configs/baseline_v3_final_v1.yaml`, receipt
`data/freezes/main_v3_final_v1.json`, manifest
`data/main/adjudicated_confirmed_v1/main_reviewed.csv` giữ nguyên.
Qwen raw `results/main/local/qwen_main_smoke_16_v1/qwen.jsonl` giữ SHA
`77f7295298cf6e63c55e28a5eb7fd35fa8b4c90d3f1f07dfbfac9649f4553f32`.
Authorization cũ chỉ 16 Qwen cells; không tự chạy lại hoặc suy rộng thành quyền full run.

## Bàn giao nhóm và việc tiếp theo

Mở [START_HERE cho nhóm](../docs/team_inference_v1/START_HERE.md) và
[file ownership](../docs/team_inference_v1/FILE_OWNERSHIP.md).
TV1 phát triển language sharding; TV2 hoàn thiện Kaggle/data loading;
TV3 hoàn thiện Colab/Gemma GPU compatibility; TV4 export/collection/recovery;
TV5 publish common base, review/integrate và tổng hợp nghiên cứu.
Không gán role cho tên thật, giả tác giả hoặc làm commit hình thức.

**Bước cụ thể tiếp theo:** hạ tầng/hướng dẫn Phase A đã publish; TV5 còn review/tích hợp common base đầy đủ với các QA/freeze WIP giữ local. Sau đó mỗi người clone,
tạo branch và tự triển khai/kiểm chứng phần được giao, tự commit/push/PR.
Sau merge/tests, chốt cùng 40-hex commit/release, đánh giá fingerprint và phê duyệt
implementation/protocol v2 rồi mới thực hiện cloud smoke và shard inference được phép.
Không sửa frozen v1 để bỏ qua gates; thay runtime cần version/approval mới.

Master `exports/VLM_ENVI_Main_Inference_Team_v1.zip` có một source snapshot
và 783 JPEG + hai pinned source inputs. Bốn member ZIP không nhân bản core/data,
chỉ trỏ cùng master SHA. Master là private; bốn ZIP cá nhân chỉ có guides/config đã được người dùng cho phép publish tại `hướng dẫn thực nghiệm/`.
Snapshot có WIP và không có `.git`, chưa phải pinned release cho Phase B.
SHA/build/restore receipts nằm ở [stage v24](stage1/v24/completion.md).

Chưa kiểm chứng Colab/Kaggle allocation, packages/Secrets/HF access từng account,
native BF16/VRAM thực tế hoặc student PRs. Gemma không tự fallback FP16;
TV4 cần môi trường BF16 được xác nhận nếu Kaggle không phù hợp.
Khác GPU/platform giữa EN và VI cần ghi provenance và thảo luận confound.
Feedback giảng viên về literature/novelty, Yes Rate, parser/failure analysis và
paired transitions vẫn phải hoàn thiện cùng kết quả main; không claim đã trả lời RQ.

Đã push hai commit hạ tầng/hướng dẫn: `5b7da87` và `2f6cac4`; báo cáo/context ghi trong commit tiếp theo. Không chạy inference mới. Mở [hướng dẫn thực nghiệm](../hướng%20dẫn%20thực%20nghiệm/README.md) để tải bốn gói cá nhân. WIP adjudication/freeze, master/ảnh/weights vẫn giữ local.

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

### v31 — 24/11/2026: Audit image pipeline và kế hoạch so chính sách ảnh

Theo yêu cầu audit sáu điểm, đã lần theo materializers, pilot/main adapters,
review v1/v2 và processors cached đúng revisions trong transformers 4.57.1.
JSON review chỉ context/decisions; image_path/hash ở CSV, HTML nhúng nguyên
JPEG base64. Đã so bytes 1.000 cards v2, 1.000 v1 và 30 pilot; 46 JSON không
có image data URL. Ghi kích thước 1.030 dòng/813 ảnh trong audit JSONL;
review intrinsic bằng JPEG, CSS viewport-dependent chưa đo layout browser.

Thumbnail RGB LANCZOS max512 được truyền vào processor ở cả pilot/main.
CPU probe 30 pilot ×2 models ×3 policies đủ 180 records, không weights/GPU:
Qwen current fast class resize theo patch/pixel bounds, có thể upscale;
Gemma slow no-pan-and-scan vẫn ép 896×896, có méo tỷ lệ. Cả hai model có
27/30 tensor A/B khác nhau; không diễn giải thành prediction flips hoặc
số đo VRAM/thời gian. Không center crop/spatial padding trong đường đang
dùng; không nontrivial EXIF orientation ở 813 ảnh. 1.296 file đầu vào giữ
hash trước/sau audit, JPEG khớp manifests; không lưu đè ảnh gốc.

Report/evidence và script tái kiểm ở reports/audits/2026-11-24/. Đề xuất
30 ảnh pilot QA approved, A512 so Bảnh gốc cùng processor; C ảnh gốc/default
Qwen budget là nhánh tách vì đổi hai yếu tố. A/B 240 cells nếu 1 repeat,
720 measured generations nếu 3 repeats, warm-up riêng. Kế hoạch ghi raw/
invalid/OOM, paired changes, processor/token shapes, timing stages và peak
allocated/reserved baseline/delta; chưa thực hiện hoặc duyệt GPU comparison.

Đã làm rõ docs baseline và links; không sửa configs/main/runtime, data,
human decisions, lịch sử raw/ZIP hoặc bypass freeze gate. Lần probe đầu
return_tensors=np không được Qwen fast hỗ trợ, helper đổi sang pt rồi đạt;
không chạy lại full suite. 396 tests vẫn là v13 ngày 22/11. Stage 1 vẫn
IN_PROGRESS, main frozen=false; Gemma engineering pilot cũ đã xong. Bước
tiếp là nhóm quyết định A/B/C và repeats, rồi mới triển khai harness pilot
riêng và xác nhận bounded GPU run; tiếp tục nhận JSON main A/B như trước.

### v32 — 24/11/2026: Harness A/B và coverage blocker trước GPU validation

Người dùng cho phép triển khai/chạy A/B kỹ thuật có điều kiện đủ bốn task,
240 measured cells, không C/main/freeze; xác nhận thuyết trình 03/12/2026.
Đã kiểm 30/30 approved pilot chỉ RePOPE. Không chạy 240 cells thiếu coverage.
RTX 3060 Laptop 6 GB, capability 8.6: CUDA matmul FP16 và BF16 thật đạt;
không gọi VLM, không load/download weights. Hai execute attempts CPU bị
TASK_COVERAGE_MISSING spatial/counting/fine_grained chặn trước adapter load,
không tạo run directories. Coverage là blocker, chưa có bằng chứng load/
OOM/model-access mới. Main gates vẫn 1000 QA pending, chưa frozen/receipt/M3.

Thêm image_ab.py và validate_image_ab.py: kế thừa MainAdapter/loaders/parser/
prompt renderer, A thumbnail512 so B original với cùng processor instance;
pilot-only gates/provenance/exclusions, fingerprints, observer shapes/grid,
raw/parse/correctness/errors, common latency, allocated/reserved baseline/
peaks, excluded warm-ups và atomic cells. Một repeat, AB/BA xen kẽ, 4 warm-up
per model; không tự resume/fallback. Analysis giữ paired/four-way-valid
denominators; metrics hiện null/NOT_RUN, không dùng giả thay GPU evidence.

Proposal metadata cụ thể 6 RePOPE đã QA +8 VSR +8 TallyQA +8 Pet. 24 candidates
chọn từ pinned frames hiện có, không trùng main/pilot IDs. Chưa acquire ảnh,
kiểm byte exclusions/dịch/review; cần proof thật trước manifest pilot mới.
Distribution từ audit 813 ảnh: 352 cạnh dài <=512, 458 từ513–640, 3 >640;
không chạy/đọc main outputs để chọn policy. Recommendation tạm giữ A trong
draft do thiếu real GPU evidence cho B, không khẳng định A accuracy cao hơn.

Full suite mới **416 passed/20,77 s**, gồm20 A/B tests. Fake adapter/torch chỉ
trong pytest tmp để kiểm orchestration, không đưa fake predictions vào report.
Targeted failures ban đầu về source fixture/proof và Windows codec được sửa,
suite cuối đạt. Evidence/report/commands ở reports/validation/image_ab_v1/;
Runtime/configs/human data/main và pilot cũ, raw, ảnh, ZIP, freeze gate giữ nguyên.
Stage1 vẫn IN_PROGRESS; GPU A/B chưa hoàn thành. Bước tiếp cụ thể: hoàn tất
ảnh/EN–VI/human QA 24 supplement rồi run240 cells +8 warm-ups và mới đề xuất
protocol/hashes khác nếu nhóm chọn B; không tự đổi/freeze main config.

### v33 — 24/11/2026: RePOPE diagnostic được tách khỏi full validation

Người dùng cho phép mode riêng, Phase1 6 ảnh/48 cells rồi mở rộng30/240cells
tổng nếu khả thi; ưu tiên reuse tương thích. Full-mode bốn task và M3 không
thay đổi. Đã thêm diagnostic_plan/run, QA import row-hash/manifest binding,
upstream source auditor offline, registry/main ID+SHA exclusions. Fingerprint
chung qua phases, check environment/code/settings/processor trước generation
mới; raw/reuse receipts giữ nguồn từng cell. Giữ lịch sử report v1 nguyên vẹn.

Phase1 GPU thật: Qwen24/24, Gemma24/24 valid;8 warm-up riêng. Phase2 reuse
48 measured cells, thêm96/model, đủ240 measured/30 ảnh,16 warm-up tổng;
0 invalid/failed/OOM/missing. Raw ở results/pilot/repope_image_ab_v1/phase1/
và phase2/, reuse receipts và analyzer đối chiếu source/row/image/prompt/
runtime hashes. Raw giữ HEAD0a910e6/code_dirty=true và implementation hashes
thực lúc chạy; không gán ngược commit công bố mới vào raw.

Qwen p50 A540,6/B650,3ms, peak allocated2539,3/2804,5MiB; flips EN2/VI3,
correctness57/60→54/60. Gemma p50 A12164,4/B12102,7ms, allocated5720,9/
reserved6332MiB cả A/B; flips EN1/VI0, correctness53/60→54/60. EN–VI
disagreements3→2/30 ở mỗi model. Đây là RePOPE pilot one-repeat, không claim
accuracy gain/significance hoặc bốn task. Reserved không phải physical
residency; main smoke vẫn cần kiểm tài nguyên thật.

Recommendation B chỉ đề xuất: bỏ resampling dư, cost Qwen+20,3% p50 và
+265,2MiB, không lợi ích VRAM từ512 ở Gemma. Chờ nhóm duyệt policy/version/
hashes mới, không sửa/freeze main. Full validation gate giữ nguyên. Full
suite423 passed/23,60s,27 A/B tests gồm7 mới, sau khi GPUmeasurement kết thúc.
Giữ813 source hashes và430 Git files ngoài các file được phép sửa; v1 reports,
QA JSON/manifests/configs/legacy runners/history không đổi. Private ZIPraw
không ảnh/weights/tokens, metrics/report/receipts ở report mới.

Diagnostic đã hoàn tất phạm vi30 RePOPE; Stage1/M1 vẫn IN_PROGRESS, M2chưa
freeze, M3NOT_RUN. Tiếp theo nhóm chốt A/B, hoàn tất main human QA/import,
tạo final config/protocol/receipt mới rồi bounded main GPU smoke bốn task;
không chạy lại pilot vô cớ hoặc trì hoãn main để mở thêm diagnostic.

### v34 — 24/11/2026: Chính thức chọn B cho main, chưa final freeze

Người dùng và task đính kèm chốt B, cho phép triển khai code/config độc lập
main QA. Thêm candidate baseline_v3_option_b_v1.yaml (frozen=false/null receipt),
policy original_rgb_processor_v1/image_max_edge=null. Main helper decode/RGB
giữ kích thước nguồn; chỉ A lịch sử thumbnail. CLI default B; model/processor
pins, NF4/dtype, generation, prompts/parser, seed, sampling/labels/IDs không đổi.
Không thay review packets/HTML/JSON/ZIP, source JPEG hoặc diagnostic raw cũ.

Schema giữ tên v1, additive policy/version và optional input-dimension fields
cho tương thích; B success yêu cầu W×H nguồn/input khớp. Policy/settings,
processor pins/flags và code hashes đi vào protocol mới. Option A config vẫn
giữ bytes và có thể đọc qua --config; không gán hashes mới vào outputs cũ.
Historical replay dùng đúng source1a253f6 tái tính240records exact metrics,
không Torch/Transformers/GPU. Không mở lại diagnostic hoặc sửa source cũ.

M3 đã chuẩn bị --smoke-per-task1/2: đủ bốn task/ENVI/hai model, IDs ghi riêng
trong identity/fingerprint, full grid vẫn4.000. Gate kiểm toàn bộ main QA/
freeze/provenance/leakage trước load; không dùngprefix --max-cells để giả
coverage. Scope main_gpu_smoke tách main benchmark. Observer hiện có được
reuse cho main shape/grid/input tokens và reserved-memory trace, không đổi
processor kwargs. Chưa chạy M3 và chưa có main generation.

Kiểm thực: full441passed/24,00s, targeted82passed/17,38s, thêm18cases;
4.000-cell plan/6 CPU platform-label dry-runs đạt; hai execute attempts
bị main gates chặn trước runtime. Helper B giữ RGB/W×H/SHA trên813ảnh.
Processors thật CPU nhận640×480 trên approved pilot ở cảQwen/Gemma,
Qwen grid34×46 vàGemma896×896 như pins. Không loadmodel weights hoặc
generation mới. Một targeted fixture issue do evaluator extra field đã sửa
trước full suite. Evidence/report/commands tại [v14](stage1/v14/completion.md).

Policy đã chọn không phải dataset/protocol freeze: M1 IN_PROGRESS (1000QA
pending), M2 PENDING, M3 NOT_RUN. Gemma reserved6332MiB vẫn không phải
physical residency và chưa bảo đảm main6GB. Tiếp theo import QA thật,
chốt final manifest/config/protocol/receipt mới, rồi main GPU smoke bốn task;
không tự frozen=true, full4.000 inference, RQ3/RQ4 hoặc training.

Code/config/tests Option B đã push riêng lên origin/main tại
`96417fa204a20163d38d1b8b86e5452a8809e885`; tài liệu/evidence v34 được công bố
trong commit kế tiếp. Không chạy lại các kiểm tra đã đạt chỉ để hoàn tất push.

### v35 — 25/11/2026: Pet xác nhận dịch và chất lượng ảnh, kế thừa nhãn nguồn

Sau thảo luận, người dùng đồng ý quy trình riêng cho Pet và xác nhận đã kiểm
ảnh/dịch, không thấy vấn đề. Đã lưu nguyên declaration với ID quy ước
project_user_conversation và thời điểm ghi nhận; không suy ra thời điểm xem
từng ảnh, không tạo reviewer B hoặc human breed identification. Policy
pet_human_translation_image_quality_source_labels_v1 chỉ áp dụng Oxford Pet.
Nhóm kế thừa nhãn official test annotations, không claim tự xác minh giống.

Đã tạo JSON tổng hợp 160 mẫu, dry-run/import thành manifest mới ở
data/main/reviewed_pet_source_v1/oxford_pet_reviewed.csv. Kiểm archive/source
record/class/species/breed, A–H, image receipts/decoding/SHA và pilot exclusions
đạt160/160, mỗi nhãn20mẫu. Baseline nhận proof riêng và recheck exact review/
source/imported rows; policy không áp dụng được cho task khác. Evidence/file
hashes được bind protocol; không hạ gate của ba task còn lại hoặc freeze gate.

Full suite thực471passed/37,37s, thêm30cases; targeted110passed/20,91s. CPU
staged plan4000cells với160Pet approved/840pending, giữcellIDs/prompts. Hai
execute attempts bị QA/freeze chặn trước environment/model. Không GPU run
hoặc main generation mới. Đối soát457Gitfiles cũ ngoài delta,813JPEG,
20rawfiles,23HTML và4ZIP không đổi. [Evidence v15](stage1/v15/completion.md).

Drafts, main configs, source labels/GT/IDs, reviewv2 packets/HTML/ZIP và raw
lịch sử giữ nguyên. Candidate mặc định vẫn trỏ drafts1000pending; reviewed
Pet được lưu riêng để tổng hợp final sau. M1 còn840mẫu/18gói A/B, M2 chưa
freeze, M3 NOT_RUN. Bước tiếp: nhận JSON A/B RePOPE/VSR/TallyQA, import version
mới và tổng hợp cùng Pet đã duyệt; không cần làm lại bốn gói Pet.

### v36 — 25/11/2026: Tiếp nhận feedback giảng viên và đối chiếu bản Word

Đã đọc phản hồi giảng viên người dùng dán trong hội thoại và nội dung180
paragraph của `Cap_nhat_project_VLM_EN_VI_feedback_giang_vien_gui_Codex.docx`
(SHA256 `32c18b0758574ad0a888d2a169cc877d22810edd58ed4df050c6d029772baa2e`).
Word là bản discuss với ChatGPT; phân biệt các đề xuất trong tệp với yêu cầu
hiện tại của người dùng. Chưa tự thực thi các mục code/commit trong tệp.
Audit bắt đầu trên main HEAD6ac3a1a, worktree sạch; chỉ cập nhật completion
để giữ context. Không sửa Word, code, protocol, QA JSON, dataset hoặc config.

Gap code được đọc trực tiếp: evaluate.py đã có confusion/FPR/FNR, valid-only
và all-expected accuracy, coverage/excluded status counts, disagreement và
hai off-diagonal correctness counts. Chưa có Yes Rate, both_correct/both_wrong
và bộ exports CSV/Markdown tổng hợp được đề xuất. Parser hiện conservative,
có aliases EN/VI và Unicode NFC cùng tests; chưa thấy căn cứ để nới parser
hoặc đổi prompts. Statistics giữ jointly-valid negative RePOPE ΔFPR, image
clusters và bootstrap seed42/B5000. Đây là đọc code, không phải test run mới.

File Word dùng snapshot v34/441tests, mới nhất là v35/471tests có receipt;
phần Pet còn nói A/B nên không thay thế quyết định thật v35 về một declaration
dịch/chất lượng ảnh và nhãn nguồn. Không làm lại Pet hoặc tạo reviewer B.
Main còn840mẫu chờ QA; M1 IN_PROGRESS, M2 PENDING, M3 NOT_RUN như trước.

Đã xác minh sơ bộ nguồn học thuật gốc, chưa làm systematic literature review:
[Ye và cộng sự, CLAIM, ACL2025](https://aclanthology.org/2025.acl-long.640/)
đã nghiên cứu multilingual object hallucination và attention intervention;
[He và cộng sự, NAACL2025](https://aclanthology.org/2025.naacl-long.349/)
đánh giá hallucination sau loại vật thể khỏi ảnh;
[Mousi và cộng sự, arXiv2602.05437v2](https://arxiv.org/abs/2602.05437v2)
dùng true/counterfactual statements EN/Arabic/dialects. Đổi ảnh và đổi mệnh
đề là các thiết kế khác nhau, không gộp thành cùng một RQ4. Không claim
first/SOTA, novelty hoặc cơ chế từ language gap. Định vị đề xuất là empirical
EN–VI paired evaluation với answer-bias/correctness/error analysis; RQ4 vẫn
conditional/future work. Không test/inference/QA/freeze/commit/push mới.

### v37 — 26/11/2026: Tổng hợp18JSON main và danh sách28mẫu cần đối soát

Người dùng nộp đủ JSON trong reviewed_final, yêu cầu tổng hợp các bất đồng,
sửa dịch và đề nghị sửa nhãn nguồn. Bắt đầu HEAD52cbdd8/main; completionv36
và5RePOPEJSON đã dirty từ người dùng. Giữ nguyên bytes input và context đó.
18/18 JSON đúng packet/hash/IDs/template; strict importer kiểm cả history,
hai ID khác nhau, finalVI và ảnh, không có import error. Long A/Long B được
người dùng xác nhận là hai người; không tạo reviewer hoặc approval mới.

Đã import812/840mẫu đạt,28chưa đạt; cộngPet160giữ nguyên thành972/1000.
RePOPE582/600, VSR120/120, TallyQA110/120, Pet160/160. Manifest mới giữ đầy
đủ IDs/GT/source/783ảnh, pending/rejected không bị loại.35bảnVI thay đổi,
31mẫu sửa đã đủ cảhaiQA,4mẫu sửa còn trong28. Lịch sử/góp ý A không thay
approval trên bảnVI mới;3mẫu phải A duyệt lại sau B áp dụng câu sửa.

28mẫu phân nhóm chính không trùng:11cùng observation khácsource,9observation
bất đồng,3cầnAduyệtVImới,3dịchpending/bất đồng,2imageQA pending. Các flag phụ
vànotes nguyên văn được giữ. TallyQA observation1000/10000 và trường hợp
observation5/note4 được nêu rõ để đối soát, không chuyển thành nhãn mới.
JSON/report/CSV/HTML ảnh gốc và lệnh ở [v16](stage1/v16/completion.md).

Thêm workflow aggregation nhỏ, tái sử dụng v2 importer/Pet checker; không
sửa backend/template/proofgate hiện có. Input hashes kiểm trước khi xuất,
không ghi đè outputs. Full suite thực488passed/33,46s, thêm17cases; targeted
70passed/8,35s trước case cuối. Bảy lỗi fixture đầu do VI nonempty/status
missing đã sửa, không nới schema. CPU staged plan4000cells giữcellIDs/EN
prompts;70VIprompts thay đổi do35text sửa trên2models. Hai execute attempts
bị28QA+freeze blockers chặn trước environment/model. Không inference mới.

Đối soát813JPEG,20historicalrawfiles,23HTML/4ZIP cũ và492Gitfiles ngoài delta
được phép.18inputJSON/Pet/raw/labels/configs vẫn nguyên; ảnh trên HTML đối
soát là nguyên JPEGbytes, chỉ scale hiển thị. M1IN_PROGRESS28mẫu, M2PENDING,
M3NOT_RUN. Bước tiếp: giải quyết28mẫu và quyết định cách xử lý source-label
disputes trước freeze; không tự đổi nhãn/EN/targets hoặc giảm1000mẫu.

Đã push nguồn review nhận được riêng tại `e7dda40` và công cụ/tests tại
`e76b0a6`; manifest/report/completion được công bố trong commit tiếp theo.
Các JSON nguồn trên Git khớp exact bytes/hashes đã dùng tổng hợp; không tự
thay attribution của người duyệt. HTML đối soát có ảnh vẫn chỉ ở exports local.

### v38 — 26/11/2026: HTML chỉnh sửa và chốt28mẫu còn lại

Người dùng yêu cầu một HTML để tự sửa/chốt VI và nhãn cho28mẫu. Đã tạo
exports/main_review_adjudication_v1.html, khoảng3MB, standalone/offline với
nguyên28JPEG, EN/VI/nhãn gốc, ý kiến/history A/B và form quyết định mới. Không
ghi đè readonlyHTMLv16 hoặc18JSON. UI có tên/ID người chốt, label typed,
lý do bắt buộc khi sửa nguồn, hai ô kiểm dịch/ảnh trước resolved, lưu/nạp/
download/tiến độ/unsaved guards; lưu tạm lỗi vẫn tải JSON được. Sửa quyết định
đã lưu giữ history. Nguồn label được lưu riêng với resolved_ground_truth.

Schema main_adjudication_v1/policy human_resolution_translation_and_label_v1
bind28IDs/case/source hashes/template. Chỉ xuất pending và kiểm JSON; chưa
thay main review proof gate, chưa nhập nhãn hiệu chỉnh vào CSV hay freeze.
Tên file tải main_28_adjudicated_v1.json; không trộn vào18JSONv2. Khi có quyết
định thật mới kiểm/import version/provenance phù hợp. [V17](stage1/v17/completion.md).

Full suite thực511passed/32,27s,23cases mới. Targeted22passed/1,62s trước case
guard CLI cuối; UI handlers synthetic chạy Node/minimalDOM và JSON roundtrip
backend. Một lỗi mock input.value của0không ép string đã sửa; không nới parser.
ActualHTML28pending/0resolved,28JPEG exacthash, nguồn/contextkhớp, node --check
đạt;517Gitfiles cũ ngoài delta giữ nguyên. Chưa visualbrowserQA. Thêm template
vào package-data, không dependency mới. Không userdecisions/QA/import/GPUrun
mới. Bước tiếp người dùng mởHTML, chốt và gửiJSON; M1còn28/M2PENDING/M3NOT_RUN.

Code/template/tests đã push riêng tại `728d86f`; hướng dẫn/receipt/completion
được công bố trong commit tiếp theo. HTML local vẫn giữ đúng hash export.

### v39 — 26/11/2026: Kiểm JSON28mẫu và báo cáo trước quyết định

Lưu nguyên receivedJSON/SHA, strictvalidate25resolved/3needs_discussion.
Ba QA đề xuất ởnotes/GTnull;13đề nghị đổi nhãn thuộc25mẫu chưa import.
Tạo Markdown/HTML/PDF6trang với3JPEGgốc; render/đọc cả6trang, không clipping/
mất dấu. PDFdependencies riêng ngoàiGit, không đổi requirements. Không main
import/QA/freeze/inference. [V18](stage1/v18/completion.md). Nhận xét/phương án
là trước quyết định v40, không yêu cầu thay lại ảnh hoặc ép quota.

### v40 — 26/11/2026: Tích hợp đúng3TallyQA custom revisions có gates

Nhóm chọn same-image custom QA. Registry lưu fulloriginalrow/history/source
hashes và revisionbinding. V1pending giữ typo; sau người dùng xác nhận “phủ”,
V2 lưu câu mới và chainV1/SHA/userdeclaration. Count4→1,2→4,4→2;997rowkhác,
813ảnh nguồn/reviews/Pet/configs gốc không đổi. Models/OptionB/pins/decoding
và RQ1primary giữ nguyên. [V19](stage1/v19/completion.md).

A mơ/B Lanh thuộc QA gốc, imageQA rejected; Khôi đặt3needs_discussion, QA mới
trongnotes. Không suy thành approvals. Form chỉ3mẫu để hai người đã kiểm xác
nhận finalrevision bằngIDthật/currenttimestamp, không backdate. Tally120=
117original+3custom;59simple/58complex/3pendingclassification. Sensitivity
dùng cùngraw/pairedrows cho120và117; hiệnNOT_RUN/metricsnull, không research
output synthetic hoặc inference mới.

Fullsuite thực532passed/36,17s; targeted76passed/17,982s và UI1passed/1,72s.
CPUplan1000rows/783images/4000cells giữcellIDs,12promptcells thay theo3QA.
Hai executionattempts bịQA/freeze chặn trước environment/model. Kiểm813ảnh
duy nhất từ1030auditrows (hai denominator khác nhau),48inputhashes,
rawdiagnostic córeceipt và2historicalpilotJSONL; không mainGPU mới.

M1vẫn28chưađủgate:25resolved đãnhận nhưng chưaimport, gồm13source-labelrequests
ngoài exact3scope.972mẫu đủcảhaiQA, khôngclaim997approved. M2PENDING/M3NOT_RUN.
Tiếp theo nhận3confirmationV2, tíchhợp25quyếtđịnh theo policy được duyệt,
rồi finalfreeze/receipt→mainGPU smoke→inference. Không tự phêduyệt freeze.

### v41 — 26/11/2026: Nhập proof thật cho3TallyQA revisionV2

Nhận tallyqa_three_revision_confirmed_v1(1).json từDownloads, copynguyênbytes
vào data/reviews/tallyqa_revisions_v1/tallyqa_three_revision_confirmed_v1.json,
SHA41ed6787faf249748114837f297e8b8d96a27bf99eb219f06380cce23ed68a84.
Khôi/Nguyễn Đăng Minh là hai ID khác nhau, cùng approved3/3, ENVI/ảnh/count/
classification khớp finalrevision/context/recordhashes. Không sửa timestamps/
approvals. Importedmanifest/candidate confirmedV2 riêng, giữ pendingV19/registry
và997rowkhác. Classification S/C/S→61simple/59complex; không ép60/60 hoặc
ghi thành officialannotation. [Stage1v20](stage1/v20/completion.md).

Mới chạy21tests passed/2,87s; full532tests là phiên trước. CPUplan1.000rows/
783images/4.000cells, cellIDs/prompts không đổi so pendingV2. Replayproof/
manifest và813imagehashes đạt; hai executeattempts bịQA/freeze chặn trước
environment/model. Không mainGPU/inference/freeze mới, sensitivityNOT_RUN.

Main975đủhai gate/25chờ; RePOPE582,VSR120,TallyQA113,Pet160. M1IN_PROGRESS25,
M2PENDING/M3NOT_RUN. Tiếp theo tíchhợp25quyếtđịnh theo policy được duyệt,
gồm13source-labelrequests, không tự thayGT mẫu khác ởtask này. Không review
lại975mẫu/Pet; đủQA mới finalfreeze/receipt→mainGPU smoke→inference.
HEAD/branch giữnguyên, công việc v18/v19 chưacommit được bảo toàn; khôngpushmới.

### v42 — 26/11/2026: Nhập25adjudications,980đạt/20chờxácnhậnB

Người dùng yêu cầu“làm cho mình nhé” sau khi đề nghị tích hợp25resolutions.
Đãáp13labelcorrections(8RePOPE,5TallyQA)+1VI vàooverlayversionriêng, giữ975row
khác/sourcefiles/originalrow/GT/reviewhistory/images. AdjudicatorKhôi được
biểu diễn từ actualresolved attestation, giữID/time; không tạoapprovalmới.
5casecó người khác đãapprovedđủtrênVI/GTkhôngđổi được táidùng;20casecònthiếu
người thứhai vẫnpending. Không nângrejected/observations thànhapproved,
không đếmKhôi2lần. [Stage1v21](stage1/v21/completion.md).

TạoHTML20mẫu từtemplatev2cũ, actualAseeded/Bblank; BkhácKhôikiểm dịch+ảnh/
nhãncuối rồi gửiadjudication_final_20_reviewed_v2.json. Khôngreviewlại980mẫu.
Followup táidùngstrictv2backend; exactA/VI/context/packet/provenance/phảiđúng.
Candidatebaseline_v3_adjudicated_v1.yaml vẫnunfrozen, main980đạt/20chờ,
M1IN_PROGRESS20/M2PENDING/M3NOT_RUN. Không mainGPU/freeze/inference mới.

Fullsuite550passed/51,18s;targeted16passed/13,12s trước2baselinecases. Kiểm
813imagehashes/570priorfilesngoàidelta, exact25replay,13GT+1VI,975rowskhác,
cellIDs4000nguyên và2VIpromptcellsthay. Hai executeattempts bịQA/freeze chặn
trướcenvironment/model. HTML20JPEGgốc/node--checkđạt; chưa visualbrowserQA.

RePOPEcandidatelabels294yes/306no khôngépbalance;Tally112QAnguyênbản+
5labelcorr+3rewritten. Sensitivity117giữ5labelcorr, loại3rewritten; ghi rõ
composition,khônggọi117QAnguyênbảnhoàntoàn. Metricsnull/NOT_RUN, không thêmRQ.
Lưu ýdiningtablenote“nghiêngvề”còntrong20pending,khôngclaimgoldchắcchắn.
HEADkhôngđổi,khôngreset/overwritepriorWIP hoặccommit/pushmới.

### v43 — 27/11/2026: Hoàn tất bàn giao phần import bị gián đoạn

Đọc lại completionv42/stagev21 và receipt cuối:551tests đạt,0failures/errors/
skips, JUnit52,889s; lần chạy thực ghi26/11. Đây là kết quả cuối sau guardID
UnicodeNFC/NFD, thay cho550tests trước bước bổ sung; không chạy lại tests khi
resume. Plan hiện tại khớp finalprotocolhash và tất cảinput fingerprints.
Không inference/freeze mới. [Receipt](stage1/v21/finalization_2026_11_27.json).

Trạng thái không đổi:25resolutions đã nhập,13GT+1VI sửa,980đạt/20pending,
M1IN_PROGRESS20/M2PENDING/M3NOT_RUN. BkhácKhôi kiểm20mẫu trongHTMLriêng,
khôngreviewlại980/Pet/3QAviếtlại. SauJSONBthật mới import/recheckversion mới
và nhóm quyết địnhfinalfreeze/receipt trước mainGPU smoke/inference.
Preservepriorwork/source/history; khôngcommit/push/reset. Hạn03/12/2026.

### v44 — 27/11/2026: Hoàn tất humanQA1.000/1.000, M1DONE

Nhận adjudication_final_20_reviewed_v2.json, copynguyênbytes, SHA530f73cd0b292bcca36b7c31af669c9fe4bf281026cd42a39ece6e931a00752c.
Strictcontext/packet/IDs/A/VI/history đạt; BNguyễn Đăng Minh khácKhôi.
Raw19/20approvedđủ, repo pe530b0b07f69caf44 imageQApending/observedno.
Hỏi rõ và người dùng xác nhận“approve nhé, bạn ấy quên ko điền”. Giữraw,
ghi user-reportedmissingstatus confirmation, archiveBpendinghistory, ghi
timestampbâygiờ khôngbackdate hoặcgiảdirectreviewersession. Proofdẫnxuất
adjudication_final_20_reviewed_v2_confirmed_v1.json SHAa0f18b81f18619b80902e12bc86eeee37d11369f94948464b1f5d9d962d8ce87.
[Stage1v22](stage1/v22/completion.md).

Importcandidate mới data/main/adjudicated_confirmed_v1/main_reviewed.csv,
configbaseline_v3_reviewed_v1.yaml. ĐủQA600RePOPE+120VSR+120TallyQA+160Pet,
1000IDs/783ảnh/4000cells. Chỉproof/status thay so v21,GT/EN/VI/prompts nguyên.
Raw/source/975rowsngoài25/history vàpriorWIP giữ nguyên.813sourceJPEGhashes
đạt, exactregistry/proofreplay vàexclusions/sourcegates đạt.38tests mới
passed17,29s; full551tests là lịch sử, không chạy lại.

M1DONE,M2PENDING,M3NOT_RUN. Hai executeattempts bịfreeze/receipt chặn trước
environment/model, khôngmainprediction/GPU mới. Preflight chỉ2freeze issues.
Đã chuẩn bịfreeze_review.md đểnhómduyệtconfig/manifest/prompts; chưa tự
frozen=true/receipt/mainGPU. Tiếp theoM2approved→smoke16cells bốntask→mainrun
được cho phép→RQ1/RQ2/report. Không thêmRQ3/RQ4/training hoặc thayprecision.
Đây hoàn tấtM1humanQA,khôngclaimStage1overall/M3hoặcresearchmetricsDONE.

### v45 — 27/11/2026: M2 freeze approved và QwenGPU smoke16/16valid

Người dùng yêu cầu16lượt bất kỳmodel/language trên máy. ChọnQwen,
2sample/task×4task×ENVI=16cells. Sau khi giải thíchM2gate và cấu hìnhv22,
người dùng xác nhận“Đồng ý chốt cấu hình và chạy 16 lượt Qwen”. Lưu explicit
authorization, configfinalmới baseline_v3_final_v1.yaml vàreceiptbind
protocolhash74353c78c3bbed176b75fd1bae6792bc8cf7c8eebaac4383829ac4cdc0cc9d69.
Chỉđổiexperimentid/frozen/receipt, giữmodels/data/prompts/decoding/sourcecandidate.
Approval chỉ16Qwen, khôngfull4.000/Gemma. [Stage1v23](stage1/v23/completion.md).

RealRTX3060Laptop6GB,torch2.7.1+cu126,CUD A12.6,Qwenrevision66285546…,
NF4/FP16,eager,OptionB,offlinecachedweights. Load2shards vàgenerate16calls
thật,16valid,0invalid/failed/OOM/missing_smoke,0warmup/retryngoài16.
OriginalW×H→processor giữ trên16cells, traceoutputshapes/VRAM/latency cóđủ.
Latency p50~1000ms,p95~1542ms,first2812ms,peakallocated2804,55MiB/
reserved3216MiB (allocatorstats). ĐúngGT13/16,EN7/8,VI6/8,1/8pairdisagree;
chỉdescriptive8samplekhôngclaimgeneralaccuracy/languagegap.

RawSHA77f7295298cf6e63c55e28a5eb7fd35fa8b4c90d3f1f07dfbfac9649f4553f32,
copyexact/CSV/meta/paired_explicit8IDs vàmetrics được lưu. Tất cảfreeze
input/implementationhashkhớp; sourcecandidategiữ bytes. Không runtimecode/
unit-test changes hoặc oldtests rerun; kiểm mới làGPUthật+strictverification.
Summaryfullgridmissing1984làunattemptedcells, không phải lỗi smoke16.

M1DONE/M2DONE/M3PARTIAL_QWEN_ONLY. Gemmamainsmoke chưa chạy, fullmainchưa
đượcphêduyệt. Tiếp theo xin thực hiệnGemmasmoke khiusercho phép,rồi mới
quyếtđịnhfullrun. Khôngtựrunchốngscope, khôngRQ3/RQ4/training. HEAD/WIP/
sourcehistorygiữ, khôngcommit/pushmới. Deadline03/12/2026.


### v46 — 27/11/2026: Bàn giao Phase A để từng thành viên đóng góp thật

Theo yêu cầu bổ sung, chuẩn bị bốn assignment configs/guides, hai notebook starter,
Git/PR/file ownership, private master ZIP và bốn thin packages dùng chung SHA.
Không làm thay language sharding/cloud workflow/collection của TV1–TV4, không
giả author/PR hoặc nhận phần scaffolding của Codex là đóng góp sinh viên.
CPU suite mới 567 passed; build/isolated restore receipts ở stage1/v24.
Local M1/M2 v1 và Qwen M3 partial giữ nguyên; không cloud GPU inference mới.
Phase B cần PR integration, cùng pinned release, approval/freeze v2 và cloud smoke.


### v47 — 27/11/2026: Công bố bốn gói hướng dẫn thực nghiệm

Theo yêu cầu người dùng, chuyển đúng bốn member ZIP từ exports vào thư mục
`hướng dẫn thực nghiệm`, giữ nguyên bytes/SHA. Master vẫn ở exports và phân phối
nội bộ; không có link Drive được bịa hoặc public images. Push riêng công cụ/config/
notebook Phase A (`5b7da87`), sau đó role guides/bốn ZIP/checksums (`2f6cac4`).
Kiểm đúng proposed public tree trên HEAD cũ: 527 passed/41,46s; giữ WIP khác ngoài
commits. GitHub connector ghi bị403, native Git fetch/push thành công; remote bốn
ZIP khớp local Git blob SHAs. Không giả author/sinh viên PR hoặc cloud/GPU passed.
Report/receipts mới ở stage1/v25. Runtime/data/freeze/raw smoke/history cũ nguyên
bytes; M1 DONE, local M2 v1 DONE, M3 PARTIAL_QWEN_ONLY. Common execution base/
sharding/PR integration/release mới/cloud verification còn chờ. Không main run mới.
