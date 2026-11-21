# Stage 1 v6 — Kiểm tra Gemma smoke FP16

Ngày 19/11/2026 (Asia/Saigon). Hoàn tất phân tích run do người dùng chạy;
pilot hai model và toàn bộ Stage 1 chưa hoàn tất.

## Bằng chứng thật

Gemma load được trên RTX 3060 Laptop, NF4/FP16, cùng revision/config đã pin.
Run `results/pilot/local/gemma_smoke_v1.jsonl` có 2 mẫu × EN/VI = 4 lượt:
success=4, invalid=4, failed=0, missing=0. Cả bốn raw_response đều là chuỗi
rỗng, parse_reason=INVALID_EMPTY. Success đếm generation không ném exception,
không có nghĩa output valid hoặc trả lời đúng.

Median processor+generation 2281,63 ms, peak PyTorch allocated 5200,24 MiB.
Không tính thời gian download/load hoặc tổng device VRAM. QA hai ảnh vẫn
pending. Lỗi pagefile 1455 trước đó không tái diễn trong run này; chưa xác nhận
người dùng đã thay Windows settings nào. Không xóa report lỗi cũ.

[Evaluation](gemma_fp16_evaluation.json), [bảng ngắn](gemma_fp16_evaluation.md),
[statistics](gemma_fp16_statistics.json), [verification](verification.json).
FPR/Delta FPR/disagreement không xác định vì không có cặp jointly valid.
Primary CI có no_eligible_rows, không trả 0 giả. Accuracy expected-grid bằng
0 theo policy invalid tính sai; không diễn giải thành năng lực thị giác 0%.

## Chẩn đoán và bước kế tiếp

Parser xử lý chuỗi rỗng đúng. Raw cũ không có generated token IDs hoặc logits,
nên chưa biết model phát special tokens hay có lỗi số học. Không đổi parser
để hợp thức hóa output, không thêm token budget theo suy đoán hoặc retry các
generation success này vào cùng file. Resume limit 10 sẽ giữ cả bốn INVALID.

Checkpoint config lưu dtype bfloat16, adapter pilot đang ép float16 cho model,
NF4 compute và image inputs. Maintainer Transformers xác nhận Gemma3 không
được thiết kế cho FP16 và khuyên BF16 trong
[issue 39972](https://github.com/huggingface/transformers/issues/39972).
Đây là căn cứ cho giả thuyết bất ổn FP16, chưa phải xác nhận nguyên nhân trên
run này. Kiểm tra mới torch.cuda.is_bf16_supported() trả True trên GPU hiện tại.

Đề xuất tiếp theo: diagnostic NF4/BF16 có version trên cùng 2 mẫu EN/VI,
giữ prompt/ảnh/revision/seed, lưu token IDs, decode có/không special tokens
và finite-logit checks. Dùng output mới và metadata precision đúng; sửa đổi
không được làm mất khả năng đối chiếu Qwen và protocol cũ. Cần ghi rõ BF16
không phải full unquantized weights, vẫn giữ NF4. Chưa implement hoặc chạy
diagnostic BF16 trong phiên chỉ hỏi bước tiếp theo này.

Sau khi xác nhận output hợp lệ và runtime ổn định, mở rộng lên cùng 10 mẫu
Qwen, kiểm resume, metrics/CI và human QA trước main freeze. Giữ nhắc pilot
Gemma qua các phiên cho đến khi có bằng chứng hoàn tất.

## Phạm vi công việc phiên này

Đọc raw/summary, replay parser bằng evaluator, chạy evaluate/statistics từ
output có sẵn, kiểm GPU hỗ trợ BF16, hashes raw/config/code và cập nhật docs.
Không đổi runner/parser/config/dependency, không model generation mới, không
human QA hoặc unit-test run mới. Suite 175 passed ngày 16/11 là lịch sử.
