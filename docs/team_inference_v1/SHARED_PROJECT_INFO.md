# Thông tin nghiên cứu và giới hạn

Zero-shot paired EN–VI: RQ1 là RePOPE negative-only ΔFPR; RQ2 gồm bốn task.
Phạm vi hiện tại không có training/LoRA hoặc RQ3/RQ4. Main có 600 RePOPE +
120 VSR + 120 TallyQA + 160 Pet = 1.000 mẫu / 783 ảnh.
Qwen dùng NF4/FP16, Gemma dùng NF4/BF16; exact revisions nằm trong
`configs/baseline_v3_final_v1.yaml`. Option B: source JPEG → RGB giữ W×H → pinned processor.
Labels/sources/history giữ nguyên. TallyQA gồm 112 QA nguồn + 5 câu hỏi nguồn
có nhãn sửa + 3 QA viết lại; sensitivity 117 vẫn giữ 5 nhãn sửa. RePOPE có 294 yes / 306 no.

M1 DONE; local M2 v1 DONE; M3 PARTIAL_QWEN_ONLY với 16 valid cells.
Gemma main chưa smoke. Receipt v1 chưa cấp phép implementation sharding mới.
Nếu PR Phase A thay runtime/fingerprint, TV5 phải version và phê duyệt
implementation/protocol v2 sau integration.

Full main chưa chạy hoặc được phê duyệt. Reuse/collection cần kiểm đúng protocol,
scope và compatibility. Cloud/Secrets/GPU chưa được kiểm thật bằng tài khoản nhóm.
Qwen EN trên Colab và VI trên Kaggle có thể khác môi trường phần cứng/numerics:
ghi đầy đủ provenance, đối chiếu smoke/compatibility trước execution và thảo luận
confound còn lại. Cùng tên model chưa đảm bảo hai môi trường tương đương.

Ngày thuyết trình 03/12/2026. Giữ scope P0; ưu tiên integration, QA, smoke, execution và report.
