# Experiment protocol

Protocol hiện hành được tập trung ở
[Research Protocol V3](research/RESEARCH_PROTOCOL_V3.md). Xem
[Handoff V3](handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md) cho yêu cầu người dùng và
[Implementation Plan](research/IMPLEMENTATION_PLAN_V3.md) cho việc cần làm.

## Phân biệt implementation và kế hoạch

- Đã có ETL/source audit/review/parser/leakage validation và portable pilot runner.
- Qwen có 20 lượt thật; Gemma chưa load, cloud chưa generation thật.
- Pilot 30 bản dịch approved; QA ảnh/nhãn pending; không dùng làm final.
- Runner hiện nhận RePOPE pilot 1–30 row. Ngày 16/11 đã thêm analysis CLI
  evaluate/statistics với metrics bốn task và image-cluster bootstrap.
- configs/main.yaml và prompts chưa frozen. Không đổi config/hash của run cũ.
- RQ1/RQ2 bắt buộc; RQ3/RQ4 có điều kiện; negation riêng là Future Work.

## Quy tắc còn dùng được

Independent EN/VI requests, không history; giữ ảnh/nghĩa/label set/cấu hình.
Parser full-answer và INVALID=null, không đoán nhãn hoặc đổi invalid thành NO.
Main cần human approvals thật và pilot-image exclusions; kiểm tra kỹ thuật
không tự approve. Giữ raw outputs, attempts, checkpoint và source provenance.

Primary ΔFPR trên jointly-valid negative pairs, kèm số cặp loại/missing/invalid,
sensitivity và paired image-cluster bootstrap theo V3 đã có ở evaluation v1.
Main data/protocol còn chờ freeze. [Evaluation guide](research/EVALUATION_V1.md).

Nội dung hướng dẫn trước 12/11 được giữ nguyên tại
archive pre-V3 (`archive/pre_v3/docs/experiment_protocol.md`, chỉ giữ local); không dùng mô tả
“chưa có adapter/inference” ở bản cũ để phủ nhận Qwen run v4.
