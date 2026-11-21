# Data sources và provenance

**Scope hiện hành 12/11/2026:** [protocol V3](research/RESEARCH_PROTOCOL_V3.md).
Trang này ghi acquisition/audit kỹ thuật và lịch sử, không có model metrics.
Main của bốn dataset chưa được thu thập/freeze đầy đủ.

**Cập nhật Stage 1 v2:** pilot đã mở rộng 30 mẫu và 30/30 khớp upstream;
[báo cáo mới nhất](../reports/stage1/v2/source_audit.json). Phần Stage 0/v1
bên dưới giữ thông tin acquisition và mốc kiểm tra trước đó.

Ngày kiểm tra: 09/11/2026. Nguồn và số liệu ở đây mô tả dữ liệu, **không phải
kết quả đánh giá VLM**.

## RePOPE

- Mirror dùng để preflight: https://huggingface.co/datasets/MM-Hallu/RePOPE
- Revision khóa: `032906d23542254438e3bfd6ace379902b0b6847`.
- Split: `train` do mirror cung cấp. Tên split này không có nghĩa nhóm huấn luyện model.
- Dataset card/API: ảnh, `image_id`, `question`, `answer`, `category`;
  card ghi 8.185 câu hỏi, viewer có 500 giá trị image ID.
- Ground truth lấy nguyên văn `answer` của mirror; không dùng output model để sửa nhãn.
- Upstream annotation: https://github.com/YanNeu/RePOPE
- Citation upstream: Yannic Neuhaus và Matthias Hein (2025),
  *RePOPE: Impact of Annotation Errors on the POPE Benchmark*, arXiv:2504.15707.
- Card của mirror khai báo MIT. Điều này không tự xác nhận quyền phân phối lại
  từng ảnh MS COCO; giữ ảnh trong `data/raw/` đã gitignore.
- **Đã đối soát 10/10 mẫu hiện có với annotations upstream** ở commit
  `bcf22e5690d587cce34e1728af3efdcfaf747d29`: khớp category/image ID/nguyên văn
  câu hỏi/nhãn. Xem [source audit](../reports/stage1/v1/source_audit.json).
  Ba file upstream có tổng 8.185 records, tải khoảng 1,00 MB annotations.
  Chưa đối soát toàn bộ mirror; mọi mẫu mới cần được audit trước khi freeze.

## Cách tải nhỏ và provenance

Dataset Viewer API: https://huggingface.co/docs/dataset-viewer/rows

Stage 0 đọc tối đa 100 row/trang tại offsets `0, 3000, 6000`, rồi chọn 10 row.
Đây là pool cố định có chủ đích để thử ETL, **không phải mẫu ngẫu nhiên từ toàn bộ
8.185 row**. Phân tầng chỉ thực hiện trong pool này.

Endpoint `/filter` trả HTTP 500 lặp lại trong phiên kiểm tra; adapter hiện dùng
`/rows`. Không tự tải Parquet toàn bộ hoặc COCO/VG để bù lỗi dịch vụ.

Dataset Viewer không cung cấp pin revision cũ như URL Hub `resolve/<hash>`.
Adapter vì vậy kiểm tra Hub HEAD trước/sau thu thập và hash revision trong
đường dẫn mọi image asset. Nếu revision không khớp, dừng; không tự cập nhật config.
Snapshot metadata và checksum được lưu để chạy offline đúng snapshot.

Ảnh tải từ cached assets của Viewer và được lưu nguyên bytes, có SHA-256, kích
thước và định dạng ảnh đọc thực tế. Chưa xác minh byte-equivalence với COCO gốc;
cần chốt chính sách ảnh/preprocessing cho final ở giai đoạn sau.
URL ký tạm chỉ nằm trong cache bị gitignore; report không chứa query/signature.

## Upstream audit — Stage 1 v1

Config: `configs/source_audit.yaml`. Chỉ tải ba JSONL tại đường dẫn commit cụ
thể, với giới hạn 5 MiB. Lưu SHA-256 từng file và receipt; replay offline kiểm
tra checksum. Join bằng category + image ID lấy từ tên file COCO + nguyên văn
câu hỏi, rồi đối chiếu label. Thiếu/duplicate/mismatch được báo rõ; không tự
sửa nhãn nguồn hoặc xuất manifest verified khi có bất kỳ mismatch nào.

Manifest verified bổ sung provenance vào metadata; `qa_status` vẫn pending.
Đối soát annotations không xác nhận tính đúng thị giác của nhãn hoặc ảnh-byte
equivalence với COCO gốc. Không suy diễn license upstream từ MIT trên mirror.

## Main metadata đã triển khai ngày 19/11

Adapters và snapshots thật đã có tại v8. [Data preparation guide](research/MAIN_DATA_PREPARATION_V1.md)
ghi revisions/SHA256, inventory sau pilot exclusions, Pet class map đề xuất
và RePOPE600/cap2 được người dùng xác nhận. Candidate metadata không phải
main manifest có ảnh/dịch/QA; chưa tải photo archives hoặc chạy main.

## Nguồn và phần còn chờ trước main

| Dataset | Nguồn chính | Cần xác minh trước main |
|---|---|---|
| VSR | https://github.com/cambridgeltl/visual-spatial-reasoning | Một test split, revision/license, mapping ảnh COCO |
| TallyQA | https://github.com/manoja328/TallyQA_dataset | Test JSON, simple/complex, ảnh COCO/VG, license |
| Oxford-IIIT Pet | https://www.robots.ox.ac.uk/~vgg/data/pets/ | Test split, 8 giống chó, candidate IDs, license |

Stage 0 chưa tải ba nguồn này là trạng thái lịch sử. V8 đã tải/parse metadata
thật và kiểm schema; split/classes vẫn là đề xuất trước freeze. Ảnh nguồn/
hashes, translations và human QA cần thực hiện ở các bước tiếp theo.
