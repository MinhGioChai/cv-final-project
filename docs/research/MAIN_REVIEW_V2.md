# Hướng dẫn review main v2 — A và B cùng kiểm dịch, ảnh và nhãn

Cập nhật 21/11/2026. Tài liệu này dành cho người review, không cần biết lập trình.
Mỗi gói có hai người A/B: A kiểm bản dịch và ảnh/nhãn; B mở JSON của A rồi kiểm lại cả hai. Cuối cùng nộp một JSON chứa hai lượt. Một người chưa đủ hoàn tất.

## 1. Mình đang kiểm tra điều gì?

Project so sánh câu trả lời của VLM khi hỏi cùng ảnh bằng tiếng Anh và tiếng Việt. Trước khi chạy benchmark chính, nhóm cần kiểm tra dữ liệu để hai ngôn ngữ hỏi đúng cùng một điều và nhãn nguồn phù hợp với ảnh.

Bạn cần kiểm hai phần riêng trên mỗi mẫu:

- Bản dịch: câu VI có đúng nghĩa EN, đủ điều kiện và tự nhiên không?
- Ảnh/nhãn: đáp án bạn quan sát từ ảnh và câu hỏi có khớp nhãn nguồn không?

Đây là kiểm dữ liệu, không phải đánh giá đáp án model. Trang không có đáp án model. Bản dịch đúng và nhãn đúng là hai quyết định riêng: một phần có thể approved trong khi phần kia vẫn pending.

Main có 1.000 câu/783 ảnh, chia 22 gói tối đa 50 câu. Không cần duyệt lại pilot 30 mẫu đã hoàn tất.

## 2. Nhận và mở đúng bộ review

Nhận file **main_review_v2.zip**, khoảng **83,4 MiB**, qua kênh chia sẻ riêng của nhóm. Người chỉ review cần gói này; không cần Git, Python, GPU, tài khoản Hugging Face hoặc tải model.

1. Tải ZIP về máy, giải nén toàn bộ vào một thư mục mới.
2. Trong thư mục vừa giải nén, tìm đường dẫn bên dưới.
3. Mở index.html bằng trình duyệt trên máy. Mở file sau khi giải nén, không thao tác ngay trong cửa sổ xem ZIP.
4. Thống nhất với nhóm tên gói và ai là A/B, rồi chọn đúng gói ở mục lục.

```text
reports/stage1/v12/main_review/index.html
```

| Gói | Số gói | Số câu mỗi gói |
|---|---|---|
| repope_01 … repope_12 | 12 | 50 |
| vsr_01 … vsr_03 | 3 | 50, 50, 20 |
| tallyqa_01 … tallyqa_03 | 3 | 50, 50, 20 |
| oxford_pet_01 … oxford_pet_04 | 4 | 50, 50, 50, 10 |

main_review_v2_git_tree.zip là snapshot code phục vụ kiểm chứng kỹ thuật. Người review dùng main_review_v2.zip. HTML/ảnh không nằm trong bản clone GitHub thông thường.

## 3. Một gói đi qua những ai?

```text
A: kiểm dịch + ảnh/nhãn → tải JSON → gửi B
B: mở JSON của A → kiểm lại dịch + ảnh/nhãn → tải JSON cuối
Người tổng hợp: validate/import JSON cuối
```

A/B là vai trò trên từng gói, không phải tên đăng nhập dùng chung. Mỗi người nhập ID/tên của chính mình, ví dụ reviewer_01 và reviewer_02; giữ thống nhất ID đó suốt quá trình làm việc. Không nhập tên của người khác để xác nhận thay họ.

B tiếp tục **cùng một JSON** của A. B không review từ trang trắng rồi gửi một JSON riêng để ghép tự động. Không cần người C chuyên kiểm nhãn.

## 4. Các ô và nút trên trang dùng để làm gì?

| Thành phần trên trang | Bạn làm gì? |
|---|---|
| ID / tên của bạn | Nhập ID/tên của chính mình |
| Lượt đang làm | A chọn Lượt A; B chọn Lượt B |
| Ảnh và Xem ảnh lớn | Quan sát, phóng lớn khi cần |
| EN và Bản dịch VI | Đối chiếu nghĩa; sửa VI khi cần |
| Quyết định dịch, Ghi chú bản dịch | Ghi kết luận về bản dịch |
| Nhãn nguồn, danh sách nhãn | Thông tin nguồn để đối chiếu; không sửa nhãn |
| Đáp án bạn quan sát | Nhập câu trả lời theo đúng định dạng tác vụ |
| Quyết định ảnh/nhãn, Ghi chú ảnh/nhãn | Ghi kết luận sau quan sát |
| Lưu cả hai phần của lượt này | Lưu cả dịch và ảnh/nhãn cho mẫu hiện tại |
| Trước / Sau / danh sách chọn mẫu | Chuyển mẫu sau khi đã lưu |
| Tải JSON review | Xuất toàn bộ kết quả hiện có của gói ra file |
| Mở JSON đã lưu | Nạp file bàn giao hoặc tiếp tục công việc |
| Lịch sử các lượt trước | Xem các lượt đã được thay thế; không tính chúng là duyệt hiện tại |

## 5. Người A thực hiện từng bước

1. Mở đúng gói, kiểm tên gói trước khi bắt đầu.
2. Nhập ID/tên của mình, chọn **Lượt A — dịch và ảnh/nhãn**.
3. Đọc câu EN, đối chiếu bản VI; giữ hoặc sửa bản VI theo mục 7.
4. Chọn Quyết định dịch. Nếu còn vấn đề, ghi rõ ở Ghi chú bản dịch.
5. Đọc câu hỏi/phát biểu, quan sát ảnh; bấm Xem ảnh lớn nếu cần.
6. Nhập Đáp án bạn quan sát đúng định dạng ở mục 8.
7. Đối chiếu Nhãn nguồn, chọn Quyết định ảnh/nhãn và ghi chú nếu cần.
8. Bấm **Lưu cả hai phần của lượt này**. Kiểm thông báo đã lưu và dòng trạng thái A bên dưới.
9. Bấm Sau để làm mẫu kế tiếp. Có thể dừng giữa gói, không phải làm hết trong một lần.
10. Trước khi nghỉ hoặc bàn giao, bấm **Tải JSON review**, xác nhận file đã tải, giữ bản backup và gửi file đó cho B.

Lần đầu nên làm thử 2–3 mẫu, tải JSON rồi mở lại bằng Mở JSON đã lưu để kiểm trạng thái A còn đầy đủ. Sau đó tiếp tục từ mẫu chưa làm; không cần duyệt lại các mẫu đã lưu đúng.

## 6. Người B thực hiện từng bước

1. Nhận JSON mới nhất A gửi, kiểm đúng tên gói.
2. Mở đúng trang HTML của gói đó. Nếu đang có công việc khác trên trang, lưu và tải backup trước khi nạp JSON.
3. Bấm **Mở JSON đã lưu**, chọn file A gửi; kiểm dòng trạng thái A xuất hiện trên mẫu A đã làm.
4. Nhập ID/tên của **B**, chọn **Lượt B — kiểm lại cả hai**.
5. Đọc lại EN/VI và tự quan sát ảnh. Quyết định của A là thông tin tham khảo, không phải lý do để bấm approved khi chưa kiểm.
6. Điền quyết định dịch, đáp án quan sát, quyết định ảnh/nhãn và ghi chú của B. Lưu từng mẫu.
7. Nếu B sửa VI, làm theo mục 10 và gửi lại JSON để A duyệt bản mới.
8. Khi bàn giao, tải JSON cuối và gửi người tổng hợp; ghi rõ gói nào, ai làm A/B, còn mẫu nào pending/rejected.

B không dùng ID của A và không sửa lượt A dưới danh tính A. Nếu A/B có ý kiến khác nhau, giữ quyết định thật và đối soát; không tự đổi quyết định người khác để đủ số approved.

## 7. Duyệt bản dịch như thế nào?

Đánh giá **tương đương ý nghĩa với EN** và sự tự nhiên của VI. Một phát biểu sai so với ảnh vẫn có thể được dịch đúng; không sửa nghĩa câu để biến nó thành phát biểu đúng.

| Cần kiểm | Câu hỏi tự kiểm |
|---|---|
| Đối tượng | Có giữ đúng người/vật được hỏi không? |
| Thuộc tính | Có giữ màu sắc, loại, kích thước và điều kiện lọc không? |
| Quan hệ | Có giữ đúng chủ thể, đối tượng và hướng trên/dưới/trái/phải không? |
| Số lượng | Có giữ đúng nội dung cần đếm, không tự thêm con số đáp án không? |
| Phủ định, lượng từ | Có bỏ/thêm không, mọi, một, các hoặc điều kiện nào không? |
| Độ tự nhiên | VI có dễ hiểu, dùng từ chỉ loại phù hợp như cái bát, con chó không? |
| Thông tin thêm | VI có tự thêm gợi ý từ ảnh hoặc nhãn mà EN không có không? |

Ví dụ minh họa, không phải kết quả review dữ liệu thật:

- Is there a bowl in the image? → Trong ảnh có cái bát nào không? Giữ cùng câu hỏi có/không; không đổi thành Trong ảnh có bao nhiêu cái bát?
- The cat is under the table. → Con mèo ở dưới bàn. Không dịch thành ở trên bàn, và không đổi quan hệ chỉ vì ảnh khiến phát biểu gốc có vẻ sai.
- How many red cars are there? → Có bao nhiêu chiếc xe màu đỏ? Không bỏ điều kiện màu đỏ.

Nếu nghĩa EN đủ rõ, sửa VI để tương đương rồi duyệt bản đã sửa. Nếu EN mơ hồ hoặc không chắc bản dịch, giữ pending/rejected và ghi cụ thể điểm chưa rõ. Không tự viết lại câu EN hoặc đổi nhãn nguồn.

## 8. Kiểm ảnh và nhãn theo từng tác vụ

Trước hết đọc đúng câu hỏi/phát biểu, quan sát ảnh rồi nhập đáp án của mình. Nhãn nguồn dùng để đối chiếu sau quan sát, không phải đáp án để chép lại khi chưa kiểm. Nếu không xác định được, nhập uncertain và ghi lý do.

### 8.1 RePOPE — vật thể có xuất hiện không?

Nhập **yes** nếu vật thể được hỏi có trong ảnh, **no** nếu quan sát đủ rõ và không có vật thể đó. Chỉ hỏi vật thể trong câu, không xét những vật khác để suy ra nhãn. Nhãn no là trường hợp bình thường, không phải dữ liệu sai.

Nếu vật thể quá nhỏ, bị che hoặc không phân biệt được, nhập uncertain, ghi chú và giữ pending/rejected. Không dùng ước đoán từ bối cảnh để ép yes/no.

### 8.2 VSR — phát biểu quan hệ đúng hay sai?

Nhập **yes** nếu phát biểu đúng, **no** nếu phát biểu sai. Trên trang, yes tương ứng TRUE và no tương ứng FALSE.

Kiểm đúng thứ tự chủ thể–quan hệ–đối tượng. Nếu EN nói A ở dưới B, không đọc thành B ở dưới A. Nếu phát biểu sai so với ảnh, giữ đúng bản dịch phát biểu đó và nhập no; không sửa VI cho phát biểu trở thành đúng.

### 8.3 TallyQA — đếm theo điều kiện câu hỏi

Nhập số nguyên không âm bằng chữ số, như **0**, **2**, **12**. Không nhập hai, 2 con, 2.0 hoặc khoảng 2. Đếm đúng đối tượng/thuộc tính/điều kiện được hỏi, không đếm mọi vật trong ảnh.

Nếu bị che khuất hoặc điều kiện đếm không rõ, dùng uncertain và ghi lý do. Không tự đoán số vật ngoài ảnh.

### 8.4 Oxford-IIIT Pet — chọn giống chó trong tám lớp

Nhập **một chữ in hoa A–H** theo danh sách ngay trên trang. Không nhập tên giống, yes/no hoặc mã lớp của bộ Pet đầy đủ. Không chắc giống thì nhập uncertain và ghi chú.

| Mã đáp án | Giống chó |
|---|---|
| A | American Bulldog |
| B | American Pit Bull Terrier |
| C | Basset Hound |
| D | Beagle |
| E | Boxer |
| F | Chihuahua |
| G | English Cocker Spaniel |
| H | English Setter |

A–H trong ô đáp án là mã giống chó; A/B ở menu Lượt đang làm là vai trò reviewer. Hai thứ này khác nhau. Giữ nguyên tên giống và mapping giữa EN–VI.

## 9. Chọn approved, pending hay rejected?

Hai phần dịch và ảnh/nhãn được chọn riêng. Không phải cứ lưu là phải approved.

| Trạng thái | Khi nào dùng? | Cần làm thêm |
|---|---|---|
| approved | Đã kiểm và đồng ý; với ảnh/nhãn, quan sát phải khớp nhãn nguồn | Lưu quyết định thật của mình |
| pending | Chưa kiểm xong, chưa đủ chắc hoặc cần trao đổi | Ghi điểm còn vướng nếu có; có thể tiếp tục sau |
| rejected | Đã phát hiện vấn đề cần xử lý | Bắt buộc ghi chú rõ lý do |

uncertain là nội dung ô Đáp án bạn quan sát, không phải lựa chọn trong menu trạng thái. Khi nhập uncertain, phải ghi chú ảnh/nhãn và để pending hoặc rejected; không chọn approved.

Ví dụ ghi chú có ích: VI đang bỏ điều kiện màu đỏ; Vật thể ở góc trái quá nhỏ để xác định; Quan sát được 3 vật nhưng nhãn nguồn là 4, cần đối soát. Tránh chỉ ghi sai hoặc không rõ mà không nói vướng ở đâu.

## 10. Nếu B sửa VI hoặc hai người không đồng ý

Khi bản VI đổi và được lưu, các lượt cũ của cả A/B được đưa vào **Lịch sử các lượt trước**; chúng không còn tính cho bản mới. Điều này áp dụng cả phần ảnh/nhãn vì mỗi lượt được gắn với câu VI đã xem.

1. B sửa VI, kiểm cả hai phần trên bản mới và lưu Lượt B.
2. B tải JSON mới gửi lại A, chỉ rõ những mẫu đã sửa.
3. A mở JSON đó, dùng ID của A và Lượt A, kiểm lại cả hai phần trên bản cuối.
4. Nếu A giữ nguyên bản VI và đồng ý thì lưu rồi gửi JSON cập nhật để tổng hợp. Nếu A lại sửa VI, B cần kiểm lại bản mới tiếp theo.

Lịch sử giúp truy vết, không thay cho việc duyệt bản hiện tại. Với bất đồng về ảnh/nhãn hoặc bản dịch, trao đổi và ghi chú, giữ pending/rejected khi chưa giải quyết. Không tự bỏ mẫu, đổi nhãn nguồn hoặc lấy đa số để làm mẫu đạt.

## 11. Lưu, nghỉ giữa chừng và bàn giao JSON

**Lưu cả hai phần** cập nhật trạng thái trên trang/browser; **Tải JSON review** mới tạo file để gửi và khôi phục trên máy khác. Dữ liệu tự lưu có thể phụ thuộc trình duyệt/máy; không dựa vào nó làm bản duy nhất.

Khi nghỉ, lưu mẫu đang làm rồi tải JSON. Khi quay lại hoặc đổi máy, mở đúng gói HTML, nạp JSON mới nhất, nhập đúng ID/lượt và chọn mẫu cần tiếp tục. Vị trí đang xem có thể trở về đầu; đối chiếu trạng thái từng mẫu, không suy ra rằng kết quả đã mất chỉ vì đang ở mẫu đầu.

File tải thường có tên như:

```text
repope_01_reviewed_v2.json
```

Giữ tên gói trong tên file. Trình duyệt có thể thêm (1), (2) khi tải nhiều lần; kiểm file mới nhất và đúng nội dung trước khi gửi. Có thể cất các lần bàn giao ở thư mục riêng để tránh ghi đè:

```text
ket_qua_review/
  repope_01/
    ban_A/repope_01_reviewed_v2.json
    ban_AB/repope_01_reviewed_v2.json
```

Không sửa nội dung JSON bằng tay để đổi reviewer/approved hoặc ghép hai file. Mở JSON đã lưu sẽ nạp một bản trạng thái của gói, không tự gộp với mọi bản đã có. Nếu đang có công việc khác trên trang, tải backup trước khi nạp.

## 12. Đọc bộ đếm và kiểm trước khi gửi

Ví dụ **1/50 · Đủ hai lượt: 0/50** nghĩa là bạn đang xem mẫu thứ nhất trong gói 50 mẫu, chưa có mẫu nào được cả A và B approved cả hai phần.

Sau khi chỉ A làm xong, Đủ hai lượt vẫn có thể là 0/50. Đây là bình thường; xem dòng A trên từng mẫu để kiểm công việc A đã lưu. B không cần xóa hoặc làm lại lượt A.

Trước khi gửi, kiểm:

- Đúng tên gói, đúng bản JSON mới nhất.
- ID của mình và lượt A/B đúng; hai người không dùng chung ID.
- Các mẫu đã kiểm có trạng thái dịch và ảnh/nhãn đúng với nhận xét thật.
- Các mẫu pending/rejected hoặc VI đã sửa được ghi rõ để người nhận biết việc còn lại.
- Đã lưu mẫu cuối, tải JSON và thử mở lại để xác nhận dữ liệu còn đủ.

Nộp JSON cuối chứa cả A/B cho người tổng hợp, kèm thông tin ngắn: gói nào, ai là A/B, còn mẫu nào cần xử lý. Nếu gói chưa xong, vẫn có thể bàn giao bản đang làm nhưng phải nói rõ; không đánh dấu hoàn tất. File HTML gốc, ảnh chụp màn hình hoặc tin nhắn đã làm xong không thay thế JSON quyết định.

Đủ hai lượt trên trang chưa tự cập nhật dataset. Người tổng hợp còn validate/import JSON và đối soát dữ liệu; có file JSON không đồng nghĩa main đã frozen hoặc được phép chạy benchmark chính.

## 13. Các lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Không thấy index.html | Kiểm đã giải nén đúng main_review_v2.zip và mở reports/stage1/v12/main_review/index.html |
| Nhận git_tree ZIP hoặc bộ v1 | Nhận lại main_review_v2.zip; giữ kết quả cũ nếu đã làm, báo người tổng hợp |
| Ảnh không hiện | Mở sau khi giải nén đầy đủ; thử Xem ảnh lớn, ghi tên gói/mẫu và báo lỗi nếu vẫn không thấy; không approve ảnh chưa xem được |
| Nhắc lưu trước khi chuyển mẫu/lượt/tải | Lưu mẫu hiện tại rồi thao tác tiếp; nếu còn vướng thì để pending và ghi chú |
| A và B phải là hai người khác nhau | B nhập ID riêng và chọn Lượt B; không dùng ID của A |
| Lượt này thuộc ID khác | Kiểm đúng lượt và đúng ID đã dùng trước đó; không đổi ID để ghi đè người khác |
| Quan sát chưa khớp nhãn | Kiểm lại ảnh/định dạng; nếu thật sự khác, để pending/rejected và ghi chú, không chép nhãn để được approved |
| JSON không thuộc đúng gói v2 | Mở đúng gói/phiên bản; không sửa context hoặc IDs trong JSON |
| Sau sửa VI, trạng thái A thành pending | Đây là lượt duyệt trên bản mới; gửi JSON cho A kiểm lại, lượt cũ còn trong lịch sử |
| Mở lại chưa thấy công việc | Nạp JSON đã tải mới nhất; kiểm đúng gói/lượt. Nếu mất cả file và bản tự lưu, báo người tổng hợp để tìm backup |

## 14. Ví dụ một vòng review

Ví dụ minh họa, không phải một mẫu đã được người thật duyệt: câu hỏi về cái bát, nhãn nguồn no và ảnh đủ rõ để xác nhận không có bát.

1. A dùng ID reviewer_01, Lượt A; kiểm bản VI đúng nghĩa, chọn dịch approved; quan sát no, chọn ảnh/nhãn approved; lưu và tải JSON.
2. B mở JSON đó, dùng ID reviewer_02, Lượt B; tự kiểm lại câu và ảnh, cũng ghi dịch approved, quan sát no và ảnh/nhãn approved; lưu rồi tải JSON cuối.
3. JSON cuối có cả hai người. Người tổng hợp kiểm/import; A và B không phải tự chạy Python.

Nếu B không thấy rõ vật thể, B nhập uncertain kèm ghi chú và giữ pending; mẫu đó còn chờ xử lý dù A đã approved. Mục tiêu là quyết định có căn cứ, không phải đạt 100% approved bằng mọi cách.

## Phụ lục — dành cho người làm code/import

Git giữ code, template v2, packet CSV/JSON pending và packets.json. Generated
HTML nhúng ảnh và ZIP vẫn ngoài Git. Main 1.000 câu/783 ảnh chưa approved,
chưa frozen; export hoặc tests không tạo human approval.

Sau khi clone và restore `team_workspace_v1.zip` để nhận ảnh/cache theo hướng
dẫn nhóm, sinh bộ mới:

```powershell
.venv/Scripts/python.exe scripts/review_main.py export --version v2
.venv/Scripts/python.exe scripts/review_main.py bundle --version v2 --archive exports/main_review_v2.zip --report reports/stage1/v12/review_bundle.json
```

ZIP/report phải có đường dẫn mới nếu đã tồn tại; đổi tên version khi đóng
gói lại. Export idempotent nhưng từ chối ghi đè file khác bytes, kể cả JSON
đã được người dùng chỉnh. Chỉ nhận ZIP riêng để review thì không cần clone,
Python, GPU hoặc workspace ZIP lớn. Checksum ở [bundle receipt](../../reports/stage1/v12/review_bundle.json).

Lưu JSON cuối vào `data/reviews/main_review_v2/`. Dry-run ví dụ:

```powershell
.venv/Scripts/python.exe scripts/review_main.py import --version v2 --manifest data/reviews/main_review_v2/repope_01.csv --review data/reviews/main_review_v2/repope_01_reviewed_v2.json --output data/main/reviewed_v2/repope_01.csv --audit reports/main_review/repope_01_import_v2.json --operator YOUR_IMPORTER_ID --dry-run
```

Thay ID người import thật. Hợp lệ mới bỏ --dry-run; giữ source batch CSV gốc,
dùng output/audit mới. Import kiểm policy/template/manifest/row hashes, đủ IDs,
ảnh, ID/time, bản VI hiện tại và cả hai QA. Operator không mặc nhiên là reviewer.
Sau từng batch còn cần tổng hợp/đối soát 1.000 IDs, xử lý bất đồng, metadata và
full runner trước freeze. Không tự cho phép chạy 4.000 inference.

## Bản v1 và các gói đã chia sẻ

V1 vẫn giữ nguyên tại data/reviews/main_review_v1 và reports/stage1/v10.
Template/backend v1, hai ZIP cũ, raw và báo cáo lịch sử không sửa. CLI mặc định
mới là v2; muốn xử lý v1 phải ghi rõ `--version v1`. JSON v1 không được mở hoặc
import như v2, và QA v1 của một người không được tự biến thành hai người duyệt.
Nếu đã có review v1 thật, giữ file gốc và đối soát riêng trước chuyển phiên bản.

Giao diện được kiểm qua JS handlers với DOM giả lập và backend synthetic
tests; chưa visual browser QA hoặc thử nghiệm với hai reviewer thật.
