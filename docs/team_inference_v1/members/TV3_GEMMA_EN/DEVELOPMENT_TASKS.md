# Development responsibilities của TV3

PR: **Add Colab main inference setup and Gemma GPU checks**

Hoàn thiện Colab main notebook/setup Python-CUDA/pinned packages, Secrets và HF gated access. Reuse gpu_preflight; bổ sung diagnostics BF16/VRAM/driver/runtime và CPUmocktests cho logic mới. NativeBF16 không đạt phải dừng với evidence, không đổi Gemma sangFP16. Ghi rõ import/CUDA probe khác model load/generation.

## File ownership

- `notebooks/main_colab_starter.ipynb`
- `scripts/cloud/colab_main.py`
- `scripts/cloud/gpu_compatibility.py`
- `tests/test_colab_main.py`
- `docs/team_inference_v1/shared/guides/COLAB.md`

Một số file là đầu việc bạn cần tạo, chưa phải tính năng đã có. Không sửa core
runner của TV1, files owner khác, source labels/reviews, model pins hoặc frozen
artifacts khi chưa thống nhất với TV5/owner. Ưu tiên tái sử dụng code hiện có.

## Acceptance checklist

- [ ] Phần code/validation/docs có ích, nêu rõ vấn đề và thay đổi thực sự.
- [ ] Tests kiểm đúng/sai, mismatch hoặc recovery phù hợp với phần việc.
- [ ] Tự chạy tests phần mình và full suite; lưu kết quả, command, environment thật.
- [ ] Phân biệt CPU mocks, cloud diagnostics, model load và actual generation.
- [ ] Docs/troubleshooting phản ánh việc đã kiểm, notebook đã clear outputs.
- [ ] Tự commit bằng identity của mình, push branch riêng và tạo PR để review.
- [ ] Không chạy shard trước khi có common release, freeze v2 và execution approval.

Nếu phần code đã đáp ứng, bạn có thể đóng góp kiểm chứng thật, regression tests
hoặc báo cáo thực nghiệm có evidence; không viết lại component để tạo commit.
