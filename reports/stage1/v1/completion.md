# Stage 1 v1 — Source audit và translation/review tooling

**Ngày:** 09/11/2026 (Asia/Saigon). **Mốc nhật ký:** v3.
**Trạng thái:** hoàn thành hai hạng mục đầu của Stage 1 trên 10 mẫu hiện có.
**Stage 1 tổng thể chưa hoàn tất:** chưa có pilot 30–50 đã QA hoặc inference model.

## Kết quả thực

| Hạng mục | Bằng chứng |
|---|---|
| Source audit | 10/10 khớp category/image ID/nguyên văn câu hỏi/label với upstream |
| Upstream pinned | `YanNeu/RePOPE@bcf22e5690d587cce34e1728af3efdcfaf747d29` |
| Annotations tải về | 3 JSONL, 8.185 record, 1.002.905 bytes; không tải ảnh/weights mới |
| Dictionary | 10 đối tượng EN–VI, toàn bộ pending, không có reviewer giả |
| Draft translations | 10/10 câu match template, có VI draft và cần người review |
| Draft import | 10 requires_review, 10 pending image/label QA, 0 human approvals |
| Validation | Pilot kỹ thuật valid, 10 row / 10 unique images; không xác nhận QA người |
| Tests | 119 passed trong phiên này, gồm toàn bộ tests Stage 0; pip check sạch |
| Replay | Source audit offline thành công; import lại giữ nguyên manifest/audit |
| Stage 0 preservation | Hash manifest gốc vẫn `e72e06d2fb5a6ba486fdaf580935e428d6c8a01f73742b7ea9a91b606973a1e9` |

Đối soát nguồn chỉ chứng minh annotation agreement trên 10 mẫu, không phải
kiểm chứng cả mirror, nhãn thị giác bởi người hay bytes ảnh COCO gốc.

## Sản phẩm mới

- `configs/source_audit.yaml`: khóa upstream revision và download budget.
- `src/vlmbench/source_audit.py`: cache/checksum JSONL, kiểm tra exact match,
  báo missing/ambiguous/mismatch; không tự sửa nhãn.
- `src/vlmbench/translate.py`, `data/dictionaries/object_en_vi.csv`: exact
  template + draft dictionary; unknown/nonmatching/rejected không tự đoán.
- `src/vlmbench/reviews.py` và CLI mới: export/import review có context,
  protected fields và audit, `--dry-run`, versioned outputs.
- `data/pilot/stage1_v1/source_verified_manifest.csv`: thêm upstream provenance.
- `data/pilot/stage1_v1/draft_manifest.csv`: thêm VI draft, chưa approved.
- `data/reviews/stage1_v1/translation_review.csv` + `.context.json`:
  sheet chờ review gắn với manifest/dictionary cụ thể.
- [Preview EN–VI và ảnh](translation_preview.md), [quy trình review](../../../docs/review_workflow.md).
- [Source audit](source_audit.json), [validation](validation_report.json),
  [draft import audit](draft_import_audit.json), [verification/hashes](verification.json).

## Chính sách review/import đã triển khai

Hai reviewer có ID khác nhau cùng approved bản dịch và final_status approved
mới tạo translation_status approved. QA ảnh/nhãn là quyết định riêng có ID và
thời gian. Operator import không phải reviewer mặc định. Pending draft import
không sinh phê duyệt nào. Trạng thái rejected được lưu kể cả chưa có bản dịch.

Import kiểm tra toàn bộ sample IDs, fingerprint manifest/row, source fields,
checksum ảnh thực, status/IDs/timestamps. Không cho sửa ground truth qua sheet.
Một lỗi thì không import một phần. Audit ghi before/after, raw decisions, hashes;
đổi quyết định cần output/audit path mới. Chạy lại cùng dữ liệu giữ audit cũ.

CSV là ghi nhận quyết định tự khai, không xác thực danh tính reviewer. Nhóm
phải bảo đảm hai người đã duyệt đúng bản dịch cuối cùng. Không tự approved
dictionary hoặc dữ liệu để vượt gate; toàn bộ approval trong tests là synthetic.

## Commands verified

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m vlmbench.cli audit-source --manifest data/pilot/pilot_manifest.csv --output data/pilot/stage1_v1/source_verified_manifest.csv --report reports/stage1/v1/source_audit.json --offline
.venv/Scripts/python.exe -m vlmbench.cli export-translation-review --manifest data/pilot/stage1_v1/source_verified_manifest.csv --output data/reviews/stage1_v1/translation_review.csv --report reports/stage1/v1/translation_draft_report.json
.venv/Scripts/python.exe -m vlmbench.cli import-translation-review --manifest data/pilot/stage1_v1/source_verified_manifest.csv --review data/reviews/stage1_v1/translation_review.csv --output data/pilot/stage1_v1/draft_manifest.csv --audit reports/stage1/v1/draft_import_audit.json --operator codex
.venv/Scripts/python.exe -m vlmbench.cli validate --manifest data/pilot/stage1_v1/draft_manifest.csv
```

Cũng đã chạy `--dry-run` trước import và kiểm tra replay cùng audit. GitHub
Actions chưa được chạy từ phiên này. Không chạy model, không có metric/p-value
hoặc latency/VRAM của VLM.

## Việc còn lại / hành động kế tiếp

1. Nhóm review dictionary và 10 draft qua preview/CSV; ghi quyết định thật,
   import ra `reviewed_manifest_v2.csv` và audit v2 sau dry-run.
2. Mở rộng pilot 30–50 row theo phiên bản mới, đối soát nguồn/dịch/QA mẫu mới;
   giữ registry ảnh pilot/final. Không dùng pool cố định cho sampling main.
3. Chốt GPU/license Gemma/model revisions/precision; viết hai adapters và chạy
   ít nhất 10 row chung × EN/VI × 2 models = 40 inference; lưu kết quả pilot.
4. Proposal 2 trang theo mốc nội bộ 11/11; lịch chính thức/nhóm 5 cần xác nhận.

Chưa có blocker kỹ thuật còn lại cho hai hạng mục đã làm. Human QA là công
việc tiếp theo, không được ghi nhận thành đã hoàn tất.
