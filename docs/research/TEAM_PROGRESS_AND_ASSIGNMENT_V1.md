# Tiến độ nghiên cứu VLM Anh Việt và phân công nhóm 5 người

Cập nhật ngày 22/11/2026 theo trạng thái repo sau commit b411688. Nhóm gồm 5 người; TV1 đến TV5 là ký hiệu phân công để thay bằng tên thật khi nhóm thống nhất. Phần việc dưới đây dành cho giai đoạn còn lại, không gán lại tác giả cho các commit đã có.

## 1 Tổng quan nghiên cứu

Tên đề tài là A Controlled English-Vietnamese Benchmark of Visual Grounding and Hallucination. Nhóm đánh giá zero-shot hai VLM khi giữ nguyên ảnh, ý nghĩa câu hỏi và ground truth, chỉ đổi ngôn ngữ EN-VI. Mục tiêu là đo chênh lệch và bất định có kiểm soát, không mặc định tiếng Việt kém hơn.

Hai câu hỏi bắt buộc P0 là RQ1 về object hallucination trên RePOPE và RQ2 về khác biệt EN-VI giữa bốn tác vụ. RQ3 paraphrase và RQ4 visual evidence là P1 có điều kiện sau core; thí nghiệm negation riêng là P2 future work. Không training, LoRA, thay model hoặc mở rộng dữ liệu/nghiên cứu tùy ý.

| Dataset và tác vụ | Câu main | Ảnh | Thiết kế đã chọn |
|---|---:|---:|---|
| RePOPE object presence | 600 | 383 | 200 mỗi nhóm random/popular/adversarial, tối đa 2 câu/ảnh |
| VSR spatial reasoning | 120 | 120 | random/test, 60 TRUE và 60 FALSE |
| TallyQA counting | 120 | 120 | test, 60 simple và 60 complex |
| Oxford IIIT Pet | 160 | 160 | test, 8 giống chó, 20 ảnh/giống, mapping A-H |
| Tổng | 1.000 | 783 | Mỗi câu chạy EN/VI trên hai model |

Tổng kế hoạch chính là 1.000 × 2 ngôn ngữ × 2 model = 4.000 lượt, 2.000/model. Đây chưa phải số lượt main đã chạy. Seed hiện là 42; ảnh pilot bị loại khỏi main theo source namespace/ID và SHA256. Pet là tập con 8 lớp, không đại diện benchmark Pet 37 lớp chuẩn.

Model là Qwen/Qwen2.5-VL-3B-Instruct dùng NF4/FP16 và google/gemma-3-4b-it dùng NF4/BF16. Model, processor và tokenizer được pin exact revisions; mọi điều kiện phải nhất quán giữa EN/VI trong cùng model. Chênh lệch precision giữa hai model cần được nêu khi diễn giải.

## 2 Tiến độ có bằng chứng

| Hạng mục | Đã xác minh | Chưa hoàn thành |
|---|---|---|
| Pilot thật | Mỗi model cùng subset 10 ảnh, 20 lượt EN/VI valid; tổng 40 lượt của hai model | Không suy pilot nhỏ thành kết luận main |
| QA pilot | 30 mẫu được duyệt dịch và ảnh/nhãn, đã import | Không dùng acceptance pilot để approve main |
| Dữ liệu main | 1.000 bilingual drafts/783 ảnh, source và leakage checks đạt | Chưa import human review main, chưa final/frozen |
| Review main v2 | 22 gói offline, A/B mỗi người kiểm dịch và ảnh/nhãn | Nhóm đang review, người giữ project sẽ gửi JSON sau |
| Baseline engineering v1 | Strict metadata/config schemas, runner bốn task, atomic checkpoint/resume/error, CPU grid 4.000 cells | Chưa có actual main GPU generation hoặc freeze receipt thật |
| Evaluation và CI | Metrics, pairing, coverage và image-cluster bootstrap; đã phân tích pilot, fake main integration đạt | Chưa có kết quả RQ1/RQ2 từ main |
| Kiểm thử phần mềm | Lần v13 ngày 22/11: 396 tests đạt, gồm 37 baseline tests; wheel offline check đạt | Tests/dry-run không phải inference hoặc human approval |
| Cloud và báo cáo | Pilot notebooks, protocol V3, guide và evidence đã có; proposal Word cũ giữ lịch sử V4.2 | Main cloud run, final Results/Discussion/report/slides còn chờ |

Trạng thái tổng thể vẫn là Stage 1 IN_PROGRESS. Main hiện frozen=false và execution_ready=false; 1.000 mẫu QA pending/translation requires_review. Runner chặn chạy thật trước khi load model. Gemma engineering pilot đã xong, không còn là blocker setup; main GPU/cloud vẫn cần xác minh.

Draft generation hiện greedy, batch=1, max_new_tokens=8, ảnh RGB thumbnail LANCZOS cạnh tối đa 512. Prompt RePOPE yêu cầu YES/NO, VSR TRUE/FALSE, TallyQA số nguyên không âm và Pet A-H. Đây là candidate settings chưa final freeze. VSR chuẩn hóa TRUE→yes và FALSE→no trong storage; không đảo nhãn vì phát biểu sai so với ảnh.

Baseline contract pin model/processor/tokenizer, source/ảnh/prompt/code/environment hashes, dtype/NF4, raw output, valid/invalid_reason, failed/missing và attempts. Fake outputs cả hai model đã qua evaluator/CI; chưa chứng minh GPU main hoạt động tốt trên bốn task.

## 3 Thiết kế phân tích và các mốc còn lại

RQ1 chính dùng các câu RePOPE nhãn NO có EN và VI đều valid: FPR là tỷ lệ trả YES trong tập negative đó. Chênh lệch ΔFPR = FPR(VI) − FPR(EN), báo theo điểm phần trăm, riêng từng model, kèm số câu/ảnh và CI 95% theo cụm ảnh. Báo cả các cặp bị loại và sensitivity với invalid/failed/missing; INVALID không biến thành NO.

RQ2 báo metric từng task: RePOPE accuracy/FPR/FNR; VSR binary accuracy; TallyQA exact match và MAE valid-only kèm coverage; Pet 8-way/per-class accuracy. Có paired disagreement và invalid/missing. Không gộp bốn metric khác bản chất thành một điểm chung hoặc dùng accuracy để xếp độ khó dataset.

Bootstrap hiện dùng cụm image namespace + image_id, giữ EN/VI cùng nhau và các câu cùng ảnh trong cụm, row weighting, B=5.000 và seed=42. Cần nêu số cụm nhỏ/CI suy biến. Review A/B nối tiếp, B thấy quyết định A; không gọi đây là review mù độc lập hoặc báo independent inter-rater agreement từ workflow này.

| Mốc | Điều kiện qua mốc | Phụ thuộc |
|---|---|---|
| M1 Dữ liệu cuối | Review thật, xử lý nghi vấn, đủ IDs/provenance, không leakage, manifest final version mới | TV1 tổng hợp, cả nhóm review |
| M2 Final protocol | Chốt settings/prompt/config và receipt freeze đúng hash, có quyết định nhóm | M1 và rà engineering TV2/TV3/TV5 |
| M3 GPU smoke | Xác nhận run nhỏ bao phủ bốn task, kiểm raw/parse/metadata/resume/tài nguyên | M2 và quyền chạy thật |
| M4 Main inference | Run được xác nhận, đủ 4.000 ô hoặc log rõ failed/missing, giữ mọi raw attempts | M3 |
| M5 Phân tích và nộp | Bảng/CI/cases tái lập, report/slides có provenance và giới hạn | M4, TV3/TV4/TV5 |

Không tự đặt deadline chính thức từ lịch V4.2. Khi chưa có dữ liệu reviewed, các thành viên vẫn phát triển công cụ, tests giả, taxonomy, Related Work và phần Method. Không viết kết luận main trước khi có raw thật. RQ3/RQ4 chỉ xét sau quyết định riêng, không phân công như điều kiện bắt buộc.

## 4 TV1 phụ trách dữ liệu và QA cuối

**Trách nhiệm chính:** biến kết quả review thật của cả nhóm thành bộ main final truy vết được. TV1 không phải tự duyệt toàn bộ 1.000 mẫu và không tự tạo approved thay người khác.

**Làm ngay:** lập sổ nhận JSON theo gói/phiên bản, kiểm đúng context và IDs; chuẩn bị công cụ tổng hợp kết quả import, phát hiện gói thiếu/trùng, bản VI cũ, ID A/B trùng nhau và các mẫu unresolved. Dùng lại importer v2 đã có, không viết lại logic review.

**Khi có JSON:** dry-run/import từng gói vào version mới, giữ bản gốc A/B; tập hợp đúng 1.000 IDs, so source fields/labels với selection, kiểm ảnh và pilot exclusions. Ghi danh sách uncertain/rejected để nhóm quyết định trước khi freeze; không tự drop/replace câu hoặc đổi ground truth. Nếu phải thay scope, cần quyết định/log/protocol mới trước model outputs.

**Đầu ra:** công cụ tổng hợp final và tests, bảng coverage QA theo gói, manifest final version mới và audit/hash receipt khi đủ điều kiện. Các vị trí dự kiến như scripts/finalize_main.py, tests/test_finalize_main.py và data/main/final_v1 hiện là đầu ra cần làm, không phải đã tồn tại.

**Hoàn tất khi:** IDs/source/leakage kiểm được, hai người đã duyệt cả dịch/ảnh trên bản cuối cho mọi mẫu sử dụng, nghi vấn được giải quyết bằng quyết định có căn cứ và toàn bộ review history còn truy vết. Chuẩn bị receipt freeze để nhóm chốt, không tự bypass gates.

**Bàn giao và report:** cung cấp TV2/TV3 manifest + hashes; viết phần Data, sampling và QA. Branch work/main-data-finalization. TV2 review PR. Các mốc commit có thể là công cụ tổng hợp/tests, import một đợt review thật, rồi manifest final/audit sau khi đạt gate.

## 5 TV2 phụ trách inference và GPU

**Trách nhiệm chính:** kiểm runner main đã có trên môi trường thực, vận hành run được phê duyệt và giữ raw/metadata đầy đủ. Nên giao slot này cho người có thể sử dụng RTX 3060 hoặc GPU cloud phù hợp; các thành viên còn lại không cần GPU để làm phần của mình.

**Làm ngay:** đọc contract v1, kiểm environment và lựa chọn interpreter, chuẩn bị kế hoạch smoke bao phủ cả bốn task, kiểm subset logging/expected grid và notebook hoặc quy trình main local/cloud. Hiện notebooks trong repo phục vụ pilot; không ghi chúng thành main cloud đã chạy.

Một điểm cần xử lý rõ: --max-cells chỉ giới hạn số cells được lấy theo queue hiện tại, không tự bảo đảm bốn task đều xuất hiện. Nếu bổ sung lựa chọn smoke theo task, phải log IDs và coverage, có CPU tests và giữ denominator main; không chọn mẫu theo model đúng/sai.

**Sau gate dữ liệu/protocol:** chạy bounded GPU smoke khi được xác nhận, kiểm dtype, raw response, parse, ảnh/processor, token budget, memory và resume; sau đó mới vận hành main theo kế hoạch được duyệt. Giữ failed/invalid/missing thật. Không tự đổi model/precision/prompts, loại mẫu hoặc chọn lần chạy tốt nhất. Thay đổi vì lỗi kỹ thuật phải tạo version/log và chốt lại protocol phù hợp.

**Đầu ra:** quy trình/notebook main, tests routing/smoke, báo cáo environment và smoke thật, run metadata/raw/error/summary cho từng model. Raw/weights/token/ảnh ở ngoài Git, Git chứa code/configs và receipt nhỏ. Kiểm cloud BF16 cho Gemma; không fallback FP16 ngầm.

**Hoàn tất khi:** run có expected grid đối chiếu được, không trộn fingerprints/attempts, GPU evidence thật và kết quả lỗi vẫn truy vết. Viết phần Models và Inference protocol. Branch work/main-gpu-validation; TV3 review PR. Mốc commit: chuẩn bị workflow/tests, receipt smoke thật, rồi coverage main thật.

## 6 TV3 phụ trách phân tích định lượng

**Trách nhiệm chính:** tạo kết quả RQ1/RQ2 tái lập từ raw, tận dụng evaluator/statistics đã triển khai. Không cần viết lại metrics để có thêm commit.

**Làm ngay:** chuẩn bị script phân tích nhận final manifest, raw/summary/meta từng model, kiểm fingerprint/IDs/attempt selection và xuất bảng/biểu đồ. Viết tests tính tay cho tầng tổng hợp/export; chạy toy/fake data với nhãn synthetic rõ ràng trong tests. Chuẩn bị layout bảng trước khi có main outputs.

**Khi có raw thật:** tính RePOPE negative-only FPR/ΔFPR và CI image-cluster riêng từng model, theo category khi đủ mẫu; báo all-expected accuracy, jointly-valid coverage, invalid/failed/missing và sensitivity. Xuất kết quả VSR, TallyQA, Pet cùng disagreement/per-class phù hợp. Ghi undefined khi không có denominator, không thay bằng 0.

**Đầu ra:** scripts/tables/figures tái lập, input hashes, bảng counts và denominators; không sửa raw response hoặc ground truth. Có thể dùng scripts/analyze_main.py và thư mục analysis mới làm tên dự kiến; đây chưa phải script đã có. Kết quả lưu version mới, ghi rõ run nào tạo mỗi bảng/hình.

**Hoàn tất khi:** mọi con số truy được về inputs và lệnh, CI dùng cụm ảnh đúng, không gộp model/platform fingerprints không tương thích, bảng/figure/report nhất quán. CI từ ít cụm hoặc selection đặc thù có giới hạn được nêu rõ. Chênh lệch không được diễn giải thành nguyên nhân nội tại model.

**Bàn giao và report:** gửi bảng/figures/counts cho TV4/TV5; viết Evaluation và phần Results định lượng. Branch work/main-analysis; TV4 review PR. Mốc commit: analysis CLI/tests và bảng mẫu synthetic, sau đó export main thật có provenance, rồi kiểm đối chiếu số liệu.

## 7 TV4 phụ trách phân tích lỗi và Related Work

**Trách nhiệm chính:** giải thích các dạng lỗi baseline bằng case có nguồn và đặt thiết kế nghiên cứu trong tài liệu liên quan. Không tự biến công việc này thành RQ3/RQ4 hoặc thí nghiệm negation mới.

**Làm ngay:** xây taxonomy và mẫu ghi case cho object hallucination, spatial relation, counting condition, fine-grained confusion và output format. Chốt tiêu chí chọn case trước khi xem main, tránh chỉ lấy ví dụ tiếng Việt sai. Chuẩn bị phần Related Work với tài liệu gốc, citations kiểm được và ghi đúng phạm vi mỗi nghiên cứu; không dùng nội dung ChatGPT như bằng chứng thực nghiệm.

**Sau main:** kiểm các nhóm EN đúng/VI sai, VI đúng/EN sai, cả hai sai/đúng và invalid khi phù hợp. Lưu sample ID, model/run/ảnh/prompt hashes, raw hai ngôn ngữ, ground truth, mã lỗi và lý do chọn. Nhờ người khác đối soát case; phân biệt lỗi model với vấn đề annotation/translation cần xử lý theo quy trình, không sửa nguồn sau khi thấy output.

**Đầu ra:** hướng dẫn taxonomy, tập case annotations, script/bộ lọc lựa chọn case nếu cần, bảng phân tích định tính và bibliography. Không public lại ảnh dataset trong Git; dùng references/IDs và chia sẻ hình theo quyền nguồn.

**Hoàn tất khi:** cases có tiêu chí và truy vết, ví dụ đủ hai chiều EN-VI, nhận xét gắn đúng bằng chứng và không suy attention/training bias từ hành vi quan sát. Related Work chỉ ra quan hệ với câu hỏi nghiên cứu mà không tuyên bố first/SOTA khi chưa xác minh.

**Bàn giao và report:** viết Related Work và Error analysis, gửi các giới hạn/confounds cho TV5. Branch work/error-analysis; TV5 review PR. Mốc commit: taxonomy/template/citations, công cụ chọn case/tests, rồi case study thật đã đối soát.

## 8 TV5 phụ trách báo cáo và khả năng tái lập

**Trách nhiệm chính:** tích hợp phần viết của cả nhóm và kiểm một người mới có thể tái lập kết quả. TV5 không phải viết thay toàn bộ report hoặc tạo commit hình thức từ file người khác.

**Làm ngay:** tổ chức khung report theo Problems, Related Work, Proposed method, Results/Discussion và Limitations; Methods có thể viết từ protocol hiện có, Results chỉ đặt khung. Kiểm clone/install CPU, đường dẫn/lệnh và phân biệt Git với ZIP dữ liệu/review; bare clone thiếu ảnh phải báo blocker phù hợp.

**Sau QA/run:** kiểm recipe từ manifest/config/raw hashes đến bảng/CI/figures trên snapshot sạch; kiểm report dùng đúng bảng TV3 và cases TV4. Ghi rõ phần cần GPU và phần chỉ CPU. Tổ chức captions, references, figure sources, slides và checklist nộp theo yêu cầu giảng viên đã được nhóm xác nhận.

**Đầu ra:** khung report/slides, reproducibility guide/check scripts hoặc CI phù hợp, lệnh build/export và checklist đối chiếu số liệu. Word V1 tháng 11 giữ scope V4.2 như lịch sử; báo cáo nghiên cứu cuối phải theo V3 và kết quả thật. Bản report tiến độ này không thay cho bản nộp cuối theo format môn học.

**Hoàn tất khi:** đầu ra tái lập bằng lệnh có inputs rõ, report phân biệt pilot/main/tests, claims không vượt evidence, giới hạn precision/subset/QA và bất định được nêu cạnh kết quả. Cả năm người đọc và giải thích được phần mình phụ trách, kiểm tra bản nộp chung.

**Bàn giao và report:** viết Introduction, tổng hợp Discussion/Limitations và biên tập bản cuối; các phần chuyên môn vẫn do TV1-TV4 cung cấp. Branch work/report-reproduction; TV1 review PR. Mốc commit: khung report/recipe, kiểm tái lập có evidence, rồi bản report/slides đã đối chiếu.

## 9 Phân bổ review chung cho 5 người

Mỗi mẫu cần A và B, mỗi người kiểm cả dịch và ảnh/nhãn. Bảng dưới cân bằng 2.000 lượt kiểm mẫu thành 400 lượt/người; mỗi lượt có hai phần quyết định. A/B là vai trò theo gói, khác TV1-TV5 là người phụ trách mảng nghiên cứu.

Nếu nhóm đã nhận hoặc đang làm gói khác, giữ kết quả/người đang làm và cập nhật bảng theo thực tế; không yêu cầu duyệt lại chỉ vì phân công mới. Không điền tên người khác để khớp bảng. Đây là phân bổ đề xuất để nhóm dùng khi các gói chưa được chốt.

| Gói | Mẫu | Lượt A | Lượt B |
|---|---:|---|---|
| repope_01 | 50 | TV1 | TV2 |
| repope_02 | 50 | TV3 | TV4 |
| repope_03 | 50 | TV5 | TV1 |
| repope_04 | 50 | TV2 | TV3 |
| repope_05 | 50 | TV4 | TV5 |
| repope_06 | 50 | TV1 | TV3 |
| repope_07 | 50 | TV2 | TV4 |
| repope_08 | 50 | TV3 | TV5 |
| repope_09 | 50 | TV4 | TV1 |
| repope_10 | 50 | TV5 | TV2 |
| repope_11 | 50 | TV4 | TV3 |
| repope_12 | 50 | TV1 | TV5 |
| vsr_01 | 50 | TV3 | TV2 |
| vsr_02 | 50 | TV5 | TV4 |
| vsr_03 | 20 | TV1 | TV2 |
| tallyqa_01 | 50 | TV3 | TV1 |
| tallyqa_02 | 50 | TV4 | TV2 |
| tallyqa_03 | 20 | TV2 | TV1 |
| oxford_pet_01 | 50 | TV5 | TV3 |
| oxford_pet_02 | 50 | TV1 | TV4 |
| oxford_pet_03 | 50 | TV2 | TV5 |
| oxford_pet_04 | 10 | TV1 | TV2 |

| Thành viên | Mẫu lượt A | Mẫu lượt B | Tổng lượt kiểm mẫu |
|---|---:|---:|---:|
| TV1 | 230 | 170 | 400 |
| TV2 | 170 | 230 | 400 |
| TV3 | 200 | 200 | 400 |
| TV4 | 200 | 200 | 400 |
| TV5 | 200 | 200 | 400 |

A commit JSON sau lượt A rồi gửi B; B lấy đúng bản mới nhất, nạp cùng JSON và commit lượt B. Một JSON cuối/gói được gửi tổng hợp; giữ các lần bàn giao và history. Nếu B sửa VI, A cần duyệt lại bản cuối. Cân bằng số lượt không bảo đảm độ khó/thời gian bằng nhau; nhóm điều chỉnh công khai nếu cần.

## 10 Phối hợp và ghi nhận commit

Trong lúc chờ review, TV1 chuẩn bị tổng hợp dữ liệu, TV2 chuẩn bị main workflow/smoke, TV3 chuẩn bị analysis exports/tests, TV4 chuẩn bị taxonomy/Related Work và TV5 chuẩn bị report/reproduction checks. Khi M1/M2 đạt, TV2 vận hành run; TV3/TV4 phân tích sau raw; TV5 ghép và đối chiếu bản nộp.

Mỗi người dùng tài khoản/author Git của mình và branch đã phân công, commit một thay đổi có ý nghĩa khi thực sự hoàn thành. PR nêu vấn đề, hành vi/đầu ra đã đổi, kiểm chứng và giới hạn. Giữ lịch sử đã push và các commit có ý nghĩa khi merge; không gán lại công việc cũ cho thành viên mới hoặc coi số commit là thước đo duy nhất.

Ví dụ message cho mốc có sản phẩm thật:

- feat(data): validate and assemble reviewed main batches
- feat(inference): add logged four-task smoke selection
- feat(analysis): export paired main tables with coverage
- docs(analysis): define baseline error taxonomy
- docs(report): add verified main reproduction workflow
- review(repope): complete A pass for packet 03
- review(repope): complete B verification for packet 03

Đây là ví dụ cho commit tương lai, không phải các commit đã tồn tại. Với mỗi commit, ghi rõ purpose, completed và validation; phân biệt tests giả, dry-run, human QA và GPU inference thật. Chỉ đưa code/manifests/review JSON và evidence nhỏ cần thiết vào Git; không đưa venv, weights, token, ZIP hoặc HTML nhúng ảnh.

Theo dõi issue bằng sản phẩm và điều kiện hoàn tất. Thứ tự PR reviewer là TV1→TV2, TV2→TV3, TV3→TV4, TV4→TV5, TV5→TV1. Tách file/section report theo người để giảm conflict; cùng một JSON review được chuyển nối tiếp, không sửa đồng thời trên hai nhánh rồi tự ghép quyết định.

## 11 Nội dung xin góp ý từ ChatGPT

Nhờ ChatGPT đọc toàn bộ report và phản biện như người góp ý phương pháp nghiên cứu. Giữ rõ ranh giới: phần mềm đã CPU-tested, pilot thật đã có, còn main chưa human-approved/frozen và chưa có kết quả. Không tạo số liệu, không mặc định VI yếu hơn, không tự mở RQ3/RQ4 thành bắt buộc.

Các câu hỏi cần góp ý:

1. RQ1 negative-only paired ΔFPR và RQ2 bốn task có trả lời được mục tiêu hiện tại không? Denominator, invalid/failed/missing và sensitivity cần diễn giải thế nào?
2. Sampling 1.000 câu/783 ảnh, RePOPE tối đa 2 câu/ảnh, Pet 8 lớp và selection cân bằng tạo giới hạn khái quát hóa nào? Cách bootstrap theo ảnh có nhất quán không?
3. Cặp EN-VI đã kiểm nghĩa nhưng khác ngôn ngữ, precision khác giữa hai model và QA nối tiếp có confounds nào cần nêu? Không dùng chúng để khẳng định cơ chế nhân quả.
4. Cần hoàn thiện gì trước final freeze và bounded GPU smoke? Cách xử lý thay đổi kỹ thuật sau smoke để giữ provenance và tránh tuning theo main accuracy?
5. Phân công TV1-TV5 có cân bằng công việc, dependencies và đầu ra kiểm chứng được không? Những việc nào làm song song ngay, việc nào phải chờ QA/raw?
6. Với thời gian nhóm xác nhận, nên giữ P0 nào và đưa phần nào sang Future Work? Đề xuất cấu trúc report và kế hoạch kiểm chứng, không tự đặt deadline chính thức.

Nếu đề xuất thay đổi, trình bày tác động đến dữ liệu, protocol/hash, công sức và validity trước; giữ nguyên label/source/pilot exclusions và lịch sử có bằng chứng. Các paths/script tương lai trong phân công là đầu ra cần xây, không được suy thành đã triển khai.

Nguồn đối chiếu trong repo:

- reports/completion.md và reports/stage1/v13/completion.md: trạng thái sống và evidence engineering mới nhất.
- reports/stage1/v13/draft_plan.json, software_checks.json, dry_runs.json, package_check.json: grid/gates/tests/installed wheel.
- docs/handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md; docs/research/RESEARCH_PROTOCOL_V3.md và IMPLEMENTATION_PLAN_V3.md: scope/priority/gates.
- docs/research/BASELINE_V1.md và MAIN_REVIEW_V2.md: contract, runner và review A/B.
- reports/stage1/v4 và v7: Qwen/Gemma pilot thật; reports/stage1/v10: pilot QA và main drafts.
- Git b411688: baseline v1; 6dd1b25: review v2; d895db9: hướng dẫn reviewer. Repo github.com/MinhGioChai/cv-final-project.

V3 thay thế các điểm khác nhau của V4.2. Các nguồn trên mô tả snapshot tại ngày 22/11/2026; mức độ hoàn thành nghiên cứu được đánh giá qua gates và sản phẩm, không quy đổi tùy ý từ số test hoặc số commit thành phần trăm.
