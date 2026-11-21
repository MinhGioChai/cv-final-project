# Kiểm duyệt main — workflow v1

**Lịch sử:** từ 21/11 dùng [workflow v2](MAIN_REVIEW_V2.md), A/B mỗi người
kiểm cả dịch và ảnh/nhãn. CLI mặc định v2; lệnh v1 dưới đây có --version v1.

Ngày 20/11/2026. Pilot đã có human image/label QA approved 30/30 theo JSON
người dùng gửi; bản dịch pilot approved 30 được giữ nguyên. Main là đợt review
riêng: không dùng acceptance của pilot để approve 1.000 câu mới.

## Nguồn và ảnh

Selection v9 giữ nguyên 600 RePOPE, 120 VSR random/test, 120 TallyQA test,
160 Pet test; seed 42 và tám lớp A–H không đổi. Ảnh mới dùng:

- VSR: cùng bucket COCO và split/filename trong annotation, qua HTTPS S3
  path endpoint để xác thực TLS. Không đổi train2017 thành val2017 hoặc ngược lại.
- TallyQA: từng JPEG trong VG_100K/VG_100K_2 trên máy chủ Stanford được
  trang Visual Genome chính thức liên kết; không tải cả hai ZIP nhiều GB.
- Pet: gói `https://thor.robots.ox.ac.uk/pets/images.tar.gz` được Oxford liên kết.
  Đọc gzip/tar theo luồng, chỉ lưu đúng 160 thành viên regular JPEG đã chọn,
  không extract đường dẫn tùy ý hoặc lưu toàn bộ archive. Kiểm gzip CRC,
  Content-Length và ghi SHA256 quan sát được của cả download vào receipt.

Nguồn tham chiếu: [VSR pinned data README](https://github.com/cambridgeltl/visual-spatial-reasoning/blob/b27a0af0ee1462d2b6b92c8c83e869d9254a241a/data/README.md),
[Visual Genome downloads](https://visualgenome.org/api/v0/api_home),
[Oxford-IIIT Pet](https://www.robots.ox.ac.uk/~vgg/data/pets/).
Pet hash lần tải đầu là receipt quan sát, không phải checksum được nhà phát hành
công bố độc lập. Giữ ghi chú license từ inventory trước; không public lại ảnh.

Cache nằm trong `data/raw/task_images_v1/<dataset>/`. Mỗi ảnh có SHA256,
kích thước, URL/provenance; resume kiểm lại bytes trước khi reuse. So trùng
với pilot và main đã có; kiểm tra tổng hợp cuối cùng cần thực hiện cả khi hai
task tải đồng thời. Không tái mã hóa JPEG. Source fields được so với candidate
frame có checksum từ inventory v8. Kiểm ảnh đọc được không thay human QA.
Nếu Windows giữ receipt tạm thời, công cụ thử atomic replacement tối đa ba
lần. Nếu lần trước đã lưu JPEG nhưng chưa commit receipt, chỉ phục hồi sau
khi tải lại đúng URL chính thức và đối chiếu SHA256 giống hệt; không ghi đè
ảnh có bytes khác, không tự sửa ACL hoặc thiết lập Windows.

```powershell
.venv/Scripts/python.exe scripts/data/prepare_task_images.py --dataset vsr --budget-mb 150 --report reports/stage1/v10/vsr_images_new_attempt.json
.venv/Scripts/python.exe scripts/data/prepare_task_images.py --dataset tallyqa --budget-mb 150 --report reports/stage1/v10/tallyqa_images_new_attempt.json
.venv/Scripts/python.exe scripts/data/prepare_task_images.py --dataset oxford_pet --budget-mb 800 --report reports/stage1/v10/pet_images_new_attempt.json
```

Chỉ chạy lại khi cần; thêm `--offline` để xác minh cache mà không tải.
Mỗi lần dùng report path mới. Pet cần đọc lại archive nếu lần tải trước chưa
hoàn tất xác minh toàn gói, nhưng giữ và đối chiếu các JPEG đã lưu.

## Bản dịch nháp

`prepare_task_translations.py` tạo 400 đề xuất và ghép với image drafts đã có.
VSR giữ thứ tự chủ thể/quan hệ/đối tượng kể cả phát biểu có vẻ sai; không đảo
câu theo ground truth. TallyQA có 120 dòng được ràng buộc với hash chính xác
của selection để tránh dịch lệch dòng. Pet giữ cùng tên giống và mapping A–H
cho cả hai ngôn ngữ. Tất cả là requires_review; không tạo reviewer/approval.

Chú ý các relation như into/off/over/within; trunks, ox, toppings, motors,
tie dye và câu nguồn sai ngữ pháp. Review notes xuất hiện ngay trên trang.
Nếu nghĩa không đủ rõ, giữ pending/rejected có lý do. Không sửa nhãn để
khớp cách dịch hoặc đáp án model. Không sử dụng API dịch/inference trả phí.

```powershell
.venv/Scripts/python.exe scripts/data/prepare_task_translations.py --report reports/stage1/v10/task_translations_new_state.json
```

## Cách review từng gói

Sau khi đủ ảnh/bilingual drafts, xuất gói bằng:

```powershell
.venv/Scripts/python.exe scripts/review_main.py export --version v1
```

Mỗi gói tối đa 50 câu, có một manifest CSV cố định, pending JSON và HTML offline
nhúng ảnh. Toàn bộ bốn task tạo 22 gói. Mục lục được lưu tại
`reports/stage1/v10/main_review/packets.json`; trang vào là
`reports/stage1/v10/main_review/index.html` sau khi hoàn tất xuất gói.
Không có model outputs trong gói. Giao diện mới đã kiểm cú pháp JS/backend;
chưa được xác nhận bằng thao tác trình duyệt trực quan.

1. Nhập ID/pseudonym của chính người đang review, chọn phần đang duyệt:
   bản dịch người 1, bản dịch người 2, hoặc ảnh/nhãn.
2. Bản dịch có thể sửa trong ô VI. Hai người khác nhau phải duyệt đúng cùng
   câu cuối cùng; sửa VI làm reset hai quyết định dịch cũ trên trang. Có thể
   chuyển JSON đã tải cho người tiếp theo mở lại; không điền hộ danh tính.
3. Với QA ảnh/nhãn, nhập `yes`/`no` (VSR tương ứng TRUE/FALSE), số nguyên
   không âm cho counting, hoặc mã A–H cho Pet. Không chắc ghi `uncertain`,
   giữ pending/rejected và thêm notes. Approved chỉ khi khớp nhãn nguồn.
4. Lưu từng mẫu/phần rồi tải `<packet>_reviewed.json`. Dữ liệu local trong
   browser chưa cập nhật manifest. Tải JSON trước khi đóng và giữ bản backup.
5. Lưu JSON đã review vào `data/reviews/main_review_v1/` rồi import bằng lệnh
   dưới. Import yêu cầu đủ IDs, context/row hash, ảnh/checksum còn khớp,
   danh tính/thời gian có múi giờ, hai người dịch khác nhau và đúng bản VI.

Ví dụ gói đầu RePOPE; đổi packet/output version khi xử lý gói khác:

```powershell
.venv/Scripts/python.exe scripts/review_main.py import --version v1 --manifest data/reviews/main_review_v1/repope_01.csv --review data/reviews/main_review_v1/repope_01_reviewed.json --output data/main/reviewed_v1/repope_01.csv --audit reports/stage1/v10/repope_01_import.json --operator YOUR_IMPORTER_ID --dry-run
```

Sau dry-run hợp lệ, bỏ `--dry-run` để lưu manifest/audit mới. Lệnh không ghi
đè output có sẵn. Chưa xong có thể giữ pending, nhưng main gate vẫn chặn.
Đây là lời xác nhận của reviewer, công cụ không xác thực danh tính của họ.
Hai reviewer bản dịch kế thừa quy trình review tổ chức đã ghi trong
[review workflow](../review_workflow.md); không phải yêu cầu chạy lại pilot.

## Sau review

Tổng hợp các batch đã duyệt vào một manifest version mới, đối chiếu đúng
1.000 sample IDs, source fields, metadata và ID/SHA leakage. Xử lý minh bạch
các mẫu rejected/uncertain trước freeze; không tự drop/replace mẫu sau khi
xem model outputs. Metadata/schema baseline và full runner vẫn cần hoàn thiện.
Chỉ xác nhận full-run sau khi dữ liệu và protocol được chốt. Xuất gói review
không đồng nghĩa với freeze hoặc cho phép chạy 4.000 inference.

Kiểm lại toàn bộ ảnh/source fields/exclusions/gate hiện tại mà không inference:

```powershell
.venv/Scripts/python.exe scripts/verify_main_draft.py --report reports/stage1/v10/readiness_new_check.json
```

V10 đã thực hiện kiểm tổng hợp này: đủ 1.000 row/783 ảnh và không phát hiện
technical/leakage issues; gate còn chặn 1.000 main rows chưa QA/translation
approved. Xem [readiness thực](../../reports/stage1/v10/readiness.json).
