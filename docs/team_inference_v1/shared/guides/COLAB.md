# Colab — TV1 và TV3

Mở `main_colab_starter.ipynb`, chọn ROLE và bật GPU qua Runtime → Change runtime type.
Đây là starter Phase A; TV3 cần hoàn thiện và kiểm chứng workflow trong PR của mình.

1. Kiểm SHA của master được TV5 gửi, giải nén vào workspace mới hoặc dùng Git clone
   chung. Đặt `BUNDLE_ROOT`/`PROJECT` đúng đường dẫn.
2. Đặt `INSTALL=True` để chạy setup đã cung cấp. Venv riêng `.venv-cloud/` được
   loại khỏi Git; không thay package pins chỉ để ép cài thành công.
3. Tạo `HF_TOKEN` trong Colab Secrets, cấp notebook access. Mỗi người dùng tài khoản
   đã chấp nhận license Gemma của mình; không dán token vào code/output.
4. Kiểm GPU thật, BF16 và VRAM. Nếu không hỗ trợ native BF16, lưu hardware evidence
   và chuyển sang môi trường BF16 được TV5 xác nhận; giữ precision đã chốt.
5. Backup raw, metadata, summary trước khi ngắt runtime. Ghi rõ nơi lưu bền vững
   và thử restore; file chỉ nằm trong VM chưa phải backup.

Colab không đảm bảo availability, loại GPU hoặc thời lượng. TV3 cần lưu evidence
setup/diagnostics/error handling thực tế. Phase B chỉ bắt đầu sau integration,
pinned release, approval/freeze và smoke được phê duyệt.

Nguồn: [Colab FAQ](https://research.google.com/colaboratory/faq.html),
[Secrets API](https://github.com/googlecolab/colabtools/blob/main/google/colab/userdata.py).
