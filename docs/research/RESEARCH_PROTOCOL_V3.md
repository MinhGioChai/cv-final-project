# Research Protocol V3

Audit 12/11, cập nhật quyết định preprocessing 24/11/2026. Tài liệu này diễn giải
[handoff V3 của người dùng](../handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md) theo code
hiện có, không phải protocol đã frozen hoặc kết quả nghiên cứu. Khi khác biệt,
ưu tiên chỉ dẫn mới của người dùng rồi V3; V4.2 là lịch sử/tham khảo.

## Scope và câu hỏi nghiên cứu

Zero-shot paired English–Vietnamese evaluation cho Qwen2.5-VL-3B-Instruct và
Gemma 3 4B IT. Không training/fine-tuning/LoRA, paid inference API hoặc tự đổi
model. Cùng ảnh, ground truth, ý nghĩa, tác vụ và output label set giữa EN/VI;
cùng cấu hình trong từng model. Báo riêng ảnh duy nhất và số câu hỏi trên ảnh.

| RQ hiện hành | Priority | Nội dung và trạng thái |
|---|---|---|
| RQ1 | P0 bắt buộc | RePOPE negative-only ΔFPR = VI − EN; paired CI theo ảnh; chưa có main metrics |
| RQ2 | P0 bắt buộc | Chênh lệch EN–VI trong từng task RePOPE/VSR/TallyQA/Pet; disagreement/invalid; chưa có full baseline |
| RQ3 | P1 có điều kiện | Paraphrase sensitivity; khoảng 40 mẫu × 2 biến thể/ngôn ngữ; chưa được triển khai/phê duyệt chạy |
| RQ4 | P1 có điều kiện | Visual evidence sensitivity; khoảng 30 cặp ảnh có/không target; chưa được triển khai/phê duyệt chạy |
| Negation riêng | P2 Future Work | Không phải tiêu chí nghiệm thu, không tự xây hoặc chạy |

Hướng chênh lệch không được giả định VI kém hơn. Không gộp các metric khác bản
chất thành một điểm chung; không dùng accuracy để xếp độ khó các dataset.
Visual evidence chỉ đo hành vi, không chứng minh cơ chế attention/training data.

## Thiết kế dữ liệu chưa freeze

| Dataset | Target | Quyết định và phần còn chờ |
|---|---:|---|
| RePOPE | 600 | 200 random/popular/adversarial; cân bằng nhãn khi khả thi; full sampling frame ngoài pool pilot |
| VSR | 120 | Random/test 60 TRUE/60 FALSE, relation diversity; main draft đã có, chưa QA |
| TallyQA | 120 | Test 60 simple/60 complex, count-bin policy; main draft đã có, chưa QA |
| Oxford-IIIT Pet | 160 | 8 giống chó ×20 đã chọn trong config; cùng mapping A–H, chưa QA; không phải benchmark 37 lớp |
| Tổng | 1.000 | Có bilingual drafts/783 ảnh; 4.000 inference chính vẫn là kế hoạch |

Ngày 19/11 người dùng chốt RePOPE 600 câu và tối đa 2 câu/ảnh sau khi loại
30 ảnh pilot. RePOPE dùng 600 câu/383 ảnh, content dedup và sáu quota 100.
Sau đó người dùng ủy quyền chọn phương án VSR/TallyQA/Pet; selection v9
được giữ nguyên, v10 đủ ảnh và EN–VI nháp cả bốn task. Config
`main_preparation_v3.yaml` vẫn frozen=false; main review, metadata/full runner
và final freeze còn chờ. [Workflow hiện tại](MAIN_REVIEW_V2.md).

Tám giống Pet và count/relation sampling được ghi trong config và selection
report trước model outputs; không suy ra phân bố tự nhiên của toàn dataset.
Baseline content/protocol vẫn cần freeze sau review. Fallback 880 là phương án từ V4.2,
không tự áp dụng. V3 yêu cầu báo cáo tính khả thi và nhóm duyệt mọi giảm mẫu/
thay model. Kế hoạch bốn tuần dùng các phase tương đối, không tự dời deadline
chính thức; ngày 06/12 trước đây chỉ là mốc nội bộ.

Giữ nguyên source labels/provenance, không loại theo output sai của model.
Main loại toàn bộ ảnh pilot theo source namespace và checksum, kể cả câu hỏi
khác trên cùng ảnh; lưu danh sách exclusion và lý do. Pool ba trang pilot
không phù hợp làm sampling frame main. Đối soát annotations không thay thế
human image/label QA hoặc xác nhận quyền phân phối lại ảnh.

## QA và schema tái sử dụng

Pilot có 30 translation approved theo acceptance người dùng; ngày 20/11 đã
import JSON human image/label QA approved 30/30 vào stage1_qa_v1 mới. Giữ
manifest lịch sử cho protocol/raw cũ. Các draft gốc 1.000 câu giữ trạng thái
requires_review/QA pending. Quy tắc chung được chốt ngày 21/11: **hai reviewer A/B, mỗi
người kiểm cả bản dịch và ảnh/nhãn**. Hai ID khác nhau cùng duyệt bản cuối và
quan sát khớp nhãn mới đủ điều kiện; một người chưa đủ. B xem JSON của A rồi
kiểm lại, không phải review mù độc lập. Sửa VI giữ lượt cũ trong history và
yêu cầu duyệt lại bản cuối. Log vấn đề/loại trừ rồi freeze. V1 giữ nguyên để
tra lịch sử, không tự chuyển một QA v1 thành hai QA. Không tạo approval thay người.

**Ngoại lệ Pet được người dùng chốt ngày 25/11/2026:** một người dùng đã
xác nhận kiểm dịch và chất lượng ảnh của 160 mẫu. Nhãn giống kế thừa official
test annotations; code kiểm mapping A–H, provenance/checksums và exclusions.
Không ghi thành hai reviewer hoặc human breed identification. Proof riêng
`pet_human_translation_image_quality_source_labels_v1` chỉ áp dụng Pet;
ba tác vụ còn lại vẫn bắt buộc A/B như trên. Xem [quy trình và JSON Pet](PET_SOURCE_REVIEW_V1.md).
160 mẫu đã import vào manifest mới; còn 840 mẫu chờ review, chưa final freeze.
Candidate draft cũ giữ nguyên trạng thái pending để bảo toàn lịch sử.

Tên trường V3 có thể được ánh xạ thay vì đổi CSV đang có:

| Trường V3 | Trường hiện tại | Hành động tối thiểu đề xuất |
|---|---|---|
| dataset | source_dataset | Document/export alias ở bản schema mới, không đổi pilot cũ |
| source_item_id | source_row_id | Giữ provenance hiện tại |
| task_type | task | Mapping giữ nguyên ý nghĩa |
| annotation_status | qa_status | Giữ trạng thái pending/approved/rejected thật |
| audit_notes | metadata và review audit/qa_notes | Chốt cột hoặc export mới có provenance, không bỏ log |
| source_split/image_id/image_path/hash | Cùng tên | Reuse validation và leakage gates |
| seed | sampling_seed | Giữ seed và phương pháp trong sampling report |

Pydantic hiện dùng extra=forbid. Không đưa tên cột V3 thẳng vào CSV cũ rồi
hy vọng parser tự nhận. Nếu cần interoperability, tạo mapping/export versioned
và kiểm thử round trip; không rename hàng loạt hoặc thay hash evidence.

## Inference và output

### Option B đã được nhóm chọn ngày 24/11/2026

Main candidate hiện hành là `configs/baseline_v3_option_b_v1.yaml`, policy
`original_rgb_processor_v1`: source JPEG → RGB giữ W×H nguồn → model processor.
Không thumbnail512, crop/pad/resize hoặc ép vuông thủ công trước processor.
Qwen giữ pixel budget200704/401408 và revisions hiện có; Gemma giữ no-pan-and-scan,
slow processor896×896, NF4/BF16. Không sửa xử lý tỷ lệ bên trong processor.

Quyết định dựa trên giữ thông tin thị giác đến processor và feasibility từ
240 RePOPE A/B cells thật, không khẳng định B Accuracy cao hơn. Pilot nhỏ/
one repeat không thay validation bốn task/M3. Gemma vẫn có áp lực VRAM cao.
Chi tiết và [commands/checklist M3](MAIN_OPTION_B_V1.md),
[evidence triển khai](../../reports/stage1/v14/completion.md).

**Chỉ policy được duyệt, chưa final freeze:** candidate vẫn frozen=false,
không có receipt; main vẫn chờ tổng hợp đủ QA (Pet theo ngoại lệ25/11). Config A/pilot/diagnostic/raw cũ
giữ nguyên; policy/settings/code hashes mới không được gán vào run lịch sử.
Preprocess và processor pins đi vào protocol/run fingerprints. Main review
HTML/JSON không thay đổi vì đã dùng ảnh gốc. Scope/RQ/gates V3 giữ nguyên.

### Contract và runtime

Ngày 22/11 đã thêm baseline contract và main runner v1 cho cả bốn task,
metadata/raw/valid/error/resume và lưới CPU 4.000 cells. Dùng configs/prompts
draft mới, không thay bytes/schema/configs pilot. Actual main execution vẫn
chặn bởi human QA v2, final config frozen và protocol-bound freeze receipt;
chưa có main GPU generation. [Contract và commands](BASELINE_V1.md),
[kiểm chứng v13](../../reports/stage1/v13/completion.md).

Runner pilot lịch sử chỉ nhận RePOPE engineering pilot 1–30 row. Qwen đã chạy thật,
runner legacy NF4/FP16 giữ hash. Gemma đã hoàn tất 10 mẫu/20 lượt NF4/BF16
ngày 19/11 qua runner riêng giới hạn 1–10 row, có raw token/logit trace và
model-declared terminal EOS handling. FP16 diagnostic xác nhận NaN/PAD,
không dùng như baseline valid. Cùng batch 1, greedy và revisions pinned;
BF16 áp dụng cho cả EN/VI Gemma, Qwen NF4/FP16 cũ giữ nguyên. Đây là pilot
settings chưa final freeze. [Gemma v7](../../reports/stage1/v7/completion.md).

Rerun cho nhóm ngày 20/11 dùng `scripts/run_pilot.py`, common limit 1–10,
configs team mới và manifest stage1_qa_v1 approved. Qwen đi qua adapter FP16,
Gemma qua adapter BF16 hiện có, không sửa runtime/parser hash lịch sử. Output
namespace team_v1 mới; notebook Colab/Kaggle đã đồng bộ launcher, chưa actual
cloud generation. Các CLI/config cũ giữ cho tái lập/diagnostic riêng.

Object existence dùng YES/NO. V3 dự kiến spatial TRUE/FALSE, trong khi prompt
cũ dùng YES/NO và parser nhận cả hai, chuẩn hóa nội bộ yes/no. Khi triển khai
VSR cần chốt external labels TRUE/FALSE và explicit mapping ground truth;
không đảo truth vì câu có phủ định, không sửa prompt pilot lịch sử. Pet dùng
mapping class IDs chung, counting số nguyên; output mơ hồ là INVALID/null.

V3 cần run_id, prompt_variant, image_variant, prompt_hash, valid, invalid_reason
và metadata tokenizer revision, quantization/dtype/device, generation config,
package versions, code_commit. Code cũ đã có raw_response, parsed_prediction,
parse_status/reason, experiment_id, protocol_hash/run_config_hash, prompt_text,
image hash, timestamps và một phần settings/runtime trong .meta.json. Baseline
v1 ngày 22/11 đã bổ sung strict record/config schemas và mapping các tên cũ,
tokenizer pins, variants, validity, dtype/device/quantization và code/env state;
metadata engineering đã có, final freeze và actual main run vẫn còn chờ.
Không bịa commit cho working tree chưa commit: ghi HEAD và dirty/source hashes.

Tách run failure, generation thành công nhưng INVALID, và missing chưa có
record. Giữ raw output/attempt history; success generation chưa chắc parse
valid. Resume chỉ chạy pending/retry đúng quy tắc, không tạo key trùng. Không
chia sẻ checkpoint giữa các config/platform/runtime không tương thích.

## Evaluation và thống kê

Ngày 16/11 đã triển khai evaluation v1 cùng hai CLI evaluate và statistics theo
yêu cầu tiếp tục của người dùng. Code/31 tests mới và phân tích Qwen pilot
ghi ở v5. Các quyết định v1 dùng all-expected accuracy, complete-case primary,
sensitivity cho unknown, row-weighted image-cluster percentile CI, B=5000 và
seed 42. Main protocol/data/metadata còn chờ freeze.
[Evaluation method](EVALUATION_V1.md), [completion v5](../../reports/stage1/v5/completion.md).

RQ1: báo n_negative, n_images, FPR EN/VI, ΔFPR theo điểm phần trăm, disagreement,
invalid/missing và CI 95%, riêng từng model. Primary ưu tiên cùng negative
rows có EN và VI đều valid như V3; không dùng hai denominator khác nhau rồi
gọi là paired. Báo số cặp loại và lý do; chốt sensitivity cho invalid/missing
trước final. Không đổi INVALID thành NO.

RQ2: RePOPE accuracy/FPR/FNR; VSR binary accuracy; TallyQA exact match và MAE;
Pet 8-way top-1/per-class accuracy; tất cả kèm paired disagreement và invalid.
Chốt accuracy tính invalid là sai, MAE chỉ valid và coverage trong final
protocol. Scoring v1 đã có code và tests. Zero valid
negatives phải báo undefined/không đủ dữ liệu, không trả FPR=0 giả.

Paired cluster bootstrap theo image_id, giữ tất cả câu và cặp EN/VI của ảnh
được resample. Cần test toy data, cố định seed/B, xử lý replicate không đủ
negative, xác định row weighting/image weighting và số cụm. Exact McNemar
theo row không xử lý clustering; V3 không đòi thêm kiểm định này. Không tự
thêm p-value, power claim hoặc formal hypothesis test khi chưa chốt phương pháp.

## Mở rộng chỉ sau gate riêng

RQ3 tham khảo: 40 mẫu × 2 model × 2 language × 2 biến thể = 320 lượt tổng;
nếu một biến thể là baseline tương đương hoàn toàn thì tái sử dụng có log,
số lượt mới có thể là 160. Không cộng lặp baseline. Cần QA ngữ nghĩa và nhóm duyệt.

RQ4 tham khảo: 30 cặp × 2 ảnh × 2 language × 2 model = 240 lượt; QA từng
ảnh/cặp và confounds bối cảnh. Cần baseline đáng tin cậy, tài nguyên, nhóm duyệt.
Không có RQ3/RQ4 vẫn có thể hoàn thành nghiên cứu chính. Negation riêng,
attention/activation analysis và model/dataset mới nằm Future Work.

Đề bài gốc Topic 14 có nêu negation trong nhóm lỗi core. V3 đặt thí nghiệm
phủ định riêng vào Future Work; đây là điểm cần nhóm giải thích giới hạn hoặc
xác nhận với giảng viên, không tự nâng negation thành P0 trái V3.

## Điều kiện chuyển sang triển khai

Ngày 12/11 hoàn thành audit và kế hoạch. Ngày 16/11 người dùng yêu cầu chạy
các bước tiếp theo, cho phép triển khai P0 evaluation/statistics từ raw pilot.
Hai phần này đã có code/test và report v5. Gemma local và pilot QA đã hoàn tất;
main adapters/sampling/ảnh/bilingual drafts đã có. Tiếp tục main human QA và
baseline metadata/full runner trước freeze và xác nhận full-run.
