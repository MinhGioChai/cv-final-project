# Review main v2 — A và B đều kiểm dịch và ảnh/nhãn

Ngày 21/11/2026. Người dùng chốt hai người: A duyệt cả dịch và nhãn, B kiểm
lại cả hai. Đây là workflow hiện hành cho main; không cần người C riêng.
Một người làm chưa đủ hoàn tất. Pilot 30 mẫu đã approved không cần duyệt lại.

## Người review làm gì?

Nhận riêng **main_review_v2.zip** (~83,4 MiB), giải nén vào thư mục mới rồi mở:

```text
reports/stage1/v12/main_review/index.html
```

1. A mở gói, nhập ID/tên của mình và chọn **Lượt A**.
2. Mỗi mẫu: kiểm/sửa bản VI, chọn quyết định dịch; xem ảnh, nhập đáp án quan
   sát, chọn quyết định ảnh/nhãn. Bấm **Lưu cả hai phần của lượt này**.
3. A bấm **Tải JSON review**, giữ bản backup và gửi JSON cho B.
4. B mở cùng gói HTML, dùng **Mở JSON đã lưu** để nạp file A gửi, nhập ID
   của B, chọn **Lượt B** và kiểm lại cả hai phần trên từng mẫu.
5. B tải `<packet>_reviewed_v2.json` cuối gửi người tổng hợp. Mỗi gói nộp một
   JSON chứa cả A và B; giữ các file bàn giao trước đó để truy vết.

Thử 2–3 mẫu, tải và mở lại JSON trước khi làm cả gói. Không điền hộ ID hoặc
thời gian. Tên/ID của một người phải thống nhất. Không dùng cùng một ID cho A/B.
Browser tự lưu chỉ là tiện ích; tải JSON trước khi đóng trang.

| Tác vụ | Đáp án quan sát |
|---|---|
| RePOPE | yes / no / uncertain |
| VSR | yes = TRUE, no = FALSE; giữ đúng hướng quan hệ |
| TallyQA | Số nguyên không âm hoặc uncertain |
| Pet | A–H theo danh sách hiển thị hoặc uncertain |

Approved ảnh/nhãn chỉ khi quan sát khớp nhãn nguồn. Nếu không rõ, để pending
hoặc rejected và ghi chú. Rejected/uncertain phải có ghi chú. Không đổi nhãn
nguồn để làm gate đạt. Không có đáp án model trong trang review.

## Sửa VI và điều kiện duyệt

Mỗi lượt có quyết định dịch và ảnh/nhãn riêng, cùng ID và bản VI được xem.
Translation approved cần A/B cùng approved dịch trên bản cuối; QA approved
cần A/B cùng approved ảnh/nhãn và cùng quan sát khớp nhãn nguồn. Hai ID phải
khác nhau. Một người approved và một người pending thì phần đó vẫn chưa xong;
có rejected thì giữ rejected để xử lý, không tự bỏ phiếu đa số.

Nếu B sửa VI, cả hai lượt trước được lưu vào history rồi mất hiệu lực đối với
bản mới. B có thể ghi lượt của mình trên bản mới, sau đó chuyển JSON lại A để
A duyệt lại. Không tính các approvals trong history vào gate hiện tại. Sửa/lưu
lại một lượt cũng giữ bản trước trong history; source fields và ảnh vẫn cố định.

Quy trình này là review nối tiếp, B nhìn được quyết định A; không gọi đây là
hai lượt mù độc lập hoặc dùng nó để suy ra mức đồng thuận độc lập. Công cụ ghi
lời xác nhận/ID/time của reviewer, không xác thực danh tính ngoài đời.

## Dành cho người làm code/import

Git giữ code, template v2, packet CSV/JSON pending và packets.json. Generated
HTML nhúng ảnh và ZIP vẫn ngoài Git. Main 1.000 câu/783 ảnh chưa approved,
chưa frozen; export hoặc tests không tạo human approval.

Sau khi clone và restore `team_workspace_v1.zip` để nhận ảnh/cache theo hướng
dẫn nhóm, sinh bộ mới:

```powershell
.venv/Scripts/python.exe scripts/review_main.py export --version v2
.venv/Scripts/python.exe scripts/review_main.py bundle --version v2 --archive exports/main_review_v2.zip --report reports/stage1/v12/review_bundle.json
```

ZIP/report phải có đường dẫn mới nếu đã tồn tại; đổi tên version khi đóng
gói lại. Export idempotent nhưng từ chối ghi đè file khác bytes, kể cả JSON
đã được người dùng chỉnh. Chỉ nhận ZIP riêng để review thì không cần clone,
Python, GPU hoặc workspace ZIP lớn. Checksum ở [bundle receipt](../../reports/stage1/v12/review_bundle.json).

Lưu JSON cuối vào `data/reviews/main_review_v2/`. Dry-run ví dụ:

```powershell
.venv/Scripts/python.exe scripts/review_main.py import --version v2 --manifest data/reviews/main_review_v2/repope_01.csv --review data/reviews/main_review_v2/repope_01_reviewed_v2.json --output data/main/reviewed_v2/repope_01.csv --audit reports/main_review/repope_01_import_v2.json --operator YOUR_IMPORTER_ID --dry-run
```

Thay ID người import thật. Hợp lệ mới bỏ --dry-run; giữ source batch CSV gốc,
dùng output/audit mới. Import kiểm policy/template/manifest/row hashes, đủ IDs,
ảnh, ID/time, bản VI hiện tại và cả hai QA. Operator không mặc nhiên là reviewer.
Sau từng batch còn cần tổng hợp/đối soát 1.000 IDs, xử lý bất đồng, metadata và
full runner trước freeze. Không tự cho phép chạy 4.000 inference.

## Bản v1 và các gói đã chia sẻ

V1 vẫn giữ nguyên tại data/reviews/main_review_v1 và reports/stage1/v10.
Template/backend v1, hai ZIP cũ, raw và báo cáo lịch sử không sửa. CLI mặc định
mới là v2; muốn xử lý v1 phải ghi rõ `--version v1`. JSON v1 không được mở hoặc
import như v2, và QA v1 của một người không được tự biến thành hai người duyệt.
Nếu đã có review v1 thật, giữ file gốc và đối soát riêng trước chuyển phiên bản.

Giao diện được kiểm qua JS handlers với DOM giả lập và backend synthetic
tests; chưa visual browser QA hoặc thử nghiệm với hai reviewer thật.
