# Pilot notebooks hiện tại

- `pilot_colab.ipynb`: upload **pilot_team_v1.zip**, GPU session, optional Drive.
- `pilot_kaggle.ipynb`: attach private pilot Dataset, GPU/Internet, results ZIP.

Cả hai gọi `scripts/run_pilot.py`: Qwen NF4/FP16, Gemma NF4/BF16. Mặc định
2 mẫu/model, tối đa 10; dùng cùng pilot manifest đã human QA approved. Gemma
chặn GPU không native BF16 trước tải weights, không chạy qua adapter FP16 cũ.

Đặt RUN_NAME riêng, RESUME=True khi tiếp tục cùng config/runtime; giữ
JSONL/meta/summary và tải results ZIP sau mỗi model. Không lưu token trong
cell, outputs, Dataset hoặc Git. Weights/venv/cache ở /tmp, tách khỏi outputs.

Notebook output-free được tạo bằng `scripts/generate_cloud_notebooks.py`.
Đã kiểm syntax/dispatch/dry-run, **chưa có real cloud generation được xác minh**.
Hướng dẫn và lệnh tạo ZIP: [local/Colab/Kaggle](../docs/run_local_colab_kaggle.md).
