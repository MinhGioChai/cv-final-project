# Stage 1 v4 — RTX 3060 smoke test

**Ngày làm việc:** 10/11/2026 (Asia/Saigon). **Trạng thái:** Qwen đã chạy thật
thành công trên RTX 3060, 10 mẫu × EN/VI = 20 inference. Gemma chưa chạy vì thiếu
quyền truy cập/token; anonymous config HTTP 401. Chưa phải main/final benchmark.

Người dùng yêu cầu chạy RTX 3060 trước. **Đính chính lịch theo phản hồi sau đó:**
hiện khoảng 01:00 ngày 10/11, tiếp tục lúc 08:00 cùng ngày. Mốc Colab 11/11
được ghi trước đó là diễn giải lệch của assistant về “mai”, không phải lịch
người dùng đã xác nhận. Proposal nội bộ vẫn là 11/11.
Người dùng báo Colab có banner provisioning issue; không suy ra thời gian khôi phục.

## Các mốc đã hoàn tất

- Đã cài `.venv-infer` riêng, torch 2.7.1+cu126 / torchvision 0.22.1+cu126 và
  toàn bộ requirements inference đã pin; pip check sạch.
- `torch.cuda.is_available()` true; phép nhân ma trận CUDA chạy đúng trên
  RTX 3060 Laptop. Xem [cuda_smoke.json](cuda_smoke.json).
- 144 tests passed trong venv inference thực, không chỉ venv nền tảng.
- Đã tải đủ khoảng 7,51 GB tensor weights Qwen pinned revision vào
  `.cache/huggingface` trong project. Đã nạp bằng NF4/FP16 trên GPU.
- Smoke test LIMIT=2 đạt 4/4 lượt, sau đó resume lên LIMIT=10 đạt 20/20 lượt.
  Lượt mở rộng chạy offline với weights đã cache; không tải lại model.
- Không failed, không invalid, không missing, không OOM ở hai lượt thử này.
- Median processor + generation **492,13 ms/lượt**; min/max và từng lượt có
  trong raw/report. Peak allocated PyTorch **2.483,91 MiB ≈ 2,426 GiB**.
  Số đo này không phải tổng VRAM NVIDIA/WDDM và không gồm tải/load weights.
- Resume thêm lần nữa: hash JSONL không đổi, vẫn đúng 20 key sample/language
  duy nhất; không có inference trùng.
- Không có HF token trong env/cache; Gemma config anonymous trả HTTP 401.
  Xem [gemma_access_check.json](gemma_access_check.json). Không tải Gemma khi
  chưa có tài khoản/token có quyền, không tự chấp nhận license.
- Local helper mặc định cache weights trong project để lần sau dùng lại.

## Kết quả và bằng chứng

- [Báo cáo đo thực](qwen_local_report.json), [bảng 10 case](local_cases.md).
- Raw: `results/pilot/local/qwen_smoke_v1.jsonl` và `.meta.json`/`.summary.json`.
  Meta giữ plan ban đầu 2 row; summary cuối và JSONL đối chiếu đúng 10 row/20 lượt.
- Protocol hash: `223b9800b7965aaca6663a13f3b1bb9ce3019081f5cc1248d27e4463ba2077aa`.
  Đã đối chiếu khớp dry-run của bundle v3 trên local/Colab/Kaggle cho Qwen.
- Exact model/processor revision: `66285546d2b821cf421d4f5eb2576359d3770cd3`.
- [Observed packages](observed_packages.json), setup log và `qwen_smoke*.log`
  được giữ tại folder này. Logs là file cục bộ, không chứa HF token.
- Fast image processor là default thực tế của Transformers 4.57.1 trong run;
  log có cảnh báo thay đổi default. `temperature` trong model generation config
  được báo ignored vì dùng `do_sample=false`; không có lỗi generation.

Đối chiếu mô tả với nhãn nguồn trên 10 case: EN 10 khớp, VI 9 khớp, một bất
đồng. Trường hợp `000000456178`, hỏi cup/cái cốc, nguồn NO: EN NO, VI YES.
Đã xem ảnh để kiểm tra case, không tự gắn human QA approved. Không loại case
hoặc sửa nhãn theo model. Cỡ pilot nhỏ và QA ảnh/nhãn pending; không suy ra
kết luận tổng quát EN/VI, không có kiểm định/p-value ở đây.

## Chạy lại / đối chiếu Colab

```powershell
python scripts/run_local_pilot.py --model qwen --limit 10 --output results/pilot/local/qwen_smoke_v1.jsonl
```

Helper dùng cache project mặc định; cùng environment/protocol sẽ resume và
không chạy lại 20 lượt đã hoàn tất. Nếu đổi config/runtime thì dùng output path mới.

Trong phiên tiếp tục lúc 08:00 ngày 10/11, có thể mở notebook Colab. Dùng bundle mới nhất,
`MODEL="qwen"`, `LIMIT=10` để có đúng cùng 10 mẫu/20 lượt; kiểm tra protocol
hash khớp và lưu output riêng theo platform. Không hứa Colab đã khôi phục.

Gemma cần người dùng chấp nhận license và cung cấp token qua secret/env hoặc
prompt ẩn của helper local. Chưa kết luận về khả năng fit VRAM Gemma vì chưa
được tải/load. Không tự đổi sang model/mirror khác để vượt quyền truy cập.
