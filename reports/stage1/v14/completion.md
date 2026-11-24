# Stage 1 v14 main Option B

Ngày24/11/2026. Nhóm chọn B cho main preprocessing; **chưa duyệt dataset/
protocol freeze**. Stage1 vẫn IN_PROGRESS. [Policy, limits và M3 commands](../../../docs/research/MAIN_OPTION_B_V1.md).

Code/config/tests đã push riêng tại commit `96417fa204a20163d38d1b8b86e5452a8809e885`;
tài liệu và evidence được công bố trong commit kế tiếp. Kết quả dưới đây là
những kiểm tra đã thực hiện trước commit, không phải một GPU run mới.

## Đã triển khai

| File | Thay đổi và mục đích |
|---|---|
| configs/baseline_v3_option_b_v1.yaml | Candidate mới chính thức B, frozen=false/receipt=null; pins/params/data giữ nguyên |
| baseline_contract.py | Thêm original_rgb_processor_v1 với image_max_edge=null; A vẫn hỗ trợ; policy/code/processor config fingerprinted |
| baseline_runtime.py | Dùng helper decode/RGB, chỉ A thumbnail; log source/input dimensions, B success yêu cầu khớp; không bypass gates |
| scripts/run_main.py | Default candidate B; smoke-per-task1/2 chọn đủ task/languages, giữ full grid và toàn bộ gates |
| tests/test_baseline.py | Kiểm B kích thước/không resize/both models/ENVI, Acompatibility, policy fingerprints và smoke/gates |
| Protocol V3/plan/docs/navigation/completion | Ghi quyết định chính thức, chưa freeze và giới hạn evidence |

Config A `baseline_v3_draft.yaml`, pilot loaders/configs, diagnostic A/B code/
raw, main/review manifests và source labels giữ nguyên. Không tạo human
approval hoặc freeze receipt. Main inputs vẫn1.000 rows/783ảnh, expected4.000cells.

## Evidence thực

- [Candidate plan](candidate_plan.json), [protocol snapshot](protocol.json):
  policy/settings/processor revisions/code hashes mới; execution_ready=false.
- [CPU checks](cpu_checks.json): lưới4.000 không đổi IDs/source/GT so với A,
  sáu local CPU dry-runs với platform labels; không phải cloud GPU runs.
  Hai execute attempts bị gate chặn trước runtime/model load.
- 813 ảnh qua helper main B giữ RGB/W×H nguồn và source SHA256. Không crop/
  pad/manual resize hoặc lưu JPEG. Đây là CPU input validation, không inference.
- [Processor input evidence](processor_input_evidence.json): processor thật
  của hai model nhận640×480 từ helper main B trên approved pilot; Qwen vẫn
  image-grid34×46, Gemma tensor1×3×896×896. Không load weights/generate.
- [Historical replay](historical_replay.json): source commit1a253f6 replay
  240 raw diagnostic records bằng CPU, exact metrics match, A4.000-cell plan;
  không import torch/transformers hoặc sửa raw. Source mới không được dùng
  để giả vờ cùng fingerprint cũ; replay dùng source version đúng.
- [Smoke plan](smoke_plan.json): đủ4tasks×2langs×2models=16bounded cells,
  chỉ planning; full QA/freeze gates vẫn đóng. **M3 NOT_RUN.**

Full suite thực **441 passed/24,00s**, thêm18 cases; targeted82passed/17,38s.
[Checks](software_checks.json), [JUnit](software_tests.xml), [preservation](preservation.json).
Không mang423tests v33 thành kết quả mới. Không có GPU generation mới trong
phạm vi thay đổi này; GPU evidence B30ảnh là diagnostic lịch sử được giữ nguyên.

## Giới hạn và việc tiếp

Gemma vẫn resize896×896/no-pan-and-scan/NF4BF16; B không sửa biến dạng tỷ lệ
hoặc giảm vision VRAM. Diagnostic RePOPE có peak allocated~5721MiB,
reserved6332MiB; không suy thành physical residency hoặc bảo đảm main6GB.
Không khẳng định B Accuracy tốt hơn; không thêm C/RQ3/RQ4/training.

M1: main human QA/import chưa xong. M2: policy đã chọn B, final config/
manifest/protocol receipt chưa approved. M3: chuẩn bị selector/logs/checklist,
chưa chạy; phải qua M1/M2 trước. Tiếp tục main QA → final freeze → M3 bốn
task → main inference → RQ1/RQ2 → report/slides trước thuyết trình03/12.
