# GPU RePOPE image A B diagnostic

Ngày 24/11/2026. Hạn thuyết trình 03/12/2026.
**Mode: REPOPE_ONLY_DIAGNOSTIC. Đây không phải validation bốn task hoặc M3.**

## Kết quả thực và phạm vi

Phase 1 đã đo 48/48 cells trên 6 ảnh QA-approved, cộng
8 warm-up riêng. Hai model load/generate/parse đạt,
không OOM. Phase 2 tái sử dụng 48 cells tương thích, đo thêm 192 cells trên
24 ảnh còn lại. Tổng 240/240 measured cells, missing=0,
16 warm-up qua hai phase; không cộng lại Phase 1
thành 288 measured cells. Raw đến từ GPU thật, không có predictions giả.

RTX 3060 Laptop 6 GB, Qwen2.5-VL-3B NF4/FP16 và Gemma 3 4B IT NF4/BF16.
Checkpoint/revisions, prompts, decoding, processor config và ảnh nguồn giữ
nguyên. A RGB→thumbnail512 LANCZOS→processor, B RGB→processor.
Qwen giữ min/max pixel 200.704/401.408; Gemma vẫn no-pan-and-scan và processor
896×896, nên B không phải thử nghiệm bỏ mọi giới hạn/default processor.
Cùng model/processor instance trong mỗi phase; mỗi phase/model warm-up hai lượt mỗi nhánh,
AB/BA theo thứ tự toàn pool cố định. Không tự fallback precision hoặc đổi model.

## Tính hợp lệ và gates

30 ảnh được bind theo hash manifest QA lịch sử, human QA JSON/import events,
row hashes và source annotation cache đúng revision. So source question/label
bằng auditor offline hiện có; kiểm SHA256 ảnh, registry pilot exclusions và
main ID/hash exclusions. Chọn sáu mẫu cân bằng category×label trước outputs.
Không sửa dataset, ground truth, review JSON, main configs hoặc pilot cũ.

Mode full vẫn đòi 30 mẫu/bốn task/human QA/provenance/exclusions như trước.
Diagnostic dùng gates riêng trên pool RePOPE đã approved; thiếu ba task chỉ
được miễn trong mode này, không biến full validation thành đạt.

| Gate | Trạng thái | Còn thiếu |
|---|---|---|
| M1 | IN_PROGRESS | 1.000 main vẫn chờ human review/import đầy đủ |
| M2 | PENDING | Nhóm chốt preprocessing/protocol; frozen=false, chưa receipt |
| M3 | NOT_RUN | Main GPU smoke bốn task sau M1/M2; diagnostic này không hoàn thành M3 |

## Prediction và consistency

| Model | Ngôn ngữ | Cặp valid | Flips | A đúng → B sai | A sai → B đúng |
|---|---|---|---|---|---|
| qwen | en | 30 | 2 | 2 | 0 |
| qwen | vi | 30 | 3 | 2 | 1 |
| gemma | en | 30 | 1 | 0 | 1 |
| gemma | vi | 30 | 0 | 0 | 0 |

Flips và correctness transitions chỉ trên cùng cặp A/B đều valid. Accuracy
nhỏ bên dưới chỉ mô tả subset, không dùng để chọn nhánh tối đa hóa điểm.

| Model | Four-way valid | EN–VI bất đồng A | EN–VI bất đồng B | Thay đổi B−A |
|---|---|---|---|---|
| qwen | 30 | 3 | 2 | -1 |
| gemma | 30 | 3 | 2 | -1 |

Denominator consistency là cùng tập EN-A/VI-A/EN-B/VI-B đều valid.

## Latency và bộ nhớ

| Model | Nhánh | Cells | Đúng | Valid | Latency p50 / p95 ms | Peak allocated / reserved MiB |
|---|---|---|---|---|---|---|
| qwen | A | 60 | 57 | 60 | 540.6 / 634.5 | 2539.3 / 3202.0 |
| qwen | B | 60 | 54 | 60 | 650.3 / 794.8 | 2804.5 / 3202.0 |
| gemma | A | 60 | 53 | 60 | 12164.4 / 26262.7 | 5720.9 / 6332.0 |
| gemma | B | 60 | 54 | 60 | 12102.7 / 26831.0 | 5720.9 / 6332.0 |

| Model | Language | Branch | Correct / expected | Invalid / failed / missing | p50 / p95 ms |
|---|---|---|---|---|---|
| qwen | en | A | 30 / 30 | 0 / 0 / 0 | 541.9 / 628.0 |
| qwen | en | B | 28 / 30 | 0 / 0 / 0 | 648.3 / 799.6 |
| qwen | vi | A | 27 / 30 | 0 / 0 / 0 | 539.6 / 634.2 |
| qwen | vi | B | 26 / 30 | 0 / 0 / 0 | 665.3 / 760.4 |
| gemma | en | A | 25 / 30 | 0 / 0 / 0 | 12057.4 / 25393.8 |
| gemma | en | B | 26 / 30 | 0 / 0 / 0 | 12157.5 / 26286.1 |
| gemma | vi | A | 28 / 30 | 0 / 0 / 0 | 12216.7 / 25131.7 |
| gemma | vi | B | 28 / 30 | 0 / 0 / 0 | 12060.3 / 26620.2 |

Latency đo chung từ verify hash/đọc/decode/RGB/thumbnail qua processor,
generate, decode/diagnostics và synchronize. Loại model load, warm-up và
checkpoint write. Một repeat; p50/p95 mô tả run hiện tại, không claim chênh
lệch có ý nghĩa thống kê. Không dùng timer này để xếp tốc độ hai model vì
Gemma adapter có thêm logits diagnostics.

Peak allocated/reserved là số đo allocator PyTorch, không phải residency
VRAM vật lý. Gemma reserved có thể lớn hơn capacity 6.144 MiB được driver
báo; không suy thành model chỉ dùng dedicated VRAM hoặc chắc chắn phù hợp
mọi ảnh. Chưa đo shared memory/paging. Cần main smoke bốn task riêng.
Warm-up/order/thermal/cache giữa phase có thể ảnh hưởng timing và reserved.
Warm-up trên cùng một ảnh anchor có 4/4 nhóm model×branch giữ cùng
parsed response qua các repeats/phases; kiểm tra này không chứng minh tính
deterministic của toàn bộ 30 ảnh.

## Recommendation

**Đề xuất B cho preprocessing trước main freeze; chờ nhóm phê duyệt, chưa áp dụng vào main config.**

B bỏ một lần resampling thủ công, giữ toàn bộ chi tiết JPEG nguồn đến processor được pin; vẫn giữ Qwen pixel budget 200704–401408 và Gemma no-pan-and-scan/896×896. Cả A/B chạy được 30 RePOPE với 0 invalid/failed/OOM. Chi phí B quan sát được ở Qwen: p50 650,3 ms so với 540,6 ms của A (khoảng +20,3%), peak allocated tăng 265,2 MiB; mức này còn phù hợp cho diagnostic trên máy 6 GB. Gemma có cùng tensor shape, peak allocated/reserved và latency median gần như nhau giữa hai nhánh; không có lợi ích VRAM quan sát được từ thumbnail 512. Đề xuất B dựa trên giữ thông tin thị giác đến processor và chi phí tăng có thể quản lý, không dựa trên tối đa hóa Accuracy hoặc giảm EN–VI disagreement.

Qwen trên pilot thực tế có 57/60 câu đúng ở A và 54/60 ở B; Gemma 53/60 ở A và 54/60 ở B. Các điểm này được báo đầy đủ, không coi B chính xác hơn tổng quát hoặc suy cơ chế bên trong model. Chỉ 30 ảnh RePOPE/one repeat; chưa có evidence bốn task. Gemma peak reserved 6332 MiB lớn hơn dedicated capacity báo 6144 MiB; allocator stats không phải physical residency, chưa đo shared memory/paging. B không sửa méo tỷ lệ 896×896 và không giảm pressure GPU của Gemma. Main smoke bốn task vẫn cần sau QA/freeze trước full main; nếu M3 gặp OOM phải báo lỗi/chốt phương án, không fallback ngầm.

Nếu nhóm đồng ý đổi policy, tạo version/hashes/protocol receipt mới theo
quy trình. Không có main config nào được đổi hoặc tự freeze trong phiên này.
Thứ tự ưu tiên vẫn main human QA → protocol freeze → main GPU smoke → main
inference. Validation bốn task/supplement 24 mẫu là việc riêng, không còn
chặn mọi diagnostic. Không mở RQ3/RQ4, branch C hoặc training.

## Provenance và tái sử dụng

Fingerprint chung `441f8ab4fbe8255fc6ab7282a79771fc0d8ddfadd893875e8417cbb55a696550` bind source/QA/input/settings/
implementation; selection/phase ghi riêng. Phase 2 kiểm đủ Phase 1 của cả
hai model và từ chối invalid/failed/missing. Trước generation mới, đối chiếu
environment packages/GPU, code state, settings/prompt snapshots và processor
identity. Mỗi cell giữ row/image/prompt hashes và runtime fingerprint riêng.
`reuse.json` bind SHA256 predictions/metadata Phase 1; analyzer kiểm lại các
hashes, không trộn runtime không tương thích. Một mẫu chỉ được tính một lần.

Run dùng HEAD `0a910e6` với `code_dirty=true` vì harness diagnostic chưa commit
lúc bắt đầu đo; không gán ngược commit công bố sau đó vào raw. Fingerprint
bind bytes implementation đang chạy, receipts giữ hashes để đối chiếu code
được công bố. Settings snapshot là candidate config chung; field branch A/B
quyết định có thumbnail, không sửa YAML giữa hai nhánh. Không chạy software
suite hay tác vụ GPU khác đồng thời với lượt đo; đây vẫn là laptop/one repeat,
không phải môi trường throughput benchmark được cô lập hoàn toàn.

Raw và metadata local ở `results/pilot/repope_image_ab_v1/phase1/` và
`phase2/`; mỗi thư mục có qwen/gemma. Danh mục/hash raw ở
[metrics.json](metrics.json), [Phase 1 metrics](phase1_metrics.json).
ZIP riêng không ảnh/weights: `exports/repope_image_ab_diagnostic_v1.zip`.
Không copy raw giả trong unit tests vào evidence GPU.

```powershell
$env:HF_HOME = "$PWD/.cache/huggingface"
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 6 --model qwen --output results/pilot/repope_image_ab_v1/phase1/qwen --execute
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 6 --model gemma --output results/pilot/repope_image_ab_v1/phase1/gemma --execute
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 30 --phase1 results/pilot/repope_image_ab_v1/phase1 --model qwen --output results/pilot/repope_image_ab_v1/phase2/qwen --execute
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 30 --phase1 results/pilot/repope_image_ab_v1/phase1 --model gemma --output results/pilot/repope_image_ab_v1/phase2/gemma --execute
.venv/Scripts/python.exe reports/validation/repope_image_ab_v1/analyze_diagnostic.py --size 30 --output reports/validation/repope_image_ab_v1/metrics_rerun.json
```

Chọn namespace mới cho rerun, không ghi đè run/evidence hiện có; dùng cùng
phase1 parent khi mở rộng. Code/source fingerprint phải khớp.
Nếu rerun trong namespace khác, truyền --run-root tương ứng cho analyzer.
Checkout đúng version code/inputs đã bind hashes khi tái phân tích lịch sử;
không bỏ kiểm hash để ghép run sau khi protocol/data thay đổi. Tests và
preservation receipt nằm trong thư mục report; commands ở đây là các lệnh
run thực của phiên này. CPU synthetic tests kiểm gates và reuse, không thay
bằng chứng load/generate GPU. Các reports v1 giữ nguyên như lịch sử trước
khi người dùng cho phép RePOPE-only.

## Source code tests và bảo toàn

- [repope_diagnostic.py](../../../src/vlmbench/repope_diagnostic.py): gates riêng,
  source/QA binding, selection và reuse kiểm tương thích.
- [image_ab.py](../../../src/vlmbench/image_ab.py): tái sử dụng instrumentation
  sau gates riêng; full mode vẫn giữ điều kiện bốn task và từ chối diagnostic plan.
- [CLI](../../../scripts/validate_image_ab.py): thêm --mode repope-diagnostic,
  --size và --phase1; mode mặc định vẫn full.
- [Tests](../../../tests/test_image_ab.py): thêm 7 tests diagnostic, tổng27
  A/B tests. Full suite thực **423 passed/23.60 s** sau khi GPU
  measurement đã kết thúc. [stdout/checks](software_checks.json),
  [JUnit](software_tests.xml); fake torch/reviewers chỉ trong pytest tmp.
- [Preservation](preservation.json): 813 ảnh khớp hash, main configs/data/
  review JSON và legacy runners/history giữ nguyên. [Raw ZIP receipt](raw_bundle.json).
- Helpers analyze_diagnostic.py/build_report.py trong thư mục này tái tạo
  bảng/report từ raw đã kiểm provenance. README/completion ghi trạng thái mới.
