# Bắt đầu — bàn giao development cho nhóm 5 người

Bốn gói cá nhân công khai và hướng dẫn nhận master nằm tại
[hướng dẫn thực nghiệm](../../hướng%20dẫn%20thực%20nghiệm/README.md).
Master vẫn được phân phối riêng; các đường dẫn ZIP tại `exports/` trong receipts
v24 là vị trí lịch sử trước khi di chuyển bốn gói cá nhân ngày 27/11.

Đây là **Phase A development handoff**. Chạy main cần release và phê duyệt riêng.
Đã có QA 1.000/1.000, frozen local protocol v1 và Qwen smoke 16/16 valid trên RTX 3060.
Core runner hiện chưa có `--language`; cloud main/sharding/recovery integration chưa hoàn tất.

1. Mở TEAM_ASSIGNMENTS.md, điền tên/GitHub của người thật vào role; không gán lại commit cũ.
2. TV5 publish/review common base trước; các thành viên clone cùng base, tạo branch riêng, làm phần mình.
3. Đọc members/<role>/START_TVx.md, DEVELOPMENT_TASKS.md và RUN_GUIDE.md.
4. Cài môi trường CPU, chạy tests/checks; private assets chỉ restore vào `data/raw/` ngoài Git.
5. Từng người tự commit/push/PR. TV5 review/integrate, chốt commit/release chung rồi freeze v2 nếu runtime thay.
6. Phase B mới smoke cloud, execute shard được cho phép và bàn giao raw riêng.

Master ZIP chứa một source snapshot chung + private assets. Snapshot hiện có WIP,
không có .git và **không được giả là pinned release**. Dùng để đọc/diagnostics;
development có attribution phải làm trên Git clone sau khi TV5 publish base.
Member ZIP nhỏ chỉ có hướng dẫn/config và hash trỏ master, không có bản core riêng.

Không cần làm lại human QA/pilot hoặc Qwen smoke v1. Runtime v1 frozen được giữ;
TV1 phát triển bằng branch rồi TV5 đánh giá fingerprint/freeze version mới.
