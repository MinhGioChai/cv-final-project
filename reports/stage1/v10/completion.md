# Stage 1 v10 — pilot QA đã import, main đủ ảnh và bilingual drafts

Ngày 20/11/2026 (Asia/Saigon). Người dùng đã lưu JSON review vào đúng folder
và yêu cầu kiểm tra rồi tiếp tục. Đã xử lý xong phạm vi chuẩn bị dữ liệu của
phiên này; toàn Stage 1/main benchmark vẫn IN_PROGRESS vì main human review,
baseline metadata/full runner và freeze chưa hoàn thành. Không inference mới.

## Human QA pilot — hoàn tất

Đã kiểm tra JSON `data/reviews/pilot_label_qa_v1/label_qa_reviewed_v1.json`:
đủ 30 sample IDs, context/manifest/row fingerprints đúng, ảnh khớp SHA256,
reviewer/thời gian hợp lệ và quan sát approved khớp nhãn nguồn. Dry-run rồi
import thật vào [manifest QA mới](../../../data/pilot/stage1_qa_v1/pilot_manifest.csv).
Kết quả **30 QA approved, 30 translation approved**. Không tạo thêm reviewer
hoặc thay bản dịch/EN/ground truth/ảnh. Giữ manifest và raw cũ để bảo toàn
protocol hashes và bằng chứng các run trước.

[Import audit](label_qa_import_v1.json), [validation](pilot_qa_validation.json).
Approval này là attestation thật từ file người dùng, công cụ không xác thực
danh tính độc lập; khác với synthetic tests và ảnh chỉ được PIL xác minh.

## Main — đủ 1.000 mẫu có ảnh và bản dịch nháp

Selection v9 giữ nguyên byte-for-byte, source labels và pilot exclusions giữ
nguyên. Không đổi split, quota, tám lớp Pet hay seed sau khi chọn.

| Task | Rows | Ảnh duy nhất | Tình trạng |
|---|---:|---:|---|
| RePOPE | 600 | 383 | Reuse toàn bộ image/bilingual draft v9, không tải/dịch lại |
| VSR random/test | 120 | 120 | JPEG + VI draft mới, requires_review/QA pending |
| TallyQA test | 120 | 120 | JPEG + VI draft mới, requires_review/QA pending |
| Pet tám giống test | 160 | 160 | JPEG + VI draft mới, requires_review/QA pending |
| Tổng | 1.000 | 783 | Chưa freeze, chưa main inference |

Ảnh mới 400 JPEG/55.531.311 bytes, từ các endpoint chính thức, nguyên bytes,
không re-encode. VSR dùng đúng split/filename COCO qua HTTPS S3 endpoint;
TallyQA lấy từng ảnh Stanford theo VG_100K/VG_100K_2. Pet stream gói Oxford
791.918.971 bytes, chỉ lưu 160 selected regular JPEG; đã kiểm gzip CRC,
Content-Length và ghi SHA256 toàn compressed download. Không lưu/extract
cả corpus. Pet receipt hash là observed acquisition, không phải independently
published checksum. RePOPE provider/giới hạn byte-equivalence v9 giữ nguyên.

[Source probes và correction](image_source_checks.json),
[VSR](vsr_images.json), [TallyQA](tallyqa_images.json), [Pet](pet_images.json).
TallyQA attempt đầu ngắt sau 110 cached images vì Windows WinError 5 khi
atomic replace receipt; một JPEG đã ghi nhưng chưa có receipt. Đã bổ sung
bounded retry và phục hồi ảnh 2354629 chỉ sau khi reacquire official JPEG có
SHA256 giống hệt, giữ bytes cũ. Resume hoàn tất; bytes report TallyQA chỉ là
run resume, không phải tổng mọi attempt. Không sửa ACL hoặc Windows settings.

[Direct offline replay](direct_images_offline_replay.json),
[Pet offline replay](pet_offline_replay.json): không tải thêm, manifest hashes
giữ nguyên. Kiểm tổng hợp sau hai luồng acquisition: đủ 783 image identities/
783 SHA256 khác nhau, không pilot ID/hash overlap, không thay source fields,
không technical/leakage issues. [Readiness](readiness.json) vẫn **main_ready=false**:
toàn bộ 1.000 câu requires_review, QA pending, MAIN_QA_NOT_APPROVED=1.000.

## Dịch và main review

Đã thêm 120 VSR proposals qua relation/noun glossary, 120 TallyQA câu nháp
ràng buộc hash selection/thứ tự, 160 Pet câu hỏi giống nhau và cùng mapping
A–H/label names giữa EN/VI. Tất cả requires_review. Các nghĩa mơ hồ và source
grammar lỗi có notes: into/off/over/within, trunks/ox/toppings/motors/tie dye.
Không dùng nhãn/model output để sửa câu nguồn hoặc tự approve bản dịch.
[Proposals ban đầu](task_translation_proposals.json),
[bilingual drafts đã ghép](task_translations_complete.json).

Đã xuất **22 gói × tối đa 50 câu**, phủ đúng toàn bộ 1.000 IDs, không lặp hoặc
thiếu. Mỗi gói có fixed CSV, pending JSON và HTML offline nhúng ảnh. Hai
người khác nhau review đúng cùng bản dịch cuối; QA ảnh/nhãn riêng. Sửa VI
làm mất hiệu lực approvals dịch cũ; importer kiểm source fingerprints,
timestamps, identities, observations và giữ nhãn. Không có model outputs.

**[Mở mục lục review main](main_review/index.html)** ·
[packet index](main_review/packets.json) ·
[hướng dẫn/import commands](../../../docs/research/MAIN_REVIEW_V1.md).
Chưa có main human review được nhập. Giao diện mới đã kiểm cú pháp JS và
backend tests, **chưa kiểm trực quan bằng trình duyệt**; không retry/bypass
Computer Use stop trước đó.

## Kiểm chứng và giới hạn

Full suite thực ngày 20/11: **302 passed trong 4,13 s**, .venv,
`-p no:cacheprovider`; thêm 33 tests so với v9. Bao gồm bounded streams,
gzip CRC/missing/link/duplicate members, image resume/corruption/leakage,
receipt interruption recovery, source-bound translations, hai reviewer,
stale VI approval và main packet import validation.
[Software checks](software_checks.json), [verification](verification.json).

Không thay parser/model runtime, không chạy lại pilot, không inference main,
training, cloud generation hoặc Windows configuration. Các v9 outputs/source
hashes và raw hai model trước đó giữ nguyên. Main chuẩn bị kỹ thuật xong
không có nghĩa dữ liệu đã được con người duyệt hoặc đã đủ điều kiện full-run.

## Bước tiếp theo

Người review mở mục lục main, làm từng gói, lưu và tải JSON, rồi đặt
`<packet>_reviewed.json` vào `data/reviews/main_review_v1/`. Chuyển JSON cho
người dịch thứ hai mở tiếp, không điền hộ danh tính. Assistant dry-run/import
vào version mới khi nhận file. Sau đó tổng hợp QA, xử lý rejected/uncertain,
hoàn thiện baseline metadata/runner và freeze protocol trước xác nhận full-run.
Không cần review lại 30 pilot hoặc setup/chạy lại Gemma.
