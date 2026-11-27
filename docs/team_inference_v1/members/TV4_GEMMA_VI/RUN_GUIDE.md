# Hướng dẫn TV4: GEMMA – VI

Bạn phụ trách phát triển hoặc kiểm chứng phần đã giao, rồi tự commit, push và
tạo PR bằng tài khoản của mình. Platform dự kiến là **Kaggle**.
Máy cá nhân không cần GPU để đọc code, chạy unit tests và làm PR.

## 1. Đọc phạm vi công việc

Đọc DEVELOPMENT_TASKS.md và ../../FILE_OWNERSHIP.md. Chỉ sửa các file mình sở hữu.
TV1 chịu trách nhiệm core runner/sharding; các role còn lại tái sử dụng runner.
Không sửa dữ liệu, nhãn, review JSON, model pins hoặc frozen config để vượt gate.

## 2. Cài Git và clone

Cài Git từ https://git-scm.com/downloads và Python 3.12. **Đợi TV5 công bố common
base** trước khi tạo nhánh phát triển. Repo hiện có nhiều thay đổi local chưa
được publish; ZIP là source snapshot để tham khảo, không phải release chung.

```powershell
git --version
git clone https://github.com/MinhGioChai/cv-final-project.git
cd cv-final-project
git fetch origin
git switch main
git pull --ff-only
git switch -c work/main-gemma-vi
git config user.name "TEN_THAT_CUA_BAN"
git config user.email "EMAIL_VERIFIED_HOAC_NOREPLY_CUA_BAN"
git config --get user.name
git config --get user.email
```

Nếu TV5 dùng base branch khác main, checkout ref đó trước khi tạo feature branch.
Nếu không có quyền push, dùng fork + PR theo ../../github/BRANCH_AND_PR_GUIDE.md.
Không dùng identity của TV5 hoặc copy cả source snapshot vào clone rồi commit
như thể mình viết toàn bộ. Mỗi người giữ attribution của phần thực sự làm.

## 3. Cài môi trường CPU

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-stage0.lock.txt
.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e .
.venv/Scripts/python.exe -m pytest tests/test_team_handoff.py -q
```

Nếu không thấy các file mới, common base chưa được TV5 publish; không tự tạo
bản core khác để thay thế. ZIP có thể dùng riêng cho việc đọc và diagnostics.

## 4. Kiểm ZIP và restore workspace assets

TV5 gửi master ZIP cùng SHA256. Dùng `Get-FileHash PATH_TO_MASTER_ZIP -Algorithm SHA256`
và so với build receipt hoặc SHARED_BUNDLE_REF.json trong ZIP cá nhân.
Giải nén master vào thư mục riêng; không ghi đè một Git clone đang có thay đổi.

```powershell
.venv/Scripts/python.exe scripts/main_team_bundle.py verify --archive PATH_TO_MASTER_ZIP
.venv/Scripts/python.exe scripts/main_team_bundle.py restore-assets --archive PATH_TO_EXTRACTED_MASTER/main_assets/main_assets_v1.zip --root .
.venv/Scripts/python.exe scripts/team_assignment.py plan --assignment configs/team_assignments_v1/TV4.yaml
```

Restore kiểm paths, binding và SHA của ảnh theo approved manifest trước khi ghi;
file khác bytes sẽ bị từ chối. Plan phải báo model **gemma**, language
**vi**, 1.000 cells; đây là Phase A planning, không gọi model.

## 5. Thực hiện development và tests

Các file tests dưới đây là phần bạn phải tạo/hoàn thiện trong PR, hiện chưa
có đủ. Không tạo file trống chỉ để lệnh chạy thành công.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_main_collection.py -q
.venv/Scripts/python.exe -m pytest -q
git status --short
git diff --check
git diff
.venv/Scripts/python.exe scripts/check_repository.py
```

Lưu command, environment, kết quả và giới hạn thật. CPU/mock tests không chứng
minh cloud GPU hoặc model generation đã chạy. Nếu component đã đáp ứng, đóng
góp validation, edge-case tests, troubleshooting hoặc báo cáo thực nghiệm có
bằng chứng; không viết lại code chỉ để có commit.

## 6. Tự commit, push và tạo PR

```powershell
git add PATH_TO_YOUR_CHANGED_FILE
git diff --cached
git commit -m "Add inference checkpoint recovery and shard result validation"
git push -u origin work/main-gemma-vi
```

Trên GitHub chọn Compare & pull request, base branch chung, head là branch của
bạn. Ghi rõ vấn đề, hành vi sau thay đổi, tests đã chạy và cloud checks còn thiếu.
Không stage toàn bộ bằng `git add .` trước khi review. Không commit images, ZIP,
tokens, weights, venv hoặc notebook outputs nhạy cảm. TV5/người được giao review
PR; chỉ merge khi tests đạt và conflicts đã xử lý.

## 7. Mở notebook đúng platform

Mở **notebooks/main_kaggle_starter.ipynb**, đặt ROLE="TV4".
Đây là khung Phase A: người sở hữu platform phải hoàn thiện mount/setup,
validation, error handling và kiểm chứng thật. Trong notebook, đặt BUNDLE_ROOT
và PROJECT đúng thư mục đã giải nén hoặc clone chung; INSTALL chỉ bật khi cài.

Kaggle: attach private Dataset, đọc từ /kaggle/input và ghi vào /kaggle/working.
Colab: chọn GPU trong Runtime settings; chuẩn bị private assets qua upload/Drive.
Kiểm quyền truy cập Dataset riêng với quyền notebook. Không giả định GPU được
cấp hoặc cùng loại GPU ở mọi tài khoản.

## 8. Setup inference và Secrets

Dùng scripts/setup_inference.py để tạo venv riêng với pins hiện có. Không tự
pip upgrade hoặc đổi precision. HF_TOKEN lấy từ Secrets của chính bạn, không
print token/env và không lưu vào notebook hoặc ZIP. Gemma cần account đã chấp
nhận license và GPU hỗ trợ native BF16. Probe CUDA/capability khác với load
model và generation; phải ghi rõ từng bước đã kiểm.

TV4 chỉ dùng Kaggle khi GPU đạt BF16; nếu không, TV5 chốt môi trường BF16 khác và ghi platform/GPU thực tế. Không fallback sang FP16.

## 9. Checkout release chung trước Phase B

Sau khi các PR được tích hợp, TV5 cung cấp cùng một 40-hex commit/release,
approved manifest/protocol v2 và execution approval. Mọi người checkout cùng
commit, kiểm `git status --short` sạch và xác minh assets/package fingerprints.
Code/runtime thay đổi làm old freeze receipt không còn hợp lệ; không sửa hash
hoặc bỏ gate để tiếp tục. Historical v1 và Qwen smoke cũ phải được giữ nguyên.

## 10. Chạy GPU smoke sau khi đủ gates

**Các lệnh dưới đây là mục tiêu sau TV1 PR**, chưa được runner hiện tại hỗ trợ
vì chưa có --language hoặc team v2 config. Không chạy trước integration/freeze.

```bash
python scripts/run_main.py run --config configs/baseline_v3_team_final_v2.yaml --model gemma --language vi --platform kaggle --run-id tv4_smoke_v2 --smoke-per-task 2 --execute
```

Kiểm đủ bốn task cho shard, raw/parsed output, invalid/failed/missing, latency,
VRAM và environment thật. Số smoke cells sau sharding phải theo contract TV1
đã test; không dùng `--max-cells` lấy prefix để giả là đủ bốn task.

## 11. Chạy đúng shard khi có execution approval

```bash
python scripts/run_main.py run --config configs/baseline_v3_team_final_v2.yaml --model gemma --language vi --platform kaggle --run-id tv4_main_v2 --output results/main/tv4/predictions.jsonl --execute
```

Shard dự kiến đúng 1.000 expected cells, full grid vẫn 4.000. Không thay câu hỏi,
GT hoặc inference settings sau khi xem predictions. Không tự sửa runtime sau freeze.

## 12. Resume, backup và bàn giao

```bash
python scripts/run_main.py run --config configs/baseline_v3_team_final_v2.yaml --model gemma --language vi --platform kaggle --run-id tv4_main_v2 --output results/main/tv4/predictions.jsonl --execute --resume
```

Giữ cùng run ID, output, code, protocol và packages. Backup raw JSONL, meta,
summary, environment, smoke receipt và SHA cùng nhau. TV4 cung cấp export/
collection utility đã test; không truncate/delete checkpoint để tự chạy lại.
Invalid không tự coi là failed để retry; failed chỉ retry explicit theo policy.

Colab VM có thể mất file; dùng private Drive/download đã kiểm. Kaggle working
outputs phải được backup hoặc lưu version và thử restore thực tế. Bàn giao raw
riêng tư, không push toàn bộ predictions hoặc bundles lên public GitHub.

## 13. Lỗi thường gặp

- GPU không được cấp: giữ diagnostics, chờ/đổi môi trường được nhóm duyệt.
- Native BF16=false: không dùng Gemma FP16 để ép chạy.
- HF401/403: kiểm license của account và secret quyền đọc, không paste token vào PR.
- Checksum/protocol mismatch: kiểm đúng bundle/release; không tự sửa hash.
- --language unrecognized: TV1 PR chưa tích hợp; không viết vòng generate riêng.
- OOM/CUDA error: giữ error/VRAM evidence, dừng và báo TV5; không tự đổi settings.
- Resume mismatch: bảo toàn checkpoint, đối chiếu run/code/env với TV4.
