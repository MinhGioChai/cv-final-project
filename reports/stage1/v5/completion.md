# Stage 1 v5 paired evaluation và bootstrap

Ngày 16/11/2026 theo Asia/Saigon. Người dùng đã yêu cầu triển khai các bước
P0 sau audit V3. Hoàn thành phần evaluation/statistics từ raw pilot hiện có.
Stage 1 hai model và main benchmark còn các hạng mục trong kế hoạch.

## Đã triển khai và kiểm thử

- evaluate.py ghép expected EN–VI grid từ manifest và optional selection.
- Kiểm tra run identity, ảnh/hash/nhãn/task/prompt, raw parse và retry history.
- Metrics bốn task với valid/invalid/failed/missing và category breakdown.
- Primary negative-only ΔFPR trên cùng complete-case pairs, sensitivity bounds.
- statistics.py resample theo namespace/image ID và giữ các câu/cặp trong ảnh.
- CLI evaluate/statistics, versioned JSON, source checksums, immutable replay
  và Markdown summary. Parser/inference implementation cũ tiếp tục được dùng.
- 31 tests mới cần thiết cho scoring/pairing/bootstrap. Full suite thực ngày
  16/11 đạt 175 passed trong .venv. Các fixture failures đầu phiên đã sửa ở
  trạng thái translation của test data và kỳ vọng sensitivity tính tay.

Chi tiết method/commands tại [evaluation v1](../../../docs/research/EVALUATION_V1.md).

## Kết quả tính từ pilot thật đã lưu

[Evaluation JSON](qwen_evaluation.json), [bảng ngắn](qwen_evaluation.md),
[statistics JSON](qwen_statistics.json), [verification](verification.json).

| Chỉ tiêu | Kết quả |
|---|---|
| Raw nguồn | Qwen local ngày 10/11, 20 lượt trên 10 mẫu |
| Accuracy expected grid EN / VI | 100% / 90% |
| Jointly-valid paired disagreement | 1/10, tương ứng 10% |
| Invalid / failed / missing | 0 / 0 / 0 |
| Negative-only pairs và image clusters | 5 / 5 |
| FPR EN / VI | 0% / 20% |
| ΔFPR VI trừ EN | +20 điểm phần trăm |
| Percentile image-cluster CI 95% | 0 đến 60 điểm phần trăm |
| Accuracy gap VI trừ EN | −10 điểm phần trăm, empirical CI −30 đến 0 |

Bootstrap dùng 5.000 resamples, seed 42, pooled row weighting trong image
clusters. Primary CI conditional trên negative pairs cùng valid. Các lựa chọn
này do assistant chọn khi triển khai pilot theo V3 và được ghi trong method
report để nhóm rà soát cho main freeze.

Report giữ scope engineering_pilot. Mẫu thực là subset kỹ thuật nhỏ, image/
label QA còn pending. CI phản ánh empirical resampling của năm negative ảnh,
chưa có số liệu main hoặc power claim. Các task còn lại mới được kiểm bằng
toy tests, cần real data/model outputs.

## Provenance và khả năng chạy lại

Raw Qwen, manifest, pilot exclusions, annotations, hai Word và báo cáo v4 được
kiểm tra checksum ở verification. File inference ngày 10/11 có 20 records như
trước. Lệnh analysis đọc lại outputs, không phát sinh model generation trong
phiên v5. Hai raw prompt/inference code hashes vẫn khớp protocol v4.

Ba report sinh ở vòng development đầu của tác vụ này được giữ trong thư mục
development để truy vết. Các link ở trên trỏ artifact cuối dùng implementation
đã qua full suite 175 tests. CLI replay của bản cuối được kiểm tra riêng.

## Việc còn lại và hành động kế tiếp

Gemma chưa có token/env/cache trên máy ở kiểm tra 16/11. Trạng thái license
chưa được kiểm chứng. Đã hỏi người dùng trạng thái chuẩn bị quyền/token qua
câu hỏi trong phiên, vẫn cần cấu hình local/secret trước smoke test.

30 image QA còn pending. Tiếp tục review thật và chạy Gemma trên cùng subset
khi có quyền, rồi bổ sung main adapters/sampling cho VSR/TallyQA/Pet và RePOPE.
Chốt baseline metadata/protocol trước main. P1/P2 giữ ưu tiên theo V3.
