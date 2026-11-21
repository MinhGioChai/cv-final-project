# Stage 1 v3 — Portable pilot: local / Colab / Kaggle

**Ngày:** 09/11/2026 (Asia/Saigon). **Mốc nhật ký:** v5.
**Trạng thái:** đã chuẩn bị runner/adapters, notebooks và gói chuyển môi trường;
chưa chạy model thật trên GPU local/cloud. Stage 1 chưa có real model outputs.

## Yêu cầu và quyết định đã ghi nhận

Người dùng muốn thử RTX 3060 của mình, Google Colab và Kaggle, để bạn không
có GPU cá nhân vẫn tham gia chạy. Người dùng cũng xác nhận bản dịch hiện tại
ổn: [translation_acceptance.json](translation_acceptance.json).

Đã tạo manifest pilot v3 với translation_status approved trên 30 mẫu, gắn
bằng chứng chấp nhận ngôn ngữ thực từ hội thoại. Không tạo reviewer CSV thứ
hai hoặc thời gian người review giả. QA ảnh/nhãn vẫn pending. Runner giới hạn
1–30 pilot rows, scope engineering; không mở main/final inference.

## Đã triển khai và kiểm chứng

- Hai notebook Colab/Kaggle sạch output; local setup/run scripts; dùng chung
  CLI `infer-pilot`. Notebook tải ZIP private hoặc nhận Dataset private.
- Cấu hình NF4 4-bit / FP16, single GPU/batch 1, image max edge 512, 8 tokens;
  exact model/processor revisions, dependency versions đã kiểm tra tồn tại.
- Adapter Qwen2_5_VL/Gemma3 theo API Transformers 4.57.1. Chỉ load một model;
  token lấy từ secret/env, không ghi vào metadata/source.
- Raw JSONL lưu atomic từng inference, resume không lặp successful/invalid,
  retry failed có flag, OOM dừng và giữ lỗi; không tự đổi precision.
- Protocol hash chứa config/model/manifest/prompt/code/parser; run hash thêm
  platform/runtime/GPU. Không dùng chung checkpoint giữa môi trường khác nhau.
- Bundle allowlist có code/notebooks/manifest/30 ảnh và context, loại .env,
  venv, weights, prediction files và raw metadata cache. Chưa upload/publish.
- **144 tests passed**, pip check sạch. Tests inference dùng synthetic backend
  trong thư mục tạm, không phải predictions thật.
- **6 dry-run plans**: qwen/gemma × local/colab/kaggle; cùng model có cùng
  protocol hash. Không import torch/load model hoặc tạo predictions ở dry-run.
- Notebook code cells đã kiểm tra Python AST, cell IDs, không stored outputs.

Xem [dry-run plans](dry_run_plans.json), [validation](validation_report.json),
[environment inventory](environment_preflight.json). Bundle được kiểm tra lại
sau build; receipt là `portable_bundle.json`/`bundle_verification.json`.

## Files chính

- `notebooks/pilot_colab.ipynb`, `notebooks/pilot_kaggle.ipynb`.
- `scripts/setup_inference.py`, `scripts/run_local_pilot.py`.
- `requirements-inference.lock.txt`, `configs/inference/pilot_4bit.yaml`.
- `src/vlmbench/pilot_runtime.py`, `src/vlmbench/portable.py`.
- `data/pilot/stage1_v3/pilot_manifest.csv`.
- [Hướng dẫn ba môi trường](../../../docs/run_local_colab_kaggle.md).
- `exports/vlmbench_pilot.zip` được build tại máy, chưa chia sẻ ra dịch vụ ngoài.

## Chưa kiểm chứng / việc tiếp theo

Chưa cài venv inference, tải model weights, thực thi notebook trên cloud,
kiểm thử CUDA/model load hay chạy generation thật. GPU/quota free không được
bảo đảm; Gemma cần chính người dùng chấp nhận license và token có quyền.
Không có accuracy/FPR, thời gian hay peak VRAM model để báo cáo.

Mỗi môi trường bắt đầu Qwen LIMIT=2 (4 EN/VI inferences), sau đó Gemma; lưu
logs/kết quả và tăng lên 10/30 khi ổn. Các bạn dùng tài khoản cloud/secret của
chính mình. Bổ sung compatibility/OOM findings thực tế vào mốc tiếp theo.
Thử ba môi trường không làm tăng số ảnh độc lập của benchmark.
