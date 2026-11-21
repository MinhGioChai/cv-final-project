# Stage 1 v7 — Gemma NF4/BF16 pilot kỹ thuật hoàn tất

Ngày 19/11/2026 (Asia/Saigon), theo yêu cầu triển khai của người dùng. Đã
hoàn tất diagnostic và pilot Gemma trên cùng 10 mẫu Qwen. Toàn bộ Stage 1/
data QA và benchmark main chưa hoàn tất.

## Thay đổi và nguyên nhân được kiểm chứng

Thêm gemma_diagnostic.py, CLI infer-gemma-trace, launcher run_gemma_pilot.py
và configs NF4/FP16, NF4/BF16. Giữ nguyên pilot_runtime.py, parser, prompt,
model pins, manifest, nhãn và raw cũ để không đổi protocol Qwen/FP16 legacy.
Runner mới có hash riêng, atomic JSONL, explicit resume/retry, cache-only
mặc định, giới hạn 1–10 row, không fallback precision.

Trên cùng 2 mẫu × EN/VI, cùng code/ảnh/prompt/seed/revision, chỉ đổi dtype:

- FP16: 4/4 lượt có logits toàn NaN ở bước đầu (262.208/262.208 giá trị),
  sinh tám token ID 0 (`<pad>`), decode rỗng. Runner mới giữ trace và đánh
  dấu NonFiniteLogits/failed, không chấm như valid. Không sửa trạng thái
  INVALID của raw legacy v1; đây là run chẩn đoán mới.
- BF16: logits hữu hạn, sinh YES/NO. Development đầu còn giữ terminal
  `<end_of_turn>` sau decode nên parser từ chối cả 4. Runtime GemmaTokenizer
  slow không có ID 106 trong all_special_ids, dù serialized configs có
  special=true. Decode([26915,106], skip_special_tokens=True) vẫn ra
  YES<end_of_turn>, đã kiểm trực tiếp không load model.
- Adapter cuối tách đúng một terminal EOS theo generation_config (1 hoặc
  106) trước content decode, giữ mọi ID và decode đầy đủ trong trace. Không
  sửa parser, tìm substring YES/NO hoặc xóa token nội bộ.

[So sánh dtype](dtype_comparison.json),
[snapshot implementation development](development/gemma_diagnostic_initial.py).
Raw development/FP16 giữ tại results/pilot/local bằng version riêng.

## Run cuối thật và kết quả theo nhãn nguồn

Raw `results/pilot/local/gemma_bf16_trace_v2.jsonl`, metadata/summary cùng tên.
Metadata giữ queue smoke ban đầu 2 row; **summary cuối** là selection đúng
10 row cho evaluator. Cache-only, không tải weights mới.

| Chỉ tiêu | Gemma NF4/BF16 |
|---|---|
| Mẫu / ảnh / lượt EN–VI | 10 / 10 / 20 |
| Valid / invalid / failed / missing / nonfinite | 20 / 0 / 0 / 0 / 0 |
| Accuracy EN / VI | 90% / 100% |
| Disagreement | 1/10 = 10% |
| Negative jointly valid pairs / ảnh | 5 / 5 |
| FPR EN / VI | 20% / 0% |
| ΔFPR VI − EN và empirical CI 95% | −20 pp, từ −60 đến 0 |
| Accuracy gap VI − EN và CI 95% | +10 pp, từ 0 đến 30 |
| Median processor+generation | 10.208,95 ms |
| Peak PyTorch allocated | 5720,93 MiB |

Timing có giữ raw logits, không gồm load hoặc CPU trace/decode; không so trực
tiếp với Qwen không instrumentation. Peak không phải tổng GPU/WDDM VRAM hoặc
bộ nhớ lúc load. Không OOM trên subset này không bảo đảm cấu hình khác/main.
Bootstrap percentile B=5000, seed42, pooled row weighting theo image clusters.
Mẫu nhỏ có selection bias và image/label QA pending; không suy rộng language
gap, power, causal mechanism hoặc model ranking. Main chưa freeze/chạy.

[Evaluation JSON](gemma_bf16_evaluation.json), [bảng](gemma_bf16_evaluation.md),
[statistics](gemma_bf16_statistics.json), [runtime report](gemma_local_report.json),
[10 cases](local_cases.md). Case bất đồng là teddy bear, ảnh 000000300368,
source NO: EN YES, VI NO. Giữ nhãn để QA tiếp. Qwen cũ có EN 100%, VI 90%,
ΔFPR +20 pp (CI 0–60) cùng subset; cả hai CI còn chạm 0.

## Tests, resume và bảo toàn

Full suite thực .venv ngày 19/11: **197 passed, 3,13 s**, gồm 22 tests mới
cho dtype/fallback, EOS boundaries, numerical failures, QA, resume/provenance,
OOM, redaction và CLI dry-run. Synthetic tests không phải model evidence.

Smoke 4 lượt giữ byte-for-byte khi mở rộng lên 20. Resume sau hoàn tất không
load model, raw/summary giữ checksum và 20 keys duy nhất. Xem
[smoke summary](gemma_bf16_smoke_summary.json), [checkpoint](smoke_checkpoint.json).
Raw SHA256 cuối: `b976b663ab017a5837728590884cd8928855b8d77a5eba170e7ca4ef4a136de1`.
Gemma protocol: `762b9688985e2a006cdebff34d510b8134ef1699a6ef05b02b42fa7df1504101`.
Qwen protocol vẫn `223b9800b7965aaca6663a13f3b1bb9ce3019081f5cc1248d27e4463ba2077aa`;
raw Qwen và tám protected files v6 giữ checksum. Hai model cùng thứ tự 10
sample IDs. Manifest/exclusions không thay đổi.

Phiên này có **28 generation mới**: 4 BF16 development, 4 FP16 diagnostic
và 20 BF16 cuối (gồm smoke, chỉ thêm 16 khi mở rộng). Không cộng các lượt lặp
thành ảnh độc lập/main data. Không Qwen generation, human QA, đổi Windows
settings, nâng dependencies hoặc main inference mới.

## Dùng lại và bước tiếp theo

```powershell
.venv/Scripts/python.exe scripts/run_gemma_pilot.py --limit 2 --dry-run
# Không lặp 20 lượt đã hoàn tất.
.venv/Scripts/python.exe scripts/run_gemma_pilot.py --limit 10 --resume
```

Mặc định cache-only, output gemma_bf16_trace_v2.jsonl. Máy mới dùng --online
để tải sau khi có quyền/token; helper hỏi ẩn và không lưu token. GPU cần BF16.
Cloud notebooks cũ vẫn FP16, chưa có Gemma/cloud generation được xác nhận.

Pilot Gemma kỹ thuật và evaluation/CI đã hoàn tất, không còn nhắc như việc
chưa làm. Tiếp theo human QA ảnh/nhãn 30 mẫu, main adapters/frame cho bốn task,
baseline metadata/freeze trước xác nhận full-run. P1/P2 giữ gate V3.
