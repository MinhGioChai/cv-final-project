# Mục lục báo cáo và bằng chứng

| Cần xem | File hoặc thư mục |
|---|---|
| Trạng thái hiện tại và context qua phiên | [completion.md](completion.md) |
| A/B preprocessing trước freeze | [Validation report](validation/image_ab_v1/report.md), [GPU kernel check](validation/image_ab_v1/gpu_kernel_preflight.json); chưa có VLM A/B vì thiếu task coverage |
| Baseline metadata, runner main và CPU grid 4.000 cells | [Stage 1 v13](stage1/v13/completion.md), [plan](stage1/v13/draft_plan.json) |
| Một hướng dẫn để hiểu project/tham gia/push | [Hướng dẫn nhóm](../HUONG_DAN_NHOM.md) |
| Rerun pilot local/Colab/Kaggle hiện tại | [Stage 1 v11](stage1/v11/completion.md), [dry-runs](stage1/v11/dry_runs.json) |
| Lịch sử completion v1–v21, giữ nguyên | [completion_history.md](completion_history.md) |
| Công bố GitHub từng phần và kiểm chứng tái lập | [Release 21/11](releases/2026-11-21/README.md) |
| Raw/summary pilot nhỏ cho người không GPU | [Pilot outputs](pilot_outputs/README.md) |
| Review hiện hành: A/B mỗi người kiểm cả dịch và ảnh/nhãn | [Stage 1 v12](stage1/v12/completion.md), [ZIP receipt](stage1/v12/review_bundle.json) |
| Pilot human QA hoàn tất, main drafts/22 gói review v1 lịch sử | [Stage 1 v10](stage1/v10/completion.md), [readiness](stage1/v10/readiness.json), HTML nhận qua ZIP riêng |
| Selection 1000 và RePOPE draft tại v9 | [Stage 1 v9](stage1/v9/completion.md), [readiness lúc đó](stage1/v9/readiness.json) |
| QA packet/inventory tại v8 | [Stage 1 v8](stage1/v8/completion.md), HTML QA cũ giữ local, [sampling RePOPE](stage1/v8/repope_sampling_v1.json) |
| Audit theo handoff mới | [Audit V3 ngày 12/11](audits/2026-11-12/repository_audit_v3.md) |
| Gemma pilot NF4/BF16 hoàn tất | [Stage 1 v7](stage1/v7/completion.md), [evaluation](stage1/v7/gemma_bf16_evaluation.json), [statistics](stage1/v7/gemma_bf16_statistics.json) |
| Gemma FP16 output rỗng trước khi sửa | [Stage 1 v6](stage1/v6/completion.md), [evaluation](stage1/v6/gemma_fp16_evaluation.json) |
| Qwen pilot thật | [Stage 1 v4](stage1/v4/completion.md), [Qwen measurements](stage1/v4/qwen_local_report.json), [10 cases](stage1/v4/local_cases.md) |
| Evaluation và image-cluster CI | [Stage 1 v5](stage1/v5/completion.md), [metrics](stage1/v5/qwen_evaluation.json), [statistics](stage1/v5/qwen_statistics.json) |
| Source audit và classifier feedback | [Stage 1 v2](stage1/v2/completion.md) |
| Translation acceptance và portable dry runs | [Stage 1 v3](stage1/v3/completion.md) |
| Foundation/preflight ban đầu | [Stage 0](stage0/completion.md) |

Tests/dry runs không phải predictions thật; source audit không phải human
image QA; bản dịch approved không đồng nghĩa ảnh/nhãn approved. V3 chỉ đổi
scope/ưu tiên, không tự tạo kết quả mới.

Proposal/Word, maintenance reports, render/source snapshots và progress notes cũ
được giữ local trên máy gốc, ngoài bản Git. Các liên kết trong stage reports
lịch sử có thể trỏ đến artifacts local; không phải đầu vào bắt buộc để tái lập.
