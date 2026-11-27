# Development responsibilities của TV4

PR: **Add inference checkpoint recovery and shard result validation**

Bổ sung export/backup và collection/shard validation còn thiếu; reuse atomiccheckpoint/resume hiện có. Kiểm duplicate/missing/invalid/failed, đúng language/model/IDs/source/protocol/implementation. Không yêu cầu run_config_hash hoặc GPU/environment của bốn shard giống nhau một cách máy móc; so các invariant đã chốt và giữ per-run provenance. Test restore/checkpoint bịcắt/corrupt/mismatched, không sửa core runner củaTV1.

## File ownership

- `scripts/export_main_results.py`
- `scripts/collect_main_shards.py`
- `tests/test_main_collection.py`
- `docs/team_inference_v1/shared/guides/RECOVERY.md`

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
