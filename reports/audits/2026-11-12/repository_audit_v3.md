# Repository audit theo Codex Handoff V3

Ngày 12/11/2026, Asia/Saigon. Phạm vi đợt này: đọc V3, audit code/data/config/
tests/evidence, lập kế hoạch P0 và sắp xếp tài liệu theo yêu cầu người dùng.
Không triển khai toàn bộ đặc tả hoặc chạy model mới. V3 mục 20 yêu cầu audit/
kế hoạch trước, chờ xác nhận trước thay đổi lớn/inference quy mô lớn.

## Kết luận và thay đổi thiết kế

Foundation/ETL/QA/parser/pilot runner dùng lại được. Qwen có 20 inference thật
trên 10 row; Gemma chưa load, cloud chưa generation thật. Main sampling/data,
metrics/evaluation và image-cluster bootstrap là khoảng trống P0 quan trọng.
Chưa đủ trả lời nghiên cứu RQ1/RQ2, dù engineering pilot chạy ổn.

| V4.2 trước đây | V3 hiện hành | Xử lý trong repo |
|---|---|---|
| RQ1 ΔFPR | RQ1 chính bắt buộc | Giữ negative-only và paired image-cluster CI |
| RQ3 task-specific gaps | RQ2 chính bắt buộc | Đổi mapping trong protocol/plan mới |
| Paraphrase RQ5, 20–30 mẫu | RQ3 optional, khoảng 40 mẫu, 2 variants/ngôn ngữ | Chỉ planning, không tạo/run |
| Contrast RQ2 ưu tiên cao, 30–40 cặp | RQ4 optional, khoảng 30 cặp | Không làm gate bắt buộc của main/final |
| Negation 40 bases là core support | Thí nghiệm riêng P2 Future Work | Không triển khai mới; giữ code/schema cũ như capability lịch sử |
| Fallback 880 đã dự kiến | Quy mô chốt sau feasibility; phải báo mọi thay đổi | Không tự kích hoạt fallback |
| Lịch theo ngày cụ thể, 06/12 nội bộ | Kế hoạch tương đối bốn tuần | Không tự dời deadline hoặc ghi đã nộp |

V3 là chuỗi phiên bản mới của handoff theo proposal, không thấp hơn V4.2 vì
số “3”. Chưa thấy proposal mới ngoài file handoff V3; không khẳng định đã đọc
bản proposal mới hoặc bài đã nộp. Hai DOCX ngày 11/11 vẫn là snapshot theo V4.2.
V3 mục 14 chỉ là phân công gợi ý; giữ workstreams, không gán cá nhân theo AGENTS.

## Cấu trúc và chức năng module

```text
README.md / README_START_HERE.md       Điểm vào và đường đọc ngắn
AGENTS.md                            Quy tắc context, scope và bảo toàn evidence
docs/
  README.md                          Mục lục theo nhu cầu
  handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md  Đặc tả người dùng, nguyên văn
  research/RESEARCH_PROTOCOL_V3.md    Scope/mapping/decisions chưa freeze
  research/IMPLEMENTATION_PLAN_V3.md  Checklist, dependencies và P0
  archive/v42/                       Ba tài liệu gốc, giữ bytes
  archive/pre_v3/                    Snapshots navigation/guides/completion
  *.md                               Hướng dẫn nguồn, dịch, QA và chạy pilot
src/vlmbench/
  cli.py                             Lệnh ETL/review/validate/doctor/pilot/bundle
  schemas.py / io_utils.py            Typed contract, CSV/JSON/atomic writes
  datasets/repope.py                 Bounded ETL/caches/image materialization
  sampling.py                        Strata, seed/cap/retention/feasibility
  qa.py                              Image/checksum, QA and leakage gates
  source_audit.py                     Pinned upstream annotations comparison
  translate.py / reviews.py           Classifier drafts, bound review/import audit
  parse.py                           Full-answer parser, invalid/null
  environment.py                     Lightweight runtime/driver inventory
  pilot_runtime.py                   Two model adapters, bounded runner/resume
  portable.py                        Allowlisted private ZIP, no weights/tokens
configs/                             Pilot/model/prompt pins; main NOT_FROZEN
data/pilot|reviews|dictionaries       Versioned inputs, true QA states/exclusions
data/raw/                            Cached pilot images/metadata, gitignored
scripts/                             Setup/local/notebook/doc builders
notebooks/                           Colab and Kaggle pilot notebooks
tests/                               Existing synthetic/fixture software checks
results/pilot/local/                 Qwen JSONL/meta/summary, gitignored
reports/
  completion.md                      Latest state and append-only version history
  stage0/; stage1/v1..v4/             Original evidence/completions retained
  proposal/                          Word v1/context, sources and original V3
  audits/2026-11-12/                  This audit, receipts and verification
exports/                             Existing portable ZIP kept, pre-V3 snapshot
```

Root V4.2 filenames trở thành file chuyển tiếp; nội dung gốc ở archive.
Không đổi src/package layout, manifests, config filenames, notebook paths
hoặc result/checkpoint paths để chạy lại vẫn truy được evidence cũ.

## Thành phần tái sử dụng và trạng thái thực

| Thành phần | Bằng chứng đã có | Giới hạn audit |
|---|---|---|
| Schema/CSV | Strict types, JSON round trip, source labels và checksum | Tên trường V3 cần mapping; không nhận extra columns tùy tiện |
| RePOPE ETL | 30 ảnh; upstream 30/30 matched; bounded cache/revision | Ba metadata pages không đại diện main; chưa full mirror audit |
| Sampling | Seed 42, six strata, retain original 10 + add 20 | Greedy có thể báo infeasible dù tồn tại nghiệm; chưa main frame |
| Translation review | Classifiers 19 objects; actual user acceptance; audit | 30 translation approved, toàn bộ image QA pending |
| Leakage | Source namespace + hash, explicit pilot/exclusion registry | Main target counts/cross-dataset overlap còn phải chốt |
| Parser | YES/NO, true/false/có/không alias, integer/A–H; null invalid | Spatial output contract V3 cần chốt TRUE/FALSE mapping |
| Adapters/runner | Qwen/Gemma code; record-by-record atomic write/resume/OOM | RePOPE pilot 1–30 only; Gemma chưa chạy; chưa full-grid runner |
| Reproducibility | Hash/pins, raw+meta, same-config resume verified v4 | New fields V3, commit/dirty and tokenizer provenance thiếu |
| Tests | Lần v4 đã 144 passed trong inference venv | Không phải kết quả suite chạy hôm nay hoặc 144 model predictions |
| Reports | Hai Word đã render 2/11 trang | Scope V4.2; giữ nguyên, cần version mới nếu revise theo V3 |

## Gaps để trả lời RQ1 và RQ2

1. **Data:** full RePOPE sampling frame loại 30 pilot images; adapters VSR/
   TallyQA/Pet, source/split/revision/license, valid image mapping, frozen label
   candidates. Không tải bulk COCO/VG chỉ để giải quyết missing assets.
2. **Human QA:** reviewer decisions thật cho ảnh/nhãn và bản dịch main; preserve
   labels và exclusion reasons; không dùng acceptance ngôn ngữ thay image QA.
3. **Models:** Gemma access và actual smoke test trên cùng subset; không đủ
   thông tin kết luận fit/OOM trên RTX. Colab/Kaggle là compute options, chưa
   real end-to-end evidence và không tạo thêm statistical samples.
4. **Metrics:** chưa có evaluate.py/statistics.py hoặc CLI evaluate/statistics.
   Cần expected grid, paired join, duplicate/attempt policy, invalid/missing,
   confusion/FPR/FNR, task metrics, disagreement và output tables tái lập.
5. **Statistics:** chưa có cluster bootstrap implementation/toy tests, seed/B,
   weighting, zero-denominator behavior, CI/sensitivity policy frozen.
6. **Run contract:** bổ sung metadata/output fields V3 bằng mapping/version mới;
   không rename pilot CSV/raw cũ hoặc thay hash checkpoint.
7. **Freeze/full-run:** configs/main.yaml vẫn frozen=false/design-only; prompts
   draft; chưa full inference runner hoặc nhóm xác nhận 4.000 lượt.

## Contract khác tên và phần thực sự thiếu

Manifest V3 dataset/source_item_id/task_type/annotation_status có tương đương
source_dataset/source_row_id/task/qa_status. audit_notes nằm phân tán metadata,
review QA notes/audit; cần export/mapping rõ. Không xây schema mới chỉ để đổi
tên rồi làm hỏng strict parser hoặc provenance pilot.

Raw V3 raw_output ↔ raw_response; timestamp ↔ recorded_at_utc; config_hash ↔
protocol_hash/run_config_hash theo đúng ý nghĩa; valid/invalid_reason có thể
derive từ run_status/parse_status/parse_reason có phân biệt failure. Runtime
settings/packages có ở meta, không phải mỗi record đều thiếu mọi metadata.

Chưa explicit run_id/prompt_variant/image_variant/prompt_hash/tokenizer_revision,
device/dtype/quantization detail ở baseline contract; chưa có code_commit với
dirty hashes. Cần thiết kế versioned output, giữ raw/attempt history. Không
bịa committed SHA cho code local chưa commit. Ghi rõ trường nào ở run metadata
và trường nào per record để không nhân dữ liệu thừa mà vẫn truy vết được.

## Rủi ro và quyết định chưa chốt

- Complete-case primary đúng hướng V3 nhưng có selection bias khi invalid lệch
  ngôn ngữ; cần exclusion/coverage và sensitivity cho cả invalid và run failure.
- MAE với invalid không có giá trị số tự nhiên; báo valid MAE + coverage và chốt
  accuracy policy. Không biến INVALID thành NO/0 hoặc kết quả đúng.
- Câu nhiều trên cùng ảnh có dependence; row McNemar không thay bootstrap theo
  ảnh. V3 không yêu cầu thêm p-values; không tự tạo confirmatory claim/power.
- Binary spatial ngoài model TRUE/FALSE khác storage yes/no; cần conversion
  được test, không đổi polarity vì câu có phủ định.
- Nhãn Pet tám lớp phải chốt trước kết quả và báo đúng 8-way subset, không 37-way.
- NF4/resize/output cap ảnh hưởng diễn giải giữa models; giữ đồng nhất EN/VI
  trong từng model và báo rõ precision. Không silent fallback/CPU offload.
- Topic 14 gốc nhắc negation trong core errors, V3 loại thí nghiệm riêng khỏi
  bắt buộc. Nhóm cần giải thích giới hạn/xác nhận yêu cầu môn học; không tự
  đưa negation trở lại P0.
- Main sampling/QA có thể là chi phí lớn hơn inference; không dự báo toàn bộ
  thời gian dự án từ median latency 492 ms của mười ảnh pilot.

## Sắp xếp file đã thực hiện

- Giữ nguyên file V3 người dùng trong reports/proposal, thêm bản canonical
  đúng bytes ở docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md; receipt ghi SHA.
- Chuyển ba tài liệu V4.2 sang docs/archive/v42 với checksum bất biến; để file
  chuyển tiếp ở root. Navigation/guides cũ có bản sao trước sửa tại archive/pre_v3.
- README/START_HERE và docs/reports/proposal indexes hướng tới V3, tách current
  khỏi lịch sử; AGENTS ưu tiên V3. Protocol/plan mới nêu đúng priority và gaps.
- Guides đang hoạt động được đính chính trạng thái; báo cáo stage, hai Word,
  nguồn Word, configs/code/tests/raw và bundle ZIP cũ được giữ nguyên.
- ZIP cũ là snapshot trước V3. Khi cần cloud kèm context mới, build output path
  mới bằng package-pilot; không ghi receipt cũ như thể bundle vừa được tạo hôm nay.

Danh sách file cũ–mới và checksum:
[organization receipt](organization_receipt.json). Kiểm tra hiện tại và kết quả
smoke/links/protected hashes: [verification](verification.json).

## Kế hoạch P0 và gate cho mở rộng

[Checklist/kế hoạch](../../../docs/research/IMPLEMENTATION_PLAN_V3.md) gồm
DONE/TODO/IN_PROGRESS/BLOCKED, thứ tự evaluation contract → metrics → bootstrap
→ Gemma/QA pilot → main adapters/data → baseline metadata/freeze → full-run
sau xác nhận. Files dự kiến tạo/sửa được liệt kê ở đó, chưa tạo diagnostic code.

RQ3 chỉ xét khi baseline ổn định/frozen, paraphrases được QA, đủ tài nguyên
và nhóm duyệt. RQ4 cần main RQ1/RQ2 đủ tin cậy và verified image pairs, nguồn
lực/nhóm duyệt. Không có kết quả hai mở rộng vẫn đủ nghiệm thu main theo V3.
Tác vụ hiện tại hoàn tất audit/sắp xếp; bước triển khai cần người dùng chọn/
xác nhận theo mục 20 V3. Không chạy thêm inference để thay thế cho audit.

## Kiểm tra sau tổ chức ngày 12/11

Kết quả offline thực: 30 row/30 ảnh validate hợp lệ, vẫn 30 translation approved
và 30 image QA pending. Raw Qwen 20 records/hash không đổi. Sáu dry-run plans
(hai model × ba platform) cùng subset/protocol theo model; Qwen khớp v4.
Adapter model không được khởi tạo.

Temporary packaging smoke có handoff/protocol/plan/archive V3, checksum mọi
entry đúng; ZIP lịch sử không đổi, không tạo cloud release. 280 local links
trong 41 Markdown files hợp lệ; 118 protected files bất biến, ba nguồn V4.2
và 12 archived snapshots giữ checksum. Không chạy lại unit suite hoặc tải
weights/dữ liệu; 144 passed vẫn là số liệu lịch sử v4.
