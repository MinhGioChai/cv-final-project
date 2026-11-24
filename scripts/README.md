# Các nhóm script

| Vị trí | Dùng cho |
|---|---|
| `scripts/` | Pilot/setup, review, verify, nhận/gói dữ liệu và kiểm repository |
| `scripts/data/` | Acquisition, selection, materialize và VI drafts; không cần chạy lại để review |
| `scripts/legacy/` | Chỉ có local, ngoài Git: builders Word v1 theo scope cũ, không dùng tạo report V3 |

Lệnh và thứ tự thao tác tại [hướng dẫn nhóm](../HUONG_DAN_NHOM.md).
`run_main.py` mặc định CPU plan; dry-run bốn task không gọi model. Main execution
có QA/freeze gates; xem [baseline v1](../docs/research/BASELINE_V1.md).
`validate_image_ab.py` phục vụ technical pilot trước freeze với hardware,
plan/run/analyze riêng; mode mặc định full vẫn cần 30 ảnh/bốn task/QA/provenance/
exclusions. Mode mới `--mode repope-diagnostic --size 6` chỉ nhận canonical
pilot RePOPE đã approved; `--size 30 --phase1 <parent>` mở rộng bằng reuse
tương thích sau Phase1 đủ hai model. Không hoàn thành M3 hoặc mở main.
Xem [diagnostic GPU thật và lệnh](../reports/validation/repope_image_ab_v1/report.md);
[full validation v1](../reports/validation/image_ab_v1/report.md) giữ lịch sử.
`review_main.py` mặc định v2: export/import/bundle cho A/B mỗi người kiểm dịch
và ảnh/nhãn; dùng `--version v1` khi tái lập workflow cũ.
Pilot dùng `run_pilot.py`; các alias cũ vẫn còn. Script data luôn chạy từ
project root, ví dụ `python scripts/data/prepare_main_selection.py --help`.
Lịch sử di chuyển script nằm trong báo cáo maintenance; dữ liệu/config paths giữ nguyên.
