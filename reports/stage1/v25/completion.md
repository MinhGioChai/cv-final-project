# Stage 1 v25 — công bố hướng dẫn thực nghiệm và bốn gói cá nhân

Ngày 27/11/2026. Theo yêu cầu người dùng: master gửi riêng; bốn member ZIP được
chuyển vào `hướng dẫn thực nghiệm/` và push cùng hạ tầng/hướng dẫn cần thiết.

## Nội dung đã công bố

1. [5b7da87](https://github.com/MinhGioChai/cv-final-project/commit/5b7da879e013cdb3a1626aeae1c301db09107785)
   — `feat(team): publish Phase A assignment and bundle verification tools`.
   13 files: bốn configs, hai notebook starter, assignment/asset helpers, builder,
   16 tests và ignore cloud venv. Không thay frozen inference implementation.
2. [2f6cac4](https://github.com/MinhGioChai/cv-final-project/commit/2f6cac43d0c15cf7d04f61750270d85b5624c281)
   — `docs(team): publish role guides and four public experiment packages`.
   38 files: role/shared/Git guides, bốn ZIP, README nhận master, checksums,
   public checks và link trong hướng dẫn tổng hợp. Đã đối chiếu bốn ZIP trên
   remote: Git blob SHA bằng local; chuyển thư mục không đổi SHA256 của ZIP.

Đọc [README thực nghiệm](../../../hướng%20dẫn%20thực%20nghiệm/README.md).
Master vẫn ở `exports/VLM_ENVI_Main_Inference_Team_v1.zip`, SHA256
`29f7b3326df239df1f2bea8286ea38c4cd12ed11f0438cae861b3b998d0689f5`.
Master có 783 ảnh nên chỉ chia sẻ nội bộ; link tải riêng chưa được cung cấp.

## Kiểm tra thực sự chạy

- Dựng tree sạch từ HEAD `6f3a530` và chỉ overlay đúng các file định publish:
  **527 passed / 41,46s**, không có failures/errors. [Receipt](publication_checks.json).
  Đây là 511 tests của public base cộng 16 handoff tests, khác full local 567
  ở v24 vì local còn tests/code adjudication chưa đưa vào đợt publish này.
- Lệnh: `python -m pytest -q -p no:cacheprovider`. Test run thực dùng Python CPU
  hiện có, import source trong tree riêng, không gọi GPU/model hoặc cloud.
- ZIP chỉ có `.md/.yaml/.json`, không images/weights/secrets. Scan credential
  patterns trên selected files và nội dung bốn ZIP đạt; không coi đây là chứng
  nhận tuyệt đối. Kiểm đường dẫn, số lượng entries, master/source reference.
- Git staged paths khớp allowlist từng commit và `git diff --cached --check` đạt.
- Master, baseline contract WIP, tests baseline, pyproject, final config,
  receipt, main manifest, Qwen raw smoke và completion history giữ nguyên bytes.
- GitHub connector đọc được repo nhưng tạo tree trả 403 (integration lacks write
  access); native Git fetch/push được dùng thành công, không có auto-review rejection.

## Scope và bước tiếp

M1 DONE, local M2 v1 DONE, M3 PARTIAL_QWEN_ONLY. Hai model engineering pilot
đã hoàn tất trước đây; Gemma main smoke và full main vẫn chưa chạy. Không có
inference/QA/freeze/PR sinh viên mới trong lần công bố này.

Đã publish **Phase A scaffolding**; chưa phải common release để chạy dữ liệu final.
WIP adjudication/freeze/data từ các phiên trước vẫn local. TV5 tiếp tục review/
tích hợp base đầy đủ; TV1–TV4 làm phần phát triển/kiểm chứng thật, tự commit/PR;
sau merge chốt pinned commit và approval/freeze mới nếu runtime đổi, rồi GPU smoke.
Core `--language`, cloud generation và shard collection chưa được đánh dấu xong.
GitHub Actions chưa được dùng làm bằng chứng passed trong report này.

Reports/hướng dẫn public có thể mô tả bằng chứng local chưa public. Master v1 là
snapshot tại lúc đóng gói; không giả nó trùng release Git hiện tại hoặc sửa hash
tham chiếu khi chưa rebuild/version. Giữ P0, không mở RQ3/RQ4/training.
