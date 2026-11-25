# Oxford Pet review theo nhãn nguồn

Ngày 25/11/2026, người dùng chốt quy trình riêng cho 160 mẫu Oxford Pet và
xác nhận đã kiểm ảnh, bản dịch, không thấy vấn đề. Nhóm kế thừa nhãn giống
trong annotation chính thức; không ghi nhận việc nhận diện giống bằng mắt.
Quy trình này chỉ áp dụng Pet. RePOPE, VSR và TallyQA vẫn cần hai reviewer A/B
theo [review v2](MAIN_REVIEW_V2.md).

## Quyết định và bằng chứng

| Thành phần | Căn cứ |
|---|---|
| Dịch EN–VI và chất lượng ảnh | Xác nhận của một người dùng trong hội thoại cho toàn bộ 160 mẫu |
| Nhãn giống chó | Kế thừa official test annotations, không phải human breed identification |
| Ảnh và mapping A–H | Code đối soát annotation archive, selected candidates, record hashes, class/species/breed IDs, image receipt, JPEG SHA256 và pilot exclusions |

JSON tổng hợp là
[`oxford_pet_reviewed_v1.json`](../../data/reviews/pet_source_review_v1/oxford_pet_reviewed_v1.json).
Policy `pet_human_translation_image_quality_source_labels_v1`, schema
`pet_source_review_v1`. Phần `human_attestation` giữ nguyên lời xác nhận,
ngày khai báo và thời điểm ghi nhận; thời điểm thực sự xem từng ảnh không
được cung cấp. `project_user_conversation` là ID quy ước của người dùng trong
phiên, không phải tên pháp lý đã xác minh. Không có reviewer B hoặc lượt
nhận diện giống được tạo thêm.

Các `decisions` bind từng sample với bản EN/VI, nhãn nguồn, ảnh/checksum và
row hash gốc. Kiểm tự động không chứng minh annotation chính thức luôn đúng;
report cần nêu rõ giới hạn kế thừa nhãn này. Khi phát hiện lỗi thực tế,
ghi nhận vấn đề và version dữ liệu trước freeze; không sửa labels tùy tiện.

## File và trạng thái sau import

- Xác nhận gốc: `data/reviews/pet_source_review_v1/user_attestation.json`.
- JSON tổng hợp: `data/reviews/pet_source_review_v1/oxford_pet_reviewed_v1.json`.
- Manifest mới: `data/main/reviewed_pet_source_v1/oxford_pet_reviewed.csv`.
- Audit import: `reports/stage1/v15/pet_import.json`.
- [Báo cáo và kiểm chứng](../../reports/stage1/v15/completion.md).

160 mẫu trong manifest mới có translation/QA approved **theo policy Pet
nêu trên**, không có nghĩa hai người đã xác nhận giống bằng mắt. Draft,
22 packet v2, HTML và ZIP cũ được giữ nguyên. JSON này không nạp vào trang
v2 hay import bằng `review_main.py`; nó là bằng chứng cho quy trình Pet riêng.
Nhóm không cần làm lại bốn gói `oxford_pet_01` đến `oxford_pet_04` theo A/B.
Còn 840 mẫu trong 18 gói RePOPE/VSR/TallyQA tiếp tục workflow v2.

Candidate main hiện hành vẫn trỏ đến draft cũ; chưa tự thay config main.
Khi tổng hợp final sau review, dùng manifest Pet mới và reviewed manifests
của ba task còn lại. Baseline preflight đọc lại JSON gốc, kiểm toàn bộ source
evidence và exact imported rows; proof Pet không áp dụng được cho task khác.
Evidence file hashes và implementation Pet được bind trong protocol hash.

## Lệnh kiểm và tái lập

Từ project root, sau restore private source/ảnh:

```powershell
.venv/Scripts/python.exe scripts/review_pet.py import --review data/reviews/pet_source_review_v1/oxford_pet_reviewed_v1.json --output data/main/reviewed_pet_source_v1/oxford_pet_recheck.csv --audit reports/stage1/v15/pet_recheck.json --dry-run
.venv/Scripts/python.exe reports/stage1/v15/verify_pet.py
.venv/Scripts/python.exe -m pytest -q
```

Dry-run không tạo output/audit. Muốn import thành version mới, dùng đường
dẫn mới và bỏ `--dry-run`. Không ghi đè reviewed CSV/JSON hoặc packet v2.
Muốn ghi một declaration mới phải có xác nhận thật và JSON attestation mới:

```powershell
.venv/Scripts/python.exe scripts/review_pet.py record --attestation PATH_TO_REAL_DECLARATION.json --review PATH_TO_NEW_PET_REVIEW.json
```

M1 vẫn IN_PROGRESS vì 840 mẫu còn chờ; M2 chưa final freeze, M3 NOT_RUN.
Không có GPU generation mới, freeze receipt hoặc thay đổi Option B trong
quyết định này. Ưu tiên QA còn lại → final freeze → M3 → main inference.
