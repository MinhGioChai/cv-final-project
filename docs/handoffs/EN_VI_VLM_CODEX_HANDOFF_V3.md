# EN–VI VLM Research — Codex Handoff V3

**Trạng thái:** Đặc tả triển khai theo Research Proposal mới nhất  
**Thời gian thực hiện:** 4 tuần  
**Quy mô nhóm:** 5 thành viên  
**Phần cứng dự kiến:** RTX 3060 6GB VRAM; có thể sử dụng Colab/Kaggle miễn phí  
**Phương pháp:** Zero-shot evaluation, không fine-tuning

## 0. Hướng dẫn quan trọng dành cho Codex

Bạn đang hỗ trợ một repository nghiên cứu Computer Vision đã tồn tại.

**Không xây dựng lại dự án từ đầu nếu các thành phần hiện tại có thể tái sử dụng.**

Trước khi chỉnh sửa code, hãy:

1. Đọc toàn bộ cấu trúc repository, README, tài liệu và cấu hình hiện có.
2. Xác định các thành phần đã hoàn thành, đang triển khai và còn thiếu.
3. Kiểm tra các script xử lý dữ liệu, inference, evaluation và kết quả pilot.
4. So sánh tình trạng hiện tại với đặc tả V3 này.
5. Đề xuất những thay đổi tối thiểu cần thực hiện.
6. Không xóa hoặc ghi đè code, dữ liệu, cấu hình hay kết quả cũ nếu chưa được đồng ý.
7. Không tự chạy benchmark quy mô lớn khi chưa có xác nhận.

**Lưu ý:** Đây là tài liệu triển khai theo proposal, không phải yêu cầu thực hiện ngay tất cả các thí nghiệm được đề cập.

## 1. Thông tin nghiên cứu

### Tên đề tài

**A Controlled English–Vietnamese Benchmark of Visual Grounding and Hallucination**

Tên diễn giải tiếng Việt:

**Khi thay đổi ngôn ngữ, câu trả lời của mô hình thị giác–ngôn ngữ thay đổi như thế nào?**

### Mục tiêu chính

Đánh giá liệu cùng một mô hình thị giác–ngôn ngữ (VLM), khi nhận cùng hình ảnh và hai câu hỏi tương đương về ngữ nghĩa bằng tiếng Anh và tiếng Việt, có tạo ra những câu trả lời khác nhau hay không.

Nghiên cứu tập trung vào:

- Sự khác biệt về *object hallucination*.
- Sự khác biệt về hiệu năng trên nhiều tác vụ thị giác.
- Mức độ nhất quán của câu trả lời giữa tiếng Anh và tiếng Việt.

### Hướng nghiên cứu mở rộng

Nếu phần đánh giá chính hoàn thành tốt và điều kiện cho phép, nhóm có thể thực hiện thêm các thí nghiệm để tìm hiểu những yếu tố có thể liên quan đến sự khác biệt Anh–Việt.

Các thí nghiệm này chỉ phân tích **hành vi quan sát được của mô hình**, không nhằm chứng minh trực tiếp cơ chế nhân quả bên trong VLM.

## 2. Research Questions

### RQ1 — Nghiên cứu chính, bắt buộc

**Tỷ lệ hallucination về sự tồn tại của vật thể có khác nhau giữa câu hỏi tiếng Anh và tiếng Việt khi hình ảnh và ngữ nghĩa được giữ nguyên hay không?**

Cách thực hiện:

- Sử dụng RePOPE.
- Đánh giá câu hỏi EN và VI theo cặp.
- Tập trung vào các mẫu có nhãn âm.
- Tính FPR cho từng ngôn ngữ.
- Tính ΔFPR và khoảng tin cậy.

Đây là **câu hỏi nghiên cứu trọng tâm**.

### RQ2 — Nghiên cứu chính, bắt buộc

**Mức chênh lệch hiệu năng giữa hai ngôn ngữ có thay đổi theo các tác vụ thị giác khác nhau hay không?**

Các tác vụ:

- Object presence — RePOPE.
- Spatial reasoning — VSR.
- Counting — TallyQA.
- Image classification — Oxford-IIIT Pet.

Cách thực hiện:

- Đánh giá hiệu năng EN và VI trong từng tác vụ.
- Tính mức chênh lệch giữa hai ngôn ngữ.
- Phân tích tỷ lệ bất đồng đáp án.
- Không so sánh trực tiếp độ khó của các dataset chỉ dựa vào accuracy.

### RQ3 — Mở rộng nếu khả thi

**Sự khác biệt trong câu trả lời giữa tiếng Anh và tiếng Việt có chịu ảnh hưởng từ cách diễn đạt câu hỏi hay không, ngay cả khi ý nghĩa được giữ nguyên?**

Thí nghiệm đề xuất:

**Paraphrase Sensitivity**

Chỉ triển khai nếu phần nghiên cứu chính đã ổn định.

### RQ4 — Mở rộng nếu khả thi

**Khả năng điều chỉnh câu trả lời theo sự thay đổi của bằng chứng thị giác có khác nhau giữa hai ngôn ngữ hay không?**

Thí nghiệm đề xuất:

**Visual Evidence Sensitivity**

Chỉ triển khai nếu có đủ thời gian để xây dựng và xác minh dữ liệu.

### Quy tắc ưu tiên

**RQ1 và RQ2 là yêu cầu bắt buộc.**

**RQ3 và RQ4 là hướng mở rộng có điều kiện, không phải tiêu chí bắt buộc để hoàn thành nghiên cứu.**

Không được trì hoãn hoặc làm giảm chất lượng RQ1–RQ2 để triển khai RQ3–RQ4.

## 3. Phạm vi nghiên cứu

### Mô hình

Dự kiến sử dụng:

1. `Qwen2.5-VL-3B-Instruct`
2. `Gemma 3 4B IT`

Yêu cầu:

- Zero-shot.
- Không fine-tuning.
- Không LoRA.
- Không sử dụng API suy luận trả phí.
- Cố định phiên bản mô hình và cấu hình trước khi chạy chính thức.
- Giữ nhất quán các điều kiện suy luận giữa EN và VI trong cùng một mô hình.

Hai mô hình cần được kiểm tra khả năng chạy trên phần cứng hiện có ngay từ tuần đầu.

Nếu một mô hình không khả thi, phải báo cáo vấn đề và đề xuất phương án xử lý. Không tự ý thay thế hoặc loại bỏ mô hình.

### Dataset và quy mô

| Dataset | Số mẫu dự kiến | Tác vụ |
|---|---:|---|
| RePOPE | 600 | Object presence |
| VSR | 120 | Spatial reasoning |
| TallyQA | 120 | Counting |
| Oxford-IIIT Pet | 160 | 8-class classification |
| **Tổng** | **1.000** | |

Mỗi mẫu được đánh giá bằng:

- Tiếng Anh.
- Tiếng Việt.
- Qwen.
- Gemma.

Tổng lượt inference chính dự kiến:

**1.000 mẫu × 2 ngôn ngữ × 2 mô hình = 4.000 lượt.**

Đây là kế hoạch dự kiến, không phải số lượt đã hoàn thành.

Quy mô chính thức chỉ được chốt sau khi kiểm tra dữ liệu và khả năng chạy mô hình.

## 4. Thiết kế benchmark

### 4.1. RePOPE

Dự kiến lựa chọn:

- Random: 200 mẫu.
- Popular: 200 mẫu.
- Adversarial: 200 mẫu.

Tổng: 600 mẫu.

Yêu cầu:

- Sử dụng đúng phiên bản dữ liệu và nhãn đã chọn.
- Ưu tiên nhãn đã được hiệu chỉnh của RePOPE.
- Cân bằng positive/negative khi dữ liệu cho phép.
- Ghi lại số ảnh duy nhất và số câu hỏi trên mỗi ảnh.
- Lưu phương pháp và seed lấy mẫu.
- Không thay đổi chiến lược lấy mẫu sau khi xem kết quả chính.

Nếu không thể lấy đúng phân bố dự kiến, phải báo cáo lý do và đề xuất phương án trước khi thay đổi.

### 4.2. VSR

Dự kiến 120 mẫu.

Yêu cầu:

- Giữ nguyên nội dung quan hệ không gian.
- Kiểm tra kỹ bản dịch các giới từ và quan hệ vị trí.
- Sử dụng định dạng đáp án nhị phân nhất quán.
- Không thay đổi ý nghĩa của phát biểu khi dịch.

### 4.3. TallyQA

Dự kiến 120 mẫu.

Yêu cầu:

- Kiểm tra vật thể cần đếm.
- Kiểm tra điều kiện lọc và quan hệ trong câu hỏi.
- Giữ nguyên số lượng đúng giữa hai ngôn ngữ.
- Phân tích kết quả bằng exact match và MAE.

### 4.4. Oxford-IIIT Pet

Dự kiến 160 ảnh:

- 8 lớp được chọn trước.
- 20 ảnh cho mỗi lớp.

Đây là thí nghiệm **phân loại tập con 8 lớp**, không phải kết quả trên benchmark 37 lớp tiêu chuẩn.

Yêu cầu:

- Lưu danh sách 8 lớp.
- Cố định mapping nhãn.
- Sử dụng cùng danh sách lựa chọn cho EN và VI.
- Không thay đổi tập lớp trong quá trình chạy chính thức.

## 5. Thiết kế đối chứng Anh–Việt

Mỗi mẫu cần có:

- Cùng hình ảnh.
- Cùng ground truth.
- Cùng tác vụ.
- Cùng ý nghĩa câu hỏi.
- Hai phiên bản câu hỏi EN và VI.

Biến được thay đổi chính là **ngôn ngữ của câu hỏi**.

Những yếu tố cần được kiểm soát:

- Phiên bản mô hình.
- Tiền xử lý hình ảnh.
- Cấu hình sinh câu trả lời.
- Định dạng đáp án.
- Danh sách nhãn.
- Cách phân tích đầu ra.

Không được thay đổi cấu hình giữa EN và VI mà không ghi nhận và giải thích.

### Kiểm tra bản dịch

Cần kiểm tra:

- Tên vật thể.
- Số lượng.
- Quan hệ không gian.
- Phủ định.
- Tính tương đương ngữ nghĩa.
- Tính tự nhiên của tiếng Việt.

Các mẫu nghi vấn phải được đánh dấu và kiểm tra trước khi đưa vào tập đánh giá chính.

Không ghi nhận dữ liệu là đã được kiểm tra thủ công nếu chưa thực hiện việc kiểm tra.

## 6. Cấu trúc dữ liệu

Tạo hoặc cập nhật benchmark manifest với các trường tối thiểu:

```text
sample_id
dataset
source_split
source_item_id
image_id
image_path
image_sha256
task_type
category
ground_truth
question_en
question_vi
translation_status
annotation_status
audit_notes
```

Yêu cầu:

- `sample_id` duy nhất.
- Đường dẫn ảnh hợp lệ.
- Nhãn đúng kiểu dữ liệu.
- Có nguồn gốc dữ liệu.
- Có seed lấy mẫu.
- Không trùng mẫu giữa pilot và main.
- Có danh sách mẫu bị loại và lý do.

Giữ riêng dữ liệu pilot, dữ liệu đánh giá chính và dữ liệu thí nghiệm mở rộng.

## 7. Pipeline inference

### Yêu cầu chung

Tạo hoặc tái sử dụng adapter cho từng mô hình.

Ưu tiên:

- Inference xác định.
- Khả năng chạy lại.
- Resume sau khi bị ngắt.
- Lưu raw output.
- Ghi nhận lỗi.
- Không tạo bản ghi trùng khi chạy lại.

### Định dạng câu trả lời

Dự kiến:

- Object presence: `YES` / `NO`.
- Spatial reasoning: `TRUE` / `FALSE`.
- Counting: số nguyên.
- Pet classification: mã lớp hợp lệ.

Có thể sử dụng hướng dẫn bằng ngôn ngữ tương ứng, nhưng cần giữ tương đương về yêu cầu và cùng tập nhãn đầu ra.

### Parser

Không dùng cách tìm chuỗi con đơn giản có thể nhận sai đáp án.

Ví dụ:

- `YES` là hợp lệ.
- `NO` là hợp lệ.
- Câu trả lời chứa cả `YES` và `NO` cần được xử lý theo quy tắc rõ ràng.
- Không suy đoán đáp án từ output mơ hồ.
- Những output không thể phân tích phải được đánh dấu `INVALID`.

### Metadata

Lưu tối thiểu:

```text
model_id
model_revision
processor_revision
tokenizer_revision
quantization
dtype
device
image_preprocessing
generation_config
prompt_template_version
package_versions
code_commit
```

## 8. Cấu trúc kết quả inference

Ưu tiên định dạng JSONL.

Mỗi bản ghi gồm:

```text
run_id
sample_id
model_id
model_revision
language
prompt_variant
image_variant
prompt_hash
image_sha256
raw_output
parsed_prediction
ground_truth
valid
invalid_reason
config_hash
timestamp
```

Có thể bổ sung:

```text
runtime_seconds
generated_tokens
device
quantization
code_commit
```

Yêu cầu:

- Giữ nguyên raw output.
- Không ghi đè kết quả mà không có log.
- Có thể truy vết một dự đoán về đúng ảnh, câu hỏi, mô hình và cấu hình.
- Phân biệt kết quả baseline với kết quả diagnostic.

## 9. Evaluation — RQ1 và RQ2

### 9.1. Metric chính cho RQ1

**ΔFPR = FPR(VI) − FPR(EN)**

Trong đó:

- FPR(EN): tỷ lệ dự đoán YES sai trên các mẫu RePOPE có ground truth là NO, sử dụng câu hỏi tiếng Anh.
- FPR(VI): tỷ lệ tương ứng khi sử dụng câu hỏi tiếng Việt.

Tính riêng cho từng mô hình.

Cần báo cáo:

- Số mẫu nhãn âm.
- Số ảnh duy nhất.
- FPR(EN).
- FPR(VI).
- ΔFPR.
- Tỷ lệ bất đồng EN–VI.
- Tỷ lệ INVALID theo ngôn ngữ.
- Khoảng tin cậy 95%.

Phân tích chính ưu tiên các cặp có đầu ra hợp lệ ở cả hai ngôn ngữ.

Đồng thời phải báo cáo dữ liệu bị thiếu hoặc không hợp lệ để tránh che giấu sai lệch do loại mẫu.

### 9.2. Bootstrap theo cụm ảnh

Sử dụng `image_id` làm đơn vị lấy mẫu lại.

Mục đích:

- Tránh xem nhiều câu hỏi từ cùng một ảnh là hoàn toàn độc lập.
- Giữ cặp EN–VI trong quá trình lấy mẫu lại.
- Ước lượng khoảng tin cậy 95% cho ΔFPR.

Phải kiểm thử implementation trên dữ liệu giả lập có đáp án đã biết.

### 9.3. Metric cho RQ2

**RePOPE**

- Accuracy.
- FPR.
- FNR.
- Paired disagreement.
- Invalid rate.

**VSR**

- Binary accuracy.
- EN–VI disagreement.
- Invalid rate.

**TallyQA**

- Exact match.
- Mean absolute error.
- EN–VI disagreement.
- Invalid rate.

**Oxford-IIIT Pet**

- 8-way top-1 accuracy.
- Accuracy theo lớp.
- EN–VI disagreement.
- Invalid rate.

Cần trình bày chênh lệch EN–VI **trong từng tác vụ**.

Không tự động gộp các metric khác bản chất thành một điểm tổng duy nhất.

### 9.4. Diễn giải kết quả

Không mặc định tiếng Việt phải kém hơn tiếng Anh.

Không xem một chênh lệch nhỏ là bằng chứng chắc chắn về khác biệt.

Nếu khoảng tin cậy rộng hoặc bao gồm 0, phải trình bày đúng mức độ bất định.

Kết quả không phát hiện chênh lệch rõ ràng vẫn là kết quả nghiên cứu hợp lệ.

## 10. RQ3 — Paraphrase Sensitivity

**Trạng thái: OPTIONAL / CONDITIONAL**

Không bắt buộc triển khai trong phạm vi nghiên cứu chính.

### Mục tiêu

Tìm hiểu liệu mức độ khác biệt EN–VI có liên quan đến cách diễn đạt câu hỏi hay không.

### Thiết kế đề xuất nếu triển khai

Chọn khoảng 40 mẫu.

Mỗi mẫu gồm:

- 2 cách diễn đạt tiếng Anh.
- 2 cách diễn đạt tiếng Việt.
- Cùng hình ảnh.
- Cùng ý nghĩa.
- Cùng ground truth.

Quy mô tham khảo:

**40 mẫu × 2 mô hình × 2 ngôn ngữ × 2 biến thể = 320 lượt inference.**

Nếu một biến thể trùng với baseline và có cùng cấu hình, có thể tái sử dụng kết quả hợp lệ.

### Phân tích

- Tỷ lệ đổi đáp án giữa các paraphrase trong cùng ngôn ngữ.
- Độ chính xác theo biến thể.
- Mức bất đồng EN–VI.
- Sự ổn định của chênh lệch EN–VI qua các biến thể.

### Điều kiện triển khai

Chỉ thực hiện khi:

1. RQ1 và RQ2 đã có pipeline ổn định.
2. Dữ liệu baseline được chốt.
3. Có đủ thời gian kiểm tra thủ công các paraphrase.
4. Có đủ tài nguyên inference.
5. Nhóm xác nhận triển khai.

Không tự động chạy thí nghiệm này.

## 11. RQ4 — Visual Evidence Sensitivity

**Trạng thái: OPTIONAL / CONDITIONAL**

Không bắt buộc triển khai trong phạm vi nghiên cứu chính.

### Mục tiêu

Tìm hiểu liệu khả năng điều chỉnh câu trả lời khi bằng chứng thị giác thay đổi có khác nhau giữa EN và VI hay không.

### Thiết kế đề xuất nếu triển khai

Xây dựng khoảng 30 cặp ảnh đã được xác minh.

Mỗi cặp gồm:

- Ảnh A: có vật thể mục tiêu.
- Ảnh B: không có vật thể mục tiêu.
- Cùng câu hỏi về vật thể mục tiêu.
- Ground truth của từng ảnh được kiểm tra thủ công.

Quy mô tham khảo:

**30 cặp × 2 ảnh × 2 ngôn ngữ × 2 mô hình = 240 lượt inference.**

### Phân tích

- Accuracy theo ngôn ngữ.
- Tỷ lệ mô hình đổi dự đoán đúng hướng khi đổi ảnh.
- Trường hợp mô hình giữ nguyên đáp án dù nhãn đã thay đổi.
- Chênh lệch EN–VI về khả năng phản ứng với bằng chứng thị giác.

### Giới hạn

Các cặp ảnh tự nhiên có thể khác nhau ở nhiều đặc điểm ngoài sự tồn tại của vật thể.

Vì vậy, kết quả chỉ được diễn giải là bằng chứng về hành vi quan sát được, không phải chứng minh cơ chế nhân quả bên trong mô hình.

### Điều kiện triển khai

Chỉ thực hiện khi:

1. RQ1 và RQ2 đã hoàn thành ở mức đủ tin cậy.
2. Có thể xác minh chất lượng các cặp ảnh.
3. Có đủ thời gian và tài nguyên.
4. Nhóm xác nhận triển khai.

Nếu không đủ điều kiện, ghi nhận RQ4 là hướng nghiên cứu tương lai.

## 12. Những việc không nằm trong phạm vi bắt buộc

Không tự ý bổ sung:

- Fine-tuning.
- LoRA.
- Mô hình thứ ba.
- Dataset lớn mới.
- Attention intervention.
- Phân tích activation nội bộ.
- Thí nghiệm phủ định riêng biệt.
- API trả phí.
- Pipeline giải thích mô hình phức tạp.

Những ý tưởng này có thể được ghi vào phần `Future Work`, nhưng không được triển khai nếu chưa có yêu cầu mới.

## 13. Kế hoạch bốn tuần

### Tuần 1 — Chuẩn bị và kiểm tra khả thi

**Bắt buộc**

- Audit repository.
- Kiểm tra dữ liệu và nhãn.
- Chốt cách lấy mẫu.
- Xây dựng manifest.
- Kiểm tra bản dịch.
- Kiểm tra Qwen và Gemma trên phần cứng.
- Kiểm thử parser.
- Chốt cấu hình baseline.

**Mốc hoàn thành:** Có dữ liệu và pipeline đủ tin cậy để bắt đầu benchmark chính.

### Tuần 2 — Baseline cho RQ1 và RQ2

**Bắt buộc**

- Chạy các lượt inference đã được phê duyệt.
- Lưu raw output và metadata.
- Kiểm tra kết quả EN–VI theo cặp.
- Kiểm tra INVALID/MISSING.
- Đảm bảo có thể resume.
- Xử lý lỗi kỹ thuật.

**Mốc hoàn thành:** Có dữ liệu đánh giá chính hoặc báo cáo rõ những phần bị chặn bởi tài nguyên.

### Tuần 3 — Phân tích chính và xem xét mở rộng

**Bắt buộc**

- Tính các metric cho RQ1.
- Tính các metric cho RQ2.
- Ước lượng bootstrap CI.
- Phân tích bất đồng EN–VI.
- Kiểm tra chất lượng kết quả.

**Tùy chọn nếu khả thi**

- Triển khai RQ3.
- Triển khai RQ4.

**Quy tắc:** Chỉ mở rộng sau khi nhóm xác nhận phần nghiên cứu chính đã ổn định.

### Tuần 4 — Hoàn thiện báo cáo

**Bắt buộc**

- Hoàn thiện bảng và biểu đồ.
- Viết Results.
- Viết Discussion.
- Phân tích limitations.
- Kiểm tra khả năng tái lập.
- Chuẩn bị slide bảo vệ.

Nếu RQ3–RQ4 chưa được thực hiện, trình bày chúng trong phần `Future Work`.

Không viết như thể các thí nghiệm tùy chọn đã được hoàn thành.

## 14. Phân công nhóm gợi ý

**Thành viên 1 — Dataset**

- Thu thập dữ liệu.
- Sampling.
- Manifest.
- Data provenance.

**Thành viên 2 — Translation QA**

- Dịch và kiểm tra câu hỏi.
- Kiểm tra nhãn.
- Theo dõi các mẫu nghi vấn.

**Thành viên 3 — Qwen Inference**

- Thiết lập môi trường.
- Pipeline Qwen.
- Tối ưu bộ nhớ.
- Kiểm thử inference.

**Thành viên 4 — Gemma Inference**

- Pipeline Gemma.
- Kiểm thử phần cứng.
- Hỗ trợ các thí nghiệm mở rộng nếu được phê duyệt.

**Thành viên 5 — Evaluation**

- Metrics.
- Bootstrap.
- Biểu đồ.
- Phân tích lỗi.
- Tổng hợp báo cáo.

Tất cả thành viên cùng kiểm tra chéo dữ liệu và kết quả.

## 15. Rủi ro và phương án dự phòng

### Không đủ VRAM

- Kiểm tra lượng tử hóa phù hợp.
- Kiểm tra offloading nếu cần.
- Thử môi trường Colab/Kaggle miễn phí khi khả dụng.
- Đo tốc độ inference thực tế.
- Báo cáo giới hạn trước khi quyết định thay đổi phạm vi.

### Benchmark chạy quá chậm

Ưu tiên theo thứ tự:

1. Hoàn thiện dữ liệu và pipeline đáng tin cậy.
2. Hoàn thiện RePOPE cho RQ1.
3. Hoàn thiện các tác vụ bổ sung cho RQ2.
4. Chỉ sau đó mới xem xét RQ3–RQ4.

Không tự ý giảm số mẫu hoặc thay đổi mô hình mà không thông báo.

### Bản dịch không tương đương

- Đánh dấu mẫu.
- Kiểm tra lại.
- Sửa trước khi chốt benchmark.
- Ghi nhận mọi thay đổi sau khi chốt.

### INVALID quá nhiều

- Kiểm tra prompt và parser.
- Phân biệt lỗi định dạng với lỗi kiến thức.
- Không âm thầm chuyển INVALID thành đáp án đúng/sai.
- Báo cáo tỷ lệ INVALID theo ngôn ngữ.

### Khoảng tin cậy rộng

- Báo cáo độ bất định.
- Không khẳng định có chênh lệch rõ ràng khi dữ liệu chưa hỗ trợ.
- Không thay đổi mẫu chỉ để tạo kết quả có ý nghĩa thống kê.

### Không đủ thời gian cho RQ3–RQ4

- Không ảnh hưởng đến kết quả RQ1–RQ2.
- Không xem đây là thất bại của nghiên cứu.
- Đưa RQ3–RQ4 vào `Future Work`.

## 16. Kiểm thử bắt buộc

Cần có các bài kiểm thử cho:

- Manifest schema.
- `sample_id` duy nhất.
- `image_path` hợp lệ.
- Ground truth hợp lệ.
- Không trùng pilot/main.
- EN–VI pairing.
- Output parser.
- INVALID handling.
- Resume không tạo trùng.
- Metric trên toy data.
- ΔFPR trên toy data.
- Bootstrap theo cụm ảnh.
- Tính nhất quán của model config.
- Tái lập kết quả từ raw outputs.

Kiểm thử cho RQ3–RQ4 chỉ cần bổ sung nếu quyết định triển khai.

## 17. Cấu trúc repository gợi ý

```text
configs/
    baseline.yaml
    diagnostics.yaml

data/
    manifests/
    qa/

src/
    datasets/
    inference/
    parsing/
    evaluation/
    diagnostics/

scripts/
    prepare_benchmark.py
    validate_manifest.py
    run_baseline.py
    analyze_results.py
    run_diagnostics.py

results/
    raw/
    metrics/
    figures/

tests/

docs/
    EN_VI_VLM_CODEX_HANDOFF_V3.md
    RESEARCH_PROTOCOL_V3.md
    EXPERIMENT_LOG.md
```

Đây chỉ là cấu trúc tham khảo.

Ưu tiên giữ cấu trúc repository hiện có nếu đã hợp lý.

Không tạo các module diagnostic không cần thiết khi RQ3–RQ4 chưa được phê duyệt.

## 18. Quy tắc quản lý tiến độ

Sử dụng bốn trạng thái:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

Phân loại công việc:

**P0 — Bắt buộc**

- Dữ liệu và bản dịch.
- Baseline inference.
- RQ1.
- RQ2.
- Thống kê.
- Reproducibility.
- Báo cáo.

**P1 — Mở rộng có điều kiện**

- RQ3 — Paraphrase Sensitivity.
- RQ4 — Visual Evidence Sensitivity.

**P2 — Future Work**

- Negation experiments.
- Attention analysis.
- Mở rộng mô hình hoặc dataset.
- Các phương pháp giải thích cơ chế chuyên sâu.

**Không được tự động nâng P1 hoặc P2 thành P0.**

## 19. Tiêu chí hoàn thành

### Hoàn thành nghiên cứu chính

Nghiên cứu chính được xem là hoàn thành khi:

1. Benchmark và phương pháp lấy mẫu được ghi nhận rõ ràng.
2. Cặp câu hỏi EN–VI được kiểm tra.
3. Các mô hình khả thi đã được chạy theo giao thức được phê duyệt.
4. RQ1 có kết quả FPR và ΔFPR.
5. RQ2 có kết quả theo tác vụ.
6. Có thống kê INVALID/MISSING.
7. Có khoảng tin cậy và phân tích độ bất định phù hợp.
8. Có thể truy vết và tái tạo các bảng từ dữ liệu gốc.
9. Báo cáo nêu rõ những giới hạn của nghiên cứu.

**Không yêu cầu phải có kết quả RQ3 hoặc RQ4 để đạt tiêu chí hoàn thành nghiên cứu chính.**

### Hoàn thành phần mở rộng

Chỉ đánh dấu RQ3 hoặc RQ4 là `DONE` nếu:

- Đã được nhóm phê duyệt.
- Có dữ liệu được xác minh.
- Có inference thực tế.
- Có metric và phân tích.
- Có mô tả giới hạn phù hợp.

## 20. Yêu cầu Codex thực hiện đầu tiên

**CHỈ THỰC HIỆN REPOSITORY AUDIT VÀ LẬP KẾ HOẠCH TRƯỚC.**

Hãy kiểm tra repository hiện tại và trả về:

1. Cây thư mục và chức năng của các module chính.
2. Những phần đã hoàn thành và có thể tái sử dụng.
3. Những phần còn thiếu để trả lời RQ1 và RQ2.
4. Các vấn đề tiềm ẩn về dữ liệu, nhãn, parser và phần cứng.
5. Danh sách file cần tạo hoặc chỉnh sửa.
6. Kế hoạch triển khai P0 theo thứ tự ưu tiên.
7. Checklist tiến độ `TODO / IN_PROGRESS / BLOCKED / DONE`.
8. Đề xuất điều kiện để sau này quyết định có triển khai RQ3–RQ4 hay không.

Sau khi báo cáo, **chờ người dùng xác nhận** trước khi thay đổi lớn hoặc chạy inference quy mô lớn.

Không tự tạo kết quả nghiên cứu.

Không tự chạy 4.000 lượt inference.

Không tự triển khai RQ3–RQ4.

**Ưu tiên số một: hoàn thành RQ1 và RQ2 với dữ liệu đáng tin cậy, phương pháp rõ ràng và kết quả có thể tái lập.**

---

**Kết thúc Codex Handoff V3.**