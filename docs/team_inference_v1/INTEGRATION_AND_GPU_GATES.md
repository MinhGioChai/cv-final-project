# TV5 — hai giai đoạn và integration checklist

## Phase A — development

- [ ] Publish common base chứa WIP đã review; hiện chưa có base commit mới.
- [ ] TV1–TV4 có PR của chính mình, đúng ownership và acceptance criteria.
- [ ] CPU tests/CI/source integrity đạt; giữ QA/freeze/exclusions/parser gates.
- [ ] Bốn shard × 1.000 cells không trùng, hợp lại đủ 4.000; giữ backward compatibility
  khi dùng cả hai ngôn ngữ; resume identity có language.
- [ ] TV2/TV3 kiểm cloud setup thật: private asset mount/checksum, Secrets, Internet/package pins.
- [ ] TV4 kiểm collection: compatibility, duplicates, missing, failed, invalid; bảo toàn raw.
- [ ] So sánh protocol/source/model/implementation/generation/processor fingerprints
  được thống nhất; ghi environment và run_config_hash riêng cho từng run.
- [ ] Đối chiếu khác GPU/platform giữa EN và VI; ghi giới hạn so sánh.
- [ ] Merge PR, chốt commit 40 ký tự hex/release sạch; tất cả checkout đúng commit.
- [ ] Giữ v1 freeze/Qwen smoke lịch sử. Runtime/code hash mới cần review,
  approval và receipt v2; không sửa receipt v1 để vượt gate.

## Phase B — execution

- [ ] Release/pinned commit/manifest/protocol/model/package pins khớp.
- [ ] GPU/native BF16/VRAM/HF license và Secrets thật đạt cho role; giữ precision đã chốt.
- [ ] Smoke được phê duyệt và chạy đủ bốn task cho từng model/language;
  đếm expected/missing đúng scope shard.
- [ ] Lưu raw/error/latency/VRAM/environment và backup. Khi OOM: giữ evidence, dừng, báo nhóm.
- [ ] Có execution approval riêng cho 1.000 cells/shard; hiện chưa có.
- [ ] Nhận bốn shard riêng, validate trước collection; giữ metadata của từng run.
- [ ] Paired EN–VI evaluation theo model sau collection, dùng cùng GT/prompts/sources đã chốt.

Hiện M1 DONE, local M2 v1 DONE, Qwen smoke có 16 valid cells. Cloud/shards chưa ready.
CPU/mock tests không thay bằng chứng Phase B. RQ3/RQ4/training ngoài scope.
