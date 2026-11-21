# Stage 1 v11 — pilot rerun cho local/Colab/Kaggle

Ngày 20/11/2026. Người dùng yêu cầu cập nhật pilot để thành viên có thể chạy
khi cần. Đây là cập nhật tooling/config/handoff, **không phải inference mới**
hoặc hoàn tất main benchmark. Toàn Stage 1 vẫn IN_PROGRESS.

## Đã cập nhật

- Entry point chung `scripts/run_pilot.py`, default 2/max 10 rows/model,
  paired EN–VI; local chọn .venv-infer khi chạy thật, cloud dùng Python venv
  được chỉ định. Dry-run chạy được trong môi trường CPU không có weights/token.
- Qwen gọi adapter NF4/FP16 hiện có; Gemma gọi `infer-gemma-trace` NF4/BF16,
  không đi qua legacy FP16. Config team mới trỏ manifest human-QA-approved
  `data/pilot/stage1_qa_v1/pilot_manifest.csv`. Không thay configs/run cũ.
- GPU preflight trước model/auth downloads: CUDA cho cả hai; Gemma cần
  capability >=8.0 và BF16 supported. Không tự fallback sang FP16/model khác.
- Online/cache-only rõ ràng: environment chỉ truyền vào child process,
  online xóa offline flags cũ; token Gemma qua terminal ẩn/secret, không lưu.
- Output namespace `results/pilot/<platform>/team_v1/<RUN_NAME>/<model>.jsonl`;
  run name được kiểm, output lịch sử/report snapshots được bảo vệ. Resume và
  retry-failed phải bật rõ ràng; runtime vẫn kiểm fingerprint/config.
- Hai helper cũ là alias của launcher mới; `run_local_pilot.py --model gemma`
  chọn BF16. FP16 diagnostic vẫn có qua CLI/config lịch sử, không là default.
- Notebook Colab/Kaggle dùng launcher chung, GPU/secret checks, run name,
  explicit resume, optional Drive hoặc Kaggle working results, export ZIP.
  Venv/Hub cache ở /tmp; không chứa stored outputs/tokens.
- Notebook kiểm SHA bundle và manifest approved, từ chối ZIP cũ/workspace ZIP
  lớn; extraction có path/type/conflict guards. Pilot ZIP builder cũng từ chối
  ghi đè bundle khác nội dung, cho phép replay khi bytes giống hệt.

[Hướng dẫn cả ba môi trường](../../../docs/run_local_colab_kaggle.md),
[Gemma](../../../docs/setup_gemma.md), [notebooks](../../../notebooks/README.md).
Source entrypoints/notebooks/docs trước cập nhật giữ nguyên ở `legacy_sources/`.

## Kiểm chứng

- Full suite mới: **334 passed/5,15 s**, .venv, no:cacheprovider; thêm 16 tests
  launcher/notebook so với maintenance v22. Negative checks bảo vệ output cũ,
  BF16 guard, token/offline behavior, archive traversal và notebook routing.
- [12 dry-runs](dry_runs.json): hai model × ba platform labels × limit 2/10,
  chạy bằng CPU local, cùng sample IDs và per-model protocol hashes; QA
  approved đúng số rows. Kiểm thêm hai alias Gemma đều BF16.
- Không tạo prediction files hoặc thay đổi results cũ trong dry-runs.
- [Bundle receipt](pilot_bundle.json), [bundle check](bundle_check.json),
  [verification cuối](verification.json) ghi bằng chứng handoff.
- [Before snapshot](before_update.json) bảo vệ runtime/parser, manifests,
  configs lịch sử, raw hai model và ZIP workspace dữ liệu trước đó.

Các dry-run có nhãn colab/kaggle **không phải chạy GPU thật trên dịch vụ**.
Notebook đã compile/dispatch/check bằng tests; chưa có real cloud generation.
Run team config mới cũng chưa được inference tại local trong phiên này.
Không nâng kết quả pilot cũ thành kết quả cho config mới.

## ZIP và lệnh sử dụng

Pilot ZIP hiện tại là `exports/pilot_team_v1.zip`, dùng cho cả hai notebook,
chỉ code/configs/reports nhỏ và 30 ảnh pilot, không weights/token/venv/main ảnh.
Các snapshot pilot nhỏ trong reports/pilot_outputs được kèm để phân tích CPU;
private results/ checkpoints không đi vào gói. Bản ZIP nháp trước sửa nhãn
receipt được giữ dưới exports/versions/, bản phát hành là đường dẫn ở trên.
Giữ riêng `team_workspace_v1.zip` cho main review/data; không nhầm hai mục đích.

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py --model qwen --run-name my_smoke_v1 --limit 2 --dry-run
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --run-name my_smoke_v1 --limit 2 --dry-run
```

Chạy thật theo guide sau khi GPU/token sẵn sàng, thêm --online khi cần tải;
sau smoke valid có thể tăng limit 10 và --resume với cùng run name/fingerprint.
Không dùng launcher này để chạy 1.000 main rows.

`scope=engineering_pilot_image_qa_pending` còn là token literal trong schema
legacy được giữ để không đổi core/hashes lịch sử. QA thật của team rows là
approved, nằm trong `image_qa_status`/`qa_status`. Config/protocol mới khác run
cũ do manifest QA/config mới; không nhập chung checkpoint/so như cùng một run.

## Tiếp theo

Thành viên dùng ZIP/notebook mới khi cần rerun, giữ JSONL/meta/summary/errors
và ghi GPU/environment thực tế. Cập nhật evidence khi có real cloud run;
hiện chưa commit/push, upload ZIP hay gửi token cho ai. Main QA/runner/freeze
vẫn theo checkpoint v10 và protocol V3.
