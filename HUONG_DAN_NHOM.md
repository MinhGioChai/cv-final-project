# Hướng dẫn tổng hợp — hiểu project và tham gia cùng nhóm

**Cập nhật 22/11/2026.** Đây là điểm bắt đầu cho thành viên mới: mục tiêu,
trạng thái, cài đặt, dữ liệu, review, chạy pilot và đưa thay đổi lên GitHub.
Các link cuối file dùng để tra sâu khi cần. Trạng thái sống nằm trong
[completion](reports/completion.md); khi số liệu tiến độ thay đổi, ưu tiên file đó.

**Đọc nhanh:** mục 1–3 giải thích nghiên cứu và kế hoạch; mục 4–7 hướng dẫn
làm việc; mục 8 là commit/push từng phần và branch/PR. Code nền tảng, dữ liệu,
evaluation, pilot và review đã được push thành các commit riêng ngày 21/11.
Mốc cộng tác hiện tại là **bàn giao ZIP và kiểm duyệt main**. Xem
[nhật ký công bố](reports/releases/2026-11-21/README.md) để đối chiếu từng commit.

## 1. Project đang nghiên cứu điều gì?

Đề tài đánh giá mô hình thị giác–ngôn ngữ (VLM): khi giữ nguyên **ảnh, ý nghĩa
câu hỏi và nhãn đúng**, đổi câu hỏi giữa tiếng Anh và tiếng Việt thì đáp án
thay đổi như thế nào?

Ví dụ một cặp câu hỏi cho cùng ảnh: “Is there a bowl in the image?” và
“Trong ảnh có cái bát nào không?”. Hai ngôn ngữ phải hỏi đúng cùng một điều.
Không đổi nhãn để khớp câu trả lời của model.

Hai model là **Qwen2.5-VL-3B-Instruct** và **Gemma 3 4B IT**. Chúng ta chạy
zero-shot evaluation, không training/fine-tuning/LoRA.

### 1.1 Mục đích và giá trị của nghiên cứu

Mục đích là đo xem một VLM có giữ ổn định khả năng dựa vào ảnh khi người dùng
đổi từ tiếng Anh sang tiếng Việt hay không. Một mô hình có thể hiểu ảnh nhưng
trả lời khác khi thay ngôn ngữ, cách hiểu câu hỏi hoặc cách xuất đáp án.
Benchmark cần tách các yếu tố đó bằng những cặp câu hỏi tương đương và điều
kiện inference được kiểm soát.

Đề tài hướng đến ba sản phẩm cụ thể:

1. Một tập đánh giá EN–VI có nguồn gốc rõ, bản dịch/ảnh/nhãn được kiểm tra,
   tách biệt pilot và main để có thể dùng lại.
2. Một pipeline có thể chạy lại và truy vết từ metrics về raw output, model
   revision, cấu hình, câu hỏi và đúng bytes của ảnh.
3. Kết quả cho biết chênh lệch nằm ở đâu, lớn đến mức nào và bất định ra sao,
   kèm phân tích trường hợp sai và giới hạn của thiết kế.

Kết quả không phát hiện khác biệt rõ ràng vẫn có giá trị. Thí nghiệm không
nhằm chứng minh tiếng Việt yếu hơn, xếp hạng tổng quát hai model hoặc kết
luận nguyên nhân bên trong model từ vài trường hợp quan sát được.

### 1.2 Nội dung nghiên cứu theo từng RQ

| Câu hỏi nghiên cứu | Mức ưu tiên | Đầu ra cần có |
|---|---|---|
| RQ1: object hallucination có khác giữa EN–VI? | Core P0 | RePOPE negative-only FPR và ΔFPR = VI − EN, CI theo cụm ảnh |
| RQ2: khoảng cách EN–VI thay đổi theo tác vụ? | Core P0 | Metrics riêng RePOPE/VSR/TallyQA/Pet, disagreement và invalid/missing |
| RQ3: nhạy với cách diễn đạt? | P1 có điều kiện | Paraphrases tương đương đã QA, chạy/phân tích sau quyết định riêng |
| RQ4: nhạy với bằng chứng thị giác? | P1 có điều kiện | Cặp ảnh có/không vật thể đã xác minh, chạy/phân tích sau quyết định riêng |

**RQ1 — Object hallucination:** với những câu RePOPE có nhãn NO, model trả
lời YES dù vật thể không có trong ảnh bao nhiêu lần? Tính FPR cho EN và VI
trên các cặp hợp lệ tương ứng, rồi ΔFPR = FPR(VI) − FPR(EN), riêng từng model.
Giá trị dương nghĩa là VI có FPR cao hơn trên subset đó; giá trị âm là chiều
ngược lại. Phải đi kèm số mẫu/ảnh và khoảng tin cậy, không chỉ một con số.

**RQ2 — Khác biệt giữa tác vụ:** xem khoảng cách EN–VI trong nhận biết có/không
vật thể, quan hệ không gian, đếm và phân loại giống chó. Báo accuracy hoặc
exact match/MAE phù hợp từng task, mức bất đồng EN–VI, INVALID và MISSING.
Không dùng accuracy của bốn dataset để kết luận task nào vốn khó hơn.

**RQ3 — Paraphrase, nếu được triển khai:** giữ cùng ảnh/nhãn/ý nghĩa nhưng
thay cách diễn đạt trong mỗi ngôn ngữ để xem đáp án có ổn định không.
Thiết kế tham khảo 40 mẫu ×2 variants/ngôn ngữ ×2 ngôn ngữ ×2 model =320
lượt tổng; baseline tương đương có thể tái sử dụng có log, không đếm lặp.

**RQ4 — Visual evidence, nếu được triển khai:** dùng khoảng 30 cặp ảnh có/
không vật thể mục tiêu, câu hỏi giữ nguyên để xem model đổi đáp án đúng
hướng không. Thiết kế tham khảo 30 cặp ×2 ảnh ×2 ngôn ngữ ×2 model =240
lượt. Chất lượng từng cặp và khác biệt bối cảnh cần được kiểm tra; kết quả
là hành vi quan sát được, không phải bằng chứng nhân quả về cơ chế bên trong.

Không mặc định tiếng Việt kém hơn. Không gộp các metric khác bản chất thành
một điểm chung hoặc coi chênh lệch nhỏ là kết luận chắc chắn. RQ3/RQ4 hiện
chưa triển khai; công việc ưu tiên là hoàn thành RQ1/RQ2.

### 1.3 Dữ liệu, thiết kế đối chứng và cách đo

| Dataset | Nội dung cần kiểm | Main rows / ảnh | Metric chính |
|---|---|---:|---|
| RePOPE | Vật thể có xuất hiện trong ảnh không; 3 category random/popular/adversarial | 600 /383 | FPR, ΔFPR; accuracy/FNR/disagreement/invalid |
| VSR random/test | Phát biểu quan hệ không gian đúng hay sai | 120 /120 | Binary accuracy, disagreement, invalid |
| TallyQA test | Đếm đúng vật thể theo điều kiện câu hỏi; 60 simple/60 complex | 120 /120 | Exact match, MAE và coverage, disagreement/invalid |
| Oxford-IIIT Pet test | Phân loại tập con 8 giống chó, 20 ảnh/giống | 160 /160 | 8-way accuracy, theo lớp, disagreement/invalid |
| Tổng | Mỗi row có EN và VI, hai model | 1.000 /783 | Báo riêng theo model/task |

Pet là thí nghiệm tập con tám lớp, không phải benchmark 37 lớp chuẩn. RePOPE
cho tối đa hai câu/ảnh nên số câu khác số ảnh. Các ảnh pilot được loại khỏi
main theo source ID và SHA256; không thêm câu khác của cùng ảnh pilot vào main.

Trong mỗi cặp EN–VI, giữ cùng ảnh, ground truth, ý nghĩa, task, output labels,
model/processor revision, preprocessing và generation settings. Khác precision
giữa hai model phải ghi nhận; trong cùng model không đổi precision giữa EN/VI.
Prompt và bản dịch cần tự nhiên nhưng không được thêm gợi ý hoặc làm mất điều
kiện lọc, số lượng, quan hệ hay phủ định của câu nguồn.

Vì nhiều câu có thể dùng cùng ảnh, bootstrap lấy mẫu theo **cụm ảnh**, giữ
cặp EN–VI cùng nhau. Phân tích chính RQ1 dùng các negative pairs hợp lệ ở cả
hai ngôn ngữ; đồng thời báo số cặp bị loại, invalid/missing và sensitivity để
tránh che giấu coverage thấp. INVALID không được chuyển thành NO. Quy tắc
metrics/CI phải được chốt trước khi xem kết quả main.

### 1.4 Điều kiện để nói nghiên cứu đã hoàn tất

Phần core hoàn thành khi main data được duyệt và có provenance, baseline
được chốt, các run được phê duyệt đã chạy với raw/metadata đầy đủ, RQ1/RQ2 có
metrics và CI/coverage đúng, cùng report phân tích được tái lập. Có code hoặc
có đủ ảnh chưa đạt mốc này. RQ3/RQ4 có gate riêng và không phải điều kiện bắt
buộc để nghiệm thu core theo V3.

## 2. Hiện đã có gì, còn làm gì?

### 2.1 Ảnh chụp tiến độ tại ngày 22/11/2026

| Hạng mục | Đã có | Còn thiếu |
|---|---|---|
| Pilot | Mỗi model 10 ảnh × EN/VI =20 lượt thật valid; pilot QA approved 30/30 | Rerun khi có nhu cầu kiểm tra, không bắt buộc làm lại |
| Main data | 1.000 câu EN–VI nháp/783 ảnh, source và leakage checks | Human review toàn main, xử lý uncertain/rejected |
| Software | Parser, review/import, pilot runner, metrics/CI; baseline metadata và runner bốn task v1 có CPU tests | Final review/freeze, kiểm main GPU smoke và inference thật |
| Thực nghiệm chính | Chưa chạy | Sau gates và xác nhận: 1.000 ×2 ngôn ngữ ×2 model =4.000 lượt |
| Báo cáo | Proposal/context Word v1 và evidence pilot | Results–Discussion/report/slides theo V3 sau main |

Main **chưa frozen**. Có ảnh/câu dịch hoặc tests pass không đồng nghĩa dữ liệu
đã được con người duyệt. Kết quả pilot nhỏ chưa đủ để kết luận language gap.
Cloud notebooks đã cập nhật code, chưa có real Colab/Kaggle generation được xác minh.

Các con số trên có các mức bằng chứng khác nhau: 20 lượt/model là inference
thật đã có; QA pilot 30 là quyết định người thật đã import; main 1.000 là
draft đã kiểm kỹ thuật, chưa có human approval. Lần kiểm thử software gần
nhất được ghi ở completion là 396 tests đạt; tests/dry-run không phải thêm
lượt inference hoặc thêm người duyệt.

### 2.2 Mốc đang chờ: đưa nhóm vào review main

**Repo đã có các commit riêng cho từng phần để nhóm clone và tham gia.**
Hai ZIP vẫn phải được người giữ project chia sẻ riêng. Project chưa
nhận/import JSON review main; chưa có kết quả benchmark chính để phân tích.

Bộ review hiện hành **v2** nằm tại `reports/stage1/v12/main_review/index.html`
trên máy giữ project hoặc sau khi giải nén `main_review_v2.zip`. Mỗi người
A/B đều kiểm bản dịch và ảnh/nhãn. Phân bố 22 gói:

| Nhóm gói | Số gói | Số mẫu trong từng gói | Tổng mẫu |
|---|---:|---|---:|
| repope_01 … repope_12 | 12 | 50/gói | 600 |
| vsr_01 … vsr_03 | 3 | 50, 50, 20 | 120 |
| tallyqa_01 … tallyqa_03 | 3 | 50, 50, 20 | 120 |
| oxford_pet_01 … oxford_pet_04 | 4 | 50, 50, 50, 10 | 160 |
| Tổng | 22 | Tối đa 50/gói | 1.000 |

Các HTML nhúng ảnh được giữ ngoài Git. Push repo thôi chưa làm nhóm nhận
được trang/ảnh review; cần chia sẻ riêng `main_review_v2.zip`. Ngược lại,
người chỉ review có thể mở ZIP ngay, không cần chờ clone/cài Python/GPU.
Mỗi gói cần **hai người A/B, mỗi người kiểm cả dịch và ảnh/nhãn**. A gửi JSON
cho B mở tiếp; mỗi gói nộp một JSON cuối. Chỉ A làm chưa đủ. Nhóm tự phối hợp,
không điền hộ ID hoặc sửa đè JSON; không cần người C riêng.

### 2.3 Những phần chưa được triển khai/xác nhận

- Main human QA/translation approvals và xử lý hết các mẫu nghi vấn.
- Chốt final metadata/configs sau review và kiểm main GPU smoke; contract/runner v1 đã có CPU tests.
- Freeze manifest, prompts, configs, revisions và kế hoạch run chính.
- Main inference 4.000 lượt dự kiến, metrics/CI/error analysis từ main.
- Report/slides theo kết quả main; Word v1 cũ chưa phải report V3 hoàn chỉnh.
- RQ3/RQ4, nếu nhóm chốt triển khai sau core; cloud GPU generation thực tế.

Không cần dựng lại dataset, duyệt lại pilot hoặc chạy lại toàn bộ tests/model
chỉ vì thành viên mới tham gia. Thực hiện checks phù hợp với thay đổi của mình.

## 3. Chọn cách tham gia

| Bạn muốn làm gì? | Cần GPU? | Bắt đầu ở đâu? | Sản phẩm bàn giao |
|---|---|---|---|
| Review ảnh/nhãn/bản dịch | Không, không cần Python | Mục 5 | JSON review từng gói |
| Sửa code/tests hoặc phân tích raw có sẵn | Không | Mục 4 rồi mục 7 | Code/tests hoặc bảng/analysis có nguồn |
| Kiểm tra chạy model | Có GPU local hoặc cloud | Mục 6 | JSONL + meta/summary/errors và ghi môi trường |
| Viết/tổng hợp report | Không | Mục 2, 7 và evidence được link cuối file | Nội dung đúng scope/phiên bản, phân biệt pilot/main |
| Đưa thay đổi lên GitHub | Không | Mục 8 | Commit theo từng việc, kiểm thử và PR rõ nội dung |

Theo yêu cầu ngày 22/11, nhóm dùng [phân công 5 người TV1–TV5](docs/research/TEAM_PROGRESS_AND_ASSIGNMENT_V1.md).
Công việc gần nhất là **main human review**; metadata/runner CPU đã có,
các mảng tổng hợp dữ liệu, GPU smoke, phân tích và report tiếp tục song song.
Không cần tất cả thành viên chạy lại pilot.

### 3.1 Thứ tự công việc tiếp theo và điều kiện qua mốc

| Mốc | Công việc | Đầu ra bàn giao | Khi nào được coi là xong? |
|---|---|---|---|
| A — Mở cộng tác ngay | Clone/kiểm repo đã push, chia sẻ guide và main_review_v2.zip, chọn gói review | Repo/ZIP nhóm truy cập được, thống nhất tên gói và cách chuyển JSON | Có thể nhận code hoặc mở review; thử lưu/tải/mở lại JSON một gói trước khi làm rộng |
| B — Review main | A kiểm dịch và ảnh/nhãn, B kiểm lại cả hai; ghi uncertain/rejected | `<packet>_reviewed_v2.json` theo đúng context, observations và reviewer/time thật | Import hợp lệ; mọi mẫu được xử lý rõ ràng trước freeze, không chỉ bấm hết pending |
| C — Baseline engineering | Metadata/prompt/config contract, full-main runner, raw/error/resume/grid checks | Code/tests, metadata spec, dry-run kế hoạch 1.000 ×2 ×2 | Kế hoạch đủ 4.000 ô, routing/labels đúng bốn task; không cần gọi model để kiểm lưới |
| D — Tổng hợp và freeze | Ghép review, kiểm IDs/source/ảnh/leakage, chốt configs và protocol | Manifest version mới, hash/freeze receipt, run plan | QA được duyệt thật, nghi vấn đã xử lý, các thay đổi loại/thay mẫu có quyết định/log; nhóm chốt trước full-run |
| E — Main inference | Chạy từng model theo kế hoạch được xác nhận, checkpoint/resume và kiểm coverage | JSONL/meta/errors/summaries, audit theo ô EN–VI | Đối chiếu đủ expected grid; lỗi/invalid/missing được ghi rõ, không bị giấu hoặc đổi thành đáp án hợp lệ |
| F — Phân tích và report | Metrics/CI từng model/task, disagreement, error cases và limitations | Bảng/biểu đồ tái lập, Results–Discussion và report/slides V3 | Mọi kết quả truy được về raw, đúng denominator/scope và có giải thích bất định |

Mốc B và C có thể làm **song song**. Trong lúc nhóm review, phần kỹ thuật
không phải đứng chờ: có thể hoàn thiện contract/runner và dùng synthetic
tests/dry-run. Rà Related Work, chuẩn bị bảng kết quả và khung report cũng có
thể làm sớm; phần Results/Discussion phải dựa trên kết quả thật khi đã có.

### 3.2 Phân công 5 người và các mảng công việc

Report [tiến độ và phân công](docs/research/TEAM_PROGRESS_AND_ASSIGNMENT_V1.md)
chia TV1 dữ liệu/QA cuối, TV2 inference/GPU, TV3 phân tích định lượng,
TV4 phân tích lỗi/Related Work, TV5 báo cáo/tái lập. TV1–TV5 là ký hiệu để nhóm
thay bằng tên thật. Mỗi phần có việc làm ngay, việc chờ QA/raw, đầu ra,
điều kiện hoàn tất và mốc commit. Mục 9 chia 22 gói review thành 400 lượt
kiểm mẫu/người, tính cả A và B; giữ các gói/người đã nhận nếu đang review.

| Workstream | Việc cụ thể | Có thể bắt đầu ngay? | Evidence cần lưu |
|---|---|---|---|
| Dữ liệu và ngôn ngữ | Review gói, sửa VI tương đương, QA ảnh/nhãn và ghi vấn đề | Có, nhận ZIP | JSON review, notes và phiên bản câu dịch được duyệt |
| Inference engineering | Hoàn thiện runner/main metadata, kiểm paired grid/resume/errors | Có, phát triển/test CPU; chạy model sau gate | PR, tests/dry-run, config/metadata contract |
| Evaluation/statistics | Kiểm metrics/CI bằng toy cases và raw pilot, chuẩn bị analysis reproducible | Có, không GPU | Analysis scripts, tests tính tay, output version mới và input hashes |
| Research/report | Related Work, mô tả thiết kế/QA, khung bảng, limitations | Có; chưa viết kết luận main | Nội dung có nguồn và bảng phân biệt đã làm/planned |
| Compute/reproducibility | Kiểm pilot khi cần, ghi môi trường, kiểm cloud GPU phù hợp | Có nếu có GPU; không bắt buộc tất cả cùng chạy | Raw/meta/summary/errors và hardware/package settings thật |

Các mảng trên mô tả kỹ năng và sản phẩm; phân công cụ thể dùng report TV1–TV5.
Ghi nhận việc đang làm qua issue/branch/PR hoặc bảng nhóm để tránh đụng cùng
một file. Mỗi người viết phần chuyên môn và commit công việc thực sự của mình;
TV5 tích hợp báo cáo chung, không viết thay cả nhóm.

### 3.3 Việc đầu tiên nên làm trong đợt cộng tác này

Cập nhật24/11: nhóm đã chọn [Option B cho main](docs/research/MAIN_OPTION_B_V1.md).
Main CLI mặc định candidate B chưa frozen; review HTML/JSON/ZIP không đổi,
không cần duyệt lại vì preprocessing. Sau QA/freeze mới chạy M3 bốn task.

1. Clone repo theo mục 4.1; người giữ project chia sẻ riêng main_review_v2.zip và guide.
2. Chọn một gói để thử quy trình review → tải JSON → mở lại → dry-run import.
   Sau khi cách làm rõ, nhóm tiếp tục các gói còn lại và chuyển JSON tuần tự
   giữa A/B, mỗi người kiểm cả dịch và ảnh/nhãn.
3. Metadata/main runner v1 và CPU dry-run đã có tại mục 7. Phần kỹ thuật tiếp
   tục chốt final config sau review, rồi kiểm main GPU smoke khi được xác nhận.
4. Gom JSON theo từng đợt để kiểm/import sớm, không đợi đủ 22 gói mới phát hiện
   sai context hoặc mất quyết định. Giữ pending nếu thực sự chưa rõ.

### 3.4 Khi nào xét RQ3/RQ4?

Chỉ xét sau khi core pipeline ổn định, dữ liệu baseline được chốt và nhóm
xác nhận đủ thời gian/QA/compute. RQ3 cần paraphrases tương đương được review;
RQ4 cần cặp ảnh và nhãn xác minh độc lập, cùng đánh giá confounds bối cảnh.
Không lấy thời gian review/core để tự mở thêm dữ liệu hoặc inference mở rộng.

## 4. Clone và cài môi trường CPU

### 4.1 Nhận repository

```text
git clone https://github.com/MinhGioChai/cv-final-project.git
cd cv-final-project
```

Nếu đang ở máy có project hiện tại, làm ngay trong folder đó, không clone
đè lên nó. Mọi lệnh Python bên dưới chạy từ project root, nơi có `pyproject.toml`.

### 4.2 Windows PowerShell

Dùng **Python 3.12**, kiểm tra `python --version` trước. Không cần activate venv
hoặc đổi ExecutionPolicy vì các lệnh gọi trực tiếp interpreter:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-stage0.lock.txt
.venv/Scripts/python.exe -m pip install --no-build-isolation --no-deps -e .
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe scripts/check_repository.py
```

### 4.3 Linux/macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-stage0.lock.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pytest -q -p no:cacheprovider
.venv/bin/python scripts/check_repository.py
```

Các mục tiếp theo viết theo Windows; Linux/macOS thay `.venv/Scripts/python.exe`
bằng `.venv/bin/python`. Môi trường này đủ cho tests/review/analysis. Chỉ cài
`.venv-infer` và CUDA packages khi cần inference. Máy đã có môi trường GPU
chạy được giữ nguyên, không cần xóa/cài lại để tham gia nhóm.

## 5. Nhận dữ liệu và review main

### 5.1 Chọn đúng gói tải về

| Gói/nơi lưu | Chứa gì? | Dùng khi nào? |
|---|---|---|
| Repository Git | Code/configs/manifests, VI drafts, review JSON/CSV, báo cáo nhỏ và pilot output snapshots | Clone, sửa code, commit/PR |
| `main_review_v2.zip` (~83,4 MiB) | 22 gói HTML v2 nhúng ảnh, CSV/JSON pending | Thành viên review: chỉ cần gói này |
| `team_workspace_v1.zip` (~184 MiB) | Ảnh/cache cho validation; kèm HTML v1 lịch sử | Làm code/data, sau restore sinh review v2 bằng lệnh bên dưới |
| `pilot_team_v1.zip` (~2,4 MiB) | Snapshot code/configs và 30 ảnh pilot | Upload vào notebook Colab/Kaggle khi cần chạy model |

Nhận ZIP qua kênh chia sẻ riêng của nhóm; Git không chứa chúng. Checksums ở
[review v2 receipt](reports/stage1/v12/review_bundle.json),
[release manifest cho hai ZIP cũ](reports/releases/2026-11-21/publication.json) và
`reports/stage1/v11/pilot_bundle.json`.
ZIP là snapshot: layout của code trong pilot ZIP có thể cũ hơn repo hiện tại,
nhưng bộ launcher/config trong gói đã được kiểm dry-run. Không ghép code của
hai snapshot vào cùng cloud workspace hoặc sửa metadata để ép resume.

### 5.2 Chỉ review — không cần cài Python

Đọc [hướng dẫn review chi tiết](docs/research/MAIN_REVIEW_V2.md): từng bước A/B,
tiêu chí dịch/ảnh theo từng task, pending/rejected, lưu/mở lại JSON và xử lý lỗi.
Bản HTML đọc offline để gửi cùng ZIP là `exports/HUONG_DAN_REVIEW_V2.html`,
nhận riêng từ người giữ project; không cần cài đặt để đọc.

1. Nhận **main_review_v2.zip**, giải nén vào một thư mục mới.
2. Mở `reports/stage1/v12/main_review/index.html`, chọn gói nhóm đã thống nhất.
3. **A:** nhập ID của mình, chọn **Lượt A**, kiểm dịch và ảnh/nhãn trên cùng
   màn hình; bấm **Lưu cả hai phần của lượt này** cho từng mẫu.
4. A tải JSON gửi B. **B:** mở cùng HTML, dùng **Mở JSON đã lưu** nạp file A,
   nhập ID của B, chọn **Lượt B** và kiểm lại cả hai phần.
5. B tải `<packet>_reviewed_v2.json` cuối gửi người tổng hợp. Giữ bản A/B làm
   backup. Nếu có repo, lưu JSON cuối vào `data/reviews/main_review_v2/`.

Cần hai ID khác nhau; một người chưa đủ hoàn tất. Nếu B sửa VI, các lượt cũ
chuyển vào lịch sử và không còn tính vào approval; B gửi lại JSON để A duyệt
bản mới. Không điền hộ tên/ngày duyệt. Approved ảnh/nhãn chỉ khi quan sát khớp
nguồn; uncertain/rejected cần ghi chú. Không sửa ground truth.

Thử 2–3 mẫu → tải JSON → mở lại trước khi làm cả gói. JSON v1 không dùng trực
tiếp trên trang v2; giữ file cũ để đối soát, không xóa hoặc tự gán approval mới.

| Task | Quan sát cần nhập |
|---|---|
| RePOPE | `yes` / `no`, hoặc `uncertain` |
| VSR | `yes` = TRUE, `no` = FALSE; giữ đúng hướng quan hệ không gian |
| TallyQA | Số nguyên không âm, giữ vật thể/điều kiện lọc/đơn vị đếm |
| Pet | Mã A–H đúng danh sách tám giống hiển thị |

Lưu ở browser chưa cập nhật manifest. JSON đặt trong folder cũng chưa tự
đổi QA status; phải qua import/validate. Pilot 30 mẫu đã được duyệt riêng,
không cần làm lại. Giao diện main đã kiểm backend/JS, chưa visual browser QA.

### 5.3 Làm code/data — nhận ảnh vào clone

Đặt `team_workspace_v1.zip` trong `exports/`, chạy:

```powershell
.venv/Scripts/python.exe scripts/team_workspace.py restore --archive exports/team_workspace_v1.zip
.venv/Scripts/python.exe scripts/verify_main_draft.py --report reports/maintenance/readiness_local_v1.json
.venv/Scripts/python.exe scripts/review_main.py export --version v2
```

Restore kiểm context/SHA256, giữ file giống hệt và từ chối ghi đè file khác
nội dung. Nếu report path đã tồn tại, dùng tên version mới. Kết quả hiện tại
sẽ đủ 1.000 row/783 ảnh, technical/leakage issues=0, nhưng `main_ready=false`
do main QA/translation chưa approved. Đây là trạng thái dự kiến, không cần
chạy lại acquisition chỉ để làm cho gate chuyển xanh.

### 5.4 Người import JSON review

Ví dụ sau khi có JSON cuối `repope_01_reviewed_v2.json`, dry-run trước:

```powershell
.venv/Scripts/python.exe scripts/review_main.py import --version v2 --manifest data/reviews/main_review_v2/repope_01.csv --review data/reviews/main_review_v2/repope_01_reviewed_v2.json --output data/main/reviewed_v2/repope_01.csv --audit reports/main_review/repope_01_import_v2.json --operator YOUR_IMPORTER_ID --dry-run
```

Thay YOUR_IMPORTER_ID bằng ID người import. Hợp lệ mới bỏ `--dry-run` để lưu
manifest/audit mới; không ghi đè output cũ. Người import không mặc nhiên là
reviewer. Giữ toàn bộ IDs, source fields và các quyết định chưa hoàn tất.

## 6. Chạy pilot khi cần

Sau khi có ảnh pilot, kiểm kế hoạch bằng CPU:

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py --model qwen --limit 2 --dry-run
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --limit 2 --dry-run
```

Local chạy thật cần NVIDIA CUDA GPU và môi trường inference. Máy mới dùng
Python 3.12 chạy `python scripts/setup_inference.py`; máy đã có `.venv-infer`
chạy tốt không cần setup lại. Launcher chọn môi trường này khi chạy thật.

```powershell
.venv/Scripts/python.exe scripts/run_pilot.py --model qwen --run-name my_smoke_v1 --limit 2 --online
.venv/Scripts/python.exe scripts/run_pilot.py --model gemma --run-name my_smoke_v1 --limit 2 --online
```

Chạy từng model. Qwen dùng NF4/FP16; Gemma dùng NF4/BF16 và kiểm native BF16
trước tải weights. `--online` cho phép tải, bỏ flag là cache-only. Gemma cần
tài khoản Hugging Face đã được cấp quyền và token của chính người chạy;
local hỏi token ẩn, cloud dùng Secret HF_TOKEN. Không paste token vào code/Git.

Mặc định 2 mẫu/model, tối đa 10. Output mới:
`results/pilot/local/team_v1/my_smoke_v1/<model>.jsonl`.
Sau smoke hợp lệ, tăng `--limit 10 --resume` với cùng run name/config/runtime.
Giữ JSONL và các file meta/summary/load_error cạnh nó. Ctrl+C rồi tiếp tục cùng
args và --resume; khác fingerprint dùng output mới, không sửa metadata.

Máy không GPU có thể dùng `notebooks/pilot_colab.ipynb` hoặc `pilot_kaggle.ipynb`
với ZIP pilot nhỏ. Bật GPU, chạy các cell theo thứ tự; đặt MODEL/LIMIT/RUN_NAME,
chỉ bật RESUME khi tiếp tục đúng checkpoint; tải results ZIP trước mất phiên.
Không bảo đảm cloud được cấp GPU BF16. Cloud generation thực tế chưa được
project xác minh; dry-runs có platform label không phải kết quả chạy cloud.

Chi tiết thao tác và GPU/secret errors ở [pilot guide](docs/run_local_colab_kaggle.md).
Các alias `run_local_pilot.py`, `run_gemma_pilot.py` vẫn dùng được. Runner này
chỉ cho pilot. Main dùng `scripts/run_main.py`; baseline v1 đã có CPU tests,
còn final QA/freeze và GPU smoke trước inference thật.

## 7. Phân tích, viết code và chọn file đúng

### Kiểm baseline main trong lúc nhóm review

```powershell
.venv/Scripts/python.exe scripts/run_main.py plan
.venv/Scripts/python.exe scripts/run_main.py run --model qwen --dry-run
.venv/Scripts/python.exe scripts/run_main.py run --model gemma --dry-run
```

CPU plan kiểm 1.000 row/783 ảnh và lưới 4.000 cells; dry-run từng model có
2.000 cells. Không gọi model, tải weights hoặc tự approve/freeze dữ liệu.
QA pending và frozen=false làm execution_ready=false là đúng trạng thái.
Thiếu ảnh cần restore workspace ZIP; code không tự tải corpus trong preflight.
Metadata, prompts, resume và gates tại [baseline v1](docs/research/BASELINE_V1.md).
Khi có review thật sẽ tổng hợp final manifest/config mới rồi mới freeze.

### Cấu trúc sử dụng hằng ngày

```text
README.md              Giới thiệu và link vào hướng dẫn này
HUONG_DAN_NHOM.md       Hướng dẫn tổng hợp cho nhóm
src/vlmbench/          Code chính: datasets, review, inference, evaluation, statistics
scripts/               Lệnh thường dùng: pilot, review, kiểm tra, nhận/gói dữ liệu
  data/                8 script acquisition/selection/draft; dùng khi cần dựng lại
  legacy/              Chỉ có trên máy giữ project; 2 builder Word v1 ngoài Git
configs/               Config hiện tại và config lịch sử cần cho reproducibility
data/                  Manifests/dictionaries/reviews qua Git; raw/ nhận bằng ZIP
notebooks/             Pilot Colab/Kaggle
tests/                 CPU tests, không cần model weights
reports/               Completion và bằng chứng; báo cáo version cũ giữ nguyên
docs/                  Protocol/hướng dẫn chuyên sâu; archive/ là lịch sử
exports/               ZIP local, không đưa vào Git
results/               Checkpoints/analysis local, không đưa vào Git
```

Các file V4.2/START_HERE ở root là compatibility links. Không cần đọc chúng
để bắt đầu. Không di chuyển data/configs/runtime theo hình thức vì paths và
bytes đã được source receipts/checkpoint tham chiếu.

### File/config hiện tại

| Nhu cầu | Dùng gì? |
|---|---|
| Manifest pilot QA approved | `data/pilot/stage1_qa_v1/pilot_manifest.csv` |
| Pilot rerun team | `configs/inference/team_qwen_v1.yaml`, `team_gemma_v1.yaml` |
| Sampling main đã chọn | `configs/main_preparation_v3.yaml`; frozen=false |
| Main RePOPE 600 câu | `data/main/preparation_v2/repope_bilingual_draft_manifest.csv` |
| Main VSR/TallyQA/Pet | `data/main/preparation_v3/<dataset>_bilingual_draft.csv` |
| Review theo gói hiện tại | `data/reviews/main_review_v2/`, `scripts/review_main.py` (mặc định v2); v1 phải ghi --version v1 |
| Raw pilot nhỏ dùng chung | `reports/pilot_outputs/`, có checksums |
| Raw/checkpoints lịch sử | Giữ nguyên manifest/config/source của chính run đó |

Các preparation_v1/v2/v3 là các bước tích lũy, không phải ba benchmark để tự
chọn phiên bản lớn nhất. Các config cũ không phải file rác; không đổi chúng
để hợp thức hóa checkpoint mới. Script dựng lại dữ liệu hiện nằm trong
`scripts/data/`; báo cáo lịch sử vẫn ghi đường dẫn tại lúc chúng được tạo.

### Phân tích mà không chạy model

Hai raw/summary pilot được copy nguyên bytes vào reports/pilot_outputs để
người không GPU có thể thử metrics/bootstrap. Ví dụ Qwen, không cần ảnh:

```powershell
.venv/Scripts/python.exe -m vlmbench.cli evaluate --manifest data/pilot/stage1_v3/pilot_manifest.csv --predictions reports/pilot_outputs/qwen_smoke_v1.jsonl --selection reports/pilot_outputs/qwen_smoke_v1.summary.json --output results/analysis/qwen_eval_v1.json --report results/analysis/qwen_eval_v1.md
.venv/Scripts/python.exe -m vlmbench.cli statistics --evaluation results/analysis/qwen_eval_v1.json --output results/analysis/qwen_ci_v1.json --resamples 5000 --seed 42
```

Ở đây dùng manifest lịch sử stage1_v3 đúng với raw đó, không thay bằng
manifest rerun chỉ vì nó mới hơn. Gemma dùng cặp `gemma_bf16_trace_v2` và output
khác. Không gộp observations từ nhiều lần chạy thành sample độc lập.

Các việc có thể chọn: main review; kiểm evaluator/statistics; bổ sung baseline
metadata/main runner; viết Results/Discussion dựa trên evidence đã có; kiểm
pilot cloud khi có GPU. Theo dõi và thảo luận scope trong issue/PR, không chạy
full inference hoặc mở RQ3/RQ4 chỉ vì đã cài được môi trường.

## 8. Commit, push và pull request

### 8A. Mỗi lần công bố một phần có thể kiểm tra được

Remote hiện tại là `https://github.com/MinhGioChai/cv-final-project.git`, nhánh
`main`. Đợt công bố 21/11 chia riêng foundation/dependencies, data, evaluation,
pilot, review HTML và tài liệu. Git log ghi đúng ngày công bố công việc đã có;
không phải ngày tạo lại thí nghiệm. [Release log](reports/releases/2026-11-21/README.md)
ghi commit và kiểm chứng của từng phần.

Với thay đổi mới, dùng branch/PR ở mục 8B và chọn file cụ thể. Ví dụ khi chỉ
cải thiện câu chữ trong hướng dẫn nhóm:

```text
git status --short
git diff -- HUONG_DAN_NHOM.md
git add -- HUONG_DAN_NHOM.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit
git push -u origin HEAD
```

Chạy tests phù hợp trước commit khi thay code; full CPU suite và Git candidate
audit dùng các lệnh ở mục 4. Một thay đổi docs chỉ cần kiểm nội dung/link nếu
không đổi workflow. Thay file trong lệnh `git add` bằng đúng file của việc đang
làm; không gom tất cả file chưa theo dõi vào một commit.

Commit message gồm tiêu đề cụ thể và phần thân ngắn:

```text
docs: clarify main review handoff

Mục đích: giúp thành viên nhận đúng gói và gửi JSON review.
Hoàn thành: làm rõ đường dẫn và A/B mỗi người kiểm cả dịch, ảnh/nhãn.
Kiểm chứng: đối chiếu lệnh/path; không có inference hoặc human approval mới.
```

Git candidate audit kiểm file quá ngân sách 5 MiB và credential/signed URL
patterns. ZIP, raw images, venv, weights, HF_TOKEN/.env và private results ở
ngoài Git. Raw snapshots nhỏ trong reports/pilot_outputs phục vụ tái lập CPU.
Các bản Word/proposal, render previews, maintenance và snapshots local cũ
được giữ trên máy gốc; không cần chúng để cài/test/review project.

Chia sẻ ZIP dữ liệu riêng và cấp quyền GitHub theo tài khoản của từng người.
Project chưa chọn license phân phối mã; quyền sử dụng dữ liệu vẫn theo nguồn.

### 8B. Thành viên — sau khi đã clone

Lấy cập nhật trước khi bắt đầu, tạo branch theo một việc:

```text
git switch main
git pull --ff-only
git switch -c work/review-repope-01
```

Nếu đang có thay đổi chưa commit, xử lý/chuyển chúng có chủ ý trước khi đổi
branch; không dùng reset/clean để xóa cho nhanh. Với một việc code khác,
đặt tên branch tương ứng. Tránh hai người sửa đồng thời cùng một JSON review;
chọn các gói khác nhau hoặc chuyển cùng JSON tuần tự giữa hai reviewer.

Sau khi sửa, chạy checks phù hợp ở mục 8A, `git add` các file của việc mình làm,
kiểm staged diff rồi commit và `git push -u origin HEAD`. Mở Pull Request vào
main với bốn ý:

1. Vấn đề/công việc được xử lý.
2. File và hành vi đã thay đổi.
3. Đã kiểm tra gì: tests/dry-run/QA thật/inference thật phân biệt rõ.
4. Còn thiếu hoặc có ảnh hưởng nào cần reviewer chú ý.

Chờ review/merge theo quy ước của nhóm. Không giải quyết conflict review JSON
bằng cách bỏ quyết định người khác; đối soát source context và bản VI cuối.

## 9. Khi gặp lỗi hoặc chưa biết nên làm gì

| Hiện tượng | Cách xử lý đầu tiên |
|---|---|
| ModuleNotFoundError: vlmbench | Đúng interpreter .venv chưa? Chạy lại bước pip install -e . ở project root |
| Missing image/cache | Nhận/restore đúng ZIP; clone Git không chứa ảnh, không cần tải lại corpus |
| main_ready=false, QA_NOT_APPROVED | Main đang chờ review; hoàn thành/import QA thật |
| Output/report đã tồn tại | Dùng tên version mới, hoặc --resume đúng checkpoint khi runner hỗ trợ |
| Checkpoint khác config/GPU/runtime | Chọn run name/output mới; giữ bản cũ, không sửa metadata để ép nhận |
| Gemma GPU thiếu BF16 | Chọn Qwen hoặc GPU BF16 phù hợp, không tự fallback FP16 |
| Pilot có invalid/failed | Giữ raw/errors và báo hardware/config; không sửa nhãn hoặc biến invalid thành NO |
| Chưa có GPU | Review, tests, analysis và report vẫn làm được bằng CPU |

Mỗi thay đổi có ý nghĩa cập nhật reports/completion.md với ngày, bằng chứng,
việc còn lại và bước tiếp. Giữ các báo cáo cũ, source labels, pilot exclusions,
reviewer/time thật, model revisions và raw outputs; tạo version mới khi cần.

## 10. Tài liệu tra sâu

- [Completion hiện tại](reports/completion.md), [checklist việc P0](docs/research/IMPLEMENTATION_PLAN_V3.md).
- [Handoff V3](docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md), [protocol nghiên cứu](docs/research/RESEARCH_PROTOCOL_V3.md).
- [Workflow review/import v2](docs/research/MAIN_REVIEW_V2.md), [pilot local/cloud](docs/run_local_colab_kaggle.md).
- [Evaluation method](docs/research/EVALUATION_V1.md), [pilot outputs](reports/pilot_outputs/README.md).
- [Báo cáo/evidence theo phiên](reports/README.md), [lịch sử completion v1–v21](reports/completion_history.md).

Scope hiện hành lấy theo V3 và chỉ dẫn mới của người dùng. Word v1/V4.2 và
archive được giữ để tra lịch sử, không phải yêu cầu tự mở rộng phần core.
