# Kaggle — TV2 và TV4

Tạo notebook private và attach Dataset private chứa master ZIP hoặc assets ZIP.
Thành viên cần được cấp access Dataset; chia sẻ notebook chưa đủ để chứng minh
Dataset access. Workflow dùng `scripts/cloud/kaggle_main.py` (chỉ thư viện chuẩn,
không load model) và `notebooks/main_kaggle_starter.ipynb`; core runner vẫn là của TV1.

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

## Lệnh của `kaggle_main.py`

| Lệnh | Làm gì | Ghi file |
|---|---|---|
| `locate` | Tìm đúng một `VLM_ENVI_Main_Inference_Team_v1.zip` hoặc thư mục đã giải nén có `BUNDLE_MANIFEST.json` dưới `/kaggle/input`; 0 hoặc ≥2 bản thì dừng | Không |
| `prepare` | Kiểm SHA256 master, kiểm từng file theo manifest, giải nén vào `/kaggle/working/VLM_ENVI_Main_Inference_Team_v1` mới rồi kiểm lại bản copy | Chỉ `/kaggle/working` |
| `diagnose` | Ghi Python, `nvidia-smi` (GPU, VRAM, driver, compute capability), torch/CUDA trong `.venv-cloud`, `gpu_preflight`, package fingerprint, Internet (khi `--check-internet`), secret có/không | Report JSON mới |
| `runner-check` | Kiểm `run_main.py` đã có `--language` và config freeze v2 chưa; in lệnh smoke mục tiêu, **không chạy** | Không |

Mọi lệnh nhận `--role TV2|TV4` (mặc định TV2). `--report` chỉ ghi file mới dưới
`/kaggle/working`; ghi vào `/kaggle/input` hoặc ghi đè đều bị từ chối.

## Xử lý lỗi

| Thông báo | Nguyên nhân và cách xử lý |
|---|---|
| `/kaggle/input not found` | Chưa attach Dataset. Add Input → chọn Dataset private của nhóm |
| `No VLM_ENVI_... under /kaggle/input` | Dataset không chứa master; xem danh sách ZIP được in ra, kiểm đúng Dataset/version |
| `Ambiguous bundles (N)` | Attach nhiều Dataset/version hoặc cả ZIP lẫn bản giải nén. Gỡ bớt, hoặc dùng `--master PATH` |
| `Master SHA256 mismatch` | Sai bundle hoặc upload hỏng. Lấy lại từ TV5; không sửa giá trị mong đợi |
| `Only an extracted tree was found` | Kaggle có thể tự giải nén ZIP khi upload. Manifest vẫn được kiểm từng file nhưng không gắn được với SHA master; hỏi TV5 rồi chạy lại với `--allow-extracted` |
| `already exists` | Workspace đã được chuẩn bị trong phiên; dùng lại, hoặc mở phiên mới. Tool không ghi đè |
| `nvidia_smi_error` trong report | Chưa bật GPU hoặc hết quota; giữ report, bật Accelerator rồi chạy lại |
| `run_main.py has no --language` | TV1 PR chưa tích hợp. Dừng, không tự viết vòng generate |

## Trạng thái kiểm chứng

- CPU: `tests/test_kaggle_main.py` dùng mount giả trong `tmp_path` (bundle tổng hợp,
  runner giả); không chứng minh Kaggle/GPU.
- Local: `verify_tree` trên bản master đã giải nén của TV2 khớp manifest 717/717 file.
- Kaggle thật (Dataset access, auto-extract khi upload, GPU, Internet, cài venv):
  **chưa chạy**. Khi chạy, thêm vào đây Dataset version, GPU/VRAM thật và lỗi gặp phải.

Availability/quota/hardware cần kiểm trên tài khoản thật. Chạy shard cần pinned release,
approval/freeze và smoke sau integration.

Nguồn: [Kaggle Notebooks](https://www.kaggle.com/docs/notebooks),
[Secrets API](https://github.com/Kaggle/docker-python/blob/main/patches/kaggle_secrets.py).
