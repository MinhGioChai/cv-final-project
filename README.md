# Benchmark VLM Anh–Việt

Zero-shot benchmark với Qwen2.5-VL-3B và Gemma 3 4B IT: khi cùng ảnh/nghĩa
câu hỏi, đổi EN ↔ VI có làm thay đổi đáp án và hallucination không?

## Thành viên mới bắt đầu ở đây

**[HUONG_DAN_NHOM.md — hướng dẫn tổng hợp từ clone đến pull request](HUONG_DAN_NHOM.md)**

File này giải thích đề tài, cấu trúc, cài CPU/GPU, chọn ZIP review/workspace/pilot,
review, pilot, analysis, chọn việc và commit/push. Không cần đọc toàn bộ lịch
sử để bắt đầu; hướng dẫn chuyên sâu được link khi cần.

## Trạng thái hiện tại

- Pilot: mỗi model 20 lượt thật valid; 30 mẫu pilot đã human QA approved.
- Main: đã tổng hợp18 JSON và Pet riêng, **972/1.000 mẫu đạt, 28 mẫu cần xử lý**,
  giữ783ảnh/source labels. [Báo cáo và danh sách đối soát](reports/stage1/v16/completion.md).
  [Policy Pet](docs/research/PET_SOURCE_REVIEW_V1.md) giữ nguyên. Candidate main
  vẫn dùng draft; manifest tổng hợp mới lưu riêng, chưa final freeze.
- Để chốt28mẫu cuối, dùng [HTML editor và hướng dẫn](reports/stage1/v17/completion.md):
  sửa VI/nhãn, ghi lý do và tải JSON đối soát riêng; không sửa các JSON A/B cũ.
- Review v2: A kiểm dịch và ảnh/nhãn, B kiểm lại cả hai; nhận riêng
  `main_review_v2.zip`, mở `reports/stage1/v12/main_review/index.html`.
  [Hướng dẫn review chi tiết từng bước cho A/B](docs/research/MAIN_REVIEW_V2.md).
- Baseline v1: đã có metadata, runner bốn task và CPU dry-run 4.000 cells;
  [hướng dẫn main](docs/research/BASELINE_V1.md). Chạy kiểm kế hoạch bằng
  `.venv/Scripts/python.exe scripts/run_main.py plan`.
- Main preprocessing đã chốt **Option B**: RGB kích thước nguồn → pinned
  processor. Default candidate `configs/baseline_v3_option_b_v1.yaml` vẫn
  chưa frozen. [Policy, bằng chứng và checklist M3](docs/research/MAIN_OPTION_B_V1.md).
- Chưa freeze hoặc chạy 4.000 inference chính. RQ1–RQ2 là core;
  RQ3–RQ4 là mở rộng có điều kiện. Không training/fine-tuning.
- Không cần GPU để làm review, tests hoặc phân tích pilot đã có.
- RePOPE-only A/B diagnostic: [report, metrics và lệnh](reports/validation/repope_image_ab_v1/report.md).
  Đã chạy GPU thật 30 ảnh/240 measured cells, cả hai model valid, không OOM;
  tái sử dụng 48 cells Phase 1. Đây không phải validation bốn task hoặc M3.
  Nhóm đã chọn B sau diagnostic; main vẫn cần QA theo policy từng task và final freeze.

Trạng thái có bằng chứng và bước tiếp: [completion](reports/completion.md).
Nguồn yêu cầu: [Handoff V3](docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md).
Git chứa code/manifests/reviews/evidence nhỏ; ảnh, weights, venv, ZIP và
private results được giữ ngoài Git.

## Tra cứu

| Cần gì | Mở đâu |
|---|---|
| Hiểu project và tham gia | [Hướng dẫn nhóm](HUONG_DAN_NHOM.md) |
| Tiến độ nghiên cứu và phân công 5 người | [Report TV1–TV5](docs/research/TEAM_PROGRESS_AND_ASSIGNMENT_V1.md) |
| Việc P0 còn thiếu | [Implementation plan](docs/research/IMPLEMENTATION_PLAN_V3.md) |
| Ảnh review và tiền xử lý VLM | [Image pipeline audit và kế hoạch pilot](reports/audits/2026-11-24/image_pipeline_audit.md) |
| Protocol và tài liệu chuyên sâu | [Docs](docs/README.md) |
| Bằng chứng/lịch sử | [Reports](reports/README.md) |

Lịch công bố theo từng phần và kiểm chứng tái lập: [release 21/11/2026](reports/releases/2026-11-21/README.md).
