# Stage 1 v17 HTML chốt 28 mẫu còn lại

Ngày 26/11/2026. Đã tạo một HTML độc lập để người dùng sửa bản dịch và chốt
nhãn cho đúng 28 mẫu. Quyết định thuộc người ghi tên/ID, được lưu riêng;
không giả thành lượt A/B hoặc ghi đè nhãn nguồn.

## File và cách dùng

**[Mở HTML chỉnh sửa và chốt 28 mẫu](../../../exports/main_review_adjudication_v1.html)**

File khoảng 3 MB, nhúng nguyên 28 JPEG nguồn, câu EN/VI và ý kiến/history
A/B. Có thể copy HTML sang máy khác, mở offline; không cần Python/GPU.

1. Nhập tên hoặc ID người chốt.
2. Chọn mẫu, xem ảnh (bấm để mở lớn), câu EN và ý kiến A/B.
3. Sửa **Bản dịch VI chốt**; nhập **Nhãn chốt**. RePOPE dùng yes/no; TallyQA
   dùng số nguyên không âm, kể cả 0. Có nút dùng nhãn nguồn nếu đã kiểm và giữ.
4. Ghi lý do nếu nhãn khác nguồn. Chưa chắc thì chọn **Cần trao đổi thêm** và
   ghi vấn đề; không cần ép mọi mẫu thành đã chốt.
5. Tích hai ô xác nhận đã kiểm dịch và ảnh/nhãn, chọn **Đã chốt**, bấm
   **Lưu quyết định** hoặc **Lưu và sang mẫu sau**.
6. Bấm **Tải JSON** để nhận `main_28_adjudicated_v1.json` rồi gửi lại.
   Có thể tải giữa chừng và **Nạp JSON đã lưu** để làm tiếp.

Chỉ thay đổi đã bấm Lưu mới vào JSON. Trang chặn chuyển mẫu/nạp/tải khi còn
thay đổi chưa lưu. Lưu tạm trong trình duyệt là hỗ trợ; giữ JSON làm bản riêng.
Nếu browser không cho localStorage, vẫn lưu trong phiên và tải JSON được.
Sau sửa quyết định đã lưu, bản cũ được giữ trong history.

JSON mới là **main_adjudication_v1**, không phải main_review_v2. Không nạp nó
vào trang 22 gói cũ hoặc trộn với 18 JSON đầu vào aggregator. Khi bàn giao có
thể đặt tại `data/reviews/main_adjudication_v1/`. Sau nhận quyết định thật,
còn kiểm/import version mới, giữ nhãn gốc/provenance và xử lý policy cho
nhãn hiệu chỉnh trước freeze. Trang không tự áp dụng lên main hay tạo approval A/B.

## Code và tái lập

`src/vlmbench/review_adjudication.py` bind IDs/source hashes/template/ảnh và
validate quyết định/history, typed labels, lý do sửa nhãn, ID/time và hai
xác nhận dịch/ảnh. Template cùng tên cung cấp editor offline. Script mới
`scripts/adjudicate_reviews.py` export hoặc validate, chưa import/freeze main.
`pyproject.toml` thêm template vào package data, không dependency mới.

```powershell
.venv/Scripts/python.exe scripts/adjudicate_reviews.py export --html exports/main_review_adjudication_v1_rebuild.html --report reports/stage1/v17/export_rebuild.json
.venv/Scripts/python.exe scripts/adjudicate_reviews.py validate --review data/reviews/main_adjudication_v1/main_28_adjudicated_v1.json --require-complete --report reports/stage1/v17/returned_validation.json
.venv/Scripts/python.exe reports/stage1/v17/verify_editor.py
.venv/Scripts/python.exe -m pytest -q
```

Chọn paths mới nếu file đã có. Validate chỉ chạy sau khi nhận JSON thật;
bỏ `--require-complete` nếu kiểm bản đang làm dở. Output liệt kê source label
và nhãn chốt khác nhau cùng lý do, không tự sửa CSV/GT.

## Kiểm chứng thực tế

[Export receipt](export.json), [verification](verification.json),
[software checks](software_checks.json), [JUnit](software_tests.xml).
HTML ban đầu có **28 pending, 0 resolved**, nhãn chốt trống và không tự điền
reviewer/time. VI điền sẵn để chỉnh, không được coi là approval.

Full suite **511 passed/32,27s**, 23 cases mới. Trước guard va chạm HTML/report
paths: 510 passed/29,02s; targeted trước case cuối: 22 passed/1,62s. Một lỗi
UI test ban đầu do DOM giả không ép input.value của số 0 thành string như
browser; đã sửa mock, không nới validator hoặc sửa dữ liệu thật.

Handlers chạy Node/minimal DOM với synthetic fixtures và JSON round-trip:
save/download/restore/history, nhãn 0, lý do sửa nhãn, thiếu checkboxes,
unsaved edits và localStorage failure. Chưa visual browser QA. HTML thực có
đủ 28 pending, context đúng nguồn, 28 JPEG nhúng khớp SHA; JS qua `node --check`.
517 file Git cũ ngoài delta được phép giữ nguyên, kể cả source JSON, manifest,
labels/configs và trang readonly v16. Không quyết định thật hoặc inference mới.

**M1 còn 28 mẫu, M2 PENDING, M3 NOT_RUN.** Bước tiếp là người dùng mở HTML,
chốt và gửi JSON; sau đó mới đối soát/import version mới trước freeze.

Code/template/tests đã push riêng tại `728d86f`; hướng dẫn/evidence được
công bố trong commit tiếp theo. HTML có ảnh vẫn là file private trong exports.
