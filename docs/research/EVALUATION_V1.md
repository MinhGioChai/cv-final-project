# Paired evaluation và bootstrap v1

Triển khai ngày 16/11/2026 sau khi người dùng yêu cầu tiếp tục các bước P0.
Hai lệnh phân tích đọc manifest và inference đã lưu. Kết quả Qwen thực được
ghi ở [Stage 1 v5](../../reports/stage1/v5/completion.md).

## Chạy từ project root

```powershell
.venv/Scripts/python.exe -m vlmbench.cli evaluate --manifest data/pilot/stage1_v3/pilot_manifest.csv --predictions results/pilot/local/qwen_smoke_v1.jsonl --selection results/pilot/local/qwen_smoke_v1.summary.json --output reports/stage1/v5/qwen_evaluation.json --report reports/stage1/v5/qwen_evaluation.md

.venv/Scripts/python.exe -m vlmbench.cli statistics --evaluation reports/stage1/v5/qwen_evaluation.json --output reports/stage1/v5/qwen_statistics.json --resamples 5000 --seed 42
```

evaluate xuất JSON có paired rows, metrics, raw source line/attempt và checksum
các input. --report tạo bản Markdown đọc nhanh. statistics kiểm tra version và
report hash, đọc paired rows đã lưu rồi xuất uncertainty có nguồn gốc liên kết.
Mỗi lệnh có --help. Chạy lại cùng dữ liệu/settings dùng lại output giống hệt.
Đổi nội dung hoặc settings thì dùng output path có phiên bản mới.

## Expected grid và pairing

--selection nhận plan/summary JSON có sample_ids. Thiếu tùy chọn này, expected
grid là toàn manifest × EN/VI, kể cả row chưa có raw record. Với Qwen hiện có,
summary cuối chứa 10 sample IDs, còn meta khởi tạo giữ plan 2 mẫu trước khi
resume. Dùng summary cuối để đánh giá đầy đủ mười mẫu đã chạy.

Một file prediction được đánh giá theo một model/model revision/processor
revision/protocol hash/run config hash. Record phải thuộc selection, giữ đúng
dataset/task/image/hash/ground truth và chứa câu hỏi manifest trong prompt.
Parser hiện tại parse lại raw response và kiểm tra nhãn đã lưu. Mỗi key
sample/language/attempt phải duy nhất. Retry sau lỗi dùng attempt cuối, giữ
source line và số attempts. Attempt theo sau generation thành công cần tách
run để có provenance rõ. Blank lines trong JSONL vẫn giữ đúng source-line index.

Paired rows ghi cả source labels, is_pilot và trạng thái QA. Scope là
engineering_pilot khi còn pilot flag hoặc approval chưa đủ. File paired rows
dùng các tên dataset/task thuận tiện cho evaluation, còn CSV/raw lịch sử tiếp
tục dùng schema hiện có. Raw generation metadata V3 còn cần hoàn thiện ở bước baseline.

## Chính sách tính điểm của phiên bản này

| Thành phần | Quy tắc được triển khai |
|---|---|
| Trạng thái output | valid, invalid, failed và missing được đếm riêng |
| Accuracy và exact match/top 1 | Số valid prediction đúng chia toàn bộ expected rows. Invalid/failed/missing đóng góp 0 vào tử số |
| Accuracy valid-only | Số đúng chia valid rows, kèm valid rate và expected denominator |
| Binary secondary | Confusion matrix, FPR/FNR/precision/recall/F1 trên valid predictions của từng language |
| Primary RePOPE | Negative rows có EN và VI đều valid, chung denominator. ΔFPR = VI trừ EN, đơn vị điểm phần trăm |
| EN–VI disagreement | Prediction khác nhau trên jointly valid pairs, báo cả n_jointly_valid và excluded-status counts |
| Counting MAE | Valid numerical predictions, kèm valid coverage và exact match toàn expected grid |
| Pet | Top 1 và per-class accuracy theo mapping A–H của manifest |
| Phân tầng | Kết quả theo dataset/task/category. RePOPE có complete-case primary trong từng category |
| Denominator bằng 0 | JSON null cho metric undefined |

Accuracy theo expected grid đo hiệu quả theo bộ lượt dự kiến. Các số
failed/missing, valid-only accuracy và coverage hỗ trợ đọc kết quả khi mức
hoàn thành khác nhau. Đây là quyết định scoring v1 cho phân tích pilot và
cần được nhóm chốt khi freeze protocol main.

Sensitivity FPR dùng toàn bộ expected negative rows. Mỗi invalid/failed/missing
có đáp án chưa quan sát. Cận dưới mỗi language dùng số FP hợp lệ đã quan sát,
cận trên cộng số chưa quan sát. Cận ΔFPR dùng tổ hợp cực trị hai phía. Report
ghi rõ denominator và unknown counts để phân biệt sensitivity bounds với CI.

## Bootstrap theo ảnh

Defaults dùng seed 42 và 5.000 resamples, percentile CI 95% với linear quantile
interpolation. Cluster key gồm image namespace và image ID. Mỗi resample lấy
lại các cụm ảnh với replacement, giữ toàn bộ câu hỏi và EN/VI của cụm được chọn.
Estimate dùng tổng chênh lệch chia tổng số row của các ảnh được resample, tức
row-weighted trong các cụm được lấy lại.

Primary bootstrap dùng các ảnh có ít nhất một jointly-valid negative RePOPE
row. Đây là khoảng ước lượng conditional trên complete-case negative frame.
Accuracy bootstrap dùng expected pairs của từng dataset/task và cùng scoring
policy ở bảng trên. Một cluster cho estimate nhưng uncertainty để null cùng
status giải thích. Không có eligible row cho estimate và interval null.
Empirical distribution suy biến được ghi cờ trong report.

V1 chưa có stratified/BCa bootstrap, p-value, power analysis hoặc điều chỉnh
multiple comparisons. Việc chọn percentile, B/seed, weighting và frame được
ghi thành metadata, giúp nhóm rà soát trước freeze main.

## Kiểm tra và phạm vi dữ liệu

31 test mới gồm bảng tính tay cho bốn task, invalid/failure/missing, provenance,
retry, duplicate, CLI replay/hash, spatial truth mapping và cluster dependence.
Suite ngày 16/11 đạt 175 tests trong .venv. Test data nằm trong fixtures hoặc
thư mục tạm và được đánh dấu synthetic_test_only.

Số liệu thực v5 được tính lại từ 20 raw Qwen outputs của phiên 10/11, trên
10 mẫu. Có 5 negative images dùng primary CI, QA ảnh/nhãn vẫn pending.
Report này hỗ trợ kiểm tra pipeline và mô tả pilot. Main data, Gemma, cloud
generation, QA và baseline freeze vẫn cần tiếp tục theo kế hoạch V3.
