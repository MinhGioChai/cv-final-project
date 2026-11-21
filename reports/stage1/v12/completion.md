# Stage 1 v12 — A/B kiểm cả dịch và ảnh/nhãn

Ngày 21/11/2026. Người dùng chốt phương án **A duyệt cả bản dịch và nhãn, B
kiểm lại cả hai**. Hoàn thành phần tooling/handoff này; toàn Stage 1 vẫn
IN_PROGRESS vì main chưa có human approval, chưa metadata/full runner/freeze.

## Kết quả sử dụng

- Hai lượt A/B trên một màn hình, mỗi lượt có quyết định dịch và ảnh/nhãn,
  cùng ID/time và bản VI được xem. A tải JSON gửi B, B mở tiếp và gửi JSON cuối.
- Cần hai ID khác nhau cho cả translation và image QA; A làm một mình chưa
  đủ. Nếu B sửa VI, lượt cũ chuyển vào history và A cần duyệt lại bản cuối.
  Không tự lấy đa số, thay nhãn nguồn hoặc tính history như approval hiện tại.
- CLI mặc định v2: export/import/bundle. Muốn tái lập v1 phải ghi --version v1.
  Không tự chuyển JSON/QA v1 thành hai lượt v2 hoặc thay schema runtime inference.
- Tạo đủ 22 gói/1.000 row/783 ảnh tại data/reviews/main_review_v2 và
  reports/stage1/v12/main_review. CSV batch giống bytes v1; pending JSON mới
  chưa có danh tính/quyết định người thật. Không thay selection/drafts.
- Gói riêng `exports/main_review_v2.zip` (nhận riêng, không nằm trong Git),
  87.428.656 bytes (~83,4 MiB), có 23 HTML kể cả index, CSV/JSON pending và
  checksums. ZIP/HTML ảnh không vào Git; [receipt](review_bundle.json).

## Kiểm chứng mới trong phiên

- Full CPU suite **359 passed/8,74 s**, thêm 25 tests cho gates/context/IDs,
  rejected/uncertain/observations, lịch sử, export/ZIP và CLI dry-run/import.
- Node chạy handlers JS thật với DOM giả lập: A lưu, B nạp JSON, chặn trùng
  ID/quan sát sai, B sửa VI giữ lịch sử, A duyệt lại, chặn JSON sai version;
  JSON thu được được backend import và kiểm cả hai gates.
- 22 pending packets được importer v2 validate, không sinh manifest approved.
  Kiểm 1.000 ảnh base64 theo SHA256 nguồn, 68 thành viên ZIP theo hash, 23 HTML.
- 225 file dữ liệu/config/evidence/core/raw/ZIP cũ giữ hash. data/README.md
  được sửa hướng dẫn có chủ ý, không nằm trong nhóm immutable data checks.
- Main readiness vẫn false; technical/leakage issues=0. Không inference,
  model downloads hoặc human approvals. [Verification](verification.json),
  [readiness](readiness.json).
- Build/cài wheel offline vào target riêng đạt, đủ cả ba HTML templates;
  context tính từ template đã cài khớp packet thật và CLI --help chạy được.
  [Package receipt](package_check.json). Không thử tải lại dependencies trên máy trắng.

Chưa visual browser QA hoặc thử nghiệm với A/B thật. B xem được quyết định A;
không gọi đây là review mù độc lập hoặc tính inter-rater agreement độc lập.
Danh tính/time là lời xác nhận trong JSON, không xác thực ngoài đời.

## Tiếp theo

Người giữ project chia sẻ ZIP mới; nhóm thử 2–3 mẫu, tải/mở lại JSON rồi làm
từng gói. Không dùng index v1 trong workspace ZIP cũ cho đợt review mới.
Giữ mọi JSON v1 đã có để đối soát riêng; tại lúc kiểm chưa có file main v1
reviewed gửi vào repo. Import các quyết định thật theo version/output mới.
Song song hoàn thiện metadata/full-main runner trước freeze và xác nhận full-run.

Hướng dẫn cho người review/import: [MAIN_REVIEW_V2](../../../docs/research/MAIN_REVIEW_V2.md),
[hướng dẫn nhóm](../../../HUONG_DAN_NHOM.md). Pilot/Gemma đã hoàn thành engineering
subset cũ; cloud GPU generation vẫn chưa được xác minh.
