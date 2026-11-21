# DRAFT CÔNG VIỆC — KẾ HOẠCH TRIỂN KHAI V4.2 (CHƯA GIAO NGƯỜI)

**Dự án:** Cross-Lingual VLM Visual Grounding & Hallucination Benchmark  
**Nhóm:** 5 thành viên (sẽ thống nhất người phụ trách sau); **hiện tại chia theo workstream, không phân công cá nhân**.  
**Ngày lập:** 07/11/2026 · **Draft:** 11/11/2026 · **Mốc hoàn thiện nội bộ:** khoảng 06/12/2026.

> Đọc trước `01_RESEARCH_OUTLINE_V42.md`: file này là **kế hoạch hành động và tiêu chí hoàn thành**, không thay thế phần nghiên cứu và phương pháp.

## A. Phạm vi phải nắm trước khi bắt tay làm

**Goal:** đánh giá 2 open VLM (Qwen2.5-VL-3B, Gemma 3 4B) trong bài toán zero-shot với cặp prompt EN/VI tương đương; đo object hallucination là chính, bổ trợ spatial/counting/fine-grained; dùng tập đối chứng ảnh để thăm dò độ phụ thuộc vào bằng chứng thị giác. **Không fine-tuning. Không khẳng định tìm được nguyên nhân nội tại từ bảng Accuracy.**

**Mức bắt buộc = 1.000 row chính:** RePOPE 600, VSR 120, TallyQA 120, Pet 160. **Tập con:** Visual Contrast 30–40 cặp, Negation 40 trường hợp hai mệnh đề; paraphrase 20–30 nếu còn thời gian. **Fallback 880:** RePOPE 600 + VSR 80 + TallyQA 80 + Pet 120.

**Tính toán:** 1.000 × EN/VI × 2 VLM = 4.000 inference chính. Tập phụ có lượng inference riêng, không gộp/nhân đôi giả. Tránh hiểu row = unique image.

## B. Danh sách hạng mục (work packages)

| Mã | Hạng mục | Các việc phải làm | Sản phẩm bàn giao / điều kiện nghiệm thu | Ưu tiên |
|---|---|---|---|---|
| **WP00** | Quản trị, scope và tài liệu | Chốt RQ/H, tiêu chí số mẫu, ngày nộp, xác nhận với thầy nhóm 5 người và Week 15 | `README.md`, scope freeze, issue board, bản draft 2 trang | **P0** |
| **WP01** | Nguồn và ETL dữ liệu | Xác minh link/license, tải/đọc RePOPE VSR TallyQA Pet, link ảnh, metadata, hash | `data_sources.md`, adapters, `source_report.json`, preflight ảnh 100% | **P0** |
| **WP02** | Lấy mẫu và quản lý split | Tạo pilot tách image IDs; main stratified; 600/120/120/160; unique image; fixed seeds; lock | `pilot_manifest`, `main_manifest`, `sampling_report`, leakage test | **P0** |
| **WP03** | Dịch EN–VI và QA | Template/RePOPE, dịch VSR/TallyQA, breed class labels, annotation QA, adjudication và logs | `translation_dictionary`, `translation_reviews`, QA report, exception list | **P0** |
| **WP04** | Inference Qwen | Adapter load/prepare/ask, deterministic, timing/VRAM, resume, batch=1 pilot | CLI Qwen, test 10+ mẫu, raw outputs, environment spec | **P0** |
| **WP05** | Inference Gemma | Access/license, adapter Gemma3, GPU/CPU fallback nếu hợp lý, cùng output schema | CLI Gemma, test 10+ mẫu, raw outputs, environment spec | **P0** |
| **WP06** | Chuẩn hóa kết quả và metrics | Parser, invalid policy, FPR/FNR, Accuracy/F1, VSR, counting MAE, Pet class-id, errors | `evaluate.py`, metric tables, parser tests, invalid audit | **P0** |
| **WP07** | Thống kê & phân tích lỗi | Cluster bootstrap theo ảnh, McNemar (valid paired), effect size, Holm, case study, charts | 95% CI, bảng discordance, figure, notebook/script tái lập | **P1** |
| **WP08** | Visual Evidence Contrast | Cặp ảnh có/không có target, bối cảnh gần nhau, review hai người, pair accuracy | 30–40 cặp hoặc tối thiểu 20–30 cặp đạt QA, bảng pair results | **P1** |
| **WP09** | Negation & prompt robustness | Tạo 40 cặp mệnh đề; logical flip; optional paraphrase 20–30 | Manifest/accuracy/consistency; ghi rõ exploratory | **P1 / P2** |
| **WP10** | Báo cáo, trình bày và tái lập | 2-page draft, milestone, 6–8 page report, poster/slide, demo video, rerun từ config | Paper figures + reproducibility instructions + bản demo 15 phút | **P0 xuyên suốt** |

**P0 = bắt buộc**, P1 = điểm nhấn, P2 = chỉ làm khi không ảnh hưởng P0. Chưa gán WP cho bất kỳ thành viên nào.

## C. Thứ tự phụ thuộc và mốc GO/NO-GO

### 07/11 — GO/NO-GO #1: Có thể tải dữ liệu + chạy thử model?

- [ ] Đọc kỹ `project_topics.md`; ghi câu hỏi chính và 4 nhóm lỗi vào draft.
- [ ] Khởi tạo git repo, Python env, `requirements`/`pyproject`, issue tracker.
- [ ] Tải vài row RePOPE có ảnh hiển thị được; ghi danh sách fields và category counts.
- [ ] Thử inference 1 ảnh bằng Qwen; không sửa nhãn theo model.
- [ ] Xác định Gemma cần license access và ghi quy trình.

**No-go nếu** không mở được ảnh hoặc pipeline còn giả lập → ưu tiên WP01/WP04, chưa mở rộng dataset mới.

### 08–10/11 — GO/NO-GO #2: Pilot end-to-end + nộp draft

- [ ] 30–50 **row pilot** RePOPE (tách ảnh khỏi final), cân bằng nhãn/cấu trúc nếu có thể.
- [ ] Hai phiên bản EN/VI được QA; metadata/source ID rõ.
- [ ] Chạy được Qwen và Gemma trên ít nhất một subset chung; hoặc ghi blocker GPU, log, fallback cụ thể.
- [ ] Chạy parser và tạo Accuracy/FPR/invalid trên pilot, **không diễn giải như kết quả nghiên cứu cuối kỳ**.
- [ ] Đo throughput, VRAM, disk, invalid rate; dự toán runtime.
- [ ] Viết **proposal 2 trang**: problem, datasets, RQ/H, protocol, primary metric, visual contrast, lịch, hạng mục công việc, rủi ro.

**No-go nếu** chưa xử lý được phản hồi/nhãn → không “nhảy” sang 1.000 mẫu; phải sửa parser trước.

### 11–17/11 — GO/NO-GO #3: Khóa dataset và config

- [ ] Xác minh 600 RePOPE: category, Yes/No, image IDs, duplicate limits; danh sách ảnh đã loại vì pilot.
- [ ] VSR 120: valid image path/label/relation; TallyQA 120: simple/complex, ảnh COCO/VG tồn tại; Pet 160: 8 breeds × 20 test images.
- [ ] Viết/kiểm tra 100% bản dịch VSR+TallyQA; toàn bộ từ điển và ngoại lệ RePOPE.
- [ ] Gắn `translation_review_status`, `qa_status`; xử lý tất cả issue blocking.
- [ ] Tạo kiểm thử leakage pilot/final, hash/manifest freeze, config snapshot.
- [ ] Thống nhất output canonical; đo độ ổn định parser; lưu model revision.

**No-go nếu** số ảnh hỏng > 0 hoặc nhãn/bản dịch chưa xong → không chạy full. Nếu QA quá tải, kích hoạt fallback **880 row** với lý do viết trước, không phụ thuộc kết quả mô hình.

### 18–24/11 — GO/NO-GO #4: Full benchmark

- [ ] Chạy RePOPE EN/VI × 2 model; kiểm tra tiến độ và sample IDs.
- [ ] Chạy VSR, TallyQA, Pet; lưu từng record ngay sau inference; resume không hỏi lặp ID đã thành công.
- [ ] `raw_response`, parsed, timestamps, duration, model config, VRAM (nếu có), error stack trace.
- [ ] Kiểm tra đủ 4.000 expected results hoặc report chi tiết missing, failed và rerun.
- [ ] Chạy test evaluate, bảng Accuracy/FPR/MAE/top1, visualizations cơ bản.

**No-go nếu** có missing IDs hoặc parser invalid hàng loạt → sửa và rerun những ID bị ảnh hưởng, không xóa lặng lẽ.

### 25–30/11 — GO/NO-GO #5: Diagnostic và phân tích

- [ ] Visual Contrast 30–40 cặp đã được review đôi (hoặc số thực đạt QA); chạy và tính pair accuracy.
- [ ] Negation 40 trường hợp, hai phát biểu, kiểm tra nhãn đối lập; paired logical consistency.
- [ ] Cluster bootstrap CIs, McNemar, report invalid, multiple tests; phân tích random/popular/adversarial.
- [ ] Error case study theo quy tắc lấy mẫu rõ ràng; có ví dụ ảnh EN đúng/VI sai và ngược lại.
- [ ] Nếu dư thời gian: 20–30 prompt paraphrases; không làm prompt tuning trên final.

### 01–06/12 — Nghiệm thu cuối

- [ ] Report 6–8 trang conference format, code + README, data cards và logs/figures.
- [ ] Bảng tổng hợp unique-image, class/category balance, discarded/reviewed samples.
- [ ] Script reproducible `make all` / CLI, tests xanh, rerun một subset nhỏ từ đầu.
- [ ] Slide 15 phút, phân bố phần nói sau; video demo offline nếu Colab/Kaggle bị ngắt.
- [ ] Tổng kết giới hạn nghiên cứu, không khẳng định nhân quả nội tại hoặc novelty vượt quá tài liệu.

## D. Tiêu chuẩn dữ liệu (Data Acceptance Criteria)

**Toàn bộ benchmark chính:**

- [ ] 100% trường bắt buộc có giá trị (`sample_id`, `dataset`, `image_id`, `image_path`, `question_en`, `question_vi`, `ground_truth`, `task`, `split`, `qa_status`).
- [ ] 100% ảnh tham chiếu tồn tại và có thể mở với PIL trước khi đưa vào inference.
- [ ] 0 overlap **image IDs** giữa pilot và final trong cùng nguồn; phát hiện trùng file ảnh bằng checksum khi khả thi.
- [ ] 100% cặp có nghĩa EN/VI tương đương và cùng ground truth (duyệt theo kế hoạch QA; lưu dấu các câu cần sửa).
- [ ] RePOPE strategy/label counts báo cáo **số thực đạt** chứ không ép cân bằng giả.
- [ ] VSR/TallyQA có ảnh và label hợp lệ; Pet 8-way candidate options cố định và cùng nghĩa giữa EN/VI.
- [ ] Các bản dịch phức tạp được kiểm tra, có exception/adjudication log, sẵn sàng phản biện.

**Không cần:** vẽ bounding boxes hàng loạt, tự gán lại toàn bộ 1.000 nhãn. **Cần:** tuyển chọn và kiểm tra chất lượng, nhất là 30–40 cặp contrast + 40 phủ định.

## E. Tiêu chuẩn inference và đánh giá

- [ ] Hai VLM zero-shot chạy với adapter riêng, cùng data manifest/nhãn; raw-response schema chung.
- [ ] EN/VI dùng ảnh, task, target giống nhau; thay đổi ngôn ngữ câu hỏi (kèm chỉ dẫn trả lời tương đương).
- [ ] Không lịch sử hội thoại giữa request; `do_sample=false` và config chốt.
- [ ] Không dùng model answer làm ground truth; không LLM-judge tự động trên final nếu chưa định nghĩa/audit.
- [ ] Không che giấu INVALID/OUT_OF_MEMORY; có bảng số lượng và cách xử lý trước định nghĩa.
- [ ] Chỉ báo cáo FPR trên nhãn NO và không gộp false negative vào hallucination.
- [ ] Báo cáo CI theo image_id / cặp ảnh; tránh coi 600 rows là 600 ảnh độc lập.
- [ ] No leakage: không thay prompt/model/label set sau khi xem test results mà vẫn gọi là confirmatory.

## F. Check-list các tài liệu phải nộp/giữ

| Tài liệu | Mục đích | Khi nào |
|---|---|---|
| `proposal_2pages.pdf` | Đề cương nộp thầy: problem, method, data, eval, workstreams | 11/11 |
| `data_sources.md` | Link, citation, split, revision, license | Tuần 1–2 |
| `pilot_manifest.csv` và `pilot_results.csv` | Xác nhận pipeline | Trước draft |
| `main_manifest.parquet` hoặc `.csv` | Dataset final khóa, có hash và QA | 17/11 |
| `sampling_report.md` và `translation_qa.csv` | Chứng minh sampling công bằng và bản dịch chuẩn | 17/11 |
| `results/raw_predictions/*.jsonl` | Reproducibility, parser audit | 24/11 |
| `results/metrics/*.csv` + `figures/*.png` | Kết quả CV metrics/statistics | 30/11 |
| `analysis/error_cases.md` | Báo cáo các mẫu sai thật | 30/11 |
| `report_final.pdf` + `slides.pdf` + `demo.mp4` | Báo cáo và trình bày | 06/12 dự kiến |

## G. Những câu hỏi phải trao đổi với thầy/người hướng dẫn

1. **Nhóm 5 người** có được chấp nhận khi mô tả chung ghi khoảng 6 người không?
2. **Ngày nộp proposal/milestone/final thực tế** là ngày nào so với Week 5/10/15 trong file đề bài?
3. Số task con như counting/spatial/negation/fine-grained là **ví dụ** hay **bắt buộc đủ 4**? Kế hoạch đã bao phủ cả 4 nhưng negation là tập nhỏ.
4. Một benchmark **không fine-tuning** nhưng có sample QA, 2 open VLM, paired EN/VI, visual contrast và thống kê có được coi là trọng tâm phù hợp Topic #14 không?
5. Có cần nộp dataset ảnh gốc hay chỉ repo code, manifests, đường dẫn và hướng dẫn tái tạo phù hợp license?

---

**Quy tắc vận hành:** Không phân công người ở giai đoạn này. Khi nhóm thống nhất, tạo GitHub Issues tương ứng WP00–WP10 rồi mới phân người, đặt review và deadline. Các khoản mục có phụ thuộc (WP01→WP02→WP03→WP04/05→WP06→WP07) phải giải quyết theo thứ tự.
