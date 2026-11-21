# Tài liệu lưu trữ

Không dùng các file này làm chỉ đạo scope hiện hành. Mở
[Handoff V3](../handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md) và
[completion](../../reports/completion.md) trước.

## Thiết kế V4.2

Ba file gốc được chuyển từ project root, giữ nguyên bytes/checksum:

- [Research outline](v42/01_RESEARCH_OUTLINE_V42.md).
- [Kế hoạch công việc](v42/02_DRAFT_CONG_VIEC_V42.md).
- [Codex handoff](v42/03_CODEX_HANDOFF_V42.md).

Project root giữ file chuyển tiếp cho các liên kết cũ. V4.2 vẫn hữu ích về
chi tiết kỹ thuật chưa bị V3 thay thế, nhưng RQ mapping, priority của contrast/
paraphrase và negation đã đổi. Không tự kích hoạt fallback 880 hoặc coi ngày
06/12 là deadline chính thức chỉ vì xuất hiện trong lịch cũ.

## Snapshots trước V3

`pre_v3/` (chỉ giữ local, ngoài Git) giữ README, START_HERE, AGENTS, completion và các hướng dẫn
trước đợt tổ chức lại ngày 12/11. File giữ nội dung gốc, kể cả mô tả trạng thái
cũ. Relative links trong snapshot được hiểu từ vị trí gốc ghi trong
[organization receipt](../../reports/audits/2026-11-12/organization_receipt.json),
không phải vị trí mới của snapshot. Dùng mục lục đang hoạt động để điều hướng.

Các báo cáo stage giữ trong Git; hai file Word ngày 11/11 giữ local ở reports như cũ; không chỉnh
lại lịch sử để chúng trông giống đã sử dụng V3.

## Trước khi rút gọn entry points ngày 20/11

`pre_cleanup_2026-11-20/` (chỉ giữ local, ngoài Git) giữ README và START_HERE trước đợt chuẩn bị GitHub,
nguyên bytes. Relative links được hiểu ở vị trí gốc, như snapshot pre_v3.
Completion v1–v21 được giữ nguyên tại
[completion history](../../reports/completion_history.md), cùng thư mục gốc
để các liên kết lịch sử tiếp tục dùng được. Current completion đã rút gọn.
