# Stage 1 v16 tổng hợp main review

Ngày 26/11/2026. Đã nhận đủ **18 JSON / 840 mẫu** trong `reviewed_final`,
đối soát context, IDs, row/manifest/template hashes, hai reviewer, bản VI
hiện tại, history và ảnh bằng importer v2 hiện có. Cộng Pet đã duyệt theo
policy riêng: **972/1.000 mẫu đạt; 28 mẫu cần xử lý**. Stage 1 vẫn IN_PROGRESS.

## File để sử dụng

- [Manifest tổng hợp đủ 1.000 mẫu](../../../data/main/reviewed_final_v1/main_reviewed.csv).
- [Danh sách 28 mẫu và việc cần làm](needs_resolution.csv), [JSON chi tiết](needs_resolution.json).
- [Trang đối soát có ảnh gốc](../../../exports/main_review_resolution_v1.html):
  mở bằng trình duyệt trên máy project. Trang chỉ đọc, không lưu approval.
- [Báo cáo máy đọc và source hashes](aggregation.json), [verification](verification.json),
  [CPU preflight](preflight.json), [tests](software_checks.json).

| Tác vụ | Tổng | Đạt cả dịch và QA | Cần xử lý |
|---|---:|---:|---:|
| RePOPE | 600 | 582 | 18 |
| VSR | 120 | 120 | 0 |
| TallyQA | 120 | 110 | 10 |
| Oxford Pet | 160 | 160 | 0 |
| Tổng | 1.000 | 972 | 28 |

Pet giữ nguyên policy ngày25/11, không được đổi thành hai reviewer nhận diện
giống. Người dùng đã [xác nhận hai ID VSR Long A/Long B thuộc hai người](reviewer_identity.json).
Đây là xác nhận trong hội thoại, không phải xác minh danh tính bên ngoài.

## 28 mẫu cần giải quyết

Các nhóm chính dưới đây không trùng nhau; JSON còn lưu các flags phụ và
toàn bộ quyết định/ghi chú/history để không mất các vấn đề đồng thời.

| Nhóm chính | Số mẫu | Cần làm |
|---|---:|---|
| A/B cùng quan sát khác nhãn nguồn | 11 | Đối soát source/ảnh; chưa tự chấp nhận nhãn sửa |
| A/B quan sát khác nhau | 9 | Xem lại cùng ảnh, câu EN/VI và tiêu chí đếm/vật thể |
| A cần duyệt lại VI cuối sau khi B sửa | 3 | A mở JSON cuối và duyệt thật cả hai phần |
| Dịch chưa đồng thuận hoặc pending | 3 | Xử lý góp ý hoặc hoàn tất lượt còn thiếu |
| QA ảnh còn pending | 2 | Reviewer tương ứng ghi quyết định thực tế |

Ba mẫu cần A duyệt lại VI cuối:
`repope_5440bf012a192cbc`, `repope_5988fc0fedca459e`,
`repope_973c58f521d09304`. A đã góp ý câu sửa, nhưng history vẫn thuộc câu cũ
và lượt A hiện tại pending. B áp dụng đúng góp ý không tự tạo approval của A.
Ngược lại, các sửa dịch có đủ A/B approved trên đúng câu cuối đã được import,
không bắt duyệt lại chỉ vì bản VI khác draft. Có **35 bản VI thay đổi**, trong
đó31 mẫu đã đạt cả hai phần và4 mẫu còn trong danh sách28.

TallyQA có các observation `1000`/`10000` và một trường hợp B ghi observation
`5`, note `4`. Các giá trị được giữ nguyên; cần xác nhận số đếm thật hoặc
ghi uncertain theo workflow. Không diễn giải chúng thành ground truth mới.
Các câu EN nguồn mơ hồ/sai ngữ pháp cũng được giữ nguyên và đưa ra đối soát.

Hai người phản đối source label là bằng chứng cần xem lại, chưa đủ để hệ
thống tự đổi nhãn, viết lại EN, bỏ mẫu hoặc thay selection. Muốn dùng nhãn
hiệu chỉnh cần quyết định/version/provenance riêng trước freeze. Hiện vẫn
giữ đủ1.000 IDs/783 ảnh và tất cả source ground truth.

## Cách tiếp tục review

Không làm lại các mẫu đã đạt. Mở trang đối soát hoặc CSV, lấy packet/sample ID,
mở đúng HTML v2 và nạp JSON đã nộp tương ứng. Reviewer sửa/ghi quyết định thật
dưới ID của mình. Nếu đổi VI, cần hai lượt trên cùng bản cuối; không sửa ID,
timestamps hoặc approved bằng tay.

Giữ `reviewed_final` hiện tại làm bản gốc. Để tổng hợp lần sau, tạo thư mục
version mới chứa đủ18 JSON, gồm các gói giữ nguyên và các JSON mới đã xử lý.
Không tự lấy file mới nhất theo tên/thời gian, không ghép hai bản cùng packet.
Các trường hợp source label vẫn pending/rejected cho đến khi có quyết định
phương pháp hợp lệ; không bấm approved chỉ để làm bộ đếm về0.

## Code và lệnh tái lập

`src/vlmbench/review_aggregation.py` và `scripts/aggregate_reviews.py` tái sử
dụng importer v2 cùng Pet checker. Không sửa component review/pilot/baseline
đang hoạt động. Kiểm input hashes lần nữa trước xuất; từ chối unknown context,
duplicate packet, stale VI/identity/approval và ghi đè outputs. Bản tổng hợp
giữ pending/rejected, không khôi phục archived approvals.

```powershell
.venv/Scripts/python.exe scripts/aggregate_reviews.py --input-dir reviewed_final --output-dir data/main/reviewed_final_recheck --report-dir reports/stage1/v16/recheck --operator YOUR_IMPORTER_ID --dry-run
.venv/Scripts/python.exe reports/stage1/v16/verify_aggregation.py
.venv/Scripts/python.exe -m pytest -q
```

Dry-run không xuất file. Import thật dùng output/report paths mới và bỏ
`--dry-run`. Script `make_resolution_report.py` tái tạo CSV/HTML riêng cho
version này, từ chối ghi đè; HTML/ảnh ở `exports`, ngoài Git.

Full suite thực **488 passed/33,46s**, thêm17 cases aggregation. Targeted trước
case cuối:70passed/8,35s. Bảy lỗi fixture ban đầu do synthetic VI nonempty
nhưng translation_status còn missing đã được sửa; không sửa dữ liệu thật
hoặc nới schema để làm tests đạt. [JUnit](software_tests.xml).

CPU preflight đủ4.000cells, giữ cell IDs và toàn bộ EN prompts.35 bản VI sửa
tạo70 VI prompts khác trên hai model; đây là thay đổi từ human review, chưa
có inference trên các câu đó. QA gate còn28 blockers; frozen=false và receipt
chưa có. Hai execute attempts bị chặn trước environment/model. Không GPU
generation, M3 hoặc full main run mới.

## Bảo toàn và gates

18 input JSON không bị sửa;5 RePOPE JSON đã dirty khi bắt đầu được giữ nguyên.
Các thay đổi completion v36 có sẵn cũng được giữ. Source fields/labels/IDs,
drafts/configs, Pet QA, pilot/raw và review HTML/ZIP cũ không đổi. Đối soát813
source JPEG hashes,20 historical raw files,23 HTML và4 ZIP cũ. Trang đối soát
nhúng nguyên bytes28JPEG, chỉ scale khi hiển thị; không có model outputs.

**M1 IN_PROGRESS (28 mẫu), M2 PENDING, M3 NOT_RUN.** Bước tiếp là giải quyết
28 mẫu, tổng hợp version mới rồi kiểm final data/protocol và quyết định freeze;
không tự giảm1.000 mẫu hoặc sửa ground truth để vượt gate. Feedback giảng viên
về evaluation/parser/literature vẫn là đầu việc độc lập, chưa triển khai ở đây.

Nguồn review được push riêng tại `e7dda40`, công cụ/tests tại `e76b0a6`;
manifest và report được công bố trong commit tiếp theo. Commit nguồn chỉ ghi
nhận đúng các file đã nhận, không nhận thay tác giả review trong JSON.
