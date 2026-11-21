# Các nhóm script

| Vị trí | Dùng cho |
|---|---|
| `scripts/` | Pilot/setup, review, verify, nhận/gói dữ liệu và kiểm repository |
| `scripts/data/` | Acquisition, selection, materialize và VI drafts; không cần chạy lại để review |
| `scripts/legacy/` | Chỉ có local, ngoài Git: builders Word v1 theo scope cũ, không dùng tạo report V3 |

Lệnh và thứ tự thao tác tại [hướng dẫn nhóm](../HUONG_DAN_NHOM.md).
Pilot dùng `run_pilot.py`; các alias cũ vẫn còn. Script data luôn chạy từ
project root, ví dụ `python scripts/data/prepare_main_selection.py --help`.
Lịch sử di chuyển script nằm trong báo cáo maintenance; dữ liệu/config paths giữ nguyên.
