# Dữ liệu

Manifests, dictionaries và review JSON/CSV được giữ qua Git; ảnh và cache
`raw/` nhận bằng ZIP riêng. Xem **mục 5 và 7 trong
[hướng dẫn nhóm](../HUONG_DAN_NHOM.md)** để chọn đúng gói và manifest.

Review hiện hành ở `data/reviews/main_review_v2/`: A/B mỗi người kiểm dịch và
ảnh/nhãn, một JSON cuối/gói. [Workflow](../docs/research/MAIN_REVIEW_V2.md).
Review v1 vẫn giữ lịch sử; không tự chuyển approvals sang v2.

Preparation_v1/v2/v3 là các bước tích lũy, giữ paths/bytes cho receipts;
không tự chọn manifest lớn số version nhất. Main vẫn chờ human review.
Trạng thái thật nằm trong [completion](../reports/completion.md).
