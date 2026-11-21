# Pilot findings đã kiểm chứng

**Gemma cập nhật 19/11/2026:** NF4/BF16, cùng 10 mẫu/20 lượt với Qwen,
20 valid, failed/invalid/missing/nonfinite=0. EN accuracy 90%, VI 100%,
disagreement 10%; FPR 20%/0%, ΔFPR −20 pp, empirical CI 95% −60 đến 0 trên
5 negative ảnh. Median có raw-logit instrumentation 10208,95 ms, peak
allocated 5720,93 MiB; không so timing trực tiếp với Qwen. Resume giữ raw
checksum. QA pending; đây là pilot kỹ thuật nhỏ, không suy rộng language gap.
[V7](../reports/stage1/v7/completion.md), [cases](../reports/stage1/v7/local_cases.md).

**Cập nhật analysis 16/11/2026** Metrics và bootstrap đã chạy từ raw Qwen lưu
sẵn. Năm negative pairs cho FPR EN 0%, VI 20%, ΔFPR +20 điểm phần trăm với
empirical CI 95% từ 0 đến 60. Accuracy gap VI trừ EN là −10 điểm phần trăm,
CI −30 đến 0. Bootstrap percentile dùng 5.000 resamples, seed 42, image clusters
và pooled row weighting. Suite 16/11 đạt 175 tests. Image QA vẫn pending.
[Stage 1 v5](../reports/stage1/v5/completion.md).

Qwen inference ngày 10/11/2026 được giữ. Gemma inference mới nhất ngày 19/11
ở v7. Đối chiếu/tổ chức tài liệu ngày 12/11 không tạo inference mới.
[Source report](../reports/stage1/v4/qwen_local_report.json),
[10 cases](../reports/stage1/v4/local_cases.md),
[completion v4](../reports/stage1/v4/completion.md).

## Dữ liệu và QA

30 row/30 ảnh RePOPE; ba categories có 5 YES và 5 NO mỗi category. Giữ 10 mẫu
cũ, bổ sung 20. Source audit 30/30 matched upstream; không chứng nhận visual
truth hoặc byte-equivalence với ảnh gốc. Manifest stage1_v3 có 30 translation
approved theo chấp nhận thật của người dùng và 30 qa_status pending.
Exclusions giữ cả 30 ảnh, không đưa vào final.

## Qwen trên RTX 3060 Laptop

| Chỉ tiêu | Kết quả thực |
|---|---|
| Runtime | .venv-infer, Python 3.12.10; torch 2.7.1+cu126; CUDA matmul đã chạy ở v4 |
| Config | Qwen pinned revision, NF4/FP16, greedy, batch 1 |
| Row/inference | 10 ảnh/10 row × EN/VI = 20 lượt |
| Errors | Failed=0, invalid=0, missing=0; không OOM trên subset này |
| Latency | Median 492,13 ms processor+generation |
| Peak memory | PyTorch allocated 2483,91 MiB; không phải tổng VRAM/WDDM |
| Source-label matches | EN 10/10, VI 9/10, một bất đồng |
| Resume | Lần v4 kiểm tra key không trùng và raw checksum không đổi |

Timing không gồm tải/load weights, PIL file I/O/thumbnail. Không nhân số đo
pilot thành thời gian hoàn thành cả dự án. Meta giữ queue đầu 2 row/4 lượt;
summary cuối và raw đúng 10 row/20 lượt.

Case cup/cái cốc ở image 000000456178, source NO: EN NO, VI YES. Giữ nhãn và
case cho bước human QA tiếp theo. Empirical CI của subset kỹ thuật đã được
tính ở v5. Việc diễn giải cần xét cỡ mẫu mười ảnh và trạng thái QA pending.

## Trạng thái chưa đạt

Gemma pilot kỹ thuật đã hoàn tất v7 sau khi khắc phục FP16 NaN và terminal
EOS decode. Colab/Kaggle chưa generation thật; main/QA/freeze cần tiếp tục.
Full suite mới 19/11 đạt 197 tests; 144/v4 và 175/16-11 giữ là lịch sử.
Các tests dùng dữ liệu tổng hợp; final real pilots có 20 records/model,
diagnostic/development lặp cùng ảnh được ghi riêng, không tăng cỡ mẫu.

Theo [V3](handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md), tiếp tục RQ1/RQ2 trước
paraphrase/visual evidence; không tự tạo negation riêng.
Snapshot findings cũ (`archive/pre_v3/docs/pilot_findings.md`, chỉ giữ local) giữ lịch sử;
các câu “chưa có model outputs” trong snapshot là trước run local v4.
