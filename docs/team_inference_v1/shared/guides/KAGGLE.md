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

## Upload master lên Dataset: dùng đuôi `.zip.bin`

Kaggle **tự giải nén** file `.zip` khi tạo Dataset (TV2 kiểm thật 27/11/2026: Dataset
`vlm-envi-main-v1` version 1 hiện thư mục `VLM_ENVI_Main_Inference_Team_v1/` thay vì ZIP,
và `main_assets/` có thêm một thư mục cạnh `main_assets_v1.zip`). Bản giải nén không
gắn được với SHA master. Vì vậy copy nguyên bytes sang tên `.zip.bin` rồi upload file đó:

```powershell
Copy-Item VLM_ENVI_Main_Inference_Team_v1.zip VLM_ENVI_Main_Inference_Team_v1.zip.bin
Get-FileHash VLM_ENVI_Main_Inference_Team_v1.zip.bin -Algorithm SHA256
```

SHA phải vẫn là giá trị TV5 công bố. `locate`/`prepare` nhận cả hai tên.

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
| `Only an extracted tree was found` | Kaggle đã tự giải nén ZIP. Tạo Dataset version mới với file `.zip.bin` (mục trên). Chỉ dùng `--allow-extracted` khi TV5 đồng ý |
| `Bundle file set differs ... extra=` | Kaggle giải nén cả ZIP lồng bên trong (ví dụ `main_assets_v1.zip`); dùng `.zip.bin` |
| `already exists` | Workspace đã được chuẩn bị trong phiên; dùng lại, hoặc mở phiên mới. Tool không ghi đè |
| `nvidia_smi_error` trong report | Chưa bật GPU hoặc hết quota; giữ report, bật Accelerator rồi chạy lại |
| `run_main.py has no --language` | TV1 PR chưa tích hợp. Dừng, không tự viết vòng generate |

## Trạng thái kiểm chứng

- CPU: `tests/test_kaggle_main.py` dùng mount giả trong `tmp_path` (bundle tổng hợp,
  runner giả); không chứng minh Kaggle/GPU.
- Local: `verify_tree` trên bản master đã giải nén của TV2 khớp manifest 717/717 file.
- Master ZIP của TV2 (98.531.572 byte) khớp SHA `29f7b332…` và 717/717 file (`verify_zip`
  và `main_team_bundle.py verify`).
- Kaggle thật: đã xác nhận Dataset tự giải nén `.zip`. Upload `.zip.bin`, GPU, Internet,
  cài venv: **chưa chạy**. Khi chạy, thêm vào đây Dataset version, GPU/VRAM thật và lỗi gặp phải.

Availability/quota/hardware cần kiểm trên tài khoản thật. Chạy shard cần pinned release,
approval/freeze và smoke sau integration.

Nguồn: [Kaggle Notebooks](https://www.kaggle.com/docs/notebooks),
[Secrets API](https://github.com/Kaggle/docker-python/blob/main/patches/kaggle_secrets.py).
