# Development responsibilities của TV1

PR: **Add language-specific inference sharding and validation**

Thêm --language en|vi|both vào shared runner và metadata/checkpoint identity. Mỗi shard đúng1.000cells; both giữ2.000/model và fullgrid4.000. Smoke phải giữ đủbốn task khi chọn một ngôn ngữ. Resume không được trộn language/scope/fingerprint. Giữ backward compatibility, raw/invalid/error handling và QA/freeze gates.

## File ownership

- `scripts/run_main.py`
- `src/vlmbench/baseline_runtime.py`
- `src/vlmbench/baseline_contract.py`
- `scripts/team_assignment.py`
- `tests/test_main_sharding.py`

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
