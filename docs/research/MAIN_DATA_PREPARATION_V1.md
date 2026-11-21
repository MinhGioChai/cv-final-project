# Main data preparation v1 — metadata và các quyết định còn chờ

Ngày 19/11/2026. Người dùng yêu cầu bắt đầu các việc còn lại của Stage 1.
Đã có adapters và nguồn metadata thật; chưa có main manifest chứa ảnh đã
kiểm checksum, bản dịch hoặc QA. Cấu hình đề xuất frozen=false; chưa inference.

## Nguồn và khả năng tái lập

`configs/data_sources_v1.yaml` pin commit + SHA256 của bốn nguồn đã tải.
Tổng tải mới 25.919.368 bytes gồm hai VSR test JSONL, TallyQA annotation ZIP
và Pet annotations archive; không tải photo archives. Chỉ đọc các test/list
text cần thiết từ archives, không extract đường dẫn tùy ý hoặc ảnh/masks.
Receipt và text tại `data/raw/main_metadata_v1/`; replay offline không tải.
RePOPE tái sử dụng annotations upstream đã cache/pin, không dùng pool ba
trang pilot làm frame chính.

| Dataset | Nguồn official | Snapshot |
|---|---|---|
| RePOPE | [YanNeu/RePOPE](https://github.com/YanNeu/RePOPE) | bcf22e5690d587cce34e1728af3efdcfaf747d29 |
| VSR | [cambridgeltl](https://github.com/cambridgeltl/visual-spatial-reasoning) | b27a0af0ee1462d2b6b92c8c83e869d9254a241a |
| TallyQA | [manoja328](https://github.com/manoja328/TallyQA_dataset) | 46cdc649ec79c3dcc2720ff227ad07d7ee51da6f |
| Pet | [Oxford VGG](https://www.robots.ox.ac.uk/~vgg/data/pets/) | SHA256 archive 52425fb6de5c424942b7626b428656fcbd798db970a937df61750c0f1d358e91 |

Các candidate giữ source row ID/hash, raw source fields cần thiết, split,
revision, namespace và image reference. Chưa có image_path/image_sha256 hoặc
human approval; schema riêng ngăn dùng nhầm như ManifestRow đủ điều kiện main.
Candidate frames nằm trong cache gitignored, không đóng gói như dữ liệu final.

## Inventory thực sau pilot exclusions theo namespace/image ID

| Frame | Số row | Số image references duy nhất | Target đề xuất |
|---|---:|---:|---:|
| RePOPE | 7.680 | 470 | 600 |
| VSR random/test | 2.194 | 1.873 | 120 |
| TallyQA test | 38.589 | 26.451 | 120 |
| Pet test, tám giống chó đề xuất | 799 | 799 | 160 |

RePOPE gốc có 8.185 row/500 ảnh; loại 505 câu trên đủ 30 ảnh pilot. VSR
random/test gốc 2.195 row, loại thêm một row cùng ảnh pilot. TallyQA test
snapshot này toàn Visual Genome (VG_100K và VG_100K_2), không có COCO. Dùng
VG filename stem làm image ID thực, giữ encoded source image_id riêng.
Pet official trainval/test không trùng image names. Byte-hash exclusions
giữa mọi namespace vẫn cần thực hiện sau khi tải ảnh được chọn.

[Inventory cuối](../../reports/stage1/v8/main_inventory_v2.json) giữ labels,
relations, simple/complex/count distribution và hashes. Bản inventory đầu
được giữ để truy vết, bản v2 bổ sung duplicate-content counts và source-pin checks.

## Các quyết định chưa freeze

1. **RePOPE image cap:** cap 1 chỉ có capacity 470, không thể đạt 600.
   Cap 2 với sampler/seed42 hiện có lấy được 600 row, 379 ảnh, đúng 100
   YES/100 NO mỗi category. Đây là feasibility, chưa tự áp dụng hoặc xuất
   main manifest. Sau inventory, người dùng xác nhận giữ 600 và tối đa
   2 câu/ảnh. Lựa chọn đã ghi trong `configs/main_preparation_v2.yaml`.
2. **Câu hỏi trùng giữa categories:** nguồn sau exclusions có 3.193 row
   lặp image/question/label qua các categories, không trùng trong category.
   Feasibility cap2 có 21 row lặp nội dung qua category. Cần chốt giữ các
   source-category rows hay tránh lặp nội dung toàn cục, rồi kiểm lại quota.
   Không cộng các row lặp thành ảnh độc lập hoặc tự xóa nhãn nguồn.
   Đã tạo thêm selection metadata với chính sách tránh trùng nội dung được
   đề xuất: **600 câu / 383 ảnh / 0 nội dung trùng**, vẫn 100 YES/100 NO mỗi
   category và cap2. Xem [sampling report](../../reports/stage1/v8/repope_sampling_v1.json).
   User chỉ chốt target/cap; content policy vẫn cần review trước freeze.
3. **VSR split:** đề xuất random/test; giữ riêng zeroshot để không trộn split.
   Snapshot zeroshot/test có 1.222 dòng, khác bảng README nêu 616; không
   âm thầm dùng số README thay file hoặc trộn hai variants. Nếu đổi variant,
   cần kiểm tra và ghi quyết định mới.
4. **Pet tám lớp:** đề xuất tám giống chó theo alphabetical source-name order,
   A–H: american_bulldog, american_pit_bull_terrier, basset_hound, beagle,
   boxer, chihuahua, english_cocker_spaniel, english_setter. Mỗi lớp có
   99–100 ảnh test, đủ 20/lớp. Chưa lựa chọn ảnh hoặc xem output model trên
   main. Mapping là đề xuất tám lớp, không phải benchmark 37 lớp.

Quyết định đề xuất ở `configs/main_preparation_v1.yaml`. Target 600/120/120/160
và 4.000 inference chưa thay đổi, không tự áp dụng fallback 880.

## Lệnh hiện có và phần còn lại

```powershell
# Trên máy này đã có snapshot, không cần tải lại.
.venv/Scripts/python.exe scripts/data/fetch_main_metadata.py --offline
.venv/Scripts/python.exe scripts/data/prepare_main_inventory.py
.venv/Scripts/python.exe scripts/data/select_main_repope.py
```

Sau khi chốt thiết kế: sampling có seed/quota/dedup policy, tải riêng ảnh được
chọn, kiểm hash và pilot leakage, dịch rồi review ngữ nghĩa/ảnh/nhãn thật,
main manifest và metadata/runner/freeze trước xác nhận full-run. Nguồn code
license không tự xác nhận quyền mọi ảnh. Pet archive README có research-only
note trong khi trang hiện tại nêu CC BY-SA 4.0; lưu cả hai nguồn và cần làm
rõ trước phân phối lại. Phiên này chỉ cache annotations riêng, chưa chia sẻ.
