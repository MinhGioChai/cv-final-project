# Main preparation v2 — selection, ảnh RePOPE và VI draft

Cập nhật 19/11/2026. Người dùng giao assistant chọn phương án chuẩn bị phù
hợp sau khi đã xác nhận RePOPE 600 câu/cap2. Các lựa chọn dưới đây dùng cho
preparation, **không phải baseline freeze hoặc phê duyệt 4.000 inference**.

## Selection metadata đủ 1.000 row

Config `configs/main_preparation_v3.yaml`, seed42, frozen=false:

| Dataset | Rows | Image references | Chính sách |
|---|---:|---:|---|
| RePOPE | 600 | 383 | Giữ nguyên selection v8, sáu quota 100, cap2, tránh trùng nội dung |
| VSR random/test | 120 | 120 | 60 TRUE/60 FALSE; round-robin đa dạng relation trong từng label; cap1 |
| TallyQA test | 120 | 120 | 60 simple/60 complex; count-bin allocation, cap1 |
| Oxford-IIIT Pet test | 160 | 160 | Tám giống đã nêu, 20/lớp A–H, cap1 |

TallyQA bins cố định 0/1/2/3/4–7/8+, tối thiểu một mẫu ở mỗi bin có dữ liệu,
rồi phân bổ số còn lại theo tần suất nguồn bằng largest remainder. Đây là
thiết kế phân tầng, không đại diện nguyên phân bố tự nhiên. VSR ưu tiên độ
phủ relation thay vì giữ nguyên tần suất nguồn. Ghi policies trước inference,
không điều chỉnh theo kết quả model. Không tự giảm target khi quota bất khả thi.

Selection nằm trong `data/main/preparation_v2/`, file tổng all_candidates.jsonl.
RePOPE được copy byte-for-byte từ v8; các task khác giữ nguyên trường nguồn,
source row hash và class map. Tổng 783 image references, không shared IDs
giữa task trong selection hiện tại; điều này chưa chứng minh không trùng
ảnh qua re-encoding. Byte-hash gate vẫn cần khi materialize từng dataset.
[Sampling report](../../reports/stage1/v9/main_selection_v1.json).

## Ảnh RePOPE

Nguồn COCO HTTPS trực tiếp lỗi hostname certificate ở kiểm tra phiên này.
Materializer dùng **MM-Hallu/RePOPE revision
032906d23542254438e3bfd6ace379902b0b6847**, cùng provider pilot, ghép bằng
COCO image ID từ annotations corrected upstream. Không tắt xác minh TLS,
không lấy nhãn từ Viewer để thay nhãn upstream.

Index kiểm Hub HEAD trước/sau và revision trong mọi asset URL. Page cache
có hash, retry backoff cho 5xx; HTTP429 dừng ngay và giữ progress để resume.
Không tự đổi pin hoặc tăng budget. Signed URLs chỉ ở cache gitignored;
report chỉ lưu asset path. Bytes JPEG giữ nguyên, PIL verify/load, SHA256,
geometry, pilot namespace/ID + byte-hash exclusions và kiểm duplicate bytes
giữa các image IDs. Cùng ảnh dùng cho nhiều câu chỉ tải một lần.
API dùng [Viewer rows](https://huggingface.co/docs/dataset-viewer/rows);
HTTP429 là rate-limit response theo [HF docs](https://huggingface.co/docs/hub/rate-limits).
Các lần lỗi/điều chỉnh acquisition được ghi tại
[source checks](../../reports/stage1/v9/image_source_checks.json).

Cache `data/raw/main_images_v1/repope/` có index/page receipts và ảnh. Chỉ
ghi `data/main/preparation_v1/repope_draft_manifest.csv` khi đủ 383 ảnh cho
600 rows, source rows đối chiếu lại pinned annotations. Draft có
is_pilot=false, qa_status=pending, translation_status=missing. Đọc được ảnh
và source match **không phải human image QA**. Byte-equivalence với COCO gốc
chưa được kiểm chứng độc lập, cần nêu rõ provider trong report cuối.

```powershell
# Smoke trên máy mới; mặc định chỉ tải tối đa hai ảnh mới trong queue.
.venv/Scripts/python.exe scripts/data/prepare_repope_images.py --limit-images 2
# Tiếp tục cùng cache tới đủ ảnh. Budget 200 MiB/run; không model inference.
.venv/Scripts/python.exe scripts/data/prepare_repope_images.py --limit-images 383
# Replay khi cache đầy đủ; không tải mạng.
.venv/Scripts/python.exe scripts/data/prepare_repope_images.py --limit-images 383 --offline
```

Nếu asset URL hết hạn và còn thiếu ảnh, --refresh-index lấy lại index cùng
revision; giữ ảnh đã có và xác minh receipt. Nếu pin/selection đổi, dùng
cache/output version mới, không ghi đè lịch sử. Không tắt kiểm checksum.

## Draft VI cho 600 câu RePOPE

Giữ nguyên dictionary CSV pilot; thêm 53 noun phrases đề xuất trong
`data/dictionaries/main_object_vi_proposals_v1.json`. Tổng phủ 72 object names
được chọn. Tái sử dụng từ chỉ loại/phrase của dictionary hiện có, không coi
approval từ vựng/pilot là approval cho câu main mới. Các đề xuất đều
requires_review; unknown object/pattern giữ missing, không đoán nhãn/dịch.
Skis/snowboard, parking meter, hot dog có ghi chú cần review ngữ nghĩa.

```powershell
.venv/Scripts/python.exe scripts/data/prepare_repope_translations.py
```

Luôn tạo VI proposals JSON. Khi image draft đã có, tạo **file mới**
`data/main/preparation_v2/repope_bilingual_draft_manifest.csv`, giữ source
labels/hashes/QA, đặt translation_status=requires_review, không chạm manifest
pilot. Không thay câu đã approved bằng draft mới. Output khác bytes cần path
version mới. Đây là bản nháp do assistant tạo, cần review thật trước freeze.

## Phần tiếp theo

QA pilot 30 mẫu vẫn chờ JSON quyết định thật qua
[workflow](../review_workflow.md). Main còn cần ảnh VSR/TallyQA/Pet, bản dịch
400 mẫu còn lại và QA toàn bộ ảnh/nhãn/EN–VI, metadata baseline/full runner,
freeze rồi xác nhận full-run. Chưa có main inference hoặc kết quả RQ1/RQ2 final.
