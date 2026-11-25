# Main Option B và chuẩn bị GPU smoke

Ngày 24/11/2026. Nhóm đã chọn **Option B cho main preprocessing** qua quyết
định của người dùng và task đính kèm. Đây là phê duyệt policy, **chưa phê
duyệt final dataset/protocol freeze**. Ngày thuyết trình 03/12/2026.

## Policy và cấu hình ứng viên

Main dùng `Source JPEG → RGB ở kích thước nguồn → model processor → VLM`.
Policy ID là **`original_rgb_processor_v1`**, candidate chính thức là
[baseline_v3_option_b_v1.yaml](../../configs/baseline_v3_option_b_v1.yaml).
`run_main.py` mặc định candidate này. `image_max_edge: null` thể hiện không
có manual resize trước processor; schema từ chối B với một giới hạn cạnh.
Config vẫn `frozen: false`, `freeze_receipt: null`.

Runtime dùng cùng hàm decode/RGB cho cả hai model, hai ngôn ngữ. Chỉ policy
historical `rgb_thumbnail_lanczos_v1` mới gọi thumbnail LANCZOS. Không crop,
pad, ép vuông, EXIF transpose hoặc lưu lại JPEG trước processor ở B. Source
image hash giữ nguyên; raw main mới có `original_image_size_wh` và
`processor_input_size_wh`, bắt buộc khớp khi B generation thành công.

Giữ nguyên model/processor/tokenizer revisions, Qwen NF4/FP16, Gemma NF4/BF16,
attention, greedy/batch1/max_new_tokens8, seed42, prompts và parser. Qwen
vẫn min/max pixels **200.704/401.408**, `use_fast` theo checkpoint/runtime
hiện tại. Gemma vẫn `use_fast=false`, `do_pan_and_scan=false`, processor
**896×896**. B không có nghĩa giữ nguyên độ phân giải hoặc tỷ lệ sau processor;
không sửa biến dạng tỷ lệ của Gemma trong quyết định này.

Baseline config/prediction/protocol schemas giữ tên v1 để tương thích;
version policy mới và candidate filename phân biệt A/B. `protocol_hash`
bind config/policy, exact processor settings/revisions, source hashes,
prompts và implementation hashes. Code revision/environment được ghi khi
execution thực. Không đổi `image_variant=original`: đó là variant nguồn,
không phải cam kết không resize bên trong processor.

## Cơ sở và giới hạn

[GPU RePOPE diagnostic](../../reports/validation/repope_image_ab_v1/report.md)
đã có 240/240 measured cells valid, 0 failed/OOM/missing trên 30 pilot đã QA;
48 cells Phase1 được reuse, 16 warm-up riêng. B giữ chi tiết nguồn đến processor
và bỏ một lần resampling dư. Qwen B p50 tăng khoảng20,3%, peak allocated tăng
265,2MiB; Gemma A/B gần tương đương về median và cùng peak allocated/reserved.

Không chọn B vì Accuracy: Qwen A57/60 so B54/60, Gemma A53/60 so B54/60 trên
pilot này. Không suy 30 RePOPE/one repeat thành accuracy gain tổng quát hoặc
validation bốn task. Gemma peak allocated~5721MiB, reserved6332MiB; reserved
không phải physical residency, chưa đo shared memory/paging. Không hứa main
chắc chắn phù hợp dedicated6GB; M3 phải kiểm tài nguyên thật.

Gói `main_review_v2`, HTML, JSON đang review, ground truth, sampling và 1.000
main IDs giữ nguyên. Không phải review lại vì B: HTML đã dùng JPEG gốc, JSON
chỉ chứa quyết định/context. Source JPEG, manifest main và raw cũ không đổi.

## Kiểm chứng CPU hiện tại

```powershell
.venv/Scripts/python.exe scripts/run_main.py plan
.venv/Scripts/python.exe scripts/run_main.py plan --smoke-per-task 1 --report results/main/option_b_plan_new.json --grid-output results/main/option_b_grid_new.jsonl
.venv/Scripts/python.exe scripts/run_main.py run --model qwen --dry-run --smoke-per-task 1
.venv/Scripts/python.exe reports/stage1/v14/collect_evidence.py
.venv-infer/Scripts/python.exe reports/stage1/v14/cpu_processor_probe.py
.venv/Scripts/python.exe reports/stage1/v14/verify_historical.py
.venv/Scripts/python.exe -m pytest -q
```

Chọn output mới nếu đã tồn tại. Probe chỉ dùng helper main và processors thật
trên **pilot human-approved**, chạy CPU; không load weights/generate hoặc
dùng main pending cho inference. [Evidence v14](../../reports/stage1/v14/completion.md)
phân biệt synthetic unit tests, CPU dry-run và GPU diagnostic lịch sử.

## A và diagnostic lịch sử

[baseline_v3_draft.yaml](../../configs/baseline_v3_draft.yaml) giữ nguyên A.
Đọc/plan lại bằng `--config configs/baseline_v3_draft.yaml`. Pilot runtimes và
config cũ, A/B diagnostic code và raw giữ nguyên ngữ nghĩa; không cập nhật
hashes trong outputs cũ để hợp code mới. Prediction A thiếu hai dimension
fields mới vẫn đọc được.

Sau khi baseline implementation đổi, fingerprint hiện tại sẽ khác run cũ.
Đó là guard đúng, không phải lý do bỏ kiểm hash. `verify_historical.py` lấy
source đúng commit `1a253f6` bằng Git blobs vào cache local, rồi CPU replay
240 records và đối chiếu exact metrics. Không sửa checkout hoặc raw lịch sử,
không rerun GPU. Reproduce run cũ dùng đúng source/inputs version và private
assets gốc; không ghép checkpoint A/B/protocol/runtime khác fingerprint.

## M3 sau khi đủ gates

M1: import human QA A/B thật (riêng Pet theo [policy nhãn nguồn25/11](PET_SOURCE_REVIEW_V1.md)), xử lý uncertain/rejected và kiểm đủ1.000 IDs,
source/provenance/ảnh/exclusions. M2: nhóm chốt manifest/config/prompts cuối,
tạo **config final mới** theo B, phê duyệt và tạo receipt bind đúng protocol.
Không sửa draft A hoặc history để làm việc này. Chỉ sau đó mới M3.

`--smoke-per-task 1` chọn một sample ID cố định mỗi task, chạy cả EN/VI trên
Qwen/Gemma: **16 cells tổng, 8/model**. IDs/tasks được ghi trong plan,
identity và summary; không chọn theo outputs. `--smoke-per-task 2` hỗ trợ
bound32cells khi có quyết định cần thêm. `--max-cells` chỉ cắt queue prefix,
không bảo đảm task coverage, nên không dùng cùng smoke flag.

Smoke vẫn kiểm **toàn bộ main QA/freeze/provenance/leakage** trước load;
không chỉ kiểm bốn mẫu được chọn. Full expected grid vẫn4.000; bounded
selection nằm riêng trong fingerprint. Scope real smoke là `main_gpu_smoke`,
không phải completed main benchmark. Không resume output smoke như full run;
metadata sẽ từ chối đổi selection/scope âm thầm.

Config final dưới đây là **đường dẫn dự kiến, chưa tạo/chưa approved**:

```powershell
$env:HF_HOME = "$PWD/.cache/huggingface"
.venv/Scripts/python.exe scripts/run_main.py plan --config configs/baseline_v3_option_b_final_v1.yaml --smoke-per-task 1 --report results/main/m3_v1/plan.json
.venv-infer/Scripts/python.exe scripts/run_main.py run --config configs/baseline_v3_option_b_final_v1.yaml --model qwen --run-id m3_qwen_v1 --smoke-per-task 1 --output results/main/m3_v1/qwen.jsonl --execute
.venv-infer/Scripts/python.exe scripts/run_main.py run --config configs/baseline_v3_option_b_final_v1.yaml --model gemma --run-id m3_gemma_v1 --smoke-per-task 1 --output results/main/m3_v1/gemma.jsonl --execute
```

Checklist operator sau run được phép:

- Hai model, đủ bốn task và EN/VI, đúng IDs và cùng source/policy.
- B input dimensions bằng source; `generation_trace.image_processor_observation`
  có processor shape/grid/input token count. Gemma vẫn896×896, no pan-and-scan.
- Parse/raw/validity, lỗi/OOM và latency được giữ; model load/processor settings
  đúng pins. Có allocated peak và trace reserved peak/baseline; không gọi đó
  physical VRAM residency.
- `bounded_smoke.missing_smoke_cells=0`; valid8/model nếu n=1. Summary vẫn có
  research-grid missing1992/model vì đây chỉ là smoke; không báo completed main.
- Giữ JSONL/meta/summary/load errors, config/protocol/run/code/env fingerprints.
  M3 không tự đánh dấu DONE chỉ vì launcher chạy xong hoặc RePOPE diagnostic đạt.
- Nếu invalid/OOM/load failure, dừng/ghi bằng chứng; mọi thay đổi kỹ thuật sau
  freeze phải version/log và được duyệt lại, không tune bằng main Accuracy.

Hiện **M1 IN_PROGRESS, M2 PENDING, M3 NOT_RUN**. Không chạy 4.000 inference,
không thêm RQ3/RQ4/training hoặc mở rộng preprocessing experiments. Ưu tiên
main QA → final freeze → M3 → main inference → RQ1/RQ2 → report/slides.
