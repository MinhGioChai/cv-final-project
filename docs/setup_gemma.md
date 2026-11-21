# Gemma pilot cho thành viên trong nhóm

Cập nhật 20/11/2026. `google/gemma-3-4b-it`, revision pinned trong
`configs/models.yaml`. Pilot local đã thành công NF4/BF16 ở v7; không cần
setup hoặc chạy lại trên máy đã có nếu không có mục đích kiểm tra mới.

## Quyền truy cập của mỗi người

Đăng nhập [model page](https://huggingface.co/google/gemma-3-4b-it), chấp nhận
điều kiện truy cập và kiểm tra tài khoản được cấp quyền. Tạo token Read cho
tài khoản đó tại [Access Tokens](https://huggingface.co/settings/tokens).
Token không tự thay thế việc chấp nhận license. Không chia sẻ token giữa
thành viên hoặc ghi vào source/notebook/output.

Local: khi chạy `--online`, launcher hỏi token ẩn nếu chưa có HF_TOKEN trong
environment và terminal tương tác. Token chỉ truyền vào child process,
không được helper ghi vào file. Cloud: dùng Secret HF_TOKEN của notebook,
không paste token vào cell. Xem [Hugging Face tokens](https://huggingface.co/docs/hub/security-tokens).

## Local

Máy mới cài `python scripts/setup_inference.py` bằng Python 3.12. Máy đã có
`.venv-infer`/weights chạy tốt giữ nguyên. Lệnh thống nhất:

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --limit 2 --dry-run
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --run-name my_gemma_v1 --limit 2 --online
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --run-name my_gemma_v1 --limit 10 --resume
```

Giữ `--online` nếu còn cần tải; bỏ flag để cache-only. GPU check chạy trước
weights/auth download, yêu cầu CUDA, native BF16 (capability >=8.0) và BF16
supported. Không tự fallback FP16 vì đường FP16 trước đây đã có NaN/PAD.
Không đạt GPU guard: dùng Qwen hoặc GPU BF16 phù hợp, không đổi parser.

Default output ở `results/pilot/local/team_v1/my_gemma_v1/gemma.jsonl`.
Ctrl+C: giữ toàn bộ file cạnh JSONL, chạy lại cùng args với `--resume`.
`Loading checkpoint shards` là nạp weights đã tải vào model; không cần tải
lại chỉ vì đã ngắt bước load. Không đổi model/config/runtime rồi ép resume.

## Colab/Kaggle

Notebook mới dùng cùng launcher BF16, kiểm secret và GPU, mặc định 2 mẫu.
Nhận `pilot_team_v1.zip` và làm theo
[hướng dẫn cả ba môi trường](run_local_colab_kaggle.md). Cloud GPU availability
và native BF16 không được bảo đảm; chưa có actual cloud generation được ghi nhận.

## Khi có lỗi

- Đọc `.load_error.json` đã sanitize và error phía trên; success generation
  không đồng nghĩa parsed output valid. Không chuyển output rỗng thành NO.
- GPU thiếu BF16/OOM: giữ logs/checkpoint và báo hardware/settings; không tự
  đổi precision/model hoặc sửa source labels.
- Windows lỗi 1455/pagefile: xem [chẩn đoán cũ](../reports/diagnostics/2026-11-18/gemma_load_v1/diagnosis.json).
  Đây là lịch sử đã được xử lý, không phải lý do tạo token mới. Không tự đổi
  pagefile/driver/Windows settings chỉ vì helper báo load failed.

Evidence cũ giữ nguyên tại [v7](../reports/stage1/v7/completion.md). Hướng dẫn
trước cập nhật được lưu trong `reports/stage1/v11/legacy_sources/docs/`.
