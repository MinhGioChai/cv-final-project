# Stage 1 v13 baseline metadata and main runner

Ngày 22/11/2026. Người dùng cho phép triển khai tiếp trong lúc nhóm review,
và sẽ gửi JSON review sau. Hoàn thành contract/planner/runtime v1 bằng CPU;
toàn Stage 1 vẫn IN_PROGRESS, chưa final QA/freeze hoặc main GPU generation.

## Đã triển khai

- Strict baseline config/prompt/record schema mới trong baseline_contract.py
  và baseline_runtime.py; không đổi schema, adapters hoặc configs pilot cũ.
- Một entry point main: scripts/run_main.py, mặc định plan; config draft
  configs/baseline_v3_draft.yaml và prompt mới configs/prompts_baseline_v1.yaml.
  QA pending vẫn tạo được grid để phát triển, execution không được mở.
- Metadata có model/processor/tokenizer pins, nguồn/ảnh/row hashes, prompt hash,
  variants, dtype/NF4/preprocess/generation, environment/code/dirty state,
  valid/invalid_reason, failed/missing, attempt và raw/trace/error.
- Prompt VSR dùng TRUE/FALSE, chuẩn hóa storage yes/no; Pet giữ câu hỏi manifest
  cả EN/VI và cùng mapping A–H. Không thêm negation/RQ3/RQ4 hoặc training.
- Gates kiểm full source selection/counts, protected fields, đọc/hash ảnh,
  pilot ID/SHA exclusions và hai reviewer A/B approved cả dịch/ảnh trên VI cuối.
  Execution cần frozen config, protocol-bound freeze receipt và explicit execute.
- Runner dùng lại Qwen FP16/Gemma BF16 adapters với GPU guard trước Hub access;
  atomic checkpoints, explicit resume/retry, không retry generation-success
  invalid, không đổi config khi OOM; load errors không bịa predictions.

## Kiểm chứng mới

- Full suite **396 passed/18,91 s**, thêm 37 baseline tests. Chạy bằng .venv
  CPU, không load model. Test data/reviewer/adapter đều synthetic và scope riêng.
- Fake outputs hai model đi qua bốn task evaluator và image-cluster CI hiện
  có, kiểm tay accuracy/negative ΔFPR=0 trên toy data. Đây là software integration.
- Tests có raw/parse/metadata tamper, duplicate/truncated checkpoints, QA proof,
  source/context/label/pilot leakage, missing, explicit failed retry, Ctrl+C,
  OOM, nonfinite diagnostics, load error redaction và adapter precision routing.
- Dry-run dữ liệu thật: **1.000 row/783 ảnh, 4.000 cells**, 2.000/model; full grid
  ở results/main/preflight_v1/grid.jsonl, ngoài Git. [Summary](draft_plan.json).
- Sáu local CPU dry-runs với platform labels local/colab/kaggle cùng IDs/hash;
  không phải real GPU cloud runs. [Dry-runs](dry_runs.json).
- Gates thực tế vẫn chặn: 1.000 MAIN_QA_NOT_APPROVED, BASELINE_NOT_FROZEN và
  FREEZE_RECEIPT_REQUIRED. Đã thử execute trên draft và bị chặn trước environment
  inventory và model load; không import torch/transformers, không tạo prediction/meta file.
- Old data/config/core/stage evidence được so với Git blobs và pilot raw/snapshot
  giữ bytes. [Preservation](preservation.json), [software checks](software_checks.json).
- Build/cài wheel offline vào target riêng đạt; planner từ package đã cài tạo
  cùng protocol/grid 4.000 cells khi không kèm ảnh và báo đúng missing-image
  blockers, không import torch/transformers. [Package check](package_check.json).
  Không thử tải lại dependencies trên máy trắng.

## Phạm vi còn chờ

Chưa nhận/import main human review mới; không tạo freeze receipt/config frozen
hoặc actual main inference. Generation settings/prompts hiện là candidates,
chưa đóng băng thành quyết định cuối. Actual main GPU behavior, số token có đủ
trên bốn task và tài nguyên Colab/Kaggle còn cần smoke sau gates/xác nhận.
Không diễn giải toy metrics thành performance hay language gap của model.

Tiếp theo: nhận JSON A/B theo đợt, import version mới, tổng hợp đủ IDs và xử lý
uncertain/rejected; chốt final manifests/metadata/prompts/configs, freeze và
xác nhận bounded smoke bốn task trước full run. Contract/schema engineering
đã có; final baseline freeze và thực nghiệm chưa xong.

Lệnh và field contract tại [BASELINE_V1](../../../docs/research/BASELINE_V1.md).
