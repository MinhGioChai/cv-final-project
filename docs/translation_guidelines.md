# Translation and QA

**Hiện tại — 12/11/2026:** 30 bản VI trong manifest stage1_v3 đã được người
dùng chấp nhận ngôn ngữ; cả 30 QA ảnh/nhãn còn pending. Không hỏi lại acceptance
cũ hoặc tạo reviewer thứ hai. Theo [V3](handoffs/EN_VI_VLM_CODEX_HANDOFF_V3.md),
ưu tiên dữ liệu RQ1/RQ2; paraphrase/visual evidence là P1 có điều kiện,
negation riêng là Future Work. [Protocol](research/RESEARCH_PROTOCOL_V3.md).

**Lịch sử — Stage 1 v2:** theo phản hồi người dùng, template chuyển sang
`repope_object_existence_vi_v2_classifiers`. Dictionary có cột `classifier_vi`
riêng, ví dụ cái bát/chiếc xe đạp/con chó/quả cam; person dùng người nào.
Legacy dictionary không có cột này vẫn đọc được. Pilot có 30 draft; xem
[preview mới nhất](../reports/stage1/v2/translation_preview.md) và
[so sánh sửa 10 câu](../reports/stage1/v2/feedback_comparison.md).
Nhận xét thật của người dùng về 10 câu cũ đã được lưu; không tự suy ra QA ảnh
hoặc reviewer thứ hai cho các câu sửa và 20 mẫu mới.

**Cập nhật Stage 1 v1 — 09/11/2026:** đã có dictionary/template draft,
`export-translation-review` và `import-translation-review`. Mười bản dịch nháp
đã xuất; tất cả vẫn requires_review/pending QA. Xem
[quy trình review và import](review_workflow.md), [preview](../reports/stage1/v1/translation_preview.md).
Các đoạn mô tả Stage 0 bên dưới là mốc trước khi có tooling Stage 1.

Stage 0 chưa dịch tự động và chưa duyệt nhãn. Manifest có `question_vi=""`,
`translation_status=missing`, `qa_status=pending`, `is_pilot=true`.
Đây là trạng thái hợp lệ cho preflight kỹ thuật, không hợp lệ cho main.

`reports/stage0/sample_review.csv` là bảng để nhóm xem câu hỏi, nhãn nguồn và
đường dẫn ảnh. Mở bằng UTF-8 và giữ `image_id` ở dạng text để không mất số 0 đầu.
Có thể thêm bản dịch VI và ghi trạng thái hai reviewer/notes; Stage 0 chưa có
lệnh import review vào manifest. Không sửa nhãn gốc dựa trên đáp án VLM.

Phạm vi Stage 1 và các stage sau:

1. Template matching chính xác cho RePOPE và từ điển object EN–VI đã review.
   Không match hoặc ngoài từ điển thì đưa vào hàng chờ, không đoán nghĩa.
2. Import bản dịch đã duyệt có kiểm tra `sample_id` và audit trail. Không tự
   gán approved cho bản dịch máy.
3. Duyệt toàn bộ VSR/TallyQA; giữ danh từ, quan hệ trái/phải/trước/sau, lượng
   từ và polarity. Hai ngôn ngữ dùng cùng đáp án chuẩn.
4. Giữ cùng tên/ID/thứ tự 8 giống Pet; chỉ dịch hướng dẫn khi tên riêng không
   có bản dịch chuẩn.
5. Chỉ khi có quyết định triển khai mở rộng: visual evidence cần review target/
   nhãn và bối cảnh; negation riêng thuộc P2 Future Work theo V3, không tự tạo.

Lệnh `prepare-pilot` giữ nguyên review sheet hiện có và từ chối ghi đè manifest
nếu dữ liệu sinh lại khác. Khi tạo pilot phiên bản mới, dùng đường dẫn manifest
và report mới; registry ảnh loại khỏi final vẫn tích lũy.
