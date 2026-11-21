# Stage 1 v9 — selection đủ 1.000 mẫu và RePOPE main draft

Ngày 19/11/2026. Tiếp tục v8, không chạy lại pilot. Người dùng giao assistant
chọn các phương án chuẩn bị phù hợp; đã ghi defaults trong config v3.
Đã hoàn tất selection metadata và RePOPE image/bilingual draft trong phiên
này. Main chưa freeze/inference, QA người thật vẫn chờ; Stage 1 còn việc.

## Selection metadata đã hoàn tất

[Sampling report](main_selection_v1.json),
[hướng dẫn/lệnh](../../../docs/research/MAIN_PREPARATION_V2.md).
Config main_preparation_v3.yaml giữ frozen=false, seed42:

| Dataset | Rows | Unique image refs | Thiết kế |
|---|---:|---:|---|
| RePOPE | 600 | 383 | Selection v8 giữ byte-for-byte, cap2, 100 mỗi category/label |
| VSR random/test | 120 | 120 | 60 TRUE/60 FALSE, đa dạng relation, cap1 |
| TallyQA test | 120 | 120 | 60 simple/60 complex, count bins có allocation policy, cap1 |
| Pet test | 160 | 160 | Tám giống đã nêu, 20/lớp A–H, cap1 |

Tổng 1.000 candidate IDs duy nhất/783 image refs, không shared IDs giữa task,
không pilot IDs. Đây chưa là byte-level leakage check cho 400 mẫu chưa ảnh.
RePOPE cũ và source fields giữ nguyên. TallyQA: bins 0/1/2/3/4–7/8+, min1
mỗi bin có dữ liệu, phần còn lại proportional largest remainder trong từng
simple/complex. VSR round-robin relation trong label. Policies ghi trước
model outputs, không coi selection như phân bố tự nhiên hoặc benchmark 37-way.

## RePOPE image materialization — hoàn tất kỹ thuật

Đã index đủ 383/383 ảnh từ MM-Hallu/RePOPE pinned revision
032906d23542254438e3bfd6ace379902b0b6847, 28 metadata pages, cùng provider pilot.
[Smoke report](repope_image_smoke.json), [source checks/corrections](image_source_checks.json).
COCO HTTPS trực tiếp lỗi hostname certificate; không tắt TLS. Nguồn ảnh có
provenance riêng, không thay label corrected upstream bằng label Viewer.
Chưa xác minh độc lập byte-equivalence với COCO gốc.

Materializer kiểm lại selection với pinned annotations, ID/hash exclusions,
JPEG readability/dimensions/SHA256, duplicate bytes, atomic cache/receipts,
resume/budget và output versioning. 429 dừng ngay giữ cache, 5xx retry có
backoff. Initial attempt thiếu page cache và gặp 429; đã sửa. Lần sau 502
giữ được sáu pages; run kế tiếp reuse và hoàn tất index. Không che các lần
thất bại hoặc cộng bytes của run cuối thành tổng download mọi attempt.

Đã xác minh đủ **383/383 JPEG**, tổng 19.484.714 bytes; tạo draft 600 rows.
Không trùng pilot theo ID hoặc SHA256. Hai ảnh smoke giữ receipt/hash nguyên
khi mở rộng. Một request tạm lỗi mạng được retry thành công, không bỏ mẫu.
[Complete image report](repope_images_complete.json),
[image draft](../../../data/main/preparation_v1/repope_draft_manifest.csv).
Offline replay không tải mới, output CSV giữ nguyên hash. Source fields
được đối chiếu lại pinned annotations, không đổi nhãn. Readable/hash-verified
images không phải human QA, không tự nâng approved.

## VI proposals

[Proposal report](repope_translation_proposals.json). Đã tạo 600 đề xuất VI,
72 object names, tất cả requires_review; không tạo approval. Giữ dictionary
pilot cũ, thêm 53 noun phrases draft trong main_object_vi_proposals_v1.json.
Risk notes cho skis/snowboard, parking meter, hot dog. Noun phrase reuse
không phải human approval cho câu main mới. Không guessing khi object/pattern
không map. Sau khi image draft có, script tạo bilingual manifest **mới**,
giữ labels và QA pending; không thay câu đã approved bằng draft.
Đã thực hiện bước ghép: [bilingual draft 600 rows](../../../data/main/preparation_v2/repope_bilingual_draft_manifest.csv),
[complete report](repope_translations_complete.json), toàn bộ requires_review.
Replay giữ bytes. [Readiness](readiness.json) xác nhận main gate vẫn chặn đủ
600 rows bằng MAIN_QA_NOT_APPROVED; không có technical/image/pilot-overlap
issue khác trong lần kiểm này. Đây không phải dataset được phê duyệt.

## Kiểm thử và scope

Full suite thực mới: **269 passed trong 7,31 s**, .venv, dùng no:cacheprovider
vì cache pytest cũ gặp ACL warning. Thêm 28 tests: 13 image acquisition,
10 task sampling, 5 VI proposal semantics. Tests không thay actual QA.
Selection/image/translation offline replay giữ bytes và RePOPE v8 giữ nguyên. Không inference,
training, Windows settings hoặc human QA mới. Browser visual QA v8 chưa
được xác nhận; phiên resume này không thử bypass Computer Use policy.

## Còn lại

Nhận JSON review pilot thật; ảnh VSR/TallyQA/Pet và VI cho 400 rows còn lại;
human QA toàn main, baseline
metadata/full runner/freeze trước xác nhận full-run. Stage 1 vẫn IN_PROGRESS.
