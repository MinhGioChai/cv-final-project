# Giới hạn và quyết định còn mở

Cập nhật 12/11/2026 theo [V3](handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md).
Snapshot trước V3 (`archive/pre_v3/docs/limitations.md`, chỉ giữ local) giữ các mốc lịch sử;
[protocol mới](research/RESEARCH_PROTOCOL_V3.md) ghi decisions/mapping hiện hành.

- Pilot 30 row, 30 ảnh; source audit khớp nhưng image/label QA vẫn pending.
  Language approval không phải hai reviewer độc lập hoặc image approval.
- Pool ba trang metadata chủ đích có selection bias; không dùng làm main frame.
- Qwen n=10 đã chạy thật trên RTX 3060/NF4-FP16; không đủ suy rộng gap EN–VI,
  không có CI hoặc p-value final. Source-label match EN 10/10 và VI 9/10 là mô tả.
- Gemma 10 mẫu/20 lượt NF4/BF16 valid thật ở v7, peak allocated 5720,93 MiB;
  không bảo đảm fit mọi ảnh/config hoặc thời gian main. FP16 diagnostic có
  NaN nên không dùng như valid baseline. Cloud chưa generation thật, notebooks
  Gemma vẫn FP16 cũ; không cam kết GPU BF16/availability/quota.
- VSR/TallyQA/Pet chưa có adapters/data main. Split/lớp/candidates và image
  provenance/license cần chốt; mirror license không tự cấp quyền mọi ảnh.
- Metrics/paired evaluator/bootstrap đã có code/tests và actual Qwen pilot
  report v5. Complete-case primary có selection bias. V1 báo invalid/missing
  và sensitivity, còn policy main cần chốt trước freeze.
- Nhiều câu cùng ảnh không độc lập; row McNemar không xử lý clustering.
  Chưa tính power, chưa đủ căn cứ tuyên bố tương đương ngôn ngữ nếu CI chứa 0.
- Metadata V3 cần mapping và bổ sung run/prompt variants/hash, tokenizer and code
  provenance; giữ raw và config hashes của pilot cũ.
- NF4, resize, output cap và khác kiến trúc giới hạn model comparison; không
  tự động coi cùng protocol là bitwise-identical trên mọi GPU/runtime.
  Qwen dùng NF4/FP16, Gemma dùng NF4/BF16 vì số học; ghi riêng theo model,
  giữ cấu hình giữa EN/VI trong model. Gemma có raw-logit instrumentation nên
  timing không so trực tiếp với Qwen không trace. CI hai pilot chỉ trên 5
  negative ảnh/model, đều chạm 0, không phải final CI hoặc power claim.
- Paraphrase/visual evidence là P1 có gate, có thể không làm. Natural image pairs
  có confounds; không suy ra causal internal mechanism. Negation riêng là P2.
- Đề bài Topic 14 có nhắc negation; nhóm cần giải thích scope V3/giới hạn hoặc
  xác nhận yêu cầu với giảng viên, không tự triển khai trái ưu tiên mới.
- Chưa thấy proposal mới ngoài handoff V3, chưa có xác nhận proposal đã nộp.
  Hai Word v1 là snapshot V4.2; ngày 06/12 chỉ là mục tiêu nội bộ cũ.
