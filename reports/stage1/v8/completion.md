# Stage 1 v8 — QA packet và chuẩn bị metadata main

Ngày 19/11/2026 (Asia/Saigon). Theo yêu cầu bắt đầu các việc còn lại, hoàn
tất tooling QA ảnh/nhãn riêng, source adapters/inventory và một selection
metadata RePOPE. **QA người thật và toàn bộ Stage 1 chưa hoàn tất.**

## Bộ QA 30 mẫu sẵn sàng cho người review

[Mở trang review offline](label_qa_review.html),
[pending JSON](../../../data/reviews/pilot_label_qa_v1/review.json),
[hướng dẫn](../../../docs/review_workflow.md). 30 ảnh nhúng nguyên bytes,
EN/VI/nhãn nguồn, reviewer ID do người review tự nhập, observed answer,
status/notes và thời gian khi lưu. Không đưa model outputs vào reviewer view.
Không có nút approve hàng loạt; output ban đầu 30 pending, không reviewer ID.

Thêm export-label-qa/import-label-qa độc lập với translation workflow cũ.
Import kiểm context manifest/row, đủ IDs, checksum ảnh, reviewer/timezone,
observed answer, notes; chỉ đổi qa_status/QA metadata vào manifest/audit
version mới. Giữ question_vi/translation approved và source labels. Approved
phải khớp nhãn nguồn; nghi sai giữ pending/rejected, không sửa ground truth.
Chạy dry-run pending thật xác nhận QA pending=30, translation approved=30,
không tạo output manifest/audit hoặc human approval.

Trang có Save, JSON download/restore, local draft cache, navigation/dirty
guard và ảnh phóng lớn. JavaScript syntax pass qua Node; full workflow import
được kiểm bằng synthetic tests. **Chưa kiểm trực quan trong browser**:
Computer Use tự dừng vì không xác định chắc URL hiện tại đủ để thực thi
policy. Không retry/bypass hoặc ghi nhận visual QA thành công.

## Dữ liệu main — chỉ metadata, chưa ảnh/translation/QA

Tải 25.919.368 bytes từ official pinned sources, lưu receipts/SHA256 và kiểm
replay offline. VSR random + zeroshot test JSONL, TallyQA annotation ZIP và
Pet annotations archive; không tải photo archives hoặc chạy model. Chỉ đọc
test/list text, không extract masks/ảnh hoặc paths tùy ý. RePOPE reuse toàn
bộ 8.185 annotations upstream pin đã cache, không dùng pool pilot.

Thêm candidates.py/repope_frame.py/vsr.py/tallyqa.py/oxford_pet.py và strict
Candidate schema khác ManifestRow để không nhầm metadata với main đã QA.
[Inventory cuối](main_inventory_v2.json) và [guide](../../../docs/research/MAIN_DATA_PREPARATION_V1.md).
Inventory đầu được giữ; v2 bổ sung source-pin và duplicate-content checks.

| Sau exclusions theo namespace/image ID | Rows | Unique image refs |
|---|---:|---:|
| RePOPE | 7.680 | 470 |
| VSR random/test | 2.194 | 1.873 |
| TallyQA test | 38.589 | 26.451 |
| Pet test, tám giống chó đề xuất | 799 | 799 |

Loại đủ 30 ảnh pilot: 505 RePOPE rows và một VSR row. TallyQA test thực toàn
VG; giữ original encoded image_id nhưng dùng VG filename stem làm identity.
Pet trainval/test không trùng tên ảnh, tám lớp đề xuất có 99–100 test ảnh/lớp.
VSR zeroshot có 1.222 rows khác README 616, giữ tách biệt, không tự dùng chung.
Ảnh main chưa tải nên byte-hash leakage vẫn chờ bước materialization.

## Quyết định người dùng và RePOPE selection

Người dùng trả lời async: **Giữ 600 câu, tối đa 2 câu/ảnh (đề xuất)**. Đã ghi
target/cap xác nhận vào config main_preparation_v2.yaml, frozen=false. Cap1
không thể đạt 600 vì chỉ còn 470 ảnh. Feasibility ban đầu cap2: 600 rows/
379 ảnh, có 21 nội dung lặp giữa categories. Nguồn không có duplicate trong
category; có 3.193 row lặp image/question/label qua categories sau exclusions.

Thêm sampler metadata có global image cap và optional content uniqueness.
Selection mới: **600 câu / 383 ảnh / cap2 / 0 nội dung trùng**, seed42, đúng
100 YES/100 NO mỗi random/popular/adversarial, không đổi trường nguồn.
[Sampling report](repope_sampling_v1.json),
[candidate selection](../../../data/main/preparation_v1/repope_candidates.jsonl).
Content-dedup policy do assistant đề xuất, vẫn review trước freeze; không
diễn giải user đã chốt mọi quyết định khác. VSR variant/Pet classes vẫn là
đề xuất. Chưa chọn ảnh/materialize hoặc dịch 1.000 main rows.

## Kiểm chứng và bảo toàn

Full suite thực .venv: **241 passed trong 3,49 s**, tăng 44 tests (16 label
QA, 22 adapters, 6 sampling). Kiểm approved thật chỉ trong synthetic_test_only
fixtures tạm, không tạo QA người thật trong project. Portable bundle đã có
template HTML trong allowlist/package data và regression test.

Inventory/selection chạy lại offline giữ bytes. JS syntax pass, payload đủ
30 ảnh/pending decisions, không model outputs. Manifest pilot SHA256 vẫn
4e9d8eb2537f410f1357fdd0301b1159c0ece240b7432cf7988f947262e51fd3.
Qwen/Gemma raw, legacy/model/parser/configs và 12 artifacts v7 giữ checksum;
trong các source v7 chỉ CLI được mở rộng có chủ đích. Không inference, human
QA, sửa Windows settings hoặc freeze/P1/P2 mới trong phiên này.

## Hành động tiếp theo

Người review dùng trang QA, tải JSON và lưu vào project theo guide rồi import
vào manifest mới với ID importer thật. Sau đó chốt các quyết định main còn
mở, chọn mẫu VSR/TallyQA/Pet, materialize riêng ảnh đã chọn, kiểm hash/leakage,
dịch/QA main và baseline metadata/runner/freeze trước xác nhận full-run.
