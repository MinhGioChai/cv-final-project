# Checkpoint/recovery — TV4
Core đã có atomic JSONL, metadata, fingerprint/resume và dừng khi error/OOM.
Đọc logic hiện có trước khi thêm export/collection. Utility mới cần kiểm archive,
manifest/SHA, expected grid, model/language, attempts, missing, invalid và failed.

Backup raw/meta/summary/environment cùng nhau; ghi GPU/platform/run ID/protocol/code.
Giữ file corrupt để đối soát. Không âm thầm truncate hoặc xóa để chạy lại.
Retry failed phải explicit; giữ record đã generation thành công, kể cả parse invalid.
Collection giữ provenance từng run; evaluation vẫn paired EN–VI theo model và cluster ảnh.

TV4 cần kiểm JSONL bị cắt, duplicate cells, sai hash/language, thiếu metadata,
run ID/environment conflicts, OOM và restore từ Kaggle private outputs thật.
Đây là contract; TV4 tự triển khai/kiểm chứng phần thiếu và tạo PR/evidence.
