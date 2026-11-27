# Hướng dẫn thực nghiệm — bắt đầu tại đây

Cập nhật 27/11/2026. Thư mục này chứa **bốn gói hướng dẫn cá nhân có thể công khai**.
Master chứa ảnh được trưởng nhóm gửi riêng; không nằm trên GitHub.

| Role | Model/ngôn ngữ | Platform dự kiến | Tải gói cá nhân | Đọc trực tiếp |
|---|---|---|---|---|
| TV1 | Qwen EN | Colab | [TV1_QWEN_EN_Package.zip](TV1_QWEN_EN_Package.zip) | [RUN_GUIDE](../docs/team_inference_v1/members/TV1_QWEN_EN/RUN_GUIDE.md) |
| TV2 | Qwen VI | Kaggle | [TV2_QWEN_VI_Package.zip](TV2_QWEN_VI_Package.zip) | [RUN_GUIDE](../docs/team_inference_v1/members/TV2_QWEN_VI/RUN_GUIDE.md) |
| TV3 | Gemma EN | Colab | [TV3_GEMMA_EN_Package.zip](TV3_GEMMA_EN_Package.zip) | [RUN_GUIDE](../docs/team_inference_v1/members/TV3_GEMMA_EN/RUN_GUIDE.md) |
| TV4 | Gemma VI | Kaggle nếu native BF16 đạt, hoặc môi trường BF16 được xác nhận | [TV4_GEMMA_VI_Package.zip](TV4_GEMMA_VI_Package.zip) | [RUN_GUIDE](../docs/team_inference_v1/members/TV4_GEMMA_VI/RUN_GUIDE.md) |

TV5 review và tích hợp. Mỗi TV1–TV4 tự làm phần việc thực tế, tự kiểm thử,
commit bằng identity của mình, push branch riêng và mở PR.
Xem [phân công](../docs/team_inference_v1/TEAM_ASSIGNMENTS.md),
[file ownership](../docs/team_inference_v1/FILE_OWNERSHIP.md) và
[Git/GitHub từ đầu](../docs/team_inference_v1/github/GITHUB_FOR_BEGINNERS.md).

## Nhận master và bắt đầu

1. Tải gói cá nhân của mình. Trên trang file GitHub chọn **Download raw** để tải ZIP.
2. Liên hệ TV5 để nhận `VLM_ENVI_Main_Inference_Team_v1.zip` qua kênh nội bộ.
   Link tải riêng chưa được cung cấp; không có link Drive giả hoặc link public thay thế.
3. Kiểm SHA256 theo [SHA256SUMS.txt](SHA256SUMS.txt) hoặc [packages.json](packages.json).
   Master SHA256 phải đúng:
   `29f7b3326df239df1f2bea8286ea38c4cd12ed11f0438cae861b3b998d0689f5`.
4. Giải nén master vào thư mục mới; mở `START_HERE.md`, sau đó
   `members/<role>/START_TVx.md` và `RUN_GUIDE.md`.
5. Master dùng chung source/assets; ZIP cá nhân chỉ có hướng dẫn/config và
   `SHARED_BUNDLE_REF.json`. Không cần bốn bản source độc lập.

Ví dụ kiểm hash trên Windows:

```powershell
Get-FileHash .\VLM_ENVI_Main_Inference_Team_v1.zip -Algorithm SHA256
Get-FileHash .\TV1_QWEN_EN_Package.zip -Algorithm SHA256
```

Master trên máy trưởng nhóm vẫn ở `exports/VLM_ENVI_Main_Inference_Team_v1.zip`.
Bốn ZIP cá nhân đã chuyển từ `exports/` sang thư mục này, giữ nguyên bytes/hash.
Đường dẫn cũ trong receipts v24 là lịch sử lúc build; `packages.json` ghi vị trí mới.

## Phạm vi hiện tại và điều kiện chạy

Đây là **Phase A — development**, chưa phải release cho phép chạy main.
Hạ tầng đã chuẩn bị gồm guides, configs, assignment planning, asset verification
và hai notebook starter. TV1 còn làm language sharding; TV2/TV3 hoàn thiện và kiểm
cloud setup; TV4 hoàn thiện export/collection/recovery. Đợt publish này không
đưa các adjudication/freeze inputs đang local lên GitHub. Common base đầy đủ
để chạy dữ liệu đã duyệt vẫn cần TV5 tích hợp/publish riêng.

Private master là source snapshot đã kiểm lúc đóng gói, không có `.git` và chưa
phải pinned GitHub release. Dùng riêng để đọc/diagnostics. Đọc RUN_GUIDE trước
khi clone; không copy toàn bộ source snapshot vào clone rồi nhận là code mình viết.
Lệnh `--language` và các tests/final configs được đánh dấu tương lai trong hướng
dẫn là phần cần phát triển, không phải tính năng đã có.

**Phase B:** sau PR integration, cả nhóm checkout cùng commit/release, chốt
implementation/protocol mới nếu fingerprint thay đổi, nhận phê duyệt và chạy
GPU smoke trước shard inference. Cloud GPU/HF Secrets/native BF16/backup vẫn
cần kiểm trên tài khoản thật. M1 đã đạt, local M2 v1 đã chốt; M3 mới có Qwen
smoke 16 cells. Gemma main smoke và full main chưa chạy.

Giữ master, ảnh, tokens, weights, venv/cache và raw main outputs ngoài Git.
Chỉ bốn ZIP nhỏ trong thư mục này là gói hướng dẫn công khai đã được kiểm tra.
