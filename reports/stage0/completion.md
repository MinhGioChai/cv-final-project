# Stage 0 completion — 09/11/2026

**Mốc bàn giao v1 — giữ làm lịch sử Stage 0.** Trạng thái mới nhất và các phiên
bản tiếp theo được theo dõi tại [nhật ký tổng](../completion.md).

**Trạng thái: đạt foundation/preflight kỹ thuật trong môi trường hiện tại.**
Đây không phải kết quả benchmark model hoặc pilot song ngữ đã QA.

## Evidence

| Tiêu chí | Kết quả thực |
|---|---|
| Editable install | Thành công trong `.venv`, Python 3.12.10 / Windows |
| Dependencies | Lock tại `requirements-stage0.lock.txt`; `pip check` sạch |
| Offline tests | 75 passed |
| Nguồn | `MM-Hallu/RePOPE`, split train, revision `032906d23542254438e3bfd6ace379902b0b6847` |
| Pool kỹ thuật | 300 row, 57 unique images từ ba trang cố định |
| Mẫu chọn | 10 row / 10 ảnh; 5 YES / 5 NO; seed 42; cap 1 row/image |
| Strata | Random 2 YES + 2 NO; popular 2 YES + 1 NO; adversarial 1 YES + 2 NO |
| Image preflight | 10/10 ảnh tồn tại, verify/load pixel được, có SHA-256 |
| Download lần thành công | 751.920 bytes payload metadata + ảnh; không bao gồm các lần thăm dò API trước đó |
| Offline replay | Thành công, 0 bytes tải thêm, giữ nguyên hash manifest |
| Manifest SHA-256 | `e72e06d2fb5a6ba486fdaf580935e428d6c8a01f73742b7ea9a91b606973a1e9` |
| Main gate | Chủ động thử với pilot: exit code 1, bị chặn do pending QA/pilot/leakage như kỳ vọng |

Đã xem trực quan ảnh `000000429109` để kiểm tra asset thực; không đánh dấu QA
con người cho bất kỳ row nào. Kết quả preflight 10/10 ở trên là kiểm tra kỹ thuật
bằng Pillow, không phải xác nhận thủ công 10 ground truths.

## Commands verified

```powershell
.venv/Scripts/python.exe -m pip install --no-build-isolation --no-deps -e .
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m vlmbench.cli prepare-pilot --config configs/pilot.yaml
.venv/Scripts/python.exe -m vlmbench.cli prepare-pilot --config configs/pilot.yaml --offline
.venv/Scripts/python.exe -m vlmbench.cli inspect --dataset repope --limit 10
.venv/Scripts/python.exe -m vlmbench.cli validate --manifest data/pilot/pilot_manifest.csv
```

`main_gate_expected_rejection.json` lưu lần thử cố ý sai để chứng minh gate chặn
pilot/unapproved data. Không dùng file đó làm report main benchmark.
CI workflow Windows/Linux mới được tạo, chưa được chạy trên GitHub Actions.

## Những gì đã tạo

Package `src/vlmbench`: CLI, strict manifest/config schema, atomic I/O,
RePOPE adapter có giới hạn tải và pin/check revision, stratified sampler,
conservative parser, preflight ảnh, QA/leakage checks.

Configs pilot/main/models/prompts, dependency lock, CI, tests offline, các tài
liệu nguồn/sampling/dịch/protocol/limitations, manifest, review CSV và reports.
Đã sửa tên tham chiếu đề bài thành `project_topics.md` và sửa phép tính contrast
thành 240–320 inference cho 30–40 cặp × 2 ảnh × 2 ngôn ngữ × 2 model.

## Vấn đề đã gặp và giới hạn còn lại

Endpoint `/filter` trả HTTP 500 lặp lại; chuyển sang `/rows` ba trang nhỏ.
Đã hoàn tất acquisition bằng endpoint này. Pool có selection bias và chỉ dùng
cho engineering preflight. Không tải toàn bộ RePOPE/COCO/VG.

Không có blocker còn lại cho Stage 0. Còn việc cho Stage 1:

- 10 bản dịch đang missing, QA đang pending; cần từ điển/template và review.
- Chưa đối soát độc lập mirror với upstream annotations và chưa chốt quyền
  sử dụng/phân phối ảnh cho bộ dữ liệu cuối.
- Chưa có model adapters, GPU preflight, license Gemma, raw model predictions,
  latency/VRAM đo thật hoặc benchmark metrics.
- Chưa triển khai VSR/TallyQA/Pet, full-run/resume/statistics/contrast/negation.
- Cần chốt chính sách paired invalid và diễn giải McNemar trong dữ liệu có
  nhiều câu/ảnh trước final; cluster-bootstrap theo ảnh là trọng tâm uncertainty.

## Bước kế tiếp cụ thể

Ưu tiên template/dictionary RePOPE và quy trình QA, mở rộng pilot lên 30–50 row
đã review. Sau đó kiểm tra môi trường GPU/license và chạy 10 mẫu chung cho mỗi
model. Mọi số liệu pilot phải được đánh dấu riêng với kết quả final.
