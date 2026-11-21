# Công bố GitHub theo từng phần — 21/11/2026

Repo: [MinhGioChai/cv-final-project](https://github.com/MinhGioChai/cv-final-project),
nhánh main. Đây là công bố công việc đã có, theo thứ tự phụ thuộc để từng
commit có thể kiểm tra được. Tất cả dùng ngày commit thật, không dựng lại
lịch sử tiến độ cũ. Mỗi phần có message nêu mục đích, hoàn thành, kiểm chứng
và giới hạn; đã push riêng và đối chiếu SHA trên remote.

| Phần | Commit | Nội dung | Tests đạt |
|---|---|---|---:|
| 1 | [aab4a4a](https://github.com/MinhGioChai/cv-final-project/commit/aab4a4ae888435218503899cb3f638ace8c5094b) | build: pin CPU environment and validate benchmark foundation | 78 |
| 2 | [a345e82](https://github.com/MinhGioChai/cv-final-project/commit/a345e822d4860abd6c5f79372f835fa450ef5b63) | feat(data): publish pinned sources and reproducible EN-VI draft selection | 166 |
| 3 | [32d6bec](https://github.com/MinhGioChai/cv-final-project/commit/32d6bec2c7671ae2ca87dcf6905d3352079142aa) | feat(eval): add paired scoring and image-cluster confidence intervals | 178 |
| 4 | [35b1ec8](https://github.com/MinhGioChai/cv-final-project/commit/35b1ec812e91bf2d2327f9d92e706bcbdcab1256) | feat(pilot): add bounded Qwen and Gemma BF16 runs across local and cloud | 309 |
| 5 | [6ff3287](https://github.com/MinhGioChai/cv-final-project/commit/6ff3287b4f452700ae643132a345ba37dcc636af) | feat(review): add offline HTML workflow for 22 main review packets | 334 |

Phần 6 trong đợt này công bố protocol, hướng dẫn nhóm và evidence nhỏ. SHA
cuối cùng của phần đó được ghi ở commit audit kế tiếp để tránh tự tham chiếu.
Nguồn chi tiết: [publication.json](publication.json).

## Cách tái lập

Clone và cài Python 3.12 theo [hướng dẫn nhóm](../../../HUONG_DAN_NHOM.md#4-clone-và-cài-môi-trường-cpu).
CPU lock là requirements-stage0.lock.txt; inference lock tách riêng, không
cần cài torch để test/review/analysis. Chạy ở project root:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe scripts/check_repository.py
.venv/Scripts/python.exe -m vlmbench.cli --help
```

Mỗi con số tests trong bảng được chạy từ ZIP của đúng Git index tree, với
PYTHONPATH trỏ vào src của bản đó, không đọc code chưa commit. Local Windows
Python 3.12; chưa kiểm kết quả GitHub Actions Ubuntu/Windows. Lần thử đầu của
phần 1 gặp lỗi quyền thư mục temp của pytest (51 passed/27 errors); đã dùng
basetemp riêng trong workspace rồi 78 tests đạt, không thay code để bỏ test.
Trước khi test phần 6, Git diff-check cũng báo CRLF và Markdown hard breaks
trong tài liệu nguồn cũ; thêm whitespace attributes cho đúng các nguồn đó,
giữ nguyên bytes/checksums thay vì định dạng lại evidence lịch sử.

### Khôi phục dữ liệu và 22 gói HTML

Nhận riêng `team_workspace_v1.zip`, đối chiếu SHA256 trong publication.json,
đặt tại exports/ rồi chạy:

```powershell
.venv/Scripts/python.exe scripts/team_workspace.py restore --archive exports/team_workspace_v1.zip
.venv/Scripts/python.exe scripts/verify_main_draft.py --report results/verification/main_draft_v1.json
.venv/Scripts/python.exe scripts/review_main.py export
```

Report phải là đường dẫn mới; khi chạy lại chọn version khác. Mở
`reports/stage1/v10/main_review/index.html`. Nhóm chỉ review có thể giải nén
ZIP vào thư mục mới và mở HTML, không cần Python/GPU.

Đã kiểm bằng Git tree phần 5 + ZIP riêng: restore có hash/binding guards,
đủ 1.000 row/783 ảnh, technical/leakage issues=0; main_ready=false do QA
pending 1.000. Sinh lại đúng 22 gói/23 HTML (kể cả index), bytes giống ZIP,
packet metadata giống Git. [Receipt](workspace_reproduction.json). Không tạo
approval, không gọi model/mạng; chưa visual browser QA hoặc thao tác thử của
hai reviewer thật. Sau khi nhận ZIP, nhóm vẫn thử lưu/mở lại một gói trước.

Phân tích saved Qwen pilot CPU không cần ảnh/GPU được kiểm từ phần 3 trở đi;
lệnh evaluate/statistics cụ thể ở mục 7 hướng dẫn nhóm. Không coi pilot nhỏ
là kết quả main; cloud GPU generation chưa được xác minh.

## Ranh giới công bố

Git chứa code, dependency pins, configs, nguồn/revisions, manifests/drafts,
review JSON/CSV, templates, generator, tests, protocol và evidence nhỏ.
Các bản preparation lịch sử cần cho source receipts/hash lineage được giữ.
Raw pilot snapshots nhỏ trong reports/pilot_outputs hỗ trợ phân tích CPU.

Ảnh/cache nguồn, HTML nhúng ảnh được sinh, env, weights, results, ZIP và token
ở ngoài Git. Proposal/Word, maintenance và source/render snapshots giữ local
trên máy gốc; không xóa nhưng không phải đầu vào cài/test/review của nhóm.
Liên kết trong báo cáo lịch sử có thể trỏ đến artifact local. Git candidate
audit theo pattern đã đạt; không phải chứng nhận toàn bộ credential risks.

Hai ZIP là snapshot được giữ nguyên bytes; pilot ZIP có layout code cũ hơn
repo. Dùng gói cloud nguyên vẹn, không trộn runtime/config để ép resume.
Không tự upload ZIP hoặc gửi thông tin cho người khác trong đợt này.

## Việc tiếp theo

Người giữ project chia sẻ riêng ZIP. Nhóm review main bằng hai reviewer dịch
và QA ảnh/nhãn; import theo version mới. Song song hoàn thiện metadata/full-main
runner. Main chưa frozen, 4.000 inference chưa chạy; RQ1/RQ2 là P0, RQ3/RQ4
có gate riêng. Các lần push tới tiếp tục một việc/commit, kiểm staged diff và
ghi rõ kiểm chứng, theo mục 8 của hướng dẫn nhóm.
