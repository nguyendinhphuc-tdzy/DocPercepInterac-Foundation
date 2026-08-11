# Document Perception — Build Status

Trạng thái thực tế của `foundation/` (+ `frontend/`) tính đến thời điểm này.
Đối chiếu với **`../Foundation_Build_Plan_v4.md`** (bản mới nhất, sau buổi họp
chuẩn bị Partners 10/08 — thay thế v3) và `Foundation_Build_Plan_v3.md`
(kiến trúc 2 lớp / data model / API chi tiết, v4 không lặp lại). Cập nhật
file này mỗi khi có module mới hoàn thành — đừng để nó trôi khỏi thực tế code.

---

## ⚠️ ĐÃ LÊN v4 (2026-08-11) — đọc trước khi làm gì tiếp

v4 đổi thật so với v3 ở 6 điểm (xem v4 mục 0), quan trọng nhất với code hiện tại:

1. **Scope MVP1 thu hẹp:** chỉ định dạng **DOC** (Word). Không XLSX/PDF ngay.
   3 module demo: extract, translate, summarize.
2. **Thêm Normalization Layer** bắt buộc trong pipeline — tất định, không AI,
   chuẩn hóa tiền tệ/ngày tháng/đơn vị theo rule KPMG tự định nghĩa, chạy
   trước khi vào Profile. **Chưa có dòng code nào cho bước này.**
3. **Ranh giới Foundation/Application siết chặt hơn:** core chỉ còn đúng 2
   năng lực — (A) tương tác file chuẩn (đọc/ghi/xóa/thay thế theo Anchor),
   (B) hỗ trợ tạo template. Extract/translate/mapping/comparison/summarize
   là **application layer**, gọi vào Foundation qua API, không viết trực
   tiếp vào `perception/`/`adapters/`.
4. **Trạng thái pdfplumber/pdf2image CHƯA chính thức bị từ chối** — chỉ là
   gợi ý cá nhân của anh Quốc dựa trên kinh nghiệm, anh đang tự hỏi lại Risk
   và xin danh sách approved chính thức từ global. Đừng viết "đã bị từ chối"
   trong tài liệu cho tới khi có xác nhận.
5. **Build UI thật (React) phải làm song song ngay**, không chờ MVP core
   xong hẳn — hai việc độc lập nhau về mặt engineering (v4 mục 7).
6. Có thêm lựa chọn hạ tầng thứ 3 (máy local KPMG, cô lập mạng, chạy model
   open/local, dành cho tài liệu không nhạy cảm) — nghiên cứu song song,
   **chưa vào MVP1**.

## ⚠️ SỬA LẠI SCOPE (2026-08-11, cùng ngày): "DOC only" ở v4 mục 1 bị sai — demo đầu là "Local file mapping", input Excel

v4 mục 1 nói MVP1 "chỉ định dạng DOC, XLSX là giai đoạn sau" — nhưng xác nhận
lại với user hôm nay: **use case demo đầu tiên thực tế là "Local file
mapping"**, cơ chế: **input Excel → map → output final là DOCX hoặc Excel**.
Đây không phải mở rộng scope ngoài kế hoạch — nó khớp chính xác với use case
gốc trong `Foundation_Master_Context.md` mục 8 (CIT Finalization workpaper:
*"Upload BCTC → extract → map vào CIT template"*, pain point #1 của Tax
Associates) mà v4 đã vô tình cắt mất khi viết lại mục 1. v4 mục 1 cần coi là
**sai/lạc hậu ở điểm này**, không phải nguồn sự thật nữa cho câu hỏi
"format nào cần build trước".

**Hệ quả cụ thể cho build order:**
- `parse_xlsx()` (đọc geometry từ Excel — input) giờ là **critical path**,
  không phải "giai đoạn sau" — cần làm sớm hơn cả phần còn lại của
  `anchor_builder.py` cho DOCX.
- Anchor cho XLSX **rẻ hơn** DOCX nhiều — theo đúng thiết kế gốc
  (`Foundation_Master_Context.md`): chỉ cần `sheet_name + cell_address`
  (hoặc `named_range` nếu có, ưu tiên hơn `cell_address`) — không cần ladder
  3 tầng như DOCX vì cell address đã đủ ổn định cho file digital.
  `openpyxl`+`defusedxml` đã duyệt, có sẵn trong `requirements.txt`.
- Output cần cả 2 hướng: ghi ra DOCX (đã có `python-docx`, chưa build write
  path) **và** ghi ra XLSX (đã có `openpyxl`, chưa build write path) — đúng
  Output Engine 3 chế độ đã định nghĩa ở v3 (Clone & Replace /
  Profile-driven Fill / Task-shaped), chưa module nào được viết.
- **OCR: xác nhận KHÔNG cần** cho use case này — input luôn là Excel digital
  thuần, không có nguồn scan. Giữ nguyên quyết định gốc (không build OCR),
  không cần cài lại RapidOCR/Tesseract.

**⏸️ TẠM DỪNG (2026-08-11, cùng ngày):** user quyết định chờ buổi họp tiếp
theo để chốt chính thức cấu trúc file Excel thật và quy trình chuẩn của
function GPTS, trước khi viết `parse_xlsx()`/`anchor_builder.py`. Không tự
ý build thuật toán parse/anchor (cả XLSX lẫn DOCX) cho tới khi có input đó
— tránh lặp lại tình huống Docling (code trước, đổi hướng sau, tốn công).
Việc không phụ thuộc buổi họp này (frontend scaffold bước 1-3, research
Digital Gateway/Copilot, xác nhận CRADL) vẫn làm được bình thường, xem bảng
build order bên dưới.

## ✅ ĐÃ GIẢI QUYẾT (2026-08-11): Docling bị loại bỏ hoàn toàn

Quyết định chốt trong nội bộ team: **không dùng Docling nữa**, thay bằng
**pdfplumber + pdf2image** (PDF) và **python-docx** (DOCX) cho Geometry
Layer — đúng track v3, không còn 2 kiến trúc song song.

Đã thực hiện:
- `perception/parser.py` viết lại hoàn toàn: `parse_docx()` (python-docx,
  deterministic, theo đúng field của `AnchorDOCX`), `parse_pdf()`
  (pdfplumber, text + bbox theo dòng, theo đúng field của `AnchorPDF`),
  `render_pdf_pages()` (pdf2image, render trang cho Input Viewer — cần
  Poppler, xem cảnh báo bên dưới), `extract_geometry()` (dispatch theo đuôi
  file — entry point của Geometry Layer).
- `tests/test_parser.py` viết lại theo API mới, tách rõ test DOCX vs PDF
  digital vs PDF scanned (không crash, trả 0 block — đúng hành vi tất định,
  không phải OCR).
- `requirements.txt`: bỏ khối Docling/FastAPI/uvicorn/aiosqlite, gộp lại
  thành 1 kiến trúc duy nhất (Geometry Layer / Classification Layer / Access
  layer Flask).
- Xóa toàn bộ model weights Docling cục bộ (~2.6GB: `foundation/models/*`,
  `docling-models-v1.zip`) — không bị git track (chỉ `models/README.md`
  được track), xóa an toàn, không ảnh hưởng lịch sử git. Xem
  `foundation/models/README.md` đã cập nhật lại.
- Test suite: **16/16 PASS**, thời gian chạy giảm từ **174.96s → 3.60s**
  (không còn load model Docling / JIT-compile torch). Lỗi cũ
  `test_parse_pdf_does_not_crash` (thiếu `cl.exe`) đã biến mất hoàn toàn vì
  không còn phụ thuộc torch.

**Cập nhật (2026-08-11, cùng ngày):** trạng thái duyệt CRADL của
pdfplumber/pdf2image nay đã **chính thức xác nhận approved** — không còn là
"chờ duyệt"/gợi ý cá nhân nữa. v4 mục 0.1 bước 2 (xác nhận lại với anh Quốc)
coi như **đã xong**. Từ giờ dùng 2 package này như bất kỳ dependency đã
duyệt nào khác (`python-docx`, `openpyxl`...), không cần thêm caveat trong
tài liệu nữa.

**Còn 1 điều chưa đổi:**
- **Poppler chưa cài trên máy dev** — `render_pdf_pages()` (dùng
  `pdf2image.convert_from_path`) vẫn fail với
  `PDFInfoNotInstalledError`. Đã verify lại 2026-08-11, chưa đổi. Chỉ ảnh
  hưởng việc render ảnh trang cho Input Viewer — `parse_pdf()` (trích
  text/bbox bằng pdfplumber) không cần Poppler, hoạt động bình thường. Cần
  cài Poppler (OS-level binary, không phải pip package) trước khi Input
  Viewer có thể hiển thị ảnh trang PDF thật.

## ✅ ĐÃ GIẢI QUYẾT (2026-08-11): Frontend scaffold — bước 1-3 mục 7.6 xong

Trong lúc chờ buổi họp chốt Excel/GPTS, đã build phần frontend không phụ
thuộc backend/dữ liệu thật (v4 mục 7.6 bước 1-3):

- **Vite + React 19 + TypeScript** scaffold thật tại `frontend/` (trước đó
  `frontend/src/components/` rỗng hoàn toàn, chỉ có mockup tĩnh). Mockup cũ
  giữ nguyên tại `frontend/mockup-reference.html` để tham chiếu thiết kế,
  không xóa.
- `react-resizable-panels` (bản mới nhất, **4.12.2** — API đổi khác nhiều so
  với v2 mà tài liệu quen thuộc: `Group`/`Panel`/`Separator` +
  `orientation` thay vì `PanelGroup`/`Panel`/`PanelResizeHandle` +
  `direction`. Đã cập nhật code theo đúng API mới, không downgrade) +
  `zustand` — cả 2 đã cài, đúng v4 mục 7.2.
- `DashboardLayout.tsx` — 4 pane thật (Input Viewer / Element Index /
  Intent-Mapping / Output+Trace), kéo-resize được cả chiều ngang lẫn dọc,
  đúng bố cục "1 màn hình, không phải tab" của mockup.
- Toàn bộ component breakdown theo đúng cây thư mục v4 mục 7.3:
  `layout/` (`DashboardLayout`, `PaneHeader`), `input-viewer/`
  (`InputViewer`, `DocumentCanvas`, `BoundingBoxOverlay`), `element-index/`
  (`ElementIndexTable`, `ElementRow`, `ConfidenceBar`, `ReviewBadge`),
  `intent-mapping/` (`IntentMappingPane`, `IntentInput`, `MappingVisual`,
  `MappingNode`), `output-trace/` (`OutputTracePane`, `OutputGrid`,
  `TraceLog`, `TraceItem`), `state/syncStore.ts` (zustand, thay cơ chế
  `data-sync`/`querySelectorAll` của mockup — đúng thiết kế mục 7.4).
- **Chưa có mock data** — đúng yêu cầu user ("build trước, data mock sau
  cũng được"). Mỗi pane hiện render empty state tiếng Việt rõ ràng (vd
  "Chưa có tài liệu nào được tải lên") thay vì trống trơn hoặc lỗi. Props
  đã đánh type sẵn (`src/types/element.ts`, mirror `perception/models.py`)
  nên khi có mock data chỉ cần truyền prop, không cần sửa lại component.
- `IntentInput` input gõ được thật (state cục bộ), nút Apply disabled có
  tooltip giải thích lý do (chưa nối `POST /documents/{id}/intent`) — không
  giả vờ hoạt động khi chưa có backend.
- **Đã verify thật bằng Playwright** (cài tạm để test, đã gỡ sau khi xong —
  không phải dependency chính thức của stack): `npm run dev`, chụp
  screenshot, xác nhận cả 4 pane render đúng tên, 3 separator kéo-resize có
  mặt, `console --errors` rỗng. Không chỉ "build xong không lỗi compile".

**Việc kế tiếp cho frontend (bước 4+ mục 7.6) — vẫn chờ backend:**
`GET /documents/{id}/perceive`, `GET/PATCH /documents/{id}/elements/{index}`,
`GET /executions/{document_id}` chưa tồn tại (xem `api/` rỗng ở mục "Chưa
làm" bên dưới) — chưa nối `react-query` được cho tới khi có endpoint thật.

**Cập nhật cùng ngày — Pane 3 đổi thành chatbox thật:** theo yêu cầu user,
`IntentMappingPane` viết lại từ 1 ô input đơn dòng thành giao diện chat đầy
đủ — `ChatMessageList`/`ChatMessageBubble` (bubble user/assistant, giữ
lịch sử hội thoại), `ChatInput` (textarea nhiều dòng, Enter để gửi,
Shift+Enter xuống dòng), `ToolBadge` (hiển thị tool đang/đã gọi:
Translate/Extract/Map/Compare), `MappingVisual`/`MappingNode` giữ lại
nhưng đổi thành card nhúng trong tin nhắn assistant khi có đề xuất mapping.
Types mới: `src/types/chat.ts` (`ChatMessage`, `ToolCall`,
`MappingProposal`).

**Quan trọng — ranh giới kiến trúc áp dụng ở đây:** chatbox này chính là
mặt tiền của **application layer** (v4 mục 6) — nối OpenAI/Workbench +
gọi tool translate/extract/mapping/compare là việc application, KHÔNG phải
Foundation core. Foundation chỉ thấy các lệnh gọi API kết quả (đọc/ghi
theo Anchor), không bao giờ biết "đây là yêu cầu dịch". Hiện tại nút Gửi
**disabled có chủ đích** (`title` giải thích rõ lý do) — chưa nối OpenAI
thật, chưa có package `applications/`, chưa có endpoint `/intent`. Việc
nối thật là backend/algorithm work — vẫn nằm trong phần đang tạm dừng chờ
họp, không tự ý build.

---

## Đã làm được

### Môi trường & hạ tầng
- Git repo khởi tạo, đẩy lên GitHub (`nguyendinhphuc-tdzy/DocPercepInterac-Foundation`).
- `.gitignore` chuẩn cho Python/Node, loại trừ `.venv`, `__pycache__`, secrets.
- Venv Python 3.11 tại `foundation/.venv`, cài đủ `requirements.txt` — **1
  kiến trúc duy nhất** kể từ 2026-08-11 (không còn 2 track song song):
  Geometry Layer (python-docx, pdfplumber, pdf2image) + Classification
  Layer (openai/Workbench) + Access layer (Flask).
- Model Docling đã **xóa hoàn toàn** khỏi máy dev (~2.6GB). GitHub Release
  `models-v1` vẫn còn trên GitHub cho ai cần tham khảo kiến trúc cũ, nhưng
  không còn dependency nào trong repo trỏ tới nó. Xem `foundation/models/README.md`.

### Code — Layer 2: Detect + Parse (P1)
| Module | Trạng thái | Ghi chú |
|---|---|---|
| `perception/models.py` | ✅ Done (cần bổ sung nhỏ cho v4, xem bảng gap) | Pydantic schemas: `ElementType`, `AnchorDOCX`/`AnchorXLSX`/`AnchorPDF`, `Element`, `ElementIndex`, `Profile`/`ProfileField` |
| `perception/detector.py` | ✅ Done | `detect_format()` — kiểm tra extension + MIME (libmagic), raise nếu mismatch/corrupt |
| `perception/parser.py` | ✅ Done, viết lại 2026-08-11 | `parse_docx()` (python-docx), `parse_pdf()` (pdfplumber, text+bbox), `render_pdf_pages()` (pdf2image, cần Poppler — chưa cài), `extract_geometry()` (dispatch theo đuôi file). Docling đã bỏ hoàn toàn. |

### Tests — đã chạy thật, kết quả 16 passed / 0 failed
```
python -m pytest tests/ -v --tb=short
============ 16 passed in 3.60s ==============
```
(Trước khi bỏ Docling: 12 passed / 1 failed, 174.96s. Sau: 16/16 pass, 3.60s
— không còn load model/JIT-compile torch.)

| File | Trạng thái |
|---|---|
| `tests/test_models.py` | ✅ Pass (6 test) |
| `tests/test_detector.py` | ✅ Pass (4 test) |
| `tests/test_parser.py` | ✅ Pass (7 test) — viết lại theo API mới, gồm test PDF digital (có bbox), PDF digital multi-page với duplicate-text (mục đích: exercise case Strategy 1 anchor sẽ gặp), PDF scanned (0 block, không crash), dispatch theo đuôi file, reject đuôi file lạ |

### Fixtures
Đã có sẵn trong `tests/fixtures/`:
- `fixture_bcdt.docx` — **xác nhận 2026-08-11: đây thực chất là file scan, không phải DOCX digital.** `python-docx` chỉ đọc được 2 paragraph có nội dung / 252 paragraph, 0 table — vì file thực chất chứa 65 ảnh trang nhúng (`word/media/image*.png`, kiểm tra qua zip nội bộ), không có text layer thật. **Đã thử thay bằng `BCTC_hop_nhat_Q2.2026_tu_lap_DT_.docx` (do user cung cấp 2026-08-11) — xác nhận trùng MD5 100% với file đang có, tức là cùng 1 file.** Gap DOCX đa dạng (nhiều heading trùng style, có table) **vẫn chưa được giải quyết** — cần fixture DOCX digital thật khác, hoặc build fixture tổng hợp.
- `fixture_report.pdf` (PDF scan ảnh, 0 chars mọi trang qua `pdfplumber`, không dùng được cho Geometry Layer tới khi có quyết định OCR) — **xác nhận trùng MD5 với `CBTTDK_BCTC_HN_Q2.26_VIE_sign.pdf` do user cung cấp**, cùng 1 file, cũng là bản scan/ký, không giúp thêm.
- `fixture_report_2.pdf` (PDF digital thật) — **xác nhận trùng MD5 với `Neweb VN-2025-VND-VN-1903.pdf` do user cung cấp.** Phân tích sâu hơn 2026-08-11: 32 trang, 9691 từ, 968 dòng text, có 40 nhóm dòng lặp lại (vd: "Công ty TNHH NeWeb Việt Nam" lặp 31 lần, "Mẫu B 09 – DN" lặp 22 lần) — **đa dạng hơn đánh giá ban đầu**, đủ tốt để test case anchor PDF bị trùng text/style qua nhiều trang. Đã thêm test `test_parse_pdf_digital_has_realistic_multipage_diversity` khai thác đúng case này.

**Còn thiếu thật sự:**
- Fixture DOCX digital đa dạng (nhiều heading trùng `style_id`, có table) — vẫn là gap chưa giải quyết, cần cho anchor_builder.py test Strategy 2/3 và table anchor.
- Fixture XLSX — **KHÔNG còn "không gấp"**, xem mục sửa scope ở trên: demo đầu ("Local file mapping") dùng Excel làm input chính. Cần fixture XLSX thật (named ranges, merged cells, nhiều sheet — kiểu template CIT theo Master Context) trước khi build `parse_xlsx()`.

---

## Chưa làm — đối chiếu trực tiếp với v4 (audit 2026-08-11)

| # | Việc theo v4 | Trạng thái code | Ghi chú |
|---|---|---|---|
| 1 | Loại bỏ Docling, chuyển Geometry Layer sang pdfplumber+pdf2image (PDF) / python-docx (DOCX) | ✅ Xong 2026-08-11 | `parser.py` viết lại hoàn toàn, 16/16 test pass. **Lưu ý:** đây là quyết định "bỏ Docling", khác với "pivot về DOC-only" của v4 mục 1-2 — team chủ động giữ nhánh PDF (`parse_pdf`/`render_pdf_pages`) chạy song song thay vì gác lại, đây là lựa chọn có chủ đích của team, không phải sai lệch khỏi plan |
| 2 | `perception/element_classifier.py` (See) | ❌ Chưa | DoclingDocument JSON → `FoundationDocument` typed elements |
| 3 | `perception/anchor_builder.py` (Locate) + P3-04 anchor stability test | ❌ Chưa | IP quan trọng nhất của project, milestone bắt buộc chưa chạm tới |
| 4 | **Normalization Layer** (v4 mục 3) — `NormalizationRule`, hàm `normalize()` | ❌ Chưa — 0 dòng code | Rule tất định (VND/VNĐ→VND, ngày tháng...), tách riêng khỏi Classification |
| 5 | `Element.text` / `text_normalized` field (v4 mục 4) | ❌ Thiếu | `models.py.Element` hiện chỉ có `name` (nhãn hiển thị), không có field chứa nội dung text gốc để Normalization xử lý |
| 6 | `ProfileField.formula: str \| None` (v4 mục 8, placeholder cho Template Authoring Phase 2) | ❌ Thiếu | Việc nhỏ, nên thêm ngay để không chặn mở rộng sau, đúng yêu cầu v4 |
| 7 | Application layer — package `applications/` (v4 mục 6) | ❌ Chưa tồn tại | Chưa vi phạm gì (vì chưa viết use-case nào) nhưng cần nhớ khi bắt đầu extract/translate/summarize |
| 8 | Module `extract` / `translate` / `summarize` (v4 mục 1, 3 module demo) | ❌ Chưa | Không có gì ngoài Detect+Parse |
| 9 | Output engine (v4 mục 5) | ❌ Chưa | Không có module nào |
| 10 | `api/` — Flask routes | ❌ Rỗng | `api/__init__.py` và `api/routes/__init__.py` hoàn toàn trống, chưa có `Flask(__name__)` nào trong code (ngoài site-packages) |
| 11 | **Frontend thật** (v4 mục 7) | ✅ Scaffold xong 2026-08-11 | Xem "Đã giải quyết" bên dưới — bước 1-3 mục 7.6 done, còn lại (kết nối API thật) vẫn chờ backend |
| 12 | Digital Gateway/Copilot competitive research (v4 mục 9) | ❌ Chưa | Checklist rỗng, không tìm thấy tài liệu/slide nào trong repo — bắt buộc phải có trước Executive Summary |
| 13 | Benchmark 3 kịch bản AI (không AI / general / fine-tune local) (v4 mục 0.1-4, mục 11) | ❌ Chưa | Không có benchmark script/kết quả nào |
| 14 | Hạ tầng thứ 3 — máy local cô lập mạng (v4 mục 10) | ⚠️ Đúng kế hoạch, chưa cần vội | v4 tự xác nhận đây là nghiên cứu song song, không chặn MVP |

---

## Chuẩn bị làm (build order theo v4, thay build order v3 cũ)

Ưu tiên theo đúng thứ tự chốt trong họp (v4 mục 0.1):

| # | Việc | Phụ thuộc | Ghi chú |
|---|---|---|---|
| 1 | Gửi câu hỏi xác nhận CRADL chính thức cho pdfplumber/pdf2image + Poppler cho anh Quốc | Không | Việc của người, không phải code — quyết định "bỏ Docling" ở trên là quyết định kỹ thuật nội bộ, KHÔNG thay thế việc xác nhận compliance chính thức này |
| 2 | Research Digital Gateway/Copilot, viết bảng so sánh 3 cột | Không | Bắt buộc trước Partners |
| 3 | ~~Pivot `parser.py`/`detector.py` bỏ Docling~~ | — | ✅ Xong 2026-08-11, xem phần "Đã giải quyết" ở trên |
| 4 | Fixture XLSX thật (named ranges, merged cells, nhiều sheet) | Không | **Nâng ưu tiên 2026-08-11** — chặn #5, cần trước khi viết `parse_xlsx()` |
| 5 | `perception/parse_xlsx()` (Geometry Layer, dùng `openpyxl`) + anchor XLSX (`sheet_name+cell_address`/`named_range`, không cần ladder) | #4 | **Critical path mới** — demo đầu ("Local file mapping") dùng Excel làm input chính, xem mục sửa scope ở trên |
| 6 | `perception/element_classifier.py` → `anchor_builder.py` (DOCX) → **P3-04 PASS** | Không (Docling đã bỏ, không còn block) | Milestone chặn cho nhánh DOCX, không negotiate — vẫn cần vì output có thể là DOCX |
| 7 | Output write path: DOCX (`python-docx`, đã duyệt) + XLSX (`openpyxl`, đã duyệt) | #5, #6 | Đúng Output Engine 3 chế độ đã định nghĩa ở v3 — chưa module nào viết. Cần cho "Local file mapping" ghi ra output final |
| 8 | Normalization Layer (`normalize()`, `NormalizationRule`) | #5, #6 (cần element có `text`) | Tất định, dễ test, làm sau khi có element thật |
| 9 | Thêm field `text`/`text_normalized` vào `Element`, field `formula` vào `ProfileField` | Không | Việc nhỏ, làm sớm để không chặn #8 và #10 |
| 10 | Module mapping (application layer, package `applications/`) cho "Local file mapping" | #5, #6, #7 | Use case demo đầu thật, thay vì extract/translate/summarize như v4 mục 1 cũ ghi |
| 11 | `api/` Flask routes | #5, #6, #10 | Access layer, thay FastAPI |
| 12 | ~~Frontend — bước 1-3 của v4 mục 7.6~~ | — | ✅ Xong 2026-08-11, xem "Đã giải quyết" bên dưới. Bước tiếp theo (mock data thật cho ElementIndexTable/OutputGrid/TraceLog, rồi nối API) vẫn chờ backend/kết quả buổi họp |
| 13 | Benchmark 3 kịch bản AI | #10 | Đo cả độ chính xác lẫn tốc độ |
| 14 | ~~OCR~~ | — | **Xác nhận 2026-08-11: không cần** — "Local file mapping" luôn nhận input Excel digital, không có nguồn scan |

### Quy tắc không được phá vỡ
- P3-04 phải PASS trước khi sang Phase 4.
- Không dùng API ngoài — mọi thứ chạy local/air-gapped.
- Module nào cần biết "đây là use case Tax/GPTS" thì không được nằm trong
  `perception/`/`adapters/` — đặt ở `applications/tax/`, `applications/gpts/`.
- Đừng viết "pdfplumber/pdf2image đã bị từ chối" cho tới khi anh Quốc xác nhận lại.
- Scope MVP1: DOC only. Đừng mở rộng loại file khác trước khi core DOC chứng minh được.
