# Kaggle — TV2 và TV4

Tạo notebook private và attach Dataset private chứa master ZIP hoặc assets ZIP.
Thành viên cần được cấp access Dataset; chia sẻ notebook chưa đủ để chứng minh
Dataset access. TV2 hoàn thiện workflow dưới đây trong PR, tái sử dụng core runner.

1. Ghi Dataset slug/version, path và SHA của bundle được TV5 gửi. Từ chối nếu có
   nhiều bundle mơ hồ; không tự chọn file đầu tiên.
2. Đọc dữ liệu từ `/kaggle/input`, giải nén/copy sang `/kaggle/working` trước khi
   chỉnh source hoặc tạo venv. Input mount là read-only.
3. Kiểm Settings GPU/Internet, package installation và Secrets `HF_TOKEN` đã
   attach notebook. Không ghi token vào code/output.
4. Ghi GPU/capability/VRAM thật. Gemma cần native BF16; nếu không đạt, dừng và
   báo TV5 để xác nhận môi trường khác. Không tự fallback precision.
5. TV4 kiểm backup/restore bằng Saved Version thực tế: raw/metadata/summary
   được lưu, tải về và bàn giao private. JSONL trong session chưa phải backup.

Availability/quota/hardware cần kiểm trên tài khoản thật. CPU tests và notebook
starter chưa chứng minh các bước trên đạt. Chạy shard cần pinned release,
approval/freeze và smoke sau integration.

Nguồn: [Kaggle Notebooks](https://www.kaggle.com/docs/notebooks),
[Secrets API](https://github.com/Kaggle/docker-python/blob/main/patches/kaggle_secrets.py).
