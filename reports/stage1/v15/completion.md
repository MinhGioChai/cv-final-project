# Stage 1 v15 Oxford Pet QA theo nhãn nguồn

Ngày25/11/2026. Đã ghi nhận xác nhận thật của người dùng rằng đã kiểm bản dịch
và ảnh Oxford Pet, không thấy vấn đề; người dùng đồng ý kế thừa nhãn giống
từ official annotations và kiểm mapping bằng code. **Không ghi nhận human
breed identification hoặc reviewer thứ hai.** Stage1 vẫn IN_PROGRESS.

## Đầu ra

- [JSON tổng hợp160mẫu](../../../data/reviews/pet_source_review_v1/oxford_pet_reviewed_v1.json),
  [declaration gốc](../../../data/reviews/pet_source_review_v1/user_attestation.json).
- [Manifest Pet mới](../../../data/main/reviewed_pet_source_v1/oxford_pet_reviewed.csv)
  và [audit import](pet_import.json). Đã chạy dry-run rồi import thật.
- [Policy và lệnh tái lập](../../../docs/research/PET_SOURCE_REVIEW_V1.md).
- [CPU staged plan](staged_plan.json), [verification](verification.json),
  [software checks](software_checks.json), [JUnit](software_tests.xml).

160mẫu/160ảnh,20mẫu mỗi nhãnA–H. Translation và QA approved **theo policy Pet
nguồn v1**, một người xác nhận dịch/chất lượng ảnh. Annotation vẫn có thể có
sai sót; kiểm mapping/bytes không phải chuyên gia phân loại giống. Không dùng
outputs model để chọn hoặc duyệt mẫu.

## Code và quy trình

`pet_review.py` là policy riêng, chỉ nhận đúng selection Pet và archive
annotation SHA256 đã pin. Kiểm official test records/class/species/breed,
candidate mappingA–H, source hashes, JPEG/receipt và pilot exclusions. Script
`scripts/review_pet.py` record declaration thật hoặc import vào output mới;
không ghi đè packetv2. Baseline contract recheck proof/source/imported rows,
bind evidence inputs và implementation hash vào protocol. Thay đổi VI/nhãn/
ảnh/mapping/proof sẽ bị chặn; Pet policy không áp dụng được cho task khác.

30cases mới kiểm các trường hợp trên. Full suite thực **471passed/37,37s**;
targeted110passed/20,91s. Không mang441tests của v14 thành một kết quả mới.

CPU integration dùng config riêng dưới thư mục evidence, thay duy nhất đường
dẫn manifest Pet bằng bản đã import. Grid vẫn4.000cells; cellIDs/prompts
không đổi,840mẫu ba task khác còn chờ A/B. Hai execute attempts bị QA/freeze
chặn trước environment/model; không tạo predictions. Config main chính thức
vẫn byte-for-byte như trước và còn trỏ drafts1000pending. Không tự chuyển
candidate sang final hoặc tạo freeze receipt.

Đã đối soát457file Git cũ ngoài delta được phép,813JPEG nguồn,20historical raw
files,23HTML và4ZIP cũ; giữ original drafts/source labels/mainIDs và44packet
CSV/JSONv2. `verify_pet.py` tái kiểm các bằng chứng này. Bộ đếm ảnh được dedup
theo image_path để phân biệt813ảnh với1030row references trong audit.

## Gates và bước tiếp

M1 **IN_PROGRESS**:160Pet đã import, còn840RePOPE/VSR/TallyQA theo hai reviewer.
Không cần review lại4góiPet; JSON riêng không nạp trong HTMLv2 cũ. M2
**PENDING**: cần tổng hợp đủ1000IDs với reviewed manifests và chốt final
protocol/data/freeze receipt mới. M3 **NOT_RUN**: chỉ sauM1/M2 mới smoke bốn
task trênGPU. Không inference/training mới hoặc đổi OptionB/NF4/processor.
Tiếp tục mainQA → finalfreeze → M3 → maininference → RQ1/RQ2 → report/slides.
