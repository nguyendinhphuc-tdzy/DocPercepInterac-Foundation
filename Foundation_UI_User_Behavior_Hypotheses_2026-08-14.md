# Foundation UI — Giả thuyết hành vi người dùng

**Ngày:** 14/08/2026
**Ngữ cảnh:** Sau khi hoàn thành tính năng sửa element trực tiếp trên UI
(ghi thẳng vào file output qua Anchor, không cần chạy lại pipeline) —
xem `foundation/STATUS.md` mục 2026-08-14.
**Mục tiêu:** Dự đoán hành vi người dùng thật (Tax Associate / GTPS
reviewer, không phải dev) khi dùng các tính năng hiện có trên Foundation,
để ưu tiên sửa trước khi demo/dùng thật.

**Cập nhật 14/08/2026 (cùng ngày, sau khi viết xong):** review lại phát
hiện toàn bộ phân tích bên dưới bị bias theo đúng 1 use case "Local file
mapping" của GTPS — cả copy UI lẫn hành vi backend (chỉ dùng
`sourceFiles[0]`) đều ngầm giả định "đây là công cụ cho GTPS". Foundation
được định vị là substrate layer dùng chung cho nhiều function
(`Foundation_Master_Context.md` — Tax, Audit, Advisory...), không phải
app riêng cho 1 use case. H3 và H15 đã được sửa ngay (xem cuối file); các
giả thuyết còn lại vẫn giữ nguyên giá trị quan sát nhưng cần đọc với tinh
thần "áp dụng cho use case bất kỳ", không riêng GTPS.

---

## 1. Màn hình Intake (upload)

- **H1 — User sẽ thử upload nhầm định dạng ở ô Source.** Lỗi trả về hiện
  là JSON thô từ API trong banner đỏ — đọc được nhưng hơi kỹ thuật.
- **H2 — User sẽ không đọc dòng mô tả dưới tiêu đề ô upload**, chỉ đọc kỹ
  khi bị chặn (nút Start Processing disabled).
- **H3 — User sẽ kéo nhiều file vào ô Source cùng lúc** (ô cho phép
  `sourceFiles: File[]`) nhưng pipeline trước đây **chỉ dùng
  `sourceFiles[0]`**, các file sau bị im lặng bỏ qua, không cảnh báo.
  **[ĐÃ SỬA — xem mục cuối file]**

## 2. Sau khi bấm Start Processing

- **H4 — Double-click phản xạ vào nút Start Processing** có thể gây 2
  request dù nút đã disable đúng — cần test tay.
- **H5 — Khi upload cặp file không khớp rule nào đã biết, user sẽ hoang
  mang vì thấy "0 mapped"** trong khi Elements/Document vẫn đầy dữ liệu —
  không hiểu tại sao "AI không làm gì" dù đã có state giải thích ngắn.

## 3. Review Elements / Document

- **H6 — User sẽ vào Elements pane trước, Document pane chỉ để đối
  chiếu ngữ cảnh** khi nghi ngờ 1 dòng cụ thể.
- **H7 — Cột Confidence toàn 100% sẽ gây mất niềm tin** thay vì gây yên
  tâm — vì đây là deterministic parse (luôn 100%), không phải AI đánh
  giá, nhưng con số đồng loạt trông giống "hệ thống không thật sự đánh
  giá gì". Cần label rõ ý nghĩa khác với "AI confidence".
- **H8 — Với tài liệu dài (2733 elements), user sẽ dùng Ctrl+F của trình
  duyệt thay vì tính năng nào của app** — ElementsPane chưa có
  search/filter.

## 4. Tính năng sửa trực tiếp (mới)

- **H9 — User sẽ tưởng "sửa trên UI" = "sửa file gốc"**, lo hỏng file đã
  upload — thực tế file gốc được giữ nguyên (đã test), nhưng UI chưa nói
  rõ điều này cho user.
- **H10 — Lỗi khi sửa hiện ở banner đầu pane, dễ bị bỏ lỡ** nếu user đã
  cuộn xuống xa để sửa đoạn khác.
- **H11 — Không có undo.** Rủi ro hành vi cao nhất của tính năng mới: sửa
  nhầm là ghi đè thẳng vào file, không có lịch sử/hoàn tác trên UI (dù có
  log lineage phía sau, chưa hiển thị).
- **H12 — User sẽ thử sửa số liệu ở Source (Excel input) vì trực giác
  "sửa sai thì sửa ở nguồn"** — hiện chỉ Target/output sửa được (đúng
  phạm vi yêu cầu ban đầu "output file"), Source read-only, không giải
  thích tại sao.

## 5. Download / kết quả

- **H13 — User sẽ tải file xuống nhiều lần để tự kiểm tra đã lưu chưa**
  vì thiếu tín hiệu "đã lưu thành công" tích cực (chỉ có banner lỗi, không
  có xác nhận khi thành công).
- **H14 — File tải về giữ nguyên layout gốc sẽ tạo ấn tượng tốt** — đúng
  điểm mạnh thiết kế Clone & Replace, khác cảm giác "AI viết lại tài
  liệu".

## 6. Agent pane (mock)

- **H15 — User sẽ gõ câu hỏi thật vào ô "Ask Foundation..." ngay lần đầu
  dùng**, không thấy phản hồi (pane chưa nối AI thật), dễ hiểu nhầm "app
  bị treo" thay vì "tính năng chưa build". Rủi ro trải nghiệm cao nhất
  toàn bộ demo nếu không cảnh báo trước. **[ĐÃ SỬA — xem mục cuối file]**

---

## Việc đã sửa ngay sau khi viết xong (2026-08-14)

**H3 — Multi-source-file giờ được xử lý đầy đủ, không riêng GTPS:**
`applications/gpts/mapping_service.py::run_mapping()` trước đây implicit
nhận 1 source path. Đã đổi sang nhận **danh sách** source path, extract +
gán anchor cho từng file riêng biệt (element index không đụng nhau giữa
các file), gộp chung vào 1 `source_map` để bất kỳ rule nào (kể cả
DEMO_RULES) tìm khớp trên toàn bộ source, không chỉ file đầu tiên.
`api/routes/process.py` nhận nhiều file qua field `source` lặp lại (Flask
`request.files.getlist`), frontend gửi toàn bộ `sourceFiles`, không chỉ
`[0]`. Đây là generalization thật, áp dụng cho use case bất kỳ cần nhiều
file input (không riêng "FA&RPTs + Appendix I" của GTPS).

**H15 — AgentPane quay lại đúng ý định gốc đã ghi trong STATUS.md:** nút
gửi **disabled có chủ đích**, tooltip giải thích "Chat chưa nối AI thật",
bỏ hội thoại giả lập trước đó (dễ gây hiểu nhầm là lịch sử thật).

**Generalization khác đã làm cùng lúc:** rà soát + sửa toàn bộ copy
UI mang giọng Tax/GTPS ("FA&RPTs", "Local file template"...) sang từ ngữ
trung lập ("source document(s)", "target template") — xem diff
`IntakeScreen.tsx`. Không đổi kiến trúc backend (`perception/` vốn đã
generic từ đầu, `applications/gpts/` vốn đã cô lập đúng chỗ theo
STATUS.md's "Quy tắc không được phá vỡ") — vấn đề bias chủ yếu nằm ở
copy/UX và ở chỗ pipeline chỉ dùng 1 source file, không phải ở core
logic.
