# Pilot outputs nhỏ dùng chung trong Git

Các file ở đây được copy nguyên bytes từ `results/pilot/local/` ngày
20/11/2026, để người không có GPU có thể thử evaluation/statistics sau clone.
Không phải inference mới. [Checksums](checksums.json) ghi đường dẫn gốc.

| Model | Raw | Selection |
|---|---|---|
| Qwen NF4/FP16 | [qwen_smoke_v1.jsonl](qwen_smoke_v1.jsonl) | [summary](qwen_smoke_v1.summary.json) |
| Gemma NF4/BF16 | [gemma_bf16_trace_v2.jsonl](gemma_bf16_trace_v2.jsonl) | [summary](gemma_bf16_trace_v2.summary.json) |

Mỗi model có 10 ảnh × EN/VI = 20 records valid. Summary giữ trạng thái QA/
scope tại lúc chạy; pilot QA được import riêng sau đó. Không viết lại raw để
trông như main benchmark hoặc dữ liệu đã approved ngay từ lúc inference.

Ví dụ không cần ảnh/GPU, chạy ở project root sau khi cài môi trường CPU:

```powershell
.venv/Scripts/python.exe -m vlmbench.cli evaluate --manifest data/pilot/stage1_v3/pilot_manifest.csv --predictions reports/pilot_outputs/qwen_smoke_v1.jsonl --selection reports/pilot_outputs/qwen_smoke_v1.summary.json --output results/analysis/qwen_evaluation.json --report results/analysis/qwen_evaluation.md
.venv/Scripts/python.exe -m vlmbench.cli statistics --evaluation results/analysis/qwen_evaluation.json --output results/analysis/qwen_statistics.json --resamples 5000 --seed 42
```

Gemma dùng hai file tương ứng và output path khác. Không resume inference
vào bản snapshot này. Toàn bộ diagnostic/FP16 attempts vẫn giữ trong results
local và các báo cáo v6/v7; snapshot Git chỉ đưa hai run valid vào entry point.
