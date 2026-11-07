# RESEARCH OUTLINE — V4.2 (BẢN CHỐT ĐỀ XUẤT)

**Dự án:** *When Language Changes What a VLM Sees: A Controlled English–Vietnamese Benchmark of Visual Grounding and Hallucination*  
**Tên tiếng Việt:** *Đánh giá đối chứng Anh–Việt về khả năng nhận biết bằng chứng thị giác và hallucination của mô hình thị giác–ngôn ngữ*  
**Học phần:** Computer Vision — Topic #14, *Probing Vision–Language Models*  
**Nhóm:** 5 thành viên; **tài liệu này chỉ chia hạng mục công việc, chưa giao cho cá nhân.**  
**Phiên bản:** 4.2 · **Ngày cập nhật:** 07/11/2026 · **Draft đề xuất:** 11/11/2026 · **Hoàn thiện nội bộ dự kiến:** 06/12/2026  
**Trạng thái:** Phương án thiết kế; chưa có kết quả benchmark thực nghiệm.

---

## 0. Tóm tắt điều hành và câu trả lời trọng tâm

**Đây vẫn là một nghiên cứu BENCHMARK / EVALUATION, không phải dự án phát triển VLM mới.** Nhóm sẽ dùng **2 open-weight generative VLM**, cùng ảnh và câu hỏi có nghĩa tương đương bằng **EN/VI**, để đo chênh lệch lỗi và tính nhất quán trong nhiều tác vụ thị giác. Trọng tâm là **object hallucination** và **visual grounding**; counting, spatial reasoning, fine-grained recognition và negation là các phép thử hỗ trợ theo đề bài.

**Mục tiêu khoa học chính:** đo xem *ngôn ngữ câu hỏi* có liên quan tới sự khác biệt về hallucination/nhận diện hay không; dùng các đối chứng về **bằng chứng thị giác**, **bản dịch** và **diễn đạt prompt** để xem *những yếu tố nào có thể góp phần tạo ra khác biệt*. **Không được khẳng định chứng minh nguyên nhân nội tại** như attention/training-data bias chỉ từ các đo lường này. Khả năng trả lời khác nhau theo ngôn ngữ là *hiện tượng quan sát được*; cơ chế sâu bên trong đòi hỏi thí nghiệm can thiệp khác.

**Chốt phạm vi:**
- **Bắt buộc:** RePOPE 600 + VSR 120 + TallyQA 120 + Oxford-IIIT Pet 160 = **1.000 trường hợp đánh giá (không phải 1.000 ảnh duy nhất)**; 2 mô hình × 2 ngôn ngữ = **4.000 lượt inference chính**.
- **Phần chẩn đoán ưu tiên cao:** Visual Evidence Contrast **30–40 cặp ảnh**, ghép có tiêu chuẩn và ghi rõ giới hạn.
- **Bổ trợ để bám sát core task:** Negation **40 cặp khẳng định/phủ định trên 40 trường hợp cơ sở**.
- **Có thể cắt:** Prompt paraphrasing trên **20–30 trường hợp**, prompt ensemble, văn hóa địa phương, model thứ ba, fine-tuning.
- **Chiến lược an toàn:** sau pilot, nếu chi phí kiểm tra dữ liệu quá cao, dùng phương án **880 mẫu**: 600 RePOPE + 80 VSR + 80 TallyQA + 120 Pet. Không cắt quá sâu RePOPE và Visual Contrast chỉ để thêm chức năng mới.

**Tiêu chuẩn chất lượng nội bộ:** hướng tới bài cuối kỳ mức 9.5+ bằng thực nghiệm có kiểm soát, báo cáo tái lập, thống kê phù hợp và phản biện trung thực; **không phải mức điểm được bảo đảm**, và thầy chưa cung cấp rubric chi tiết.

## 1. Căn cứ từ đề bài giảng viên

Từ `project_topics(1).md`, **Topic #14 – Probing vision–language models** ghi:
- **Core:** zero-shot classification của CLIP hoặc open VLM trên **nhiều datasets**, đánh giá có hệ thống các lỗi *counting, spatial relations, negation, fine-grained categories*.
- **Extensions:** prompt sensitivity, prompt ensembling, non-English prompts hoặc Vietnamese cultural content.
- **Publication angle:** đánh giá prompt tiếng Việt và khái niệm thị giác phù hợp Việt Nam.
- **Deliverables toàn môn:** proposal **2 trang**, milestone **3 trang**, báo cáo **6–8 trang theo conference format**, repo tái lập và trình bày **15 phút**.

**Cách dự án đáp ứng:** 4 tập dữ liệu đáp ứng nhiều nhiệm vụ zero-shot; EN–VI là extension; Visual Contrast và phân tích thống kê tăng chiều sâu. **Lưu ý hành chính:** đề bài nói nhóm *~6*, trong khi nhóm có **5**; lịch chính thức dùng *Week 15*, trong khi nhóm dự kiến hoàn thành sau khoảng một tháng. Hai điểm này **cần xác nhận với thầy**, không mặc nhiên giả định phù hợp.

## 2. Định nghĩa học thuật và giới hạn

1. **Object-existence hallucination** (trong thiết kế RePOPE): khi nhãn thật là **NO** nhưng mô hình trả lời **YES**; đó là false positive (FP). Câu thật YES mà mô hình trả lời NO là **false negative**, không gộp vào hallucination FPR.
2. **Visual grounding** trong dự án được đo *theo hành vi*: đáp án có phù hợp bằng chứng ảnh hay không và có thay đổi đúng khi ảnh thay đổi hay không. Đây **không phải phép đo attention/cơ chế nội tại**.
3. **Cross-lingual inconsistency:** cùng ảnh và cùng ý hỏi nhưng dự đoán sau chuẩn hóa khác nhau giữa EN/VI.
4. **Zero-shot:** không fine-tune, không huấn luyện trên các nhãn benchmark và không chọn prompt dựa vào kết quả test. Có thể dùng một pilot tách biệt để sửa lỗi pipeline.
5. **Trường hợp/row** ≠ **ảnh duy nhất/image ID**. RePOPE HF có khoảng **8.185 câu hỏi nhưng chỉ khoảng 500 ảnh COCO**; mỗi ảnh có thể xuất hiện nhiều lần. Số ảnh duy nhất và số câu hỏi/ảnh phải được báo cáo.
6. Các phát hiện không chứng minh rằng **tiếng Việt nói chung** yếu hơn tiếng Anh; chỉ áp dụng cho các mô hình, câu hỏi, lựa chọn dữ liệu và giao thức đã thử.

## 3. Research Questions (RQ) & Hypotheses (H)

| ID | Câu hỏi / giả thuyết *đăng ký trước* | Đo thế nào? | Mức ưu tiên |
|---|---|---|---|
| **RQ1** | Cùng ảnh/cùng nội dung, hỏi bằng EN hay VI có làm thay đổi tỷ lệ object-existence hallucination? | **RePOPE negative-only FPR**, ΔFPR = FPR_VI − FPR_EN, riêng từng model và pooled theo strategy | **Chính / confirmatory** |
| **H1 (two-sided)** | ΔFPR khác 0 trên ít nhất một mô hình; **không giả định trước VI kém hơn** | CI 95% cluster-by-image; McNemar paired trên cặp valid âm tính; hiệu chỉnh kiểm định nhiều mô hình | **Đăng ký** |
| **RQ2** | Khi bằng chứng đổi (có ↔ không có vật thể) mà câu hỏi cố định, mô hình có cập nhật nhận định đúng không; điều này thay đổi theo ngôn ngữ? | Visual Contrast **paired image accuracy**, response-flip consistency, EN/VI gap, kiểm tra ghép cặp | **Thí nghiệm chẩn đoán quan trọng / exploratory** |
| **H2** | Mức nhất quán thị giác có thể khác giữa hai ngôn ngữ | Báo cáo tỷ lệ và CI theo **cặp ảnh**, không tuyên bố nhân quả | **Khám phá** |
| **RQ3** | Các loại lỗi thị giác (spatial, counting, fine-grained) có khoảng cách EN/VI khác nhau không? | Accuracy VSR, exact match + MAE TallyQA, top-1 8-way Pet, EN/VI disagreement | **Secondary / exploratory** |
| **H3** | Chênh lệch phụ thuộc loại tác vụ và mô hình | So sánh mô tả, CI, biểu đồ, không khẳng định tác vụ nào tệ nhất nếu mẫu nhỏ | **Khám phá** |
| **RQ4** | Phủ định có làm thay đổi độ ổn định về mặt logic? | Affirmative/negative paired consistency, accuracy, EN/VI gap | **Core-task support** |
| **H4** | Mô hình có thể mất nhất quán khi câu đổi từ khẳng định sang phủ định | Tập negation riêng; phân tích mô tả | **Khám phá** |
| **RQ5 (optional)** | Diễn đạt lại prompt có gây khác biệt ngay trong cùng ngôn ngữ không? | 1 biến thể tương đương/mẫu, độ ổn định trong EN và trong VI | **Có thể cắt** |

**H0 chính:** H0: ΔFPR = 0 trong từng mô hình trên tập RePOPE negative được chọn, đối chiếu **ghép cặp chính xác theo cùng sample_id**. Không suy ra tương đương EN–VI chỉ từ p > 0,05; báo cáo effect size và khoảng tin cậy.

## 4. Bộ dữ liệu: nguồn, nhãn, đơn vị và phân tầng

### 4.1 Bảng chốt 1.000 mẫu

| Bộ dữ liệu | Nguồn và đường dẫn | Số row mục tiêu | Các trường/nhãn gốc | Lấy mẫu / hạn chế |
|---|---|---:|---|---|
| **RePOPE** | [HF dữ liệu kèm ảnh](https://huggingface.co/datasets/MM-Hallu/RePOPE), [repo relabel](https://github.com/YanNeu/RePOPE) | **600** | `image`, `image_id`, `question`, `answer` yes/no, `category` random/popular/adversarial | **200/category × 3**; cố gắng **100 YES/100 NO mỗi category**; tối đa hóa ảnh duy nhất, cân nhắc cap số câu/ảnh |
| **VSR** | [repo gốc](https://github.com/cambridgeltl/visual-spatial-reasoning), [bản mô tả HF](https://huggingface.co/datasets/albertvillanova/visual-spatial-reasoning) | **120** | Ảnh COCO tham chiếu riêng, caption quan hệ không gian, True/False, relation | **60 True / 60 False**; một split test cố định; ưu tiên nhiều nhóm quan hệ và ảnh khác nhau |
| **TallyQA** | [repo gốc + data](https://github.com/manoja328/TallyQA_dataset) | **120** | `question`, `answer` integer, `image`, `image_id`, `issimple`, `data_source` | **60 simple / 60 complex** trên test; đa dạng đáp án, đối tượng và ảnh; cần map đường dẫn ảnh COCO/VG |
| **Oxford-IIIT Pet** | [Oxford VGG official](https://www.robots.ox.ac.uk/~vgg/data/pets/), [HF thuận tiện](https://huggingface.co/datasets/timm/oxford-iiit-pet) | **160 ảnh** | ảnh, `label` breed, test split | **8 giống chó × 20 ảnh/giống**; 8-way **closed-set zero-shot**, giống phải chọn trước khi xem kết quả model |
| **Tổng** | | **1.000** | | **2 mô hình × EN,VI → 4.000 lượt hỏi chính** |

**Quan trọng:** cân bằng 100 YES/100 NO trong từng category của RePOPE là **mục tiêu cần xác minh trên dữ liệu thực**. Nếu không đạt vì tỷ lệ nhãn/ảnh duy nhất, script phải báo thống kê khả dụng và lấy mẫu gần cân bằng nhất; **không được tự sửa nhãn hay nhân bản mẫu để đạt chỉ tiêu**.

**RePOPE và provenance:** HF là bản tiện dùng vì đóng gói sẵn ảnh, còn repo gốc chứa annotation correction; phần trích dẫn/tên phiên bản có thể khác giữa mirror/dataset card. Trong `data_sources.md` cần ghi rõ **repo, dataset revision, số row, nhãn, tác giả/citation đã kiểm chứng**, tránh trộn POPE gốc với RePOPE sửa nhãn.

**VSR:** có thể dùng `cambridgeltl/vsr_random` test theo hướng dẫn repo hoặc zero-shot split riêng; **chốt đúng một split**, không gộp tùy tiện. Từ “zero-shot split” trong VSR (concept-disjoint) khác với việc nhóm chạy *zero-shot inference* của VLM.

**TallyQA:** phải tải file QA JSON và **các ảnh tham chiếu từ MS COCO/Visual Genome**; đừng giả định câu hỏi có sẵn ảnh trong cùng dataset. Ưu tiên sample có ảnh tải được trước; không lọc tùy tiện theo câu trả lời của mô hình.

**Oxford Pet:** nhãn giống là ground truth có sẵn. Vì nhiều tên giống ít có bản dịch tiếng Việt được chuẩn hóa, nên cân nhắc **giữ tên giống chuẩn dạng riêng** trong danh sách lựa chọn của cả EN và VI, chỉ dịch phần hướng dẫn. Ghi rõ đây là giới hạn khi nghiên cứu “ngôn ngữ”, vì tên nhãn có thể giống nhau trong hai điều kiện. Cùng **danh sách 8 nhãn và thứ tự lựa chọn** cho EN/VI, hoặc sử dụng một thứ tự hoán vị có seed nhưng giống giữa hai ngôn ngữ cho từng mẫu.

### 4.2 Tập phụ có thể xây dựng, không phải benchmark lớn thứ năm

| Tập phụ | Đơn vị & số mục tiêu | Cách dựng/nhãn | Phân tích | Giới hạn |
|---|---|---|---|---|
| **Visual Evidence Contrast** | **30–40 cặp ảnh** (60–80 ảnh, không nhất thiết ảnh mới) | Cùng object target; ảnh A có, B không có; bối cảnh tương đối tương tự, nhãn kiểm tra độc lập | Pair accuracy (đúng cả A & B), đáp án có flip đúng theo nhãn không, EN–VI gap | Nếu chỉ là cặp ảnh tự nhiên, bối cảnh chưa hoàn toàn cố định; **không chứng minh tác động nhân quả thuần túy của một vật thể** |
| **Negation** | **40 trường hợp cơ sở** × **2 phát biểu** (khẳng định/phủ định) | Câu A “There is a dog.” và B “There is no dog.”; nhãn True/False đối lập; kiểm tra logic thủ công | Accuracy từng dạng, logical consistency, EN–VI gap | Nhãn NO ở RePOPE **không tự động đồng nghĩa** đã kiểm thử negation |
| **Prompt paraphrase** | **20–30 trường hợp cơ sở**; tùy chọn | Thêm một cách diễn đạt cùng nghĩa cho EN và VI; giữ nhãn | Within-language answer stability; kiểm tra độ nhạy wording | Chỉ thực hiện sau khi xong benchmark chính |

**Chi phí suy luận thêm (nếu mỗi trường hợp riêng biệt):** 30–40 cặp Visual Contrast × 2 ảnh × 2 ngôn ngữ × 2 mô hình = **120–160 lượt**; 40 trường hợp negation × 2 phát biểu × 2 ngôn ngữ × 2 mô hình = **320 lượt**; paraphrase bổ sung 25 mẫu × 1 cách diễn đạt thêm × 2 ngôn ngữ × 2 mô hình = **100 lượt thêm**. Có thể tái sử dụng kết quả tương đương đã lưu, nhưng **không đếm trùng** trong báo cáo.

### 4.3 Phân biệt số liệu để báo cáo không sai

- `n_questions` = số row ảnh–câu hỏi/mệnh đề; `n_images` = số `image_id` duy nhất; `n_pairs` = số cặp ảnh Visual Contrast.
- `n_inferences` = số lần mô hình được chạy thực tế; phải log cả thất bại/OOM/invalid và rerun.
- Tập final không chứa bất kỳ **image_id** nào đã đưa vào **pilot** (kể cả ảnh có nhiều câu khác nhau), đối với cùng nguồn hoặc ảnh trùng giữa datasets nếu kiểm tra được.
- `max_questions_per_image` là tham số lấy mẫu có thể đặt, **không ép cứng khiến 600 mẫu bất khả thi**. Lưu thống kê thực tế theo ảnh.
- 1.000 row **không tương đương 1.000 mẫu thống kê độc lập**.

## 5. Phương pháp thực nghiệm

### 5.1 Mô hình và môi trường

- **Model A:** [`Qwen/Qwen2.5-VL-3B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct).
- **Model B:** [`google/gemma-3-4b-it`](https://huggingface.co/google/gemma-3-4b-it); chấp nhận điều khoản Google/Hugging Face trước khi tải.
- **Zero-shot; không fine-tuning.** Sử dụng Transformers + adapters riêng cho từng kiến trúc, một model một lần, có caching và khả năng resume.
- **Ưu tiên GPU miễn phí** Colab/Kaggle nếu được cấp; chỉ chi tiền khi cần. Laptop RTX 3060 6 GB phù hợp code/metrics; chạy fp16 trọn vẹn 3B/4B có nguy cơ OOM. Nếu lượng tử hóa, ghi lại precision, phương pháp, phiên bản; không suy ra chênh lệch chỉ do model.
- Cố định model revision, processor revision, ảnh, chính sách resize (trong từng model), seed, `do_sample=false`, giới hạn token, batch size, phiên bản Transformers/PyTorch, môi trường. Đọc ảnh đúng định dạng. Test bộ nhớ và throughput bằng pilot.

### 5.2 Protocol ghép cặp EN/VI

1. Mỗi row gốc có **ID bất biến**, ảnh tham chiếu, câu hỏi/mệnh đề EN, ground truth gốc.
2. Tạo VI tương đương nghĩa; ưu tiên template cho RePOPE, từ điển đối tượng và review ngoại lệ; VSR/TallyQA review cẩn thận cấu trúc quan hệ/đếm.
3. **Chỉ khác ngôn ngữ** giữa EN/VI trong một cặp; giữ ảnh, nội dung thị giác, tác vụ, target, trình tự label, độ dài output kỳ vọng tương ứng.
4. Chạy yêu cầu độc lập, **không dùng history** giữa EN/VI. Cố định giải mã (`do_sample=false`), cùng chính sách preprocessing cho cả hai ngôn ngữ trong từng model.
5. Các câu trả lời được đưa về nhãn chuẩn: YES/NO, TRUE/FALSE, số nguyên, hoặc `breed_id` 0–7. Nhãn không parse được = **INVALID**, không im lặng đoán hoặc biến thành NO.
6. Lưu **raw_response** và **prompt nguyên bản**, không chỉ nhãn chuẩn; logs đầy đủ để truy vấn lỗi.
7. Pilot dùng để kiểm tra kỹ thuật và thống nhất prompt; **khóa prompt trước khi chạy final**. Không chọn prompt sau khi xem điểm final.

**Mẫu prompt mang tính minh họa:**

- Object existence EN: `Is there a dog in the image? Reply with only YES or NO.`
- VI: `Trong ảnh có con chó nào không? Chỉ trả lời YES hoặc NO.`
- Spatial EN: `Is this statement true for the image: "The cup is behind the laptop"? Reply YES or NO.`
- VI: `Mệnh đề sau có đúng với ảnh không: "Chiếc cốc ở phía sau máy tính xách tay"? Chỉ trả lời YES hoặc NO.`
- Counting EN: `How many ...? Reply with one integer.`; VI: `Có bao nhiêu ...? Chỉ trả lời một số nguyên.`
- Pet: hiển thị **cùng 8 nhãn** kèm ID từ A–H, dịch hướng dẫn và yêu cầu đáp án là một ký tự A–H; model phải thấy cùng candidate classes.

### 5.3 Quality Assurance: không annotation lại toàn bộ

- **Nhãn gốc đã có sẵn** cho 4 datasets; không vẽ bounding boxes, không huấn luyện labeler.
- RePOPE: tự động dịch template + tên object; soát toàn bộ từ điển, mẫu ngoại lệ và sample QA phân tầng. Kiểm tra nhãn gốc đối với ảnh nhập nhằng/đáng nghi; không tự động đảo nhãn chỉ vì model trả lời khác.
- VSR + TallyQA: **đề xuất duyệt thủ công 100% 240 bản dịch** (đặc biệt trái/phải, trước/sau, số lượng, danh từ). Khuyến nghị hai người kiểm tra độc lập các trường hợp khó và một tỷ lệ kiểm tra chéo được xác định trước.
- Pet: rà soát danh sách 8 giống, alias, ID và ảnh trên test split; không tự sửa nhãn tùy tiện.
- Visual Contrast: **toàn bộ cặp phải được hai người kiểm tra** về nhãn, mục tiêu vật thể và mức tương đồng bối cảnh; ghi thông tin người duyệt hoặc ID reviewer nhưng không cần tên cá nhân trong dữ liệu công khai.
- Negation: rà soát 100% phép đảo logic và tính tự nhiên của câu VI.
- Lưu `qa_status`, `qa_notes`, `review_count`, nguồn nhãn, log mọi loại trừ. Khi có tranh chấp, adjudicate theo quy trình rồi **đóng băng danh sách mẫu trước final**.

## 6. Metrics và phương pháp thống kê

### 6.1 Metrics chính

**RePOPE (binary):** Accuracy, balanced accuracy, Precision, Recall, F1; **FPR = FP / (FP + TN)** trên **câu nhãn NO**; FNR riêng trên câu YES; theo language, model, sampling strategy.  
**ΔFPR = FPR_VI − FPR_EN** (điểm phần trăm), paired. Báo cáo **EN–VI disagreement rate**, loại bất đồng EN đúng–VI sai và ngược lại.

**VSR:** binary accuracy, per-relation category nếu đủ mẫu.  
**TallyQA:** exact-match counting accuracy và MAE; số nguyên ngoài phạm vi/không parse được = INVALID.  
**Pet:** 8-way top-1 accuracy và confusion matrix; báo cáo hạn chế 20 ảnh/giống.  
**Visual Contrast:** `pair_accuracy` = số cặp đúng **cả hai ảnh** / số cặp; `correct_flip_rate` có nghĩa chỉ khi các đáp án đối lập đúng theo ground truth; `incorrect_same_answer_rate`; tính CI bằng resampling **cặp**, không từng ảnh riêng lẻ.  
**Negation:** accuracy riêng câu khẳng định/phủ định, logical consistency trên cặp và so sánh EN/VI.

### 6.2 Thống kê có kiểm soát

- **Primary analysis:** ΔFPR trên câu NO của RePOPE cho từng VLM; thống kê theo chiến lược để phân tích bổ trợ. **95% cluster bootstrap theo `image_id`** cho chênh lệch và Accuracy; cố định seed/resample count, ghi rõ N cụm.
- **McNemar exact** cho tỷ lệ lỗi paired trên cùng mẫu chỉ khi nhãn parse hợp lệ ở **cả EN và VI**, report số cặp bị loại do invalid. Thử nghiệm chính khác nhau theo model; nếu kết luận cho cả hai, cân nhắc **Holm correction** để hạn chế multiple comparisons.
- **Predefine invalid:** báo cáo `invalid_rate` cho từng language/model/task; INVALID tính là sai trong Accuracy toàn phần; đối với FPR nhị phân báo cáo FPR trên các đáp án parse hợp lệ **và số lượng invalid ở nhóm NO**, kèm sensitivity bounds nếu cần. Không gán INVALID = NO.
- **Paired bootstrap** hoặc McNemar cho accuracy EN/VI khi có đủ mẫu; các phân tích task con cỡ nhỏ mang tính khám phá; không tuyên bố không khác biệt chỉ vì p-value lớn.
- **Power/sample size:** dùng pilot để ước lượng thời gian, tỷ lệ invalid và tỷ lệ discordance; nếu có tính toán power thì ghi các giả định, không tự báo “đủ power” khi chưa tính.
- **No p-hacking:** khóa bảng sample/prompt trước khi chạy final; mọi phân tích nảy sinh sau khi xem kết quả phải ghi rõ *post-hoc exploratory*.

## 7. “Tìm hiểu nguyên nhân” sẽ làm theo cách nào?

Nhóm **không thể đo nguyên nhân bên trong** chỉ từ Accuracy/FPR. Thay vào đó, xây dựng **phân tích yếu tố liên quan và đối chứng giảm nhiễu**:

1. **Kiểm soát ngôn ngữ / dịch:** cùng ảnh, nghĩa câu hỏi tương đương, review kỹ ngữ nghĩa; so sánh ảnh hưởng sau khi loại câu dịch nhập nhằng (sensitivity analysis).
2. **Kiểm soát bằng chứng thị giác:** Visual Contrast có một ảnh có và một ảnh không có mục tiêu; xem VLM có thay đổi dự đoán đúng không khi giữ câu hỏi. **Ảnh tự nhiên vẫn có confounds bối cảnh.**
3. **Độ khó câu hỏi / image:** RePOPE random–popular–adversarial, VSR loại quan hệ, TallyQA simple–complex, Pet nhóm giống dễ nhầm; cùng seed và manifest.
4. **Nhạy cảm cách diễn đạt:** paraphrase trong cùng ngôn ngữ trên tập nhỏ nếu có thời gian để nhận diện khác biệt do wording, tránh quy mọi thứ cho EN–VI.
5. **Bộ phân tích lỗi cụ thể:** chọn trước quy tắc sampling case-study (ví dụ 10 EN đúng–VI sai, 10 EN sai–VI đúng, 10 cả hai sai), thêm ảnh, prompt, nhãn và raw output; **không chọn ví dụ đẹp làm bằng chứng duy nhất**.

Cách diễn đạt kết luận đúng: “Kết quả **gợi ý/cho thấy sự liên hệ** giữa language và chất lượng grounding trong điều kiện kiểm thử”; **không viết:** “Chứng minh mô hình hallucinate vì thiếu dữ liệu tiếng Việt/attention lỗi”. Nghiên cứu trước đã xem xét multilingual hallucination (CLAIM, ACL 2025); không tuyên bố đây là đóng góp đầu tiên trong lịch sử.

## 8. Rủi ro, quyết định và quy tắc giảm phạm vi

| Rủi ro | Dấu hiệu | Quyết định giảm thiểu |
|---|---|---|
| Qwen/Gemma OOM hoặc phiên bản Transformers lỗi | Pilot không chạy ổn | Chạy riêng từng model trên GPU miễn phí; chốt precision/quantization; đo VRAM; không mặc định 6GB FP16 đủ |
| VSR/TallyQA thiếu ảnh | File JSON có nhưng `image_path` không tồn tại | Preflight images rồi mới lấy mẫu; hỗ trợ download/instructions COCO/VG; báo fail rõ |
| Bản dịch gây thay đổi ý | Có mẫu VI sai danh từ, quan hệ, phủ định | QA hai ngôn ngữ; review thủ công; lưu reasons loại mẫu |
| 600 RePOPE không đủ độc lập | Nhiều câu trên cùng 500 ảnh | Report unique image IDs, cluster-bootstrap, giới hạn tuyên bố |
| Visual Contrast không tìm được 30–40 cặp chất lượng | Bối cảnh A/B quá khác, nhãn không rõ | Giữ 20–30 cặp kiểm chứng, ghi *diagnostic exploratory*, tuyệt đối không giả tạo đối chứng |
| 1.000 mẫu quá tải kiểm tra | Dịch/ảnh/QA chậm hơn kế hoạch | Fallback **880 mẫu** đã định nghĩa, vẫn giữ 4 dataset và contrast |
| Tính công bằng EN/VI yếu | Parser, nhãn Pet, token output bị lệch | Đầu ra chuẩn cùng format, câu tương đương, audit invalid, kiểm thử parser |
| Bị hiểu là NLP thuần túy | Không phân tích theo ảnh/độ khó/visual contrast | Đưa Visual Contrast, failure examples và spatial/counting vào báo cáo chính |
| Thầy không chấp nhận nhóm 5 hoặc deadline | Quy định “~6” / Week 15 | Xác nhận giảng viên ngay, ghi mốc nội bộ và mốc thầy riêng |

**Priority rule:** hoàn thiện hai VLM trên RePOPE + ba task phụ + số liệu/QA/CI trước; Visual Contrast kế tiếp; negation ở mức nhỏ; paraphrase cuối. Không triển khai third model, image generation, fine-tune, prompt ensembling hay thử hàng chục cấu hình nếu chưa có baseline đáng tin cậy.

## 9. Timeline nội bộ và điều kiện nghiệm thu

| Thời gian | Công việc chính | Deliverable / exit criterion |
|---|---|---|
| **07–08/11** | Đóng khung RQ, đọc nguồn, tạo repo, thử tải 30–50 sample pilot, chạy Qwen và kiểm tra ảnh | Repo/README, manifest pilot, 1 inference end-to-end và log ảnh/nhãn |
| **09–10/11** | Chạy Gemma pilot, QA bản dịch, đo tốc độ/VRAM, draft 2 trang | 2 VLM chạy pilot *nếu GPU cho phép*; nếu chưa được, có phương án GPU; proposal 2 trang và backlog rõ |
| **11/11** | Nộp draft/proposal | Problem, RQ/H, datasets, method, metrics, chia **hạng mục** cho 5 người, timeline, risks |
| **12–17/11** | Chọn sample 1.000, hoàn thiện ảnh/VI, validation, khóa tập test và config | `main_manifest.csv/parquet`, `data_quality_report.md`, prompts/model config frozen |
| **18–24/11** | Chạy 4.000 lượt inference, resume, đánh giá bước đầu | Prediction raw + parsed, 4 task metrics, 95% CI, tính throughput thực tế |
| **25–30/11** | Visual Contrast, negation, phân tích lỗi, figure + sensitivity | Contrast manifest được duyệt, figure, bảng lỗi, kết luận không vượt bằng chứng |
| **01–06/12** | Báo cáo 6–8 trang, README tái lập, slide 15 phút, test rerun, mock Q&A | Package nộp cuối kỳ, code chạy lại trên subset, video demo dự phòng |

*Ngày hoàn thiện nội bộ 06/12 là phép nội suy từ “khoảng một tháng” người dùng cung cấp; không tự nhận là deadline chính thức. Đề bài ghi Week 15.*

## 10. Đầu ra và hình thức báo cáo

**Draft/proposal 2 trang (theo thầy):** Problem & motivation; novelty positioning; RQs/H; datasets/sampling; models/protocol; primary & secondary metrics; QA, risks, timeline, workstream split. Không đưa “kết quả” chưa chạy vào như thật.

**Báo cáo cuối 6–8 trang:** Abstract; Introduction; Related Work; Dataset/Protocol & QA; Models/Setup; Main Results; Visual Contrast & Error Analysis; Discussion/Limitations; Conclusion; References. Đưa bảng thống kê ảnh duy nhất, missing/invalid, phương sai CI, raw output examples, reproducibility details vào phụ lục/repo nếu thiếu chỗ.

**Chứng cứ điểm cao:** kết quả chính không tùy chọn, nguồn và nhãn rõ, có paired analysis và CIs, biết giải thích trường hợp kết quả âm tính, Visual Contrast đúng nghĩa, code tái lập và cả nhóm trả lời được khi phản biện.

## 11. Tài liệu gốc, hướng dẫn và nguồn liên quan

1. **Teacher's assignment:** `project_topics(1).md` (đính kèm trong bộ tài liệu).
2. **RePOPE data + ảnh:** https://huggingface.co/datasets/MM-Hallu/RePOPE ; **annotation repo:** https://github.com/YanNeu/RePOPE . Ghi chính xác revision / provenance.
3. **POPE benchmark:** https://github.com/RUCAIBox/POPE ; paper: https://aclanthology.org/2023.emnlp-main.20/ .
4. **VSR official:** https://github.com/cambridgeltl/visual-spatial-reasoning ; paper: https://arxiv.org/abs/2205.00363 .
5. **TallyQA official:** https://github.com/manoja328/TallyQA_dataset ; paper: https://doi.org/10.1609/aaai.v33i01.33018076 .
6. **Oxford-IIIT Pet official:** https://www.robots.ox.ac.uk/~vgg/data/pets/ ; HF: https://huggingface.co/datasets/timm/oxford-iiit-pet .
7. **NegBench (đọc tham khảo, không dùng nhầm protocol):** https://negbench.github.io/ ; https://github.com/m1k2zoo/negbench .
8. **Qwen2.5-VL-3B-Instruct:** https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct .
9. **Gemma 3 4B IT:** https://huggingface.co/google/gemma-3-4b-it ; https://huggingface.co/docs/transformers/model_doc/gemma3 .
10. **CLAIM, ACL 2025 (công trình liên quan):** https://aclanthology.org/2025.acl-long.640/ .
11. **Visual object-removal/contrast prior work:** https://aclanthology.org/2025.naacl-long.349/ .
12. **Colab FAQ:** https://research.google.com/colaboratory/faq.html . GPU free không bảo đảm luôn khả dụng.

---

**Trạng thái chốt:** dữ liệu, cỡ mẫu và các giả thuyết ở đây là **đề xuất** cần pilot/preflight xác minh. **Chưa có số liệu chất lượng mô hình**, không điền Accuracy hay p-value dự đoán vào báo cáo.
