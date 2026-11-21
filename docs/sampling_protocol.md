# Sampling protocol — foundation

**Cập nhật 12/11/2026:** phần dưới ghi sampling kỹ thuật/lịch sử hiện có.
Main vẫn chưa freeze. Scope/mục tiêu hiện hành ở
[protocol V3](research/RESEARCH_PROTOCOL_V3.md); fallback cần nhóm quyết định,
không tự nới cap hoặc giảm target.

## Mở rộng pilot — Stage 1 v2

Config `configs/pilot_stage1_v2.yaml`, target 30 row / 30 ảnh. Lệnh
`prepare-pilot --retain-manifest data/pilot/pilot_manifest.csv` giữ toàn bộ 10
row gốc, rồi bù quota còn thiếu để tổng đạt 5 YES + 5 NO mỗi category.
Không chọn lại 30 row rồi bỏ các mẫu người dùng đã xem. Giữ nguyên ID, ảnh,
nhãn và metadata của row cũ; chỉ 20 row mới được materialize vào cache v2.
Sampling report lưu hash manifest cha và số retained/added.

Retained rows phải khớp pinned pool và tuân thủ cap/quota/exclusions; xung đột
thì dừng, không âm thầm bỏ row cũ. Registry exclusions hiện tích lũy 30 ảnh.
Pool vẫn là ba trang kỹ thuật cố định, chỉ phù hợp pilot; main cần sampling
frame riêng và không chứa bất kỳ ảnh nào từng dùng trong pilot.

## Sampling Stage 0 đã thực hiện

- Seed: `42`; 10 row RePOPE, cap cứng 1 row/image cho preflight này.
- Pool: tối đa 300 row tại ba offsets cố định trong revision đã pin.
- Sáu strata: random/popular/adversarial × yes/no.
- Với 10 row, quota lần lượt là `2/2`, `2/1`, `1/2`: tổng 5 YES, 5 NO.
- Sort nguồn theo source row ID trước khi shuffle để thứ tự đầu vào không ảnh
  hưởng kết quả. RNG cục bộ, không thay seed toàn cục.
- Chọn greedy theo strata ít ứng viên trước. Nếu không đạt quota/cap, xuất
  `sampling_feasibility_report.json` và dừng. Thuật toán không bảo đảm tìm được
  mọi nghiệm khả thi; không tự giảm quota, nới cap hay nhân bản mẫu.
- Giữ source row index, ID mẫu ổn định từ revision/category/image/question,
  checksum ảnh và báo cáo unique-image/rows-per-image.

`data/pilot/image_exclusions.json` lưu tích lũy ảnh từng dùng trong preflight/pilot.
Không xóa registry khi đổi seed hoặc tăng pilot. Final phải loại ảnh có cùng ID
trong namespace nguồn (ví dụ COCO), và loại file cùng checksum dù khác dataset.

## Giai đoạn sau, chưa thực hiện

Pilot hiện có 30 row/30 ảnh, bản dịch approved theo acceptance v3, image QA
pending; Stage 0 gốc là mẫu kỹ thuật 10 row được giữ nguyên.
Main cần lấy mẫu từ metadata đầy đủ với cap mềm được ghi log, không dùng pool
Stage 0 làm sampling frame. Mục tiêu 600/120/120/160 chỉ là kế hoạch đến khi
preflight xác nhận khả dụng. Fallback 880 cần quyết định của nhóm và lý do.

Freeze manifest, prompt/config/revision và hash trước final. Không chọn/loại mẫu
theo kết quả model. Báo cáo row count và unique-image count riêng.
