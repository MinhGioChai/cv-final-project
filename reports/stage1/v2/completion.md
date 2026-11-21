# Stage 1 v2 — Classifiers, pilot 30 mẫu và environment preflight

**Ngày:** 09/11/2026 (Asia/Saigon). **Mốc nhật ký:** v4.
**Trạng thái:** đã cập nhật bản dịch theo nhận xét người dùng, mở rộng dữ liệu
pilot lên 30 mẫu và kiểm kê GPU/runtime. Chưa hoàn tất QA độc lập hoặc inference.

## Phản hồi và thay đổi

Người dùng đã xem 10 bản dịch v1, nhận xét nhìn chung ổn và đề nghị thêm từ
chỉ loại, ví dụ “có cái bát nào không?”. Đã lưu nguyên văn phản hồi tại
[user_feedback.json](user_feedback.json); không bỏ sót nhận xét này ở phiên sau.

Template v2 dùng `classifier_vi` trong dictionary: cái bát, chiếc xe đạp,
con thuyền/con chó, quả cam; person vẫn là người nào. Trong 10 câu cũ có 9 câu
được sửa, 1 câu giữ nguyên. Xem [so sánh v1–v2](feedback_comparison.md).
Dictionary v1/v2 được lưu tại `data/dictionaries/versions/`; không ghi đè
review/audit/manifest của Stage 1 v1.

Phản hồi là nhận xét ngôn ngữ thật của người dùng về 10 câu v1; không suy ra
người duyệt thứ hai, QA ảnh/nhãn hoặc đã xem 20 mẫu mới. Cờ tổng hợp vẫn
requires_review/pending. Không tạo reviewer ID hoặc timestamp duyệt giả.

## Kết quả thực

| Hạng mục | Kết quả |
|---|---|
| Mở rộng pilot | 30 row / 30 ảnh / 30 checksum khác nhau |
| Giữ mẫu cũ | Đủ 10 mẫu gốc, giữ nguyên toàn bộ row nguồn, ID, ảnh, nhãn và metadata |
| Mẫu mới | 20 row mới; tải thêm metadata/ảnh nhỏ, 1.276.204 bytes trong lần chuẩn bị thành công |
| Cân bằng | 5 YES + 5 NO cho mỗi random/popular/adversarial; tổng 15 YES/15 NO |
| Preflight | 30/30 ảnh đọc được, checksum hợp lệ |
| Source audit | 30/30 khớp upstream commit `bcf22e5690d587cce34e1728af3efdcfaf747d29` |
| Drafts | 30/30 có VI draft, 19 đối tượng, template v2_classifiers |
| Exclusions | Registry tích lũy đủ 30 ảnh pilot, giữ ảnh cũ |
| Tests | 132 passed ở phiên này; pip check sạch |
| Replay | Prepare offline giữ manifest, import lại giữ draft/audit |
| Lịch sử | Các artifact có hash trong verification v1 vẫn nguyên vẹn |

Pool vẫn là ba trang cố định, 300 row / 57 ảnh; chỉ dùng pilot kỹ thuật, không
dùng làm sampling frame cho main. Không chạy inference, không có metric VLM.

## Môi trường đã kiểm tra

[Environment report](environment_preflight.json) ghi nhận RTX 3060 Laptop,
tổng bộ nhớ 6.144 MiB, driver 581.95. Đây không phải peak VRAM chạy model.
Venv chưa có torch/transformers/accelerate/bitsandbytes/qwen-vl-utils.
`doctor` không import model, không kiểm thử CUDA qua torch, không tải weights.
Không khẳng định cấu hình chạy được trước khi có smoke test thật.

## File và lệnh mới

- `configs/pilot_stage1_v2.yaml`: pilot 30 mẫu, cache/output riêng.
- `prepare-pilot --retain-manifest`: giữ mẫu cũ, bù quota, báo xung đột thay vì bỏ mẫu.
- Dictionary có `classifier_vi`; loader vẫn hỗ trợ schema v1.
- `doctor`: inventory GPU driver/package versions, không tải model.
- [Preview 30 mẫu](translation_preview.md), [CSV review](../../../data/reviews/stage1_v2/translation_review.csv),
  [source audit](source_audit.json), [sampling](sampling_report.json),
  [validation](validation_report.json), [verification/hashes](verification.json).
- [Pilot findings](../../../docs/pilot_findings.md): phân biệt dữ liệu/môi trường đã kiểm tra với kết quả model chưa có.

```powershell
.venv/Scripts/python.exe -m vlmbench.cli prepare-pilot --config configs/pilot_stage1_v2.yaml --retain-manifest data/pilot/pilot_manifest.csv --offline
.venv/Scripts/python.exe -m vlmbench.cli audit-source --manifest data/pilot/stage1_v2/pilot_manifest.csv --output data/pilot/stage1_v2/source_verified_manifest.csv --report reports/stage1/v2/source_audit.json --offline
.venv/Scripts/python.exe -m vlmbench.cli export-translation-review --manifest data/pilot/stage1_v2/source_verified_manifest.csv --output data/reviews/stage1_v2/translation_review.csv --report reports/stage1/v2/translation_draft_report.json
.venv/Scripts/python.exe -m vlmbench.cli import-translation-review --manifest data/pilot/stage1_v2/source_verified_manifest.csv --review data/reviews/stage1_v2/translation_review.csv --output data/pilot/stage1_v2/draft_manifest.csv --audit reports/stage1/v2/draft_import_audit.json --operator codex
.venv/Scripts/python.exe -m vlmbench.cli validate --manifest data/pilot/stage1_v2/draft_manifest.csv
.venv/Scripts/python.exe -m vlmbench.cli doctor --output reports/stage1/v2/environment_preflight.json
.venv/Scripts/python.exe -m pytest -q
```

## Bước kế tiếp

Chuẩn bị inference environment và viết adapters Qwen/Gemma với output schema,
checkpoint/resume và parser chung; chốt revisions/precision, thử CUDA/load từng
model. Chuẩn bị subset đạt QA để chạy tối thiểu 10 row × EN/VI × 2 model.
Nhận xét đã nhận về 10 câu được giữ làm bằng chứng; phần ngôn ngữ mới cần xem
là các câu đã sửa với từ chỉ loại và 20 mẫu mới, cùng QA ảnh/nhãn còn thiếu.
Gemma license access cần tài khoản người dùng khi đến bước tải model.

Proposal 2 trang theo mốc nội bộ 11/11 vẫn là công việc song song. Lịch chính
thức và nhóm 5 cần xác nhận với giảng viên; không tự coi mốc nội bộ là deadline thầy.
