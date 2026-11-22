# Implementation Plan V3

Ngày audit 12/11/2026. Dùng TODO / IN_PROGRESS / BLOCKED / DONE.
Ngày 16/11 người dùng yêu cầu triển khai các bước tiếp theo. Evaluation và
statistics P0 được thực hiện theo [v5 completion](../../reports/stage1/v5/completion.md).
DONE chỉ áp dụng đúng phạm vi có bằng chứng, không cho cả stage chỉ vì một
module đã có. Đây là kế hoạch, chưa là phê duyệt full-run hoặc P1/P2.

## Checklist hiện tại

**Nhắc Gemma đã hoàn tất ngày 19/11:** NF4/BF16 10 mẫu/20 lượt valid, có
resume và evaluation/CI tại [v7](../../reports/stage1/v7/completion.md).
Không nhắc setup/pilot như việc pending; human QA/main còn tiếp tục.

| ID | Priority | Hạng mục | Trạng thái | Bằng chứng hoặc phần còn thiếu |
|---|---|---|---|---|
| A01 | P0 | Audit repo và đọc V3 | DONE | [Audit 12/11](../../reports/audits/2026-11-12/repository_audit_v3.md) |
| A02 | P0 | Mục lục, archive và scope V3 | DONE | README, docs/reports index, protocol/plan, receipt |
| A03 | P0 | Foundation và parser pilot | DONE | Suite maintenance guide 20/11 đạt 334 tests; 8 data script --help và 2 Word ROOT checks đạt. V11 dry-runs giữ riêng; parser/core runtime legacy giữ hash |
| A04 | P0 | RePOPE source audit subset 30 | DONE | [Source audit](../../reports/stage1/v2/source_audit.json); không phải toàn mirror |
| A05 | P0 | Bản dịch pilot 30 | DONE | Chấp nhận hội thoại thật; không phải hai reviewer độc lập |
| A06 | P0 | Human QA ảnh/nhãn pilot | DONE | JSON người dùng 20/11 import hợp lệ 30/30 approved vào stage1_qa_v1; source fields và translation approved giữ nguyên, audit v10 |
| A07 | P0 | Model adapters và smoke test hai model | DONE | Qwen NF4/FP16 và Gemma NF4/BF16 cùng 10 mẫu/20 lượt mỗi model thật; Gemma 20 valid và resume giữ hash tại v7; QA vẫn riêng A06 |
| A08 | P0 | Quyền truy cập Gemma | DONE | Run v7 NF4/BF16 hoàn tất; không còn blocker access/pagefile/output rỗng trên subset này |
| A09 | P0 | Metrics RQ1/RQ2 và paired evaluator | DONE | Code/CLI, bốn task toy tests, actual hai model pilot evaluation |
| A10 | P0 | Cluster bootstrap và CI | DONE | Code/toy tests, empirical CI hai pilot, B=5000 và seed 42 |
| A11 | P0 | Dữ liệu main bốn task | IN_PROGRESS | v10 đủ 1000 bilingual draft/783 JPEG, source/ID/byte leakage checks đạt, 22 gói review v2 đã xuất theo quyết định 21/11: A/B mỗi người kiểm dịch và ảnh/nhãn. Tất cả main requires_review/QA pending; chưa frozen main |
| A12 | P0 | Chốt metadata/schema baseline V3 | DONE | Engineering contract v1 có fields/strict schemas và CPU tests, [v13](../../reports/stage1/v13/completion.md); final settings/protocol freeze còn A13 |
| A13 | P0 | Baseline freeze và full runner | IN_PROGRESS | Main runner bốn task v1/dry-run 4.000 cells và resume/error/eval integration đã CPU-tested; QA/final freeze và main GPU smoke còn chờ |
| A14 | P0 | Main inference | TODO | 4.000 expected; chưa chạy hoặc được xác nhận full-run |
| A15 | P0 | Reproducibility pilot | DONE | Hash/revisions/resume/raw hiện có; main reproducibility chưa làm |
| A16 | P0 | Báo cáo theo V3 | IN_PROGRESS | Word v1 theo V4.2 đã có, chưa revise V3; nộp chưa xác nhận |
| A17 | P0 hỗ trợ | Compute Colab/Kaggle | IN_PROGRESS | V11 notebooks dùng launcher team/Gemma BF16, manifest QA approved và ZIP pilot nhỏ; dry-runs có, chưa GPU generation thật trên cloud |
| X01 | P1 | RQ3 paraphrase | TODO | Có điều kiện; chưa nhóm duyệt, chưa tạo/run |
| X02 | P1 | RQ4 visual evidence | TODO | Có điều kiện; chưa nhóm duyệt, chưa tạo/run |
| F01 | P2 | Negation riêng/attention/model mới | TODO | Future Work; không có quyết định triển khai |

## Thứ tự triển khai P0 được đề xuất

Maintenance 20/11 đã chuẩn bị GitHub/team handoff, rút gọn navigation và
completion, thêm ZIP dữ liệu riêng/CPU checks. Không thay thế gates nghiên
cứu hoặc tạo inference/QA mới. Báo cáo dọn repo chi tiết giữ local; xem
[release log](../../reports/releases/2026-11-21/README.md) cho bản Git.
Hướng dẫn vào nhóm được gom tại [HUONG_DAN_NHOM](../../HUONG_DAN_NHOM.md),
data preparation chuyển vào scripts/data/, Word builders cũ ở scripts/legacy/ (chỉ local, ngoài Git);
đường dẫn runtime/data/config giữ nguyên.

1. **Đóng hợp đồng evaluation/schema:** tận dụng parser/raw cũ, thống nhất
   pairing keys, expected run grid, invalid/missing, complete-case denominator,
   spatial TRUE/FALSE mapping; ghi quyết định vào protocol có phiên bản.
2. **Metrics + evaluation từ outputs hiện có:** tạo evaluate.py và tests tính
   tay; không inference lại Qwen. Bảng kết quả phải giữ scope engineering pilot
   vì human QA pending; kiểm tra EN 10/10, VI 9/10 chỉ là descriptive matches.
3. **Statistics:** paired cluster bootstrap, seed/B, toy cases có ảnh nhiều câu,
   EN=VI, empty/zero denominator, missing/invalid; không dùng row-independence.
4. **Gỡ Gemma và hoàn tất pilot:** người dùng xử lý license/token, image QA thật;
   smoke test cùng subset nhỏ sau xác nhận phù hợp. Không đổi model/precision
   ngầm; ghi block nếu thiếu tài nguyên.
5. **Data main:** lấy metadata có provenance ngoài pool pilot, adapters VSR/
   TallyQA/Pet, sampling và image mapping; QA translations/labels; exclusions.
   Chốt tám lớp, split và phân bố trước xem kết quả. Đề xuất giảm scope nếu
   infeasible, không tự thực hiện fallback 880.
6. **Baseline runner/config:** thêm metadata V3, atomic/resume/audit, expected
   grid và CLI main tách khỏi engineering pilot; freeze chỉ khi gates đạt.
7. **Sau xác nhận full-run:** chạy và đối chiếu main; evaluation/CI từ raw,
   error analysis, bảng/biểu đồ tái lập, report/README/limitations.

Một số việc có thể làm cùng giai đoạn như human QA và quyền Gemma; đây là
dependencies công việc, không phải phân công cá nhân hoặc yêu cầu tạo agents.

## Phases bốn tuần theo V3

| Phase | Đầu ra và gate |
|---|---|
| Tuần 1 | Audit, data/QA, parser, hai model feasibility, baseline config; không tự đánh dấu tuần này xong |
| Tuần 2 | Baseline được phê duyệt; raw paired data, missing/invalid/error/resume |
| Tuần 3 | Metrics, clustered CI, bất đồng; xét gate riêng P1 sau core ổn định |
| Tuần 4 | Results/Discussion/limitations, reproduce figures, report và slides |

Chưa tự chốt ngày bắt đầu/kết thúc bốn tuần. Lịch tháng 11–12 trong V4.2 là
lịch sử tham khảo; deadline chính thức và việc đã nộp proposal chưa được bổ sung
bằng chứng trong đợt audit này.

## Gate P1 và nghiệm thu

RQ3 chỉ xét khi pipeline RQ1–RQ2 ổn định, baseline freeze, có QA paraphrases,
tài nguyên và nhóm xác nhận. RQ4 cần RQ1–RQ2 đủ tin cậy, cặp ảnh xác minh và
nguồn lực/nhóm duyệt. Không tạo diagnostic modules trước gate. Tái sử dụng
baseline tương đương có log, không nhân số quan sát độc lập.

Nghiên cứu chính DONE khi sampling/provenance rõ, EN–VI được kiểm tra, models
khả thi được chạy theo protocol đã duyệt, RQ1/RQ2 có metrics, invalid/missing,
CI/bất định và có thể tái tạo từ raw; báo giới hạn. P1 không là điều kiện bắt
buộc. Không loại model không khả thi mà không báo và xin quyết định nhóm.

## File đề xuất ở phiên triển khai tiếp

| File | Trạng thái triển khai |
|---|---|
| src/vlmbench/evaluate.py | Đã có pairing, expected grid, task metrics, coverage/error audit |
| src/vlmbench/statistics.py | Đã có image-cluster percentile bootstrap |
| tests/test_metrics.py | Đã có tests tính tay, CLI/provenance/replay |
| tests/test_statistics.py | Đã có determinism, image dependence, zero/empty tests |
| src/vlmbench/datasets/vsr.py | Metadata adapter và 120 selected JPEG/bilingual draft đã có tại v10; chờ main QA |
| src/vlmbench/datasets/tallyqa.py | Test/simple-complex/VG identity và 120 selected JPEG/bilingual draft đã có; chờ main QA |
| src/vlmbench/datasets/oxford_pet.py | Eight-way mapping/test subset và 160 selected JPEG/bilingual draft đã có; chờ main QA |
| configs/baseline_v3_draft.yaml | Draft v1 mới đã có cho CPU planning, frozen=false; sau QA dùng final config/receipt mới, không sửa pilot |
| src/vlmbench/cli.py và schemas.py | Mở rộng có version/mapping sau khi contract được duyệt |

Giữ package src/vlmbench thay vì đổi thành src/evaluation, src/inference chỉ
để giống sơ đồ tham khảo. Không viết lại ETL/parser/runner đang dùng được.
