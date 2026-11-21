# Review pilot RePOPE — quy trình Stage 1

**Cập nhật 20/11/2026:** đã nhận JSON người dùng và import thành công 30/30
image/label QA approved; translation approved 30 được giữ nguyên. Manifest
hiện tại cho QA là `data/pilot/stage1_qa_v1/pilot_manifest.csv`, audit tại
[v10](../reports/stage1/v10/label_qa_import_v1.json). Các câu pending bên dưới
ghi trạng thái lúc tạo packet 19/11, không phải kết quả mới. Không cần review
lại 30 mẫu này. Dữ liệu main dùng [workflow main riêng](research/MAIN_REVIEW_V1.md).

## QA ảnh/nhãn riêng — dùng từ ngày 19/11

Đã có [trang review offline 30 mẫu](../reports/stage1/v8/label_qa_review.html).
Ảnh được nhúng nguyên bản; xem từng mẫu, nhập ID của chính người review,
chọn quan sát YES/NO/uncertain, status và ghi chú rồi **Lưu quyết định mẫu này**.
Trang không hiển thị output model. Ảnh mơ hồ giữ pending/uncertain có ghi chú;
nghi nhãn sai chọn rejected và ghi lý do, không sửa ground_truth. Approved
chỉ khi quan sát khớp nhãn nguồn. Chưa xem thì không điền quyết định.

Bấm **Tải JSON review** để giữ kết quả; có thể mở lại JSON trong trang. Save
trong browser chưa cập nhật manifest. Copy JSON đã tải vào project, ví dụ
`data/reviews/pilot_label_qa_v1/label_qa_reviewed_v1.json`, rồi import vào
đường dẫn version mới. Không gửi token hoặc thông tin cá nhân trong notes.

```powershell
.venv/Scripts/python.exe -m vlmbench.cli import-label-qa --manifest data/pilot/stage1_v3/pilot_manifest.csv --review data/reviews/pilot_label_qa_v1/label_qa_reviewed_v1.json --output data/pilot/stage1_qa_v1/pilot_manifest.csv --audit reports/stage1/v8/label_qa_import_v1.json --operator YOUR_IMPORTER_ID --dry-run
```

Sau khi dry-run hợp lệ, bỏ --dry-run để lưu audit/manifest mới. Công cụ kiểm
đủ sample IDs, context/row fingerprint, bytes ảnh, reviewer/timezone/notes và
quan sát, giữ nguyên toàn bộ source fields, câu VI và translation approved
hiện có. Các decision pending không xóa approval/evidence cũ. Đây là attestation,
không xác thực danh tính. Hiện 30 QA vẫn pending; chưa import quyết định người.

Lệnh dựng lại packet (không ghi đè nội dung đã thay đổi):

```powershell
.venv/Scripts/python.exe -m vlmbench.cli export-label-qa --manifest data/pilot/stage1_v3/pilot_manifest.csv --output data/reviews/pilot_label_qa_v1/review.json --html reports/stage1/v8/label_qa_review.html
```

Các phần bên dưới là workflow review bản dịch cũ/đợt mới. Không dùng sheet V2
để import QA vào manifest V3 đã approved, vì workflow bản dịch có quyết định
riêng và có thể đưa translation về requires_review khi chưa có hai reviewer.

**Cập nhật v3:** người dùng đã xác nhận bản dịch hiện tại ổn. Manifest pilot v3
ghi translation_status approved theo [bằng chứng hội thoại](../reports/stage1/v3/translation_acceptance.json).
Đây là chấp nhận ngôn ngữ để chạy engineering pilot; không bịa reviewer CSV
thứ hai hoặc QA ảnh/nhãn. Quy trình CSV hai reviewer bên dưới vẫn dùng cho
các đợt review có tổ chức/final; QA ảnh/nhãn vẫn còn pending và main gate giữ nguyên.

## Các file hiện có

- [Bảng đọc nhanh 30 mẫu EN–VI và ảnh](../reports/stage1/v2/translation_preview.md).
- [CSV để điền review](../data/reviews/stage1_v2/translation_review.csv).
- [Từ điển 19 đối tượng có từ chỉ loại](../data/dictionaries/object_en_vi.csv).
- [Đối soát nguồn](../reports/stage1/v2/source_audit.json).
- [Nhận xét của bạn và so sánh 10 câu đã sửa](../reports/stage1/v2/feedback_comparison.md).

30/30 mẫu hiện có khớp câu hỏi/nhãn upstream. Người dùng đã xem 10 câu v1 và
nhận xét nhìn chung ổn, yêu cầu thêm từ chỉ loại; phản hồi này đã được lưu.
Ở mốc V2, nhóm giữ đủ 10 mẫu cũ, sửa 9 câu/giữ câu person và thêm 20 mẫu.
Sau đó người dùng đã chấp nhận toàn bộ bản dịch hiện tại theo acceptance v3.
Đối soát annotations và nhận xét về bản dịch không tự xác nhận QA ảnh/nhãn
hoặc có người duyệt thứ hai. CSV/draft V2 còn requires_review/pending, còn
manifest inference V3 có translation approved và image QA pending. Theo
[handoff hiện hành](handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md), áp dụng workflow
QA này cho RQ1/RQ2; không tự mở thí nghiệm P1/P2.

## Cách kiểm tra

1. Mở bảng đọc nhanh, ảnh tương ứng và CSV. Đọc ID ảnh dưới dạng text để giữ
   số 0 đầu; file CSV là UTF-8 BOM. Giữ nguyên tên/thứ tự các cột.
2. Sửa `question_vi` nếu cần, giữ đúng vật thể và nghĩa câu hỏi có/không.
   Hai người review cùng bản dịch cuối cùng. Nếu sửa câu sau khi đã có quyết
   định của một người, đặt quyết định cũ về pending để người đó review lại.
3. Mỗi người điền bộ cột `reviewer_1_*` hoặc `reviewer_2_*`: ID/pseudonym,
   status (`pending`, `approved`, `rejected`) và thời gian `reviewed_at`.
   Thời gian dùng ISO 8601 có múi giờ, ví dụ `2026-11-09T20:00:00+07:00`.
4. `final_status=approved` chỉ khi hai người có ID khác nhau đều approved
   đúng bản dịch đang lưu. Giữ pending khi chưa xong; rejection cần notes.
5. Người kiểm tra ảnh/nhãn điền riêng `qa_reviewer_id`, `qa_status`,
   `qa_reviewed_at`. Duyệt bản dịch không tự duyệt ảnh/nhãn. Nếu nghi nhãn
   sai/ảnh nhập nhằng, ghi notes và rejected/pending; không sửa ground_truth.

`sample_id`, `image_id`, `image_sha256`, `category`, `question_en`, `ground_truth`,
`source_row_sha256`, `manifest_sha256` là các cột nguồn được bảo vệ.
Không sửa/xóa/thêm ID; import yêu cầu đủ toàn bộ row của manifest gốc.
Các cột object/dictionary/template là thông tin draft, không phải quyết định QA.

File `.context.json` cạnh CSV chứa phiên bản manifest/từ điển lúc export;
giữ cùng CSV. Muốn review một manifest khác thì export ra đường dẫn mới.

## Import một phiên bản đã review

Stage 1 hiện đã có bản nháp import tại `data/pilot/stage1_v2/draft_manifest.csv`
và audit riêng; không ghi đè các file đó khi có quyết định người mới.

```powershell
.venv/Scripts/python.exe -m vlmbench.cli import-translation-review --manifest data/pilot/stage1_v2/source_verified_manifest.csv --review data/reviews/stage1_v2/translation_review.csv --output data/pilot/stage1_v2/reviewed_manifest_v3.csv --audit reports/stage1/v2/review_import_v3.json --operator YOUR_IMPORTER_ID --dry-run
```

`YOUR_IMPORTER_ID` là người thực hiện import, không phải người duyệt thay cho nhóm.
Sau khi dry-run hợp lệ, bỏ `--dry-run` để lưu. Sau đó:

```powershell
.venv/Scripts/python.exe -m vlmbench.cli validate --manifest data/pilot/stage1_v2/reviewed_manifest_v3.csv
```

Validation chế độ pilot vẫn cho phép pending; phải đọc counts `qa_status` và
`translation_status` để biết số mẫu thực sự đã duyệt. Chưa có inference command.

## Lưu dấu vết và giới hạn

Import kiểm tra fingerprint manifest/row, nhãn và câu hỏi nguồn, ID đầy đủ,
checksum ảnh thực, reviewer IDs/status/timestamps. Toàn bộ sheet được kiểm tra
trước khi xuất manifest; lỗi một row thì không import một phần.
Audit lưu before/after, nguyên bản quyết định, hash input/review/context/output
và import operator. Chạy lại cùng dữ liệu giữ nguyên audit; đổi quyết định cần
đường dẫn output/audit phiên bản mới.

CSV ghi nhận lời xác nhận của reviewer; công cụ không xác thực danh tính hoặc
chứng minh đã có người review. Người vận hành phải bảo đảm các quyết định là thật.
Không điền approved hàng loạt để vượt gate. Mọi quyết định trong tests là
`synthetic_test_only` trong thư mục tạm, không phải QA dữ liệu dự án.
