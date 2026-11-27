# Development responsibilities của TV2

PR: **Add Kaggle main inference workflow and data validation**

Hoàn thiện Kaggle main notebook/launcher: nhận private Dataset ZIP hoặc mount đã giải nén, phát hiện path/version trùng, kiểmSHA, chỉ ghi /kaggle/working. Kiểm Internet/package installs/Secrets/GPU thật. Tái sử dụng runner+sharding TV1, không viết vòng generate riêng. Viết validationtests cófixtures và troubleshooting từ kiểm thử thật.

## File ownership

- `notebooks/main_kaggle_starter.ipynb`
- `scripts/cloud/kaggle_main.py`
- `tests/test_kaggle_main.py`
- `docs/team_inference_v1/shared/guides/KAGGLE.md`

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
