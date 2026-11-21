# Chạy pilot local, Colab và Kaggle

Cập nhật 20/11/2026. Một lệnh chung: **`scripts/run_pilot.py`**.
Qwen dùng NF4/FP16, Gemma dùng runner NF4/BF16 đã thành công tại local.
Các run mới dùng 30 mẫu pilot đã human QA approved, chọn cùng subset EN–VI.
Mặc định 2 mẫu/model, tối đa 10; đây không phải runner main 1.000 mẫu.

## Local — bắt đầu bằng dry-run

Clone/cài môi trường CPU theo [README](../README.md) và nhận dữ liệu nhóm.
Nếu chỉ muốn kiểm tra kế hoạch, không cần GPU, token hoặc weights:

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py --model qwen --limit 2 --dry-run
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --limit 2 --dry-run
```

Kết quả cần có 2 rows/4 expected inferences, image_qa_status approved=2.
Dry-run chỉ kiểm dữ liệu/config, không chứng minh GPU/token/weights chạy được.

Để chạy thật trên máy mới, dùng Python 3.12 cài môi trường GPU riêng:

```powershell
python scripts/setup_inference.py
```

Máy đã có `.venv-infer` hoạt động không cần cài lại. Launcher local tự chọn
`.venv-infer` khi chạy thật; `--python <path>` cho phép chỉ định interpreter.
Linux/macOS thay Scripts/python.exe bằng bin/python; inference cần CUDA GPU.

Chạy từng model, dùng RUN_NAME riêng cho người/phiên chạy:

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py --model qwen --run-name my_smoke_v1 --limit 2 --online
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --run-name my_smoke_v1 --limit 2 --online
```

`--online` cho phép tải weights. Bỏ flag để dùng cache-only; launcher truyền
offline settings vào child process trước khi Hub được import. Gemma online
cần tài khoản được cấp quyền và token riêng, xem [setup Gemma](setup_gemma.md).
Launcher kiểm GPU trước tải weights: Gemma cần capability >=8.0 và BF16
supported; GPU không đạt sẽ dừng, không tự fallback FP16. Qwen có thể dùng
GPU FP16 khi Gemma không phù hợp. Không tự đổi precision giữa EN/VI.

Output mặc định:
`results/pilot/local/team_v1/my_smoke_v1/qwen.jsonl` hoặc `gemma.jsonl`.
Tên output lịch sử và thư mục report snapshots được bảo vệ trong launcher.
Nếu muốn chọn nơi lưu khác, dùng `--output <path.jsonl>`.

Sau smoke hợp lệ, mở rộng cùng cấu hình và cùng run name:

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py --model qwen --run-name my_smoke_v1 --limit 10 --resume
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --run-name my_smoke_v1 --limit 10 --resume
```

Thêm `--online` nếu vẫn cần tải. Resume giữ records thành công, kể cả output
INVALID; không giả vờ sửa thành valid. `--retry-failed --resume` chỉ thử lại
failed attempts. Khác model/config/GPU/runtime fingerprint phải dùng output
mới khi checkpoint bị từ chối; không chỉnh tay metadata để ép resume.

Hai tên helper cũ `run_local_pilot.py`, `run_gemma_pilot.py` là alias của
launcher mới; `--model gemma` luôn dùng BF16. Chẩn đoán FP16 lịch sử vẫn có
qua CLI/config cũ, không phải đường chạy thông thường cho nhóm.

## ZIP pilot nhỏ cho cloud

Người giữ repo và 30 ảnh tạo bundle code/config/ảnh pilot, không chứa weights,
token, venv hoặc ảnh main. Dùng output version mới nếu file đã tồn tại:

```powershell
.venv/Scripts/python.exe -m vlmbench.cli package-pilot --manifest data/pilot/stage1_qa_v1/pilot_manifest.csv --output exports/pilot_team_v1.zip
```

Notebook kiểm manifest approved, launcher mới và hashes trước setup. Không
dùng `team_workspace_v1.zip` lớn cho workflow này. Notebook được sinh lại
bằng `python scripts/generate_cloud_notebooks.py`; không lưu cell outputs/token.

## Colab

1. Upload `notebooks/pilot_colab.ipynb`, chọn GPU trong runtime settings.
2. Cell đầu upload đúng một `pilot_team_v1.zip`; cell setup cài venv riêng.
3. Phần chọn model: giữ MODEL=qwen, LIMIT=2, đặt RUN_NAME riêng, RESUME=False.
   Gemma dùng Secret HF_TOKEN; cấp notebook quyền đọc, không dán token vào cell.
4. USE_DRIVE=True mount Drive của chính bạn để lưu checkpoint; có thể đổi
   False và tải ZIP kết quả trước khi mất runtime. Weights/venv luôn ở /tmp.
5. Dry-run rồi chạy cell inference; tải ZIP kết quả sau mỗi model. Đổi MODEL
   và chạy lại phần chọn model/inference/export, không cần setup lại nếu env còn.

GPU/quota không được bảo đảm; không tự đổi Gemma sang FP16 vì GPU cấp không
đạt BF16. Khi đó chạy Qwen hoặc chọn GPU phù hợp nếu có. Xem
[Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Kaggle

1. Import `notebooks/pilot_kaggle.ipynb`; bật GPU và Internet trong session settings.
2. Tạo/attach private Dataset từ `pilot_team_v1.zip`; hỗ trợ cả ZIP còn nguyên
   và thư mục Kaggle đã giải nén. Không đưa token hoặc weights vào Dataset.
3. Chạy setup, đặt MODEL/LIMIT/RUN_NAME/RESUME như Colab. Gemma lấy HF_TOKEN
   qua Kaggle Secrets. Launcher thực hiện cùng native-BF16 guard.
4. Kết quả ở `/kaggle/working/vlmbench-results/kaggle/team_v1/<RUN_NAME>/`.
   Tải ZIP hoặc giữ outputs bằng workflow của Kaggle trước khi mất session;
   venv/weights ở /tmp, không đi vào outputs.

[Kaggle notebook docs](https://www.kaggle.com/docs/notebooks).
Các notebook đã cập nhật code, nhưng **chưa có real cloud generation được
project xác minh**. Dry-runs trên máy local với platform=colab/kaggle không
phải kết quả chạy GPU của các dịch vụ này.

## Giữ và phân tích kết quả

Giữ cùng nhau JSONL, `.meta.json`, `.summary.json`, `.load_error.json` nếu có.
Config mới dùng `stage1_qa_v1`; protocol hash khác run cũ, không trộn checkpoint.
Tên `scope=engineering_pilot_image_qa_pending` là token schema legacy được
giữ để không sửa runtime/hash cũ; trạng thái QA thật nằm trong
`image_qa_status`/`qa_status` và sẽ là approved cho các rows pilot mới này.

Evaluate theo đúng manifest/config của run, ghi output path mới. Không gộp
run của nhiều GPU/người thành các quan sát độc lập hoặc coi pilot là main.
Raw cũ để phân tích CPU có tại [pilot outputs](../reports/pilot_outputs/README.md).

Nguồn API: [PyTorch 2.7.1 CUDA/BF16](https://github.com/pytorch/pytorch/blob/v2.7.1/torch/cuda/__init__.py),
[Hub environment variables](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables).
