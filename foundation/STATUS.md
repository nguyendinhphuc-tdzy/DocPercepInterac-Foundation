# Document Perception — Build Status

Trạng thái thực tế của `foundation/` (+ `frontend/`) tính đến thời điểm này.
Đối chiếu với **`../Foundation_Build_Plan_v5.md`** và `Foundation_Build_Plan_v4.md` / `v3`.

---

## 📍 TÌNH TRẠNG HIỆN TẠI (2026-08-19) — Stage B: Full Foundation Audit Completed

- **Comprehensive Audit Report**: Đã tạo tài liệu kiểm toán kiến trúc toàn diện tại `docs/audit/Foundation_Core_Audit_2026-08-19.md`.
- **Backend Test Suite**: **109/109 tests PASS** (0 warnings, 0 errors).
- **Stage A Baseline Hardening**: Đã kiểm tra đối chuẩn trên fixture khó `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx` (848 elements) — đạt **802/848 (94.6%)** direct mapping DOM:
  - Paragraphs: 210/210
  - Headings: 60/60
  - Table Cells: 505/505
  - Footnotes: 25/25
  - Footer: 1/1
  - Bidirectional click & tree synchronization verified via Playwright.
- **Frontend Type & Lint Check**: `npm test` (`oxlint && tsc -b && vite build`) đạt 0 warnings, 0 errors.
- **Git Hygiene**: Đã dọn dẹp file ảnh tạm `UsersPCAppDataLocalTemp...` khỏi git tracking.

---

## 📍 TÌNH TRẠNG LỊCH SỬ (2026-08-14) — đọc mục này nếu cần tra cứu tiến trình cũ

Toàn bộ nội dung từ mục "✅ ĐÃ GIẢI QUYẾT (2026-08-14): Access layer..."
trở xuống (trước bảng "Đã làm được") là **1 phiên làm việc duy nhất, cùng
ngày 2026-08-14** — không phải nhiều ngày như số thứ tự cũ từng ghi nhầm
(đã sửa lại toàn bộ ngày tháng trong file này cho đúng). Mục này tóm tắt
kết quả cuối cùng của phiên đó; đọc các mục "✅ ĐÃ GIẢI QUYẾT" bên dưới nếu
cần biết **tại sao**/**như thế nào**.

**Backend (`foundation/`) — chạy được thật, 48/48 test pass:**
- Geometry Layer (`perception/parser.py`) — parse DOCX/XLSX/PDF tất định,
  không AI. Giữ cả table cell rỗng (placeholder thật, không phải noise).
- **Anchor system** (`perception/anchor_builder.py`, IP cốt lõi) — assign +
  resolve cho cả 3 định dạng, **P3-04 PASS thật**, tự hồi phục qua drift
  (DOCX table hash, DOCX paragraph tie-break qua `duplicate_ordinal`, XLSX
  qua nhãn dòng, PDF qua vị trí). Generic — không biết gì về GTPS.
- Application layer (`applications/gpts/mapping_service.py`) — pipeline
  đầy đủ cho demo "Local file mapping": nhận N file source + 1 file
  target, trả elements thật + áp `DEMO_RULES` (hard-code 1 client HMV,
  không phải logic chung).
- Access layer (`api/app.py`, `api/routes/process.py`) — `POST
  /api/process`, `PATCH /api/elements/<id>` (sửa 1 element, ghi thẳng vào
  output, không chạy lại pipeline), `GET /api/download/<id>`.
- **Không có database** — mọi thứ file-based dưới `.uploads/<id>/`
  (gitignored). Chưa cần, xem lý do trong hội thoại 2026-08-14 nếu cần
  tham khảo lại (chưa lưu thành mục riêng ở đây).

**Frontend (`frontend/`) — 1 màn hình workspace duy nhất, không còn Intake riêng:**
- Thêm document qua nút "+" ngay trong pane DOCUMENT — tự phân loại
  source/target theo đuôi file, không bắt user chọn vai trò thủ công.
- Sửa element trực tiếp trên UI (Document + Elements pane) → ghi thẳng
  vào file output qua PATCH, có **Undo** (session-only, nút ở header +
  Ctrl/Cmd+Z), hover 1 pane → highlight + tự cuộn tới element liên quan ở
  pane khác (Document ↔ Elements ↔ Results).
- Copy đã trung lập hóa (không còn giọng Tax/GTPS). `AgentPane` là
  placeholder trung thực (input disabled, không giả vờ hoạt động) — chưa
  nối AI thật.

**Giới hạn thật, không phải bug, cần nhớ khi demo:**
- `DEMO_RULES` chỉ khớp đúng 1 client (HMV) — file khác vẫn extract +
  anchor thật nhưng `mapped: []`.
- `element_classifier.py` chưa build — không có phân loại/đề xuất mapping
  tự động cho tài liệu chưa biết trước ngoài GTPS/HMV.
- Sửa trực tiếp (PATCH) chỉ hỗ trợ output DOCX, chưa mở route cho XLSX
  (engine phía dưới đã hỗ trợ, chỉ chưa nối route).
- `detect_format()` (MIME check) reject nhầm file `.docx`/`.xlsx` thật
  trên máy dev này — `api/` không dùng hàm này để validate.
- Poppler chưa cài — `render_pdf_pages()` (ảnh trang PDF) chưa dùng được.
- Digital Gateway/Copilot research + benchmark AI: deprioritized theo yêu
  cầu user, chưa làm, không phải bỏ.

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

**⚠️ SUPERSEDED (2026-08-14):** toàn bộ cây component mô tả ở trên
(`DashboardLayout`, `input-viewer/`, `element-index/`, `intent-mapping/`,
`output-trace/`) đã bị **thay thế** bởi một bản dựng lại frontend, không
xóa file cũ (vẫn nằm trong `src/components/` làm tham chiếu) nhưng
`App.tsx` không còn render chúng nữa. Xem mục "✅ ĐÃ GIẢI QUYẾT
(2026-08-14)" ngay bên dưới cho kiến trúc hiện hành thật sự.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-14): Access layer (Flask) + application layer (GTPS) xong, frontend nối API thật cho use case demo đầu

**Bối cảnh:** user báo lỗi UI "màn hình trắng, chỉ hiện text" khi build —
audit phát hiện 2 lớp vấn đề tách biệt, cả hai đã xử lý xong trong phiên
này.

**⚠️ SUPERSEDED (2026-08-14):** flow "Intake → Workspace" mô tả ngay dưới
đây đã bị thay bằng **1 màn hình duy nhất** — xem mục "Bỏ màn hình Intake
riêng" ở dưới. `IntakeScreen` đã bị xóa hẳn khỏi repo, không phải chỉ
ngừng render.

**1. Bug UI thật (đã sửa) — Tailwind CSS chưa từng được cài:**
Frontend đã được dựng lại (không rõ từ phiên nào, không có ghi chú trước
đó trong file này) thành flow **Intake → Workspace** hoàn toàn mới, thay
cho `DashboardLayout` 4-pane mô tả ở mục "Frontend scaffold" phía trên:
- `App.tsx` → `IntakeScreen` (upload Source + Target, nút "Start
  Processing") hoặc `WorkspaceLayout` (`WorkspaceHeader` + 4 pane:
  `DocumentPane`/`ElementsPane`/`AgentPane`/`ResultsPane`, dùng
  `react-resizable-panels` `Group`/`Panel`/`Separator` với prop
  `orientation` — đúng API 4.12.2, khớp ghi chú cũ).
- State: `state/workspaceStore.ts` (zustand) thay `syncStore.ts` cũ.
- Toàn bộ component mới viết bằng Tailwind utility classes
  (`flex`, `bg-gray-50`, `rounded-lg`...) nhưng **`tailwindcss` không có
  trong `package.json`, không config, không `@tailwind`/`@import` nào
  trong `index.css`** — mọi class vô tác dụng, render ra HTML không style
  (đúng triệu chứng "trắng, chỉ hiện text"). Đã cài `tailwindcss` +
  `@tailwindcss/vite` (v4, plugin-based, không cần `postcss.config`),
  thêm `@import "tailwindcss";` vào `index.css`. Đồng thời sửa
  `WorkspaceLayout.tsx` dùng nhầm prop `direction` (API cũ) thay vì
  `orientation` (API 4.12.2 thật) trên `Group`.
- `frontend/src/App.tsx`, `WorkspaceHeader.tsx` có 2 unused-import lỗi
  chặn `tsc -b`/`npm run build` — đã dọn.

**2. Access layer + application layer (mới xây, chưa có gì trước đó):**
`api/` trước đây hoàn toàn rỗng (mục "Chưa làm" #10 cũ). Đã build:
- `foundation/applications/gpts/mapping_service.py` — package
  `applications/` (v4 mục 6, mục "Chưa làm" #7 cũ) đầu tiên trong repo.
  Chứa `geometry_block_to_element()` (adapter `GeometryBlock` →
  `Element`/`Anchor` pydantic thật, KHÔNG phải
  `element_classifier.py` — type là heuristic tối thiểu, có ghi chú rõ
  trong code để không ai nhầm đây là Classification Layer thật) và
  `run_mapping()` (gọi lại `mapping/demo_mapper.py`'s `DEMO_RULES` +
  `mapping/lineage.py` + `mapping/writeback.py`, parameterized theo
  path thay vì hard-code, trả JSON-serializable thay vì print).
- `foundation/api/app.py` + `api/routes/process.py` — Flask thật đầu
  tiên trong repo. `POST /api/process` (nhận multipart source+target,
  chạy `run_mapping`, trả elements + mapped + `download_url`),
  `GET /api/download/<id>` (trả DOCX đã patch). CORS mở (`*`, local-only
  tool, không có auth boundary).
- `perception/models.py`: `AnchorDOCX.paragraph_index` đổi từ `int` bắt
  buộc → `Optional[int] = None` (table-cell block không có
  paragraph_index) + thêm `table_hash` — mirror sang
  `frontend/src/types/element.ts`. Đây là phần "cần bổ sung nhỏ" đã ghi
  chú sẵn ở bảng P1 phía trên.
- `mapping/lineage.py::log_mapping()` giờ `return record` (trước đây
  không return gì) — để API có data trả JSON, không phá caller cũ
  (`demo_mapper.py` không dùng giá trị trả về).
- Frontend: `src/api/client.ts` (fetch + FormData), `workspaceStore.ts`
  thêm `runProcessing()`, 4 pane (Document/Elements/Agent trừ ra/Results)
  đọc dữ liệu thật thay vì mock cứng. `AgentPane` **cố tình chưa đụng** —
  vẫn đúng ranh giới đã ghi ở trên (chờ OpenAI/Workbench thật).

**Giới hạn đã biết, không phải bug:** `DEMO_RULES` hard-code cho đúng 1
client (HMV) — chỉ map ra kết quả non-zero khi nguồn là
`HMV-FA&RPT FY2024.xlsx` và đích là 1 trong các bản Local File HMV (kể cả
bản `_drifted`, nhờ self-healing anchor). File bất kỳ khác vẫn parse ra
elements thật (kèm anchor thật — xem mục P3-04 ngay dưới), `mapped: []` —
hành vi đúng của MVP, chưa có `element_classifier.py` (mục "Chưa làm" #2,
vẫn ❌ chưa làm — khác với anchor, đây là bước phân loại ngữ nghĩa, đề xuất
mapping tự động cho tài liệu chưa biết trước, KHÔNG phải bước gán anchor).

**Phát hiện mới — gotcha máy dev:** `perception/detector.py::detect_format()`
(MIME check qua `python-magic-bin`) **reject cả file `.docx` thật, chưa
chỉnh sửa gì** trên máy dev này — libmagic bundle detect ra
`application/octet-stream` thay vì OOXML mime thật. `api/routes/process.py`
vì vậy **không dùng `detect_format()`** để validate upload, chỉ check đuôi
file (giống cách `extract_geometry()` tự dispatch). Chưa điều tra sâu
`detect_format()` — nếu sau này cần dùng lại (vd validate ở chỗ khác),
nhớ gotcha này trước.

**Tests:** 18 → **20 passed** (`tests/test_mapping_service.py` mới, 2
test — 1 chạy thật với fixture HMV thật, skip nếu máy không có
`anonymize client/Demo files/`, 1 test cặp file bất kỳ → xác nhận
`mapped == []`). Đã verify thật qua browser (Playwright, cài tạm rồi gỡ
— cùng cách team làm 2026-08-11): upload đúng cặp file demo → Document
pane hiện mục lục thật, Elements pane hiện đủ 2733 elements thật, Results
pane hiện "3 mapped" + giá trị thật + link tải DOCX đã patch, 0 lỗi
console.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-14, cùng ngày): `perception/anchor_builder.py` thật + P3-04 PASS — milestone lớn nhất đã chạm tới

**Bối cảnh:** user yêu cầu rõ — tạm gác research Digital Gateway/Copilot và
benchmark AI, tập trung xây thuật toán anchor **tự động, tổng quát**, phải
đọc được file DOCX/PDF/XLSX **chưa biết trước** (khác hẳn `DEMO_RULES`
hard-code 1 client ở mục trên). Đây chính là milestone P3-04 mà
`Foundation_Master_Context.md` §5 gọi là "IP của dự án" và
`Foundation_Build_Plan_v3.md` §9.2 định nghĩa là "milestone bắt buộc,
không negotiate". Thiết kế **đã có sẵn đầy đủ** trong 2 file đó — việc làm
hôm nay là triển khai đúng thiết kế, không phải tự nghĩ ra thuật toán mới.

**Sửa 1 lỗi đặt sai chỗ trước khi build:** `mapping/anchor_builder.py`
(có sẵn từ trước, `build_table_hash`/`resolve_table_anchor` — cơ chế
self-heal DOCX table qua hash, generic, không biết gì về GTPS) **đặt sai
thư mục** so với đúng kiến trúc `Foundation_Master_Context.md` §9 (liệt kê
rõ `perception/anchor_builder.py`). Đã **di chuyển nguyên vẹn** (không sửa
logic) sang `perception/anchor_builder.py`, sửa 2 import site
(`mapping/writeback.py`, `perception/parser.py`), xóa file cũ — không để
lại re-export shim.

**Đã build trong `perception/anchor_builder.py` (module giờ đầy đủ cho cả
3 định dạng):**
- **DOCX** — `assign_docx_anchor()` (paragraph: `paragraph_index`+
  `style_id`+`text_fingerprint`; table cell: `table_index`+`table_hash`+
  `row_index`+`col_index`, tái dùng logic đã có). `resolve_docx_anchor()`
  — ladder đúng 3 tầng theo Master_Context §5: **Strategy 1**
  style_id+text_fingerprint khớp (tốt nhất, sống sót khi có
  insert/delete paragraph ở chỗ khác — đây chính là kịch bản P3-04),
  **Strategy 2** paragraph_index+style_id khớp (fallback, cảnh báo nội
  dung có thể đã đổi), **Strategy 3** paragraph_index đơn thuần (cảnh báo
  độ tin cậy thấp), **FAIL** → raise `ValueError` (không bao giờ âm thầm
  trả sai). Table-cell anchor dùng lại nguyên `resolve_table_anchor()` đã
  có (self-heal qua hash).
- **XLSX** — `assign_xlsx_anchor()` + `resolve_xlsx_anchor()`: `named_range`
  ưu tiên hơn `cell_address` đúng spec, không có ladder (đúng quyết định
  cũ — cell address đủ ổn định cho file digital).
- **PDF** — `assign_pdf_anchors()` (tính `bbox_relative` từ bbox tuyệt đối
  + kích thước trang mới thêm vào `GeometryBlock`, `reading_order_index`
  reset theo từng trang). `resolve_pdf_anchor()` — **cố tình không dùng
  content fingerprint** (khác DOCX): `tests/test_parser.py` đã chứng minh
  văn bản tài chính thật lặp lại boilerplate 10+ lần qua nhiều trang, nên
  match theo nội dung không an toàn cho PDF — đúng như `AnchorPDF` không
  có field `text_fingerprint`. Strategy 1 = khớp `(page,
  reading_order_index)` **và** bbox gần đúng vị trí cũ (tự phát hiện: nếu
  chỉ khớp index mà không kiểm tra bbox, một block khác trôi vào đúng vị
  trí cũ sẽ bị nhận nhầm — bug này bị 1 test tự viết bắt được và đã sửa
  trước khi merge). Strategy 2 (fallback, cảnh báo) = bbox gần nhất trên
  cùng trang, bỏ qua reading order.
- `applications/gpts/mapping_service.py` **đổi từ tự xây anchor inline
  sang gọi `assign_anchors()`** — đúng ranh giới kiến trúc (anchor là core
  IP, không phải chuyện riêng của GTPS). Tiện thể thêm luôn nhánh PDF còn
  thiếu (trước đây source PDF sẽ crash `ValueError` dù `api/` đã cho phép
  upload PDF).

**P3-04 PASS thật** (`tests/test_anchor_builder.py`, test
`test_p304_docx_paragraph_anchor_survives_insertion_at_start`): build DOCX
nhiều paragraph, gán anchor cho 1 đoạn, chèn 1 paragraph mới vào đầu file
(shift toàn bộ `paragraph_index` phía sau), parse lại, resolve anchor cũ
→ **vẫn trả về đúng đoạn text cũ**, Strategy 1, không cảnh báo. Đúng 100%
kịch bản P3-04 mô tả trong `Foundation_Build_Plan_v3.md` §9.2.

**Chưa làm / vẫn ❌ (không đổi):** `element_classifier.py` — phân loại
ngữ nghĩa (heading/table/note...) và đề xuất mapping cho tài liệu chưa
biết trước. Anchor không phụ thuộc classification (đúng nguyên tắc "anchor
trước, nhãn sau" — `Foundation_Build_Plan_v3.md` mục 4), nên việc này build
xong không bị chặn bởi #2, nhưng #2 vẫn cần cho bất kỳ demo nào ngoài
GTPS/HMV.

**Deprioritized theo yêu cầu user (không phải bỏ, chỉ tạm gác):** Digital
Gateway/Copilot competitive research (mục "Chưa làm" #12), benchmark 3
kịch bản AI (#13). Output engine giữ nguyên "Clone & Replace" — user xác
nhận đủ cho MVP, Profile-driven Fill/Task-shaped để sau.

**Tests:** 20 → **32 passed** (`tests/test_anchor_builder.py` mới, 12
test — assign sanity cho cả 3 format, P3-04 thật, Strategy 2 fallback khi
nội dung đổi, fail sạch khi anchor trỏ ra ngoài văn bản, XLSX
resolve/named_range, PDF Strategy 1+2). Regression: `test_mapping_service.py`
2 test cũ vẫn pass nguyên — HMV demo qua `/api/process` sống thật vẫn trả
đúng 662/2733 elements + 3 mapped sau khi refactor. Spot-check
`assign_pdf_anchors` trên fixture PDF 32 trang thật (`fixture_report_2.pdf`)
— 968 block, 0 bbox_relative lệch khoảng [0,1], reading_order_index reset
đúng ở mọi ranh giới trang.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-14, muộn hơn cùng ngày): 3 gap độ tin cậy của anchor — đóng cả 3

Ngay sau khi build xong `perception/anchor_builder.py`, tự đánh giá lại
mức độ sẵn sàng cho "document chưa biết trước" thì thấy rõ: **assign**
(gán anchor) đã generic thật, nhưng **resolve** (tìm lại khi tài liệu đổi)
mới chỉ chứng minh chắc chắn ở nhánh DOCX table (nhờ fixture drift thật).
3 gap còn lại — user yêu cầu đóng cả 3, đã xong cả 3:

**1. DOCX paragraph — Strategy 1 tie-break dưới drift lệch (không đều):**
Tìm được ngay trong file HMV thật: caption "Source: TP Cat database" lặp
lại **9 lần**, cùng style `BodyText` — ambiguity thật, không phải giả
định. Test cũ (`test_p304...`) chỉ chèn 1 đoạn ở đầu file → mọi occurrence
dịch chuyển ĐỀU nhau, không thật sự thử tie-break. Test mới
(`test_p304_docx_duplicate_ordinal_survives_uneven_drift_on_real_document`)
chèn 50 đoạn **giữa** occurrence #4 và #5 (không đều) — **verify bằng
toán**: thuật toán tie-break cũ ("gần nhất với paragraph_index đã ghi")
**sẽ chọn sai** (occurrence #4 ở khoảng cách 3, occurrence #5 đúng ở
khoảng cách 50). Đã sửa bằng field mới `AnchorDOCX.duplicate_ordinal` —
thứ hạng của paragraph này trong số các paragraph cùng chữ ký
(style_id+text_fingerprint), tính từ đầu văn bản — bất biến với insertion
ở chỗ khác vì các occurrence cùng chữ ký không đổi thứ tự tương đối với
nhau. Test verify bằng **object identity** (`resolved._p is expected._p`),
không chỉ so text — loại trừ khả năng "đúng ngẫu nhiên vì trùng text".

**2. XLSX — hoàn toàn không có cơ chế tự phục hồi (gap nghiêm trọng nhất):**
Trước đây `resolve_xlsx_anchor` chỉ tra `sheet_name!cell_address` trực
tiếp — nếu user chèn/xóa dòng, trả về **sai ô mà không báo lỗi**. Đã thêm
`AnchorXLSX.row_label_fingerprint` (hash của ô đầu tiên có dữ liệu tính từ
trái sang trong cùng dòng — quy ước phổ biến của báo cáo tài chính: nhãn
dòng ở cột A/B, số liệu bên phải) + field mới `GeometryBlock.row_label`
(`parser.py::parse_xlsx()` tính sẵn). `resolve_xlsx_anchor()` giờ: tra
trực tiếp trước, nếu nhãn dòng hiện tại khớp thì trả luôn (fast path);
nếu lệch → quét lại cùng cột để tìm dòng có nhãn khớp, tự hồi phục — cùng
ý tưởng với cơ chế table_hash cho DOCX. Test
`test_xlsx_resolve_self_heals_when_row_inserted_above` dùng
`ws.insert_rows()` thật của openpyxl để chèn 1 dòng — verify tìm đúng giá
trị "Net profit" (600) chứ không phải giá trị mới chèn (999). Test
`test_xlsx_resolve_raises_when_row_label_gone` xác nhận fail sạch khi
không tìm được (không đoán bừa).

**3. PDF — resolve chỉ test bằng dữ liệu giả lập, chưa test trên tài liệu
dày đặc thật:** Test mới
(`test_pdf_resolve_survives_realistic_insertion_on_real_dense_document`)
dùng **block thật** từ `fixture_report_2.pdf` (32 trang, có boilerplate
lặp thật) — lấy 1 dòng thật, chèn 1 dòng giả lập vào đúng vị trí trong
danh sách block thật (mọi trang khác giữ nguyên 100% dữ liệu thật), verify
resolve vẫn tìm đúng dòng gốc giữa nhiễu thật của tài liệu, không bị
đánh lừa bởi boilerplate lặp ở trang khác.

**Kết luận sau vòng này:** cả 4 nhánh (DOCX paragraph, DOCX table, XLSX,
PDF) giờ đều có ít nhất 1 test dùng **dữ liệu thật** (không chỉ giả lập)
chứng minh resolve sống sót qua drift — không còn nhánh nào "logic đúng
nhưng chưa thử lửa" như đánh giá trước đó cùng ngày. Gap còn lại vẫn là
`element_classifier.py` (ngoài scope của anchor).

**Tests:** 32 → **36 passed** (4 test mới: DOCX duplicate_ordinal thật,
2 XLSX row-drift, 1 PDF real-data drift). Regression: `/api/process`
sống thật verify lại — vẫn đúng 662/2733/3 mapped, `AnchorXLSX` giờ có
`row_label_fingerprint` thật trong response JSON.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-14): Sửa element ngay trên UI, ghi trực tiếp vào file output — không cần chạy lại pipeline

**Bối cảnh:** user hỏi có hiểu cơ chế "Profile-driven — sửa nội dung ngay
trên UI, cập nhật trực tiếp vào file output" không. Đây là ý tưởng đã ghi
trong `Foundation_Build_Plan_v3.md` §6 (Output Strategy) + endpoint
`PATCH /documents/{id}/elements/{index}` đã liệt kê trong plan — nhưng
**chưa hề có code nào** (Elements pane trước đó chỉ đọc, không route PATCH
nào tồn tại). Đã build xong cả 3 phần user yêu cầu:

**1. `mapping/writeback.py::WritebackEngine.apply_single_patch()`** —
method mới, khác với `apply_patches_docx/xlsx` cũ (nhận batch string-anchor
hard-code từ `DEMO_RULES`): nhận thẳng 1 `Anchor` pydantic (AnchorDOCX/
AnchorXLSX), gọi `perception.anchor_builder.resolve_docx_anchor`/
`resolve_xlsx_anchor` để tìm đúng vị trí (tận dụng lại toàn bộ ladder +
self-heal vừa xây), ghi giá trị mới, trả về message tự hồi phục nếu có.
PDF bị từ chối tường minh (`raise ValueError`) — đúng thiết kế cũ "PDF chỉ
đọc, không ghi được".

**2. `PATCH /api/elements/<process_id>`** (`api/routes/process.py`) —
nhận `{anchor, value}`. Tự tìm file đang làm việc: nếu đã có
`*_patched.docx` (từ lần chạy `DEMO_RULES` trước) thì sửa tiếp lên đó
(cộng dồn nhiều lần sửa); nếu chưa có (vd 0 rule nào khớp) thì **tự tạo**
bằng cách clone từ target gốc rồi mới sửa — người dùng luôn sửa được
ngay cả khi mapping tự động không ra kết quả nào. Chỉ hỗ trợ output DOCX
(khớp đúng những gì demo hiện tại thực sự sản xuất ra).

**3. Frontend** — `EditableText` component mới (`components/shared/`),
dùng chung cho `DocumentPane` (click vào đoạn văn/ô bảng) và `ElementsPane`
(click vào ô "Element"). `workspaceStore.ts` thêm `processId` (trước đây
không lưu, giờ cần để gọi PATCH), `editTargetElement()` — cập nhật UI
ngay (optimistic), gọi API, rollback nếu lỗi. Element vừa sửa tay được
đánh dấu `source: "manual"` (field này **đã có sẵn** trong
`perception/models.py` từ trước — schema đã lường trước tính năng này) +
tô nền vàng nhạt để phân biệt với dữ liệu extract tự động.

**Bug thật tìm thấy khi verify qua browser:** CORS preflight chặn PATCH —
`api/app.py` chỉ khai `Access-Control-Allow-Methods: GET, POST, OPTIONS`,
thiếu PATCH. Đã sửa. Nếu không verify bằng browser thật (chỉ test bằng
Flask test client, vốn không chạy CORS preflight) sẽ không phát hiện ra.

**Verify end-to-end qua browser thật** (Playwright, cài tạm rồi gỡ): sửa
đoạn "Contents" thành "EDITED BY AUTOMATED TEST — Contents" trực tiếp trên
DOCUMENT pane → tải file `_patched.docx` về → mở lại bằng `python-docx` →
**xác nhận đúng đoạn đó trong file thật đã đổi**, không phải chỉ đổi trên
UI. Elements pane cùng lúc hiện đúng giá trị mới + tô vàng, link
"Download patched DOCX" tự xuất hiện dù trước đó `mapped=0`.

**Giới hạn hiện tại:** chỉ sửa được element có `anchor.format == "docx"`
(đúng phạm vi output hiện có). Sửa Source (Excel input) chưa hỗ trợ ở
route level — không nằm trong yêu cầu ("output file"), engine phía dưới
đã hỗ trợ XLSX rồi nếu sau này cần mở route. Không có undo/lịch sử sửa
đổi trong UI (mỗi lần sửa ghi đè giá trị cũ trong file, có ghi log nhưng
chưa hiển thị).

**Tests:** 36 → **46 passed** (10 test mới ở `tests/test_patch_element.py`
— `apply_single_patch` unit-level cho paragraph/table cell/tích lũy nhiều
lần sửa/từ chối PDF, route-level qua Flask test client cho cả happy path
lẫn lỗi 400/404).

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-14, cùng ngày): Bias theo use case GTPS — sửa 2 điểm rủi ro cao nhất

**Bối cảnh:** user chỉ ra đúng — sau khi viết
`Foundation_UI_User_Behavior_Hypotheses_2026-08-14.md` (giả thuyết hành vi
user, lưu tại repo root), phát hiện cả UI copy lẫn 1 phần backend đang
ngầm giả định "Foundation = công cụ cho GTPS", trong khi Foundation được
định vị là substrate layer dùng chung nhiều function
(`Foundation_Master_Context.md`). **Không phải vấn đề kiến trúc** —
`perception/` vốn đã generic, `applications/gpts/` vốn đã cô lập đúng chỗ
theo "Quy tắc không được phá vỡ" — mà là 2 chỗ thật sự bias:

**1. `sourceFiles` chỉ dùng phần tử đầu tiên (H3 trong file hypotheses):**
UI cho phép chọn nhiều source file (`multiple` trên input) nhưng
`applications/gpts/mapping_service.py::run_mapping()` trước đây nhận
đúng 1 `source_path`, các file sau bị im lặng bỏ qua. Đã sửa:
- `run_mapping(source_paths: list[str], ...)` — extract + gán anchor cho
  **từng file riêng**, element index không đụng nhau, gộp chung vào 1
  `source_map` để rule nào cũng tìm khớp trên toàn bộ input, không chỉ
  file đầu.
- `api/routes/process.py`: nhận nhiều file qua `request.files.getlist("source")`
  (field lặp lại), lưu đè tránh trùng tên bằng prefix index.
- Frontend: `processDocuments(sources: File[], target)` gửi toàn bộ
  `sourceFiles`, không chỉ `[0]`.
- Test mới `test_run_mapping_merges_elements_from_multiple_source_files`
  + verify qua browser thật (2 file Excel FA&RPT FY2023+FY2024 cùng lúc) —
  1329 source elements (662+667), mapping vẫn đúng.

**2. AgentPane giả vờ hoạt động (H15):** hiển thị hội thoại mẫu cứng +
input trông như gõ được, trong khi STATUS.md từ đầu đã ghi rõ ý định gốc
"nút Gửi disabled có chủ đích". Đã viết lại đúng ý định đó: bỏ hội thoại
giả, input+nút disabled thật, thông báo rõ "Chat is not connected to an
AI model yet — this is a placeholder pane."

**3. Copy UI mang giọng Tax/GTPS:** "Upload FA&RPTs (Excel) or PDF
reports" → "Upload source data — Excel or PDF, any number of files.";
"Upload the local file template (Word)" → "Upload the target document
(Word) to map source data into." Không đổi nhãn "Source Documents"/
"Target Template" (đã đủ trung lập).

**Việc KHÔNG làm (cân nhắc rồi bỏ qua):** không xây hệ thống "profile
plugin" cho nhiều rule set — hiện chỉ có đúng 1 rule set thật
(`DEMO_RULES`), xây abstraction cho tương lai giả định là over-engineering.
Khi có rule set thứ 2 thật (vd cho Audit) mới là lúc tách interface
chung.

**Tests:** 46 → **47 passed** (1 test mới cho multi-source-file merge).
`tsc -b` sạch, verify qua browser thật xác nhận cả 2 điểm sửa.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-14, muộn hơn cùng ngày): Undo cho sửa tay + highlight element liên quan giữa các pane

**Bối cảnh:** user yêu cầu 2 việc — (1) nút undo cho tính năng sửa trực
tiếp mới build, (2) "responsive" cho hành vi user: hover/tương tác ở 1
pane phải highlight element liên quan ở pane khác. Trong lúc build và tự
verify bằng browser thật, phát hiện thêm 2 bug thật không liên quan trực
tiếp tới yêu cầu nhưng chặn đúng tính năng này hoạt động đúng — đã sửa
luôn thay vì báo cáo suông.

**1. Undo — session-only, mỗi lần undo là 1 PATCH mới với giá trị cũ:**
`workspaceStore.ts` thêm `editHistory: EditHistoryEntry[]` (index + anchor
+ previousValue, đẩy vào sau mỗi `editTargetElement` thành công) và
`undoLastEdit()` — pop phần tử cuối, gọi lại `patchElement` với
`previousValue`. Không phải "undo thật" ở server (không rollback file) —
là 1 write mới ghi giá trị cũ đè lên, nên **cũng được log lineage** như
mọi edit khác (`api/routes/process.py` đã thêm log này cùng lúc). Nút
Undo đặt ở `WorkspaceHeader` (global, luôn thấy được dù đang ở pane nào),
hiện số lượng edit có thể undo, kèm phím tắt **Ctrl/Cmd+Z** (nhường quyền
undo gốc của trình duyệt khi đang gõ dở trong 1 ô input/textarea).

**2. Highlight element liên quan — hover 1 nơi, sáng lên ở nơi khác:**
Thêm `hoveredElementIndex` dùng chung giữa `DocumentPane`, `ElementsPane`,
`ResultsPane`. Hover 1 đoạn/ô trong Document ↔ đúng dòng trong Elements
sáng lên **và tự cuộn tới** (dùng `scrollIntoView({block: 'nearest'})` —
không làm gì nếu phần tử đã hiện sẵn trên màn hình, nên không giật khi
hover ngay tại pane đang xem).

**Bug thật #1 — bắt được nhờ tự verify, không phải giả định:** hover 1
dòng "Mapped" trong Results **không** highlight được gì cả. Điều tra ra:
cả 3 giá trị `DEMO_RULES` map vào đều là **ô trống tại thời điểm parse**
(số liệu chưa điền) — mà `parse_docx()` cũ **bỏ qua mọi table cell rỗng**
(`if not cell.text.strip(): continue`), nên các ô đó chưa từng có Element
nào để mà highlight, **và cũng chưa từng sửa tay được** (không có gì để
click). Đã sửa: bỏ hẳn điều kiện skip cho table cell (giữ nguyên cho
paragraph — ô trống trong bảng là placeholder thật cần điền, khác đoạn
văn trống chỉ là khoảng trắng định dạng). `EditableText` đã có sẵn UI
"(empty — click to fill in)" cho trường hợp này từ trước (chưa dùng tới
tới giờ) — tự nhiên khớp đúng.

**Bug thật #2 — sâu hơn, phát hiện sau khi sửa bug #1:** vẫn không
highlight được, dù ô giờ đã tồn tại. Điều tra bằng cách gọi trực tiếp
`resolve_table_anchor()`: DEMO_RULES anchor `table:6:376644e1_row:1_col:4`
**tự hồi phục (self-heal) sang table 4**, không phải table 6 — đúng cơ chế
anti-drift đã build, nhưng **`table_index` trong chuỗi anchor gốc đã lạc
hậu** ngay khi self-heal xảy ra. Cách match cũ ở frontend
(`anchorMatch.ts`, tự parse chuỗi rồi so `table_index` trực tiếp) **không
biết gì về self-heal**, nên luôn tìm sai/tìm hụt. Sửa đúng gốc: chuyển
việc resolve này về **backend** — `applications/gpts/mapping_service.py`
thêm `target_element_index` vào mỗi `MappedEntry`, tính bằng cách tra theo
`(table_hash, row, col)` thay vì `table_index` (cùng field self-heal đã
dùng) ngay khi `run_mapping()` build xong `target_elements`. Frontend giờ
chỉ đọc `mapped[i].target_element_index` có sẵn — đã **xóa hẳn**
`anchorMatch.ts` (logic sai, không cần nữa) thay vì giữ lại làm fallback.
Bài học: đừng để 2 nơi (backend + frontend) cùng tự suy luận lại 1 kết quả
resolve — chỉ nên tính 1 lần ở nơi có đủ thông tin (backend, nơi
anchor_builder.py sống), rồi truyền thẳng kết quả.

**Tests:** 47 → **48 passed** (`test_parse_docx_keeps_empty_table_cells`
mới; `test_run_mapping_maps_all_demo_rules` bổ sung assertion mọi
`MappedEntry.target_element_index` phải resolve ra đúng element thật).
Verify qua browser thật (Playwright, cài tạm rồi gỡ): undo bằng chuột +
phím tắt đều đúng, hover Elements↔Document sáng đúng cặp, hover Results
sáng đúng ô đích (element #633, giá trị "193,729,728,552" — đúng số vừa
map) — không còn silent-fail.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-14, muộn hơn cùng ngày): Bỏ màn hình Intake riêng — thêm file ngay trong workspace

**Bối cảnh:** user gửi screenshot màn Intake và chỉ ra 2 vấn đề: (1) vẫn
bias theo GTPS dù đã sửa copy hôm trước — vì **kiến trúc** "Source
Documents → Target Template → map vào" tự nó chính là hình dạng của use
case Local File mapping, đổi chữ không đổi được điều đó; (2) nhìn thiếu
chuyên nghiệp vì quá đơn giản (khung nét đứt nổi giữa khoảng trắng mênh
mông, không phân cấp thị giác). Sau khi hỏi lại mức độ sửa (chỉ visual
hay sửa cả mô hình), user chọn hướng triệt để nhất: **bỏ hẳn màn hình
Intake, đưa document vào ngay trong UI 4-pane qua nút "+" ở pane
DOCUMENT.**

**Thay đổi kiến trúc:**
- `App.tsx` không còn switch màn hình — luôn render thẳng
  `WorkspaceLayout`. Xóa hẳn `components/intake/` (không giữ lại làm dead
  code).
- `workspaceStore.ts`: bỏ `currentScreen`/`setScreen`. Thêm
  `addDocument(file)` — tự động định tuyến file vào `sourceFiles` hay
  `targetFiles` theo **đuôi file** (`.docx` → target, thay thế target cũ
  nếu có; `.xlsx`/`.pdf` → source, cộng dồn) — khớp đúng
  `SOURCE_FORMATS`/`TARGET_FORMATS` đã có ở `api/routes/process.py`,
  **không cần sửa backend** vì user không còn phải tự phân loại nữa, hệ
  thống tự biết. Thêm `resetWorkspace()` — dọn sạch toàn bộ state
  (files/elements/processId/editHistory/...) về trạng thái ban đầu.
- `DocumentPane.tsx`: khi chưa có `targetElements`, hiện view mới
  (`DocumentIntake`) — nút "+" tròn mở file picker (`multiple`,
  `accept=".xlsx,.pdf,.docx"`), danh sách file đã thêm với nhãn màu phân
  biệt vai trò (tím = Target template, xanh = Source data — tự động, user
  không cần chọn), báo lỗi inline nếu file sai định dạng, nút "Start
  Processing" xuất hiện ngay khi đủ điều kiện.
- `WorkspaceHeader.tsx`: icon Home (trước gọi `setScreen('intake')`, giờ
  không còn màn đó để quay về) đổi thành icon "New document" gọi
  `resetWorkspace()`. Thêm trạng thái động thay cho chữ "Ready" tĩnh cũ:
  "No document loaded" (chưa có gì) / "Processing" (spinner xanh) /
  "Ready" (xanh lá) / "Error" (đỏ) — phản ánh đúng `processingStatus`
  thay vì luôn hiện "Ready" kể cả khi chưa xử lý gì.
- `ResultsPane.tsx`: sửa message rỗng bị sai ngữ cảnh — trước đây dù chưa
  upload gì cũng hiện "No rule matched this document pair" (ngụ ý đã chạy
  xử lý rồi), giờ phân biệt rõ theo `processingStatus`: chưa có gì → "Add
  documents in the Document pane to get started."; lỗi → trỏ về Document
  pane; đã chạy nhưng 0 rule khớp → giữ nguyên message giải thích cũ.
- Dọn thêm `editingTargetIndex`/`startEditingTarget` (dead code có sẵn từ
  trước, không component nào dùng — `EditableText` tự quản lý state sửa
  cục bộ) trong lúc sửa file này.

**Không đổi gì ở backend** — toàn bộ thay đổi nằm ở frontend, vì
`POST /api/process` vốn đã nhận đúng shape `source` (nhiều file) +
`target` (1 file) rồi, chỉ là trước đây UI ép user tự chọn ô nào bỏ file
nào.

**Verify qua browser thật** (Playwright, cài tạm rồi gỡ): mở app vào
thẳng workspace (không còn màn hình chờ riêng), thử file sai định dạng →
báo lỗi đúng chỗ không crash, thêm 2 file qua cùng 1 input "+" → tự phân
loại đúng nhãn màu, "Start Processing" chỉ hiện khi đủ, xử lý xong hiện
đúng dữ liệu thật, bấm "New document" ở header → về đúng trạng thái trống
ban đầu, 0 lỗi console suốt toàn bộ luồng.

**Tests:** không đổi backend nên vẫn 48/48. `tsc -b` sạch.

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
| `perception/models.py` | ✅ Done | Pydantic schemas: `ElementType`, `AnchorDOCX`/`AnchorXLSX`/`AnchorPDF`, `Element`, `ElementIndex`, `Profile`/`ProfileField`. Gap cũ (`text`/`text_normalized`/`source` trên `Element`, `formula` trên `ProfileField`, `paragraph_index` optional + `table_hash` trên `AnchorDOCX`) đã vá hết — xem mục 2026-08-14. |
| `perception/detector.py` | ⚠️ Done nhưng có gotcha máy dev | `detect_format()` — kiểm tra extension + MIME (libmagic). **2026-08-14: reject cả file `.docx` thật trên máy dev này** (`python-magic-bin` detect sai MIME) — `api/` không dùng hàm này để validate upload, xem mục 2026-08-14. |
| `perception/parser.py` | ✅ Done, viết lại 2026-08-11, `parse_xlsx()` + `page_width`/`page_height` + `row_label` thêm sau đó | `parse_docx()` (python-docx), `parse_pdf()` (pdfplumber, text+bbox+kích thước trang), `parse_xlsx()` (openpyxl, named ranges, nhãn dòng cho self-heal), `render_pdf_pages()` (pdf2image, cần Poppler — chưa cài), `extract_geometry()` (dispatch theo đuôi file, cả 3 format). Docling đã bỏ hoàn toàn. |
| `perception/anchor_builder.py` | ✅ Done (2026-08-14, vá thêm cùng ngày) | Locate step thật — assign + resolve Anchor cho DOCX/XLSX/PDF, P3-04 PASS. Trước đó bản table-hash generic nằm sai chỗ ở `mapping/anchor_builder.py`, đã di chuyển đúng chỗ. Vá thêm: `duplicate_ordinal` (DOCX tie-break dưới drift lệch), row-label self-heal (XLSX), test resolve PDF trên dữ liệu thật. Xem 2 mục 2026-08-14 |
| `applications/gpts/mapping_service.py` | ✅ Done (2026-08-14) | Application layer đầu tiên trong repo — xem mục 2026-08-14 |
| `api/app.py` + `api/routes/process.py` | ✅ Done (2026-08-14) | Flask access layer đầu tiên trong repo — xem mục 2026-08-14 |

### Tests — đã chạy thật, kết quả 48 passed / 0 failed
```
cd foundation && .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
============ 48 passed in ~13-19s ==============
```
(Trước khi bỏ Docling: 12 passed / 1 failed, 174.96s. Sau khi bỏ: 16/16
pass, 3.60s. Sau khi thêm `parse_xlsx()` + `mapping_service`: 20/20 pass.
Sau khi thêm `anchor_builder.py` (`perception/`) + P3-04: 32/32 pass. Sau
khi vá 3 gap độ tin cậy: 36/36 pass. Sau khi thêm PATCH element + undo +
generalization + fix empty-cell/self-heal resolution (2026-08-14): 48/48
pass.)

| File | Trạng thái |
|---|---|
| `tests/test_models.py` | ✅ Pass (6 test) |
| `tests/test_detector.py` | ✅ Pass (4 test) |
| `tests/test_parser.py` | ✅ Pass (9 test) — viết lại theo API mới, gồm test PDF digital (có bbox), PDF digital multi-page với duplicate-text, PDF scanned (0 block, không crash), XLSX (named range), dispatch theo đuôi file, reject đuôi file lạ, **giữ table cell rỗng (2026-08-14)** |
| `tests/test_mapping_service.py` | ✅ Pass (3 test) — 1 chạy thật với fixture HMV thật (kèm assertion `target_element_index` resolve đúng qua self-heal), 1 test cặp file bất kỳ → `mapped == []`, 1 test gộp nhiều source file |
| `tests/test_anchor_builder.py` | ✅ Pass (16 test) — assign sanity DOCX/XLSX/PDF, **P3-04 thật**, **duplicate_ordinal trên file HMV thật**, Strategy 2 fallback, fail sạch khi anchor không resolve được, XLSX named_range priority + self-heal khi chèn dòng thật, PDF Strategy 1+2 + resolve trên block thật từ fixture 32 trang |
| `tests/test_patch_element.py` | ✅ Pass (10 test, mới 2026-08-14) — `apply_single_patch` unit-level (paragraph/table cell/tích lũy/từ chối PDF), route-level qua Flask test client |

### Fixtures
Đã có sẵn trong `tests/fixtures/`:
- `fixture_bcdt.docx` — **xác nhận 2026-08-11: đây thực chất là file scan, không phải DOCX digital.** `python-docx` chỉ đọc được 2 paragraph có nội dung / 252 paragraph, 0 table — vì file thực chất chứa 65 ảnh trang nhúng (`word/media/image*.png`, kiểm tra qua zip nội bộ), không có text layer thật. **Đã thử thay bằng `BCTC_hop_nhat_Q2.2026_tu_lap_DT_.docx` (do user cung cấp 2026-08-11) — xác nhận trùng MD5 100% với file đang có, tức là cùng 1 file.** Gap DOCX đa dạng (nhiều heading trùng style) — **đã giải quyết 2026-08-14, không cần fixture riêng**: dùng thẳng file demo GTPS thật (`anonymize client/Demo files/.../HMV-26-Final-Local File.../_drifted.docx`, không nằm trong `tests/fixtures/`, tham chiếu qua path + skipif) — file này tự nhiên có 9 lần lặp caption "Source: TP Cat database" cùng style, đủ để stress-test tie-break thật, xem `test_anchor_builder.py`.
- `fixture_report.pdf` (PDF scan ảnh, 0 chars mọi trang qua `pdfplumber`, không dùng được cho Geometry Layer tới khi có quyết định OCR) — **xác nhận trùng MD5 với `CBTTDK_BCTC_HN_Q2.26_VIE_sign.pdf` do user cung cấp**, cùng 1 file, cũng là bản scan/ký, không giúp thêm.
- `fixture_report_2.pdf` (PDF digital thật) — **xác nhận trùng MD5 với `Neweb VN-2025-VND-VN-1903.pdf` do user cung cấp.** Phân tích sâu hơn 2026-08-11: 32 trang, 9691 từ, 968 dòng text, có 40 nhóm dòng lặp lại (vd: "Công ty TNHH NeWeb Việt Nam" lặp 31 lần, "Mẫu B 09 – DN" lặp 22 lần) — **đa dạng hơn đánh giá ban đầu**, đủ tốt để test case anchor PDF bị trùng text/style qua nhiều trang. Đã thêm test `test_parse_pdf_digital_has_realistic_multipage_diversity` khai thác đúng case này.

**Còn thiếu thật sự:**
- ~~Fixture DOCX digital đa dạng (nhiều heading, có table)~~ — **2026-08-17: đã xong.** `fixture_generic_handbook.docx` (sinh từ `tests/fixtures/_generate_generic_docx.py`, deterministic — 4 heading qua 3 level + 4 đoạn văn + 1 table 3x3) — xem mục "✅ ĐÃ GIẢI QUYẾT (2026-08-17)" bên dưới. **Lưu ý:** đây là fixture generic/phi-tài-chính để chứng minh Geometry Layer không bias về hình dạng BCTC, KHÔNG phải fixture để test anchor Strategy 2/3 (vốn cần heading **trùng** `style_id` để test tie-break — gap đó vẫn còn, khác mục đích với fixture mới này).
- ~~Fixture XLSX~~ — **2026-08-14: không còn chặn.** `parse_xlsx()` + `test_mapping_service.py` dùng thẳng file demo thật (`anonymize client/Demo files/.../HMV-FA&RPT FY2024.xlsx`) làm fixture, không cần file tổng hợp riêng trong `tests/fixtures/`.

---

## Chưa làm — đối chiếu trực tiếp với v4 (audit 2026-08-11)

| # | Việc theo v4 | Trạng thái code | Ghi chú |
|---|---|---|---|
| 1 | Loại bỏ Docling, chuyển Geometry Layer sang pdfplumber+pdf2image (PDF) / python-docx (DOCX) | ✅ Xong 2026-08-11 | `parser.py` viết lại hoàn toàn, 16/16 test pass. **Lưu ý:** đây là quyết định "bỏ Docling", khác với "pivot về DOC-only" của v4 mục 1-2 — team chủ động giữ nhánh PDF (`parse_pdf`/`render_pdf_pages`) chạy song song thay vì gác lại, đây là lựa chọn có chủ đích của team, không phải sai lệch khỏi plan |
| 2 | `perception/element_classifier.py` (See) | ✅ **Xong (2026-08-17)** | `classify_block()`/`classify_blocks()` — deterministic baseline (di dời từ `applications/gpts/mapping_service.py::geometry_block_to_element`, hành vi giữ nguyên y hệt) + seam `Classifier` protocol để cắm AI model của user sau này. Xem mục "✅ ĐÃ GIẢI QUYẾT" 2026-08-17 |
| 3 | `perception/anchor_builder.py` (Locate) + P3-04 anchor stability test | ✅ **Xong (2026-08-14)** | IP quan trọng nhất của project — milestone bắt buộc đã chạm tới. Assign+resolve cho cả DOCX (ladder 3 tầng + table self-heal)/XLSX (named_range/cell_address)/PDF (position+bbox, không content-match). P3-04 PASS thật (insert paragraph → resolve vẫn đúng). Xem mục "✅ ĐÃ GIẢI QUYẾT" 2026-08-14 |
| 4 | **Normalization Layer** (v4 mục 3) — `NormalizationRule`, hàm `normalize()` | ❌ Chưa — 0 dòng code | Rule tất định (VND/VNĐ→VND, ngày tháng...), tách riêng khỏi Classification |
| 5 | `Element.text` / `text_normalized` field (v4 mục 4) | ✅ Xong | `text` có sẵn (populated bởi `applications/gpts/mapping_service.py`), `text_normalized` có field nhưng chưa ai ghi vào (chờ #4 Normalization Layer) |
| 6 | `ProfileField.formula: str \| None` (v4 mục 8, placeholder cho Template Authoring Phase 2) | ✅ Xong | Field đã thêm, chưa có code nào set giá trị (đúng — chỉ là placeholder cho Phase 2) |
| 7 | Application layer — package `applications/` (v4 mục 6) | ⚠️ Bắt đầu (2026-08-14) | `applications/gpts/mapping_service.py` — chỉ cho use case GTPS/HMV demo. Chưa có `applications/tax/` hay use case tổng quát nào khác |
| 8 | Module `extract` / `translate` / `summarize` (v4 mục 1, 3 module demo) | ❌ Chưa | Demo thật hiện có là "Local file mapping" (GTPS), không phải extract/translate/summarize — xem mục sửa scope |
| 9 | Output engine (v4 mục 5) | ⚠️ 1/3 chế độ | "Clone & Replace" qua `mapping/writeback.py::apply_patches_docx/xlsx` (batch, DEMO_RULES) **+ `apply_single_patch()`** (1 element/lần, dùng bởi PATCH live-edit — cùng chế độ, khác đường vào). Chưa có Profile-driven Fill / Task-shaped |
| 10 | `api/` — Flask routes | ✅ Xong (2026-08-14) | `api/app.py` (`create_app()`, CORS gồm PATCH) + `api/routes/process.py` (`POST /api/process` nhận nhiều source file, `PATCH /api/elements/<id>` sửa trực tiếp, `GET /api/download/<id>`) — chỉ phủ use case GTPS demo, chưa có `/documents/{id}/perceive` v.v. theo đúng v4 §7.5 |
| 11 | **Frontend thật** (v4 mục 7) | ✅ Nối API thật + sửa trực tiếp (2026-08-14) | **Không còn màn hình Intake riêng** — 1 workspace duy nhất, thêm document qua nút "+" ngay trong pane DOCUMENT (tự phân loại source/target theo đuôi file). Sửa element trực tiếp trên UI ghi thẳng vào output (PATCH), có Undo (session-only, Ctrl/Cmd+Z), hover 1 pane highlight + auto-scroll pane liên quan. Copy đã trung lập hóa, không còn giọng Tax/GTPS. `AgentPane` vẫn honest placeholder, chờ OpenAI/Workbench thật — xem các mục 2026-08-14 |
| 12 | Digital Gateway/Copilot competitive research (v4 mục 9) | ❌ Chưa | Checklist rỗng, không tìm thấy tài liệu/slide nào trong repo — bắt buộc phải có trước Executive Summary |
| 13 | Benchmark 3 kịch bản AI (không AI / general / fine-tune local) (v4 mục 0.1-4, mục 11) | ❌ Chưa | Không có benchmark script/kết quả nào |
| 14 | Hạ tầng thứ 3 — máy local cô lập mạng (v4 mục 10) | ⚠️ Đúng kế hoạch, chưa cần vội | v4 tự xác nhận đây là nghiên cứu song song, không chặn MVP |

---

## Chuẩn bị làm (build order theo v4, thay build order v3 cũ)

Ưu tiên theo đúng thứ tự chốt trong họp (v4 mục 0.1):

| # | Việc | Phụ thuộc | Ghi chú |
|---|---|---|---|
| 1 | Gửi câu hỏi xác nhận CRADL chính thức cho pdfplumber/pdf2image + Poppler cho anh Quốc | Không | Việc của người, không phải code — quyết định "bỏ Docling" ở trên là quyết định kỹ thuật nội bộ, KHÔNG thay thế việc xác nhận compliance chính thức này |
| 2 | Research Digital Gateway/Copilot, viết bảng so sánh 3 cột | Không | **Deprioritized 2026-08-14 theo yêu cầu user** — tạm gác, không phải bỏ. Vẫn "bắt buộc trước Partners" khi quay lại làm |
| 3 | ~~Pivot `parser.py`/`detector.py` bỏ Docling~~ | — | ✅ Xong 2026-08-11, xem phần "Đã giải quyết" ở trên |
| 4 | ~~Fixture XLSX thật (named ranges, merged cells, nhiều sheet)~~ | — | ✅ Xong — dùng luôn fixture demo thật (`HMV-FA&RPT FY2024.xlsx`) thay vì fixture tổng hợp riêng |
| 5 | ~~`perception/parse_xlsx()` + anchor XLSX~~ | #4 | ✅ Xong — `parse_xlsx()` (openpyxl, named ranges) + `AnchorXLSX` |
| 6a | `perception/anchor_builder.py` (DOCX/XLSX/PDF generic) → **P3-04 PASS** | Không (Docling đã bỏ, không còn block) | ✅ **Xong (2026-08-14)** — xem mục "Đã giải quyết" cùng ngày |
| 6b | `perception/element_classifier.py` | Không (anchor không phụ thuộc classification — nguyên tắc "anchor trước, nhãn sau") | ✅ **Xong (2026-08-17)** — baseline tất định + seam `Classifier` cho AI model tương lai. Chưa build model AI thật (ngoài scope việc này) — vẫn cần cho demo/use case ngoài GTPS/HMV khi nào có model |
| 7 | Output write path: DOCX (`python-docx`, đã duyệt) + XLSX (`openpyxl`, đã duyệt) | #5, #6 | ⚠️ 1/3 — chỉ có "Clone & Replace" (`mapping/writeback.py`). Profile-driven Fill / Task-shaped vẫn chưa |
| 8 | Normalization Layer (`normalize()`, `NormalizationRule`) | #5, #6 (cần element có `text`) | **Vẫn ❌ chưa làm** — element đã có `text` (xong ở #9) nhưng chưa ai gọi normalize |
| 9 | ~~Thêm field `text`/`text_normalized` vào `Element`, field `formula` vào `ProfileField`~~ | Không | ✅ Xong |
| 10 | ~~Module mapping (application layer, package `applications/`) cho "Local file mapping"~~ | #5, #6a, #7 | ✅ Xong (2026-08-14) — `applications/gpts/mapping_service.py`, dùng `mapping/demo_mapper.py`'s `DEMO_RULES` (hard-code 1 client) + `perception/anchor_builder.py`'s `assign_anchors()` (generic, #6a) — #6b (`element_classifier.py`) vẫn là gap thật cho use case khác HMV |
| 11 | ~~`api/` Flask routes~~ | #5, #6a, #10 | ✅ Xong (2026-08-14) — `api/app.py` + `api/routes/process.py`: `POST /api/process` (nhiều source file), `PATCH /api/elements/<id>` (sửa trực tiếp), `GET /api/download/<id>` — chỉ phủ GTPS demo, chưa theo đúng REST shape v4 §7.5 (`/documents/{id}/...`) |
| 12 | ~~Frontend — bước 1-3 của v4 mục 7.6~~ | — | ✅ Xong 2026-08-11, dựng lại 2 lần nữa cùng 2026-08-14 (Intake→Workspace, rồi bỏ hẳn Intake — 1 workspace duy nhất, thêm document qua nút "+" tại chỗ). Sửa trực tiếp + Undo + cross-highlight đã có. `AgentPane`/OpenAI vẫn chờ |
| 13 | Benchmark 3 kịch bản AI | #10 | **Deprioritized 2026-08-14 theo yêu cầu user** — tạm gác, không phải bỏ |
| 14 | ~~OCR~~ | — | **Xác nhận 2026-08-11: không cần** — "Local file mapping" luôn nhận input Excel digital, không có nguồn scan |

### Quy tắc không được phá vỡ
- P3-04 phải PASS trước khi sang Phase 4. **✅ Đã PASS (2026-08-14)** —
  xem `tests/test_anchor_builder.py`. **2026-08-17: coverage giờ không còn
  điều kiện** — `tests/test_anchor_p304_synthetic.py` chạy P3-04 (kể cả
  nhánh `duplicate_ordinal` dưới drift lệch) trên fixture tổng hợp phi-tài-
  chính, không `skipif`, không phụ thuộc file thật nào. Xem mục "✅ ĐÃ GIẢI
  QUYẾT" 2026-08-17.
- Không dùng API ngoài — mọi thứ chạy local/air-gapped.
- Module nào cần biết "đây là use case Tax/GPTS" thì không được nằm trong
  `perception/`/`adapters/` — đặt ở `applications/tax/`, `applications/gpts/`.
- Đừng viết "pdfplumber/pdf2image đã bị từ chối" cho tới khi anh Quốc xác nhận lại.
- Scope MVP1: DOC only. Đừng mở rộng loại file khác trước khi core DOC chứng minh được.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-17): Bỏ `ElementType.GLOSSARY` khỏi core — thay bằng `Element.tags` chung

**Bối cảnh:** `perception/models.py::ElementType` có sẵn giá trị `GLOSSARY =
"glossary"` — không phải structural primitive (khác `heading`/`table`/
`cell`/`para`/`picture`), mà là 1 semantic role chỉ liên quan tới use case
dịch thuật (translation). Vi phạm đúng "Quy tắc không được phá vỡ" ở trên
("module nào cần biết use case cụ thể thì không được nằm trong
`perception/`"). Chưa consumer nào dùng giá trị này, xóa an toàn.

**Đã sửa:**
- `perception/models.py`: bỏ `GLOSSARY` khỏi `ElementType` (giờ chỉ còn 5
  structural primitive), thêm comment nói rõ enum này CHỈ chứa structural
  primitive. Thêm field chung `Element.tags: list[str] = Field(default_factory=list)`
  — nơi application layer tự gán role ngữ nghĩa bất kỳ (vd
  `applications/gpts/` sau này có thể set `tags=["glossary"]`), core
  không hard-code tên tag nào.
- `frontend/src/types/element.ts`: bỏ `'glossary'` khỏi union `ElementType`,
  thêm `tags?: string[]` vào `ElementRowData` — mirror đúng model Python.
- `tests/test_models.py`: thêm `test_element_type_has_no_glossary_member`
  + `test_element_tags_roundtrip` (Element với `tags=["glossary"]` round-trip
  qua JSON đúng).

**Tests:** 48 → **50 passed** (2 test mới). `tsc -b` chạy sạch, không lỗi.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-17): Fixture DOCX generic/phi-tài-chính — đóng gap "genericity chưa được verify"

**Bối cảnh:** toàn bộ fixture DOCX/PDF/XLSX hiện có (`fixture_bcdt.docx`,
`fixture_report.pdf`, `fixture_report_2.pdf`, file demo HMV) đều là tài
liệu tài chính thật. Claim "`perception/` generic, không bias theo domain
cụ thể" (v3/v4, "Quy tắc không được phá vỡ") vì vậy chưa từng được kiểm
chứng bằng test — chỉ đúng vì `parser.py`/`anchor_builder.py` tình cờ chưa
viết logic riêng cho BCTC, không phải vì có test nào chặn regression nếu
sau này ai đó (vô tình) thêm giả định tài chính vào.

**Đã thêm:**
- `tests/fixtures/_generate_generic_docx.py` — script deterministic dùng
  `python-docx` sinh `fixture_generic_handbook.docx`: tài liệu hư cấu hoàn
  toàn ("Community Garden Member Handbook"), không tên người/công ty thật,
  không số liệu tài chính. Cấu trúc cố định trong code (nguồn sự thật duy
  nhất, test import thẳng từ đây, không hard-code lặp lại): 4 heading qua
  3 level (`Heading 1/2/3`), 4 đoạn văn nội dung, 1 table 3x3 (header +
  2 dòng data). Cả file `.docx` sinh ra lẫn script sinh nó đều commit —
  đúng yêu cầu "reproducible from code", không phải blob nhị phân mù mờ.
- `tests/test_parser_generic.py` — chạy `parse_docx()`/`extract_geometry()`
  trên fixture này, assert **thuần cấu trúc** (đúng cho bất kỳ DOCX nào,
  không riêng tài chính): >0 block, đúng số heading + mỗi heading có
  `style_id` thật (`Heading1/2/3`, không `None`), table có đúng 9 cell ở
  đúng `table_index`/`row_index`/`col_index` với đúng nội dung, các đoạn
  văn nội dung được giữ nguyên. Cố tình KHÔNG assert gì liên quan tài
  chính — đây chính là điểm khác `test_parser.py`.
- Verify: parser xử lý đúng ngay lần đầu, không tìm thấy bug nào — không
  có bias tài chính ẩn trong `parse_docx()` tại thời điểm này. Fixture này
  giờ là **regression guard**: nếu sau này `element_classifier.py` hay
  `anchor_builder.py` vô tình thêm giả định "shape BCTC" (vd giả định
  heading luôn là tên khoản mục kế toán), test này sẽ đỏ.

**Không đóng:** gap "heading trùng `style_id`" (cần cho test Strategy 2/3
của anchor resolve) — khác mục đích, fixture này cố tình mỗi heading dùng
level/text riêng, không lặp lại như boilerplate BCTC thật. Xem ghi chú
cập nhật ở mục "Còn thiếu thật sự" phía trên.

**Tests:** 50 → **56 passed** (6 test mới ở `test_parser_generic.py`).
Không sửa `perception/` — chỉ thêm fixture + test.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-17, cùng ngày): `perception/element_classifier.py` (See step) — thăng cấp từ GTPS lên core, thêm seam cho AI classifier

**Bối cảnh:** `geometry_block_to_element()` — hàm gán `ElementType`/tên hiển
thị cho 1 `GeometryBlock` — nằm ở `applications/gpts/mapping_service.py`,
nhưng docstring của chính nó từ trước đã ghi rõ đây là stand-in tạm cho
`perception/element_classifier.py` (milestone #2 ở bảng "Chưa làm", chưa
build). Đây là năng lực core generic (See step, v3 §9.2) bị mắc kẹt trong
module use-case cụ thể — nếu Audit/Advisory sau này cần typed elements, sẽ
phải import từ `gpts` (phá "Quy tắc không được phá vỡ") hoặc viết lại.

**Đã làm:**
- Tạo `perception/element_classifier.py` — **chỉ import
  `perception.models` + `typing`**, không đụng `mapping/`/`applications/`,
  không có string GTPS/HMV/tax nào. Gồm:
  - `classify_block(block, index, fmt, anchor) -> Element` — baseline tất
    định, logic **giữ nguyên y hệt** `geometry_block_to_element()` cũ (dời
    nguyên khối, không đổi hành vi): DOCX heading/para theo `style_id`
    prefix, table cell theo `table_index`, XLSX luôn CELL theo
    `named_range`/`cell_address`, PDF luôn PARA theo dòng text.
  - `classify_blocks(blocks, fmt, anchors, start_index=0, classifier=classify_block) -> list[Element]`
    — hàm assembly xây cả Element Index cho 1 document, đánh số từ
    `start_index` (để caller gộp nhiều source file vẫn giữ 1 dải index
    liên tục).
  - `Classifier` — `Protocol` định nghĩa chữ ký `(block, index, fmt, anchor) -> Element`.
    `classify_blocks` nhận `classifier` tuỳ chọn (mặc định là baseline) —
    **đây là seam cho Classification Layer AI thật (model do user cung
    cấp, không phải OpenAI/Workbench) cắm vào sau này**, không cần sửa
    `classify_blocks` hay bất kỳ caller nào. Chưa build model AI nào —
    đúng scope việc này chỉ là seam.
- `applications/gpts/mapping_service.py`: xoá hẳn
  `geometry_block_to_element()` cục bộ, import + gọi
  `classify_blocks()` từ `perception.element_classifier` (cả cho
  `target_elements` lẫn vòng lặp nhiều `source_paths`, vẫn giữ đúng dải
  index liên tục qua `start_index`). `run_mapping()` không đổi hành vi —
  `test_mapping_service.py` (3 test, gồm cả test multi-source-file merge)
  vẫn pass nguyên, xác nhận `source_elements`/`target_elements`/`mapped`
  giống hệt trước.
- `tests/test_element_classifier.py` (7 test mới) — dùng
  `fixture_generic_handbook.docx` (fixture phi-tài-chính, xem mục ngay
  trên): heading → `ElementType.HEADING` (đúng số lượng + có `style_id`),
  para → `PARA`, table cell → `CELL` (đúng 9 cell, đủ
  `table_index`/`row_index`/`col_index`), `start_index` offset đúng,
  `classify_block` khớp `classify_blocks` từng phần tử, **và 1 test chứng
  minh seam hoạt động thật**: truyền 1 mock classifier luôn trả về `PARA`
  — assert `classify_blocks` dùng đúng mock đó (không phải baseline), kèm
  sanity-check baseline KHÔNG trả toàn `PARA` để loại trừ khả năng test
  pass "ngẫu nhiên".

**Tests:** 56 → **63 passed** (7 test mới ở `test_element_classifier.py`).
Không sửa `anchor_builder.py`/`parser.py`/`detector.py`, không thêm
dependency mới.

**⚠️ SUPERSEDED (2026-08-17, muộn hơn cùng ngày):** chữ ký `Classifier`/
`classify_blocks(..., classifier=...)` mô tả ngay trên — seam **per-block**
— đã bị thay bằng seam **document-level**. Xem mục "✅ ĐÃ GIẢI QUYẾT" ngay
bên dưới.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-17, muộn hơn cùng ngày): Nâng seam `Classifier` từ per-block lên document-level

**Bối cảnh:** seam vừa build (mục ngay trên) nhận từng `block` một —
`Classifier = (block, index, fmt, anchor) -> Element`. Vấn đề: 1 model AI
cắm vào seam này không thấy được các block xung quanh, nên không thể suy
luận theo ngữ cảnh (vd gán "section" cho heading dựa vào heading liền kề)
và bắt buộc phải gọi model 1 lần/block (tốn kém, mất ngữ cảnh) thay vì
batch cả document trong 1 lần gọi.

**Đã sửa (chỉ đổi hình dạng seam, hành vi baseline giữ nguyên y hệt):**
- `Classifier` protocol đổi chữ ký thành document-level:
  `(blocks, fmt, anchors, start_index=0) -> list[Element]` — nhận toàn bộ
  block của 1 document trong 1 lần gọi.
- `classify_block(block, index, fmt, anchor) -> Element` **giữ nguyên**
  — vẫn là building block per-block cho baseline, không đổi logic.
- `classify_blocks(blocks, fmt, anchors, start_index=0) -> list[Element]`
  — bỏ tham số `classifier=` (seam per-block không còn ở đây nữa), thân
  hàm map `classify_block` qua từng `(block, anchor)` **y hệt logic cũ**,
  và giờ chính hàm này khớp đúng chữ ký `Classifier` document-level →
  đóng vai trò baseline Classifier mặc định. Cơ chế inject: caller giữ 1
  biến `Classifier` (mặc định `classify_blocks`) rồi gọi thẳng — model AI
  tương lai cùng chữ ký là drop-in replacement, không cần dispatcher riêng.
- `applications/gpts/mapping_service.py`: không cần sửa gì — vốn đã gọi
  `classify_blocks(...)` không truyền `classifier=` từ trước. Verify lại:
  `test_mapping_service.py` (3 test) vẫn pass nguyên, `run_mapping()`
  không đổi hành vi.
- `tests/test_element_classifier.py`: thay test seam per-block cũ bằng 2
  test document-level — 1 xác nhận `classify_blocks` khớp đúng
  `Classifier` protocol mới, 1 chứng minh 1 classifier document-level khác
  (mock, có `len(blocks)` trong tên phần tử — bằng chứng nó "thấy" toàn
  bộ document) dùng thay baseline được, kèm sanity-check baseline không
  trả toàn `PARA` để loại trừ pass ngẫu nhiên.

**Tests:** 63 → **64 passed** (net +1 — 1 test cũ thay bằng 2 test mới).
Chưa build model AI nào — đúng scope, chỉ đổi hình dạng seam.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-17, muộn hơn cùng ngày nữa): Harness so sánh Classifier — chỗ verify model AI của user trước khi thay baseline

**Bối cảnh:** seam `Classifier` document-level (mục ngay trên) đã cho phép
cắm 1 model AI thay `classify_blocks`, nhưng chưa có cách nào để user tự
kiểm tra model của họ "hợp lý" tới đâu trước khi thật sự dùng nó — không
có công cụ nào so sánh output của candidate với baseline trên cùng 1 input.
Việc này xây đúng công cụ đó, **không đụng pipeline mapping** hiện có.

**Đã thêm (package mới `foundation/eval/`, hoàn toàn tách biệt):**
- `eval/classifier_diff.py` — **chỉ import từ `perception.*`** (+ stdlib),
  tuyệt đối không đụng `applications/`/`mapping/`/`gpts`, không string
  use-case nào — công cụ generic, dùng được cho bất kỳ Classifier nào.
  - `ComparisonReport` (dataclass) — `total_elements`, `count_match`,
    4 tỉ lệ (`type_agreement`/`name_agreement`/`anchor_preserved`/
    `exact_agreement`, tính trên các index có mặt ở CẢ HAI phía),
    `divergences` (list chi tiết từng điểm lệch) + `missing_in_candidate`/
    `extra_in_candidate` (khi độ dài 2 bên không khớp). Docstring nhấn
    mạnh rõ: đây là **đồng thuận với baseline, KHÔNG phải "độ chính
    xác"** — baseline chỉ là heuristic tạm, 1 model tốt có thể **cố tình**
    lệch (type/section tinh hơn) — phải tự soát `divergences` để phân
    biệt "tốt hơn" với "sai".
  - `diff_elements(baseline, candidate) -> ComparisonReport` — **pure
    function, không I/O**, so khớp theo `Element.index` (không phải vị trí
    list, để chịu được candidate đánh số lệch), anchor so bằng `==` (đúng
    invariant: Classifier không được sửa Anchor, chỉ được gán nhãn).
  - `compare_on_document(path, candidate, baseline=classify_blocks) -> ComparisonReport`
    — end-to-end thật: `extract_geometry` → `assign_anchors` **1 lần duy
    nhất**, cả 2 Classifier chạy trên đúng cùng input rồi mới diff.
  - `render_report(report) -> str` — bảng metric + list divergence (cắt ở
    50 dòng, có dòng "... and N more").
  - `candidate_stub(...)` — placeholder, hiện **delegate thẳng sang
    `classify_blocks`** (đánh dấu rõ bằng comment `# TODO: REPLACE...` nêu
    đúng chữ ký bắt buộc) — cho phép chạy harness ngay hôm nay, ra
    100% agreement như 1 phép thử "harness tự nó không tạo diff giả".
  - `if __name__ == "__main__":` — chạy `compare_on_document` trên
    `fixture_generic_handbook.docx` (fixture phi-tài-chính, không phải
    GTPS/HMV) với `candidate_stub`, in `render_report(...)` — verify thật
    qua `python -m eval.classifier_diff`, ra đúng 17 element, 100% mọi
    tỉ lệ, "No divergences."
- `tests/test_classifier_diff.py` (6 test) — 5 test thuần `diff_elements`
  (không I/O): giống hệt nhau → full agreement; có type/name lệch → đúng
  số lượng + đúng index divergence; candidate ít phần tử hơn →
  `count_match=False` + `missing_in_candidate` đúng, chỉ diff phần giao;
  candidate đổi Anchor → `anchor_preserved<1.0` + `anchor_changed=True`
  đúng chỗ; `render_report` cắt đúng ở 50 dòng. + 1 smoke test end-to-end
  (`compare_on_document` trên fixture thật + `candidate_stub` → chạy
  không lỗi, `exact_agreement == 1.0`).

**Không đụng:** `perception/` (element_classifier/anchor_builder/parser/
detector/models), `mapping/`, `applications/`, `api/` — chỉ thêm mới
`eval/` + test tương ứng.

**Tests:** 64 → **70 passed** (6 test mới ở `test_classifier_diff.py`).

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-17, muộn hơn cùng ngày nữa): Tách `mapping/` — `demo_mapper.py` (GTPS) rời khỏi `writeback.py`/`lineage.py` (core, đổi tên `output/`)

**Bối cảnh:** thư mục `mapping/` gộp chung 3 thứ khác cấp use-case, gây lẫn
ranh giới:
- `demo_mapper.py` — `DEMO_RULES` (toạ độ cell của đúng 1 client HMV) +
  `__main__` hard-code đường dẫn máy cá nhân tới file client → thuộc use
  case GTPS, không phải Foundation.
- `writeback.py` (`WritebackEngine`) — ghi giá trị vào file theo Anchor,
  chỉ import `perception.anchor_builder`, không biết gì về HMV/tax → năng
  lực Foundation thật (đọc/ghi/xoá/thay theo Anchor).
- `lineage.py` (`LineageLogger`) — trace generic, không biết use-case nào.

`writeback.py`/`lineage.py` đang được dùng chung bởi `api/routes/process.py`
**và** `tests/test_patch_element.py` (không chỉ gpts) — nên KHÔNG thể dời
vào `applications/gpts/` (sẽ buộc `api/` phải import ngược từ `gpts`, sai
đúng loại lỗi vừa sửa ở `element_classifier.py`). Giải pháp: tách, không
dời cả cục.

**Đã làm (hành vi runtime giữ nguyên 100%, chỉ đổi vị trí file + import):**
- `mapping/demo_mapper.py` → `applications/gpts/demo_mapper.py` (dùng
  `git mv`, giữ lịch sử). Nội dung `DEMO_RULES`/`build_docx_anchor`/
  `build_xlsx_anchor`/`run_demo_mapping` **không đổi**. `__main__` sửa:
  bỏ hẳn đường dẫn tuyệt đối hard-code
  (`c:\Users\PC\Downloads\...\anonymize client\...`) — giờ đọc từ
  `sys.argv`, in usage + `sys.exit(1)` nếu thiếu tham số
  (`python -m applications.gpts.demo_mapper <excel_path> <docx_path>`) —
  không còn đường dẫn máy/client nào nhúng trong code.
- Đổi tên `mapping/` → `output/` (`git mv`, giữ nguyên nội dung
  `writeback.py`/`lineage.py`) + `output/__init__.py` mới. Xoá sạch
  `mapping/` (kể cả `__pycache__` cũ) — không còn thư mục nào tên
  `mapping` trong repo.
- Cập nhật import ở mọi nơi dùng tới: `api/routes/process.py`
  (`mapping.lineage`→`output.lineage`, `mapping.writeback`→
  `output.writeback`), `tests/test_patch_element.py`
  (`mapping.writeback`→`output.writeback`),
  `applications/gpts/mapping_service.py` (`mapping.demo_mapper`→
  `applications.gpts.demo_mapper`, `mapping.lineage`→`output.lineage`,
  `mapping.writeback`→`output.writeback`) + sửa docstring/comment nhắc
  đường dẫn cũ trong 3 file này và `.gitignore` (dòng ghi chú
  `mapping/lineage.py`→`output/lineage.py`).
- Grep lại toàn repo xác nhận hết `from mapping`/`import mapping`. Còn
  đúng 1 chỗ nhắc "mapping/anchor_builder.py" trong comment ở
  `perception/anchor_builder.py` (dòng 48) — **cố tình để nguyên**: đây là
  di tích của 1 lần dời khác, từ trước (`mapping/anchor_builder.py` cũ,
  đã xoá hẳn từ 2026-08-14 khi anchor logic dời vào `perception/`), không
  liên quan gì tới việc tách `mapping/` hôm nay, và sửa file này vi phạm
  đúng ràng buộc "không đụng `perception/`" của việc này.
- Verify ranh giới: `output/writeback.py` chỉ import
  `perception.anchor_builder` + `docx`/`openpyxl` (khi cần) — không biết
  `applications`/`demo_mapper`/`DEMO_RULES`. `output/lineage.py` chỉ
  import `pydantic`/stdlib. Không sửa gì bên trong 2 file này — đã đúng
  ranh giới từ trước, chỉ cần đổi tên thư mục chứa.
- Verify thêm: `api/app.py::create_app()` load route bình thường (4 route
  cũ vẫn nguyên), `python -m applications.gpts.demo_mapper` (không tham
  số) in đúng usage + exit code 1, không crash.

**Tests:** vẫn **70 passed** (không thêm/bớt test — thuần refactor vị trí
file, hành vi mapping demo giữ nguyên y hệt, xác nhận qua
`test_mapping_service.py` + `test_patch_element.py` pass nguyên).

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-17, muộn hơn cùng ngày nữa): P3-04 (`duplicate_ordinal`) — coverage không còn phụ thuộc file thật/`skipif`

**Bối cảnh:** `test_p304_docx_duplicate_ordinal_survives_uneven_drift_on_real_document`
(`tests/test_anchor_builder.py`) — bài test P3-04 quan trọng nhất
(disambiguation qua `duplicate_ordinal` khi có drift lệch giữa các
occurrence trùng chữ ký) — chỉ chạy được khi có file HMV thật trên máy
(`@requires_real_docx`, `skipif` nếu thiếu). Trên 1 checkout sạch hoặc CI
không có file này, test **bị skip âm thầm** — nghĩa là guarantee quan
trọng nhất của anchor system có thể có **0% coverage thật** mà không ai
biết, và fixture cũ cũng không neutral (1 tài liệu tài chính duy nhất).

**Đã thêm (không sửa `perception/anchor_builder.py` — logic đã đúng từ
trước, chỉ thêm fixture + test):**
- `tests/fixtures/_generate_anchor_stress_docx.py` — script deterministic
  sinh `fixture_anchor_stress.docx`: tài liệu hư cấu hoàn toàn ("sổ tay
  thư viện dụng cụ khu phố"), không tên client/số liệu tài chính nào.
  Tái tạo đúng ambiguity thật của P3-04: caption `"See the note at the end
  of this section."` lặp lại **8 lần** (≥6 theo yêu cầu), luôn cùng style
  `Normal` — cùng chữ ký `(style_id, text_fingerprint)` mà
  `assign_docx_anchor` group theo — mỗi lần cách nhau đúng 1 heading + 1
  đoạn văn riêng (nội dung khác nhau, vị trí biết trước: occurrence thứ k
  luôn ở `paragraph_index = 3k + 4`). Cả file `.docx` sinh ra lẫn script
  sinh nó đều commit.
- `tests/test_anchor_p304_synthetic.py` (3 test, **không `skipif` nào**):
  - `test_fixture_exists` + `test_synthetic_fixture_has_duplicate_caption_signature_and_correct_ordinals`
    — guard: fixture có đúng 8 occurrence cùng chữ ký (≥6), `assign_anchors`
    gán đúng `duplicate_ordinal == k` cho occurrence thứ k (test cả k=0,
    k=4 — occurrence giữa, và k cuối).
  - `test_p304_synthetic_duplicate_ordinal_survives_uneven_drift_between_occurrences`
    — bài test lõi: chèn 50 paragraph filler ngay trước occurrence #4
    (không phải đầu file) → occurrence #4 dịch +50, nhưng occurrence #3
    liền trước **đứng yên hoàn toàn** và trở thành "gần" record cũ hơn
    (cách 3) so với target thật (cách 50). **Sanity/false-pass guard**:
    assert tường minh 1 chiến lược nearest-`paragraph_index` ngây thơ SẼ
    chọn sai (chọn occurrence #3, không phải target) — chứng minh kịch
    bản test không tầm thường. Sau đó `resolve_docx_anchor` qua
    `duplicate_ordinal` phải trả **đúng** occurrence #4 (verify bằng
    object identity `resolved._p is expected._p`), `message is None`
    (Strategy 1, không cảnh báo).
  - Verify: cùng 1 phiên chạy, `tests/test_anchor_builder.py`'s
    `@requires_real_docx` test (máy này có sẵn file HMV thật) vẫn PASS
    song song, không đổi/không xoá — coverage thật giờ có ở **cả 2 nguồn**
    (thật khi có file, tổng hợp luôn luôn có).

**Tests:** 70 → **73 passed, 0 skipped** (3 test mới, xác nhận chạy thật —
không nằm trong danh sách skip của pytest run này).

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-18): Sửa lệch kiến trúc lớn — bỏ giả định GTPS khỏi lớp upload/task chung, tách Perceive khỏi Execute

**Bối cảnh:** user chỉ ra đúng lỗi kiến trúc nghiêm trọng nhất từ trước tới
giờ — lớp "generic" upload/task (`api/routes/process.py` cũ,
`workspaceStore.ts`, mọi pane dựng trên đó) thực chất mã hoá cứng **1 luồng
GTPS duy nhất** xuyên suốt: `upload → (đuôi file suy ra vai trò
source/target) → tự động POST vào route CHÍNH LÀ
applications/gpts/mapping_service.run_mapping → response CÓ HÌNH DẠNG
source_elements/target_elements/mapped`. Không có ranh giới nào giữa
**Perceive** (trích xuất + phân loại, generic) và **Execute** (chạy mapping
GTPS, thuộc application). Phát hiện nghiêm trọng nhất: **`AgentComposer`
khoá ô chat cho tới khi `processingStatus === 'done'`** — nghĩa là nơi
DUY NHẤT user có thể "nêu yêu cầu" lại nằm SAU bước Execute nó lẽ ra phải
đi trước — đảo ngược hoàn toàn nguyên tắc `Perceive → user nêu ý định →
Execute`.

**Audit trước khi sửa (leakage report đầy đủ đã trình bày cho user):** liệt
kê từng leak với file:line cụ thể ở cả backend (`api/routes/process.py`)
và frontend (`workspaceStore.ts`, `NewTaskPage.tsx`, `FileRail.tsx`,
`AgentPane.tsx`/`AgentComposer.tsx`, `DocumentPane.tsx`/`ElementsPane.tsx`/
`ResultsPane.tsx`, `agentStore.ts`, `api/client.ts`) — bao gồm đúng câu chữ
user trích dẫn `"Add a target document (.docx) to continue"`
(`NewTaskPage.tsx:211`).

**Kiến trúc mới (đã lên plan mode, user duyệt kèm 12 điểm refinement):**

**Backend:**
- `api/routes/process.py` **xoá hẳn**, thay bằng 2 route file tách biệt
  theo đúng ranh giới:
  - `api/routes/documents.py` — **hoàn toàn generic, không import
    `applications.*` nào**: `POST /api/documents` (1 file/lần — không phải
    batch, để mỗi tài liệu có trạng thái độc lập thật sự
    `perceiving`/`ready`/`error`, không phải 1 cờ workspace chung),
    `GET /api/documents/<session_id>`, `GET .../elements/<doc_id>` (lazy —
    không nhét sẵn elements vào response upload, tự thiết kế lại theo yêu
    cầu review #3), `PATCH .../elements/<doc_id>` (sửa được **bất kỳ**
    tài liệu nào, không chỉ "target" — tiện thể sửa luôn bug thật: XLSX
    trước đây bị chặn sửa dù `WritebackEngine.apply_single_patch` vốn đã
    hỗ trợ), `GET .../download/<doc_id>`. Có `manifest.json` per-session
    (`doc_id` uuid4 — không bao giờ dùng filename/index/thứ tự upload làm
    identity, đúng yêu cầu review #8).
  - `api/routes/gpts.py` (mới) — **route DUY NHẤT dưới `api/` được phép
    import `applications.gpts.*`**: `POST /api/gpts/map` nhận
    `session_id` + `source_doc_ids`/`target_doc_id` **do caller khai báo
    tường minh**, gọi thẳng `run_mapping()` **không đổi 1 dòng logic**.
  - `applications/gpts/workbench_client.py` → di dời thành
    `applications/workbench_client.py` (grep lại toàn repo trước khi dời —
    đúng 2 nơi tham chiếu: `api/routes/agent.py`,
    `tests/test_agent_route.py`, cả 2 đã cập nhật) — module này thật ra
    generic (proxy Workbench), không phải riêng GTPS, bị đặt sai chỗ từ
    trước.
  - `api/routes/agent.py::_build_system_prompt` bỏ nhánh
    `mapped_count`/`mapped_summary` — route Agent phải generic hoàn toàn,
    enrichment riêng GTPS không thuộc về đây.
- Test mới `tests/test_documents_route.py` (11 test) — gồm 1 test grep
  tường minh xác nhận response `/api/documents` **không chứa** bất kỳ từ
  khoá GTPS nào (`source_elements`, `mapped`, `gtps`, `hmv`,
  `demo_rules`...), và 1 test end-to-end xác nhận `/api/gpts/map` vẫn ra
  đúng 3 giá trị mapped y hệt `test_mapping_service.py` (chứng minh tách
  route không đổi hành vi `run_mapping`). `tests/test_patch_element.py`
  viết lại theo route mới + thêm test XLSX patch thật (mở lại file bằng
  `openpyxl`, xác nhận đúng giá trị + file gốc không đổi — theo yêu cầu
  review #7, không chỉ check HTTP 200).
- **Bug thật bắt được khi viết test** (không phải leak, bug logic Python):
  `api/routes/gpts.py` ban đầu viết `from api.routes.documents import
  UPLOAD_ROOT` — import kiểu này đông cứng giá trị tại thời điểm import
  đầu tiên; test monkeypatch `documents_module.UPLOAD_ROOT` sau đó không
  ảnh hưởng tới `gpts.py` vì đây là 2 binding độc lập. Sửa bằng cách import
  cả module (`from api.routes import documents as documents_module`) và
  luôn đọc `documents_module.UPLOAD_ROOT` — tra cứu động tại thời điểm
  gọi, không đông cứng.

**Frontend:**
- `state/workspaceStore.ts` viết lại hoàn toàn: bỏ hẳn `sourceFiles`/
  `targetFiles`, thay bằng `documents: WorkspaceDocument[]` generic (mỗi
  doc có `clientId` ổn định + `status` độc lập). `addDocument()` không suy
  luận vai trò gì từ đuôi file. State `gptsMapping` tách hẳn riêng — đây
  chính là khái niệm "task" (theo review #1), chỉ được tạo khi gọi
  `runGptsMappingTask()` tường minh, không bao giờ tự động.
- **Sửa quan trọng nhất (review #12):** `AgentComposer`/`AgentPane` giờ mở
  khoá dựa trên "**có ≥1 document đã perceive xong**"
  (`documents.some(d => d.status === 'ready')`), KHÔNG còn dựa vào trạng
  thái xử lý GTPS — đúng thứ tự `Perceive → Agent sẵn sàng → user nêu yêu
  cầu → Execute`.
- `NewTaskPage.tsx` bỏ hẳn CTA `"Add a target document (.docx) to
  continue"` và mọi gate 2-vai-trò — chỉ cần ≥1 file perceive xong là vào
  được workspace.
- Hành động GTPS mới, **cố tình phụ (secondary)** theo đúng review #5:
  `components/gpts/GptsMappingAction.tsx` (thư mục riêng, soi gương
  `applications/gpts/` bên backend) — chỉ xuất hiện qua menu "Applications"
  phụ trong `WorkspaceHeader`, không phải CTA mặc định nào trên màn hình
  upload. User tự chọn tài liệu nào là source/target ngay trong panel này
  — đây là nơi DUY NHẤT vai trò được gán, luôn luôn tường minh.
- `FileRail.tsx` bỏ nhãn "Target"/"Source", chỉ còn tên file + icon định
  dạng + trạng thái perceive. `DocumentPane.tsx`/`ElementsPane.tsx` đọc
  theo tài liệu đang active (`activeDocClientId`) thay vì `targetElements`
  cứng — giờ xem/sửa được bất kỳ tài liệu nào, không chỉ "target".
  `ResultsPane.tsx` đọc từ `gptsMapping` (đúng là view riêng của GTPS,
  ngôn ngữ GTPS ở đây hợp lệ vì đã tường minh scoped, không phải leak).
- **Bug thật bắt được qua browser thật (Playwright, cài tạm rồi gỡ đúng
  quy ước cũ):** upload 2 file cùng lúc → `addDocument()` gọi
  `uploadDocument()` cho từng file gần như đồng thời, cả 2 đều đọc
  `get().sessionId` là `null` trước khi request đầu tiên kịp trả về →
  BACKEND TỰ TẠO 2 SESSION KHÁC NHAU thay vì 1 session dùng chung. Hệ quả
  thật thấy được: gọi `/api/gpts/map` báo `404 Unknown doc_id` dù UI vẫn
  hiện đúng tên file. Sửa bằng `pendingSessionPromise` (module-level) —
  lệnh upload đầu tiên trong 1 batch đồng bộ mới được tạo session mới,
  các lệnh upload còn lại trong batch phải đợi promise đó rồi mới gọi API
  với đúng `session_id`. Không phát hiện được nếu chỉ chạy `tsc`/pytest —
  cần trình duyệt thật mới lộ ra (đúng lý do phải verify UI bằng browser
  thật thay vì chỉ tin type-check).
- **Bug thật thứ 2, cũng chỉ browser thật mới bắt được:** nút "Download" ở
  `WorkspaceHeader` hiện ra ngay khi tài liệu active có `docId` — bất kể
  đã từng sửa/patch gì chưa — bấm vào sẽ 404. Thêm field `hasPatch` vào
  `WorkspaceDocument`, chỉ bật `true` sau khi `editElement`/`undoLastEdit`
  hoặc `runGptsMappingTask` thành công; nút Download giờ chỉ hiện khi
  `hasPatch === true`.

**Verify thật qua browser (Playwright, cài tạm rồi gỡ — không còn trong
`package.json`):**
1. Upload 1 file `.docx` bất kỳ, không ghép cặp gì → không còn chữ "target
   document (.docx)"/"Source"/"Target" nào trên màn hình upload → nút
   "Open Workspace" xuất hiện ngay (không cần file thứ 2) → vào workspace
   → **ô chat Agent đã mở khoá ngay**, chưa hề chạy hành động GTPS nào → 0
   lỗi console.
2. Upload cả 2 file demo HMV thật (source xlsx + target docx) — xác nhận
   Output pane vẫn "No output yet" (chưa tự chạy gì) → mở menu
   "Applications" (menu phụ, không phải CTA chính) → chọn GTPS Local File
   Mapping → tự chọn vai trò source/target → bấm Run → **"Done — 3
   elements mapped"**, Output pane hiện đúng 3 mapped value + đúng anchor
   (`RPTs!E8`, `RPTs!F8`, `Financial Analysis!D7`) — khớp 100% với
   `test_mapping_service.py`/`test_documents_route.py`'s regression test —
   Download link xuất hiện đúng lúc, tải được, 0 lỗi console.

**Không đụng:** `perception/`, `output/`, `eval/`,
`applications/gpts/mapping_service.py`/`demo_mapper.py` (logic giữ
nguyên 100%, chỉ đổi nơi gọi vào).

**Cập nhật "Quy tắc không được phá vỡ":** ranh giới "module biết use-case
cụ thể không được nằm ngoài `applications/`" giờ áp dụng rõ ràng luôn cho
`api/` — chỉ đúng 1 file (`api/routes/gpts.py`) được phép import
`applications.gpts.*`; mọi route khác dưới `api/` phải generic hoặc dùng
`applications/` dùng chung (`applications/workbench_client.py`).

**Tests:** 73 → **90 passed** (11 test mới `test_documents_route.py` + test
XLSX patch mới + test agent route cập nhật). `tsc -b` sạch, `npm run
build` sạch. Frontend verify bằng browser thật, không chỉ type-check.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-18, muộn hơn cùng ngày): Chốt tường minh vòng đời multi-document session — điểm review #13

**Bối cảnh:** sau khi duyệt refactor ở mục trên (kèm 12 điểm review), user
nêu thêm 1 điểm quan trọng: contract `session_id` giữa nhiều lần upload
cần **tường minh** — nhiều tài liệu bất kỳ (PDF/XLSX/DOCX...) upload cùng
lúc, tuần tự, hay bổ sung sau đều phải rơi vào **đúng 1 session** duy
nhất, không được vô tình tách thành nhiều session (`Session A → File 1,
Session B → File 2...`). Yêu cầu: chọn 1 API contract rõ ràng, ghi tài
liệu tường minh, và có test khoá lại hành vi này trước khi tiếp tục.

**Thực ra bug đúng kịch bản này đã bắt được và sửa ở mục trên** (2 file
upload gần như đồng thời → 2 request đều thấy `sessionId` là `null` →
backend tự tạo 2 session khác nhau → `/api/gpts/map` báo `404 Unknown
doc_id`) — sửa bằng `pendingSessionPromise` phía frontend. Nhưng đúng như
user chỉ ra: **verify lúc đó chỉ là 1 script Playwright thủ công, xoá đi
ngay sau khi chạy** — không có test tự động nào khoá lại invariant này,
và tài liệu (docstring) chưa nêu rõ ràng 3 khái niệm Document/Session/Task
tách biệt theo đúng thuật ngữ user dùng.

**Đã đóng gap:**
- `api/routes/documents.py`: viết lại phần đầu docstring thành 1 "glossary"
  tường minh — `Document` = 1 artifact đã upload/perceive (`doc_id`),
  `Session` = context chứa 0+ document (`session_id`), `Task` = thao tác
  do user yêu cầu tường minh (**không tồn tại trong module này**, chỉ tồn
  tại ở `api/routes/gpts.py`). Có sơ đồ ASCII
  `Session -> Document A/B/C -> Elements/Anchors` đúng hình dạng user mô
  tả. Ghi rõ: **route này chỉ giữ đúng nửa hợp đồng đơn giản** ("cho
  `session_id` thì join, không cho thì tạo mới") — nửa còn lại (không bao
  giờ gửi 2 request "chưa có session" cùng lúc) là trách nhiệm của
  caller/frontend, và trỏ thẳng tới nơi frontend thực hiện điều đó
  (`pendingSessionPromise`).
- `state/workspaceStore.ts`: thêm khối comment glossary tương tự ở đầu
  file, cùng thuật ngữ Document/Session/Task, cùng sơ đồ ASCII — để 2 phía
  backend/frontend mô tả đúng 1 mental model, không lệch nhau.
- `tests/test_documents_route.py` — test mới
  `test_three_arbitrary_formats_share_one_session_with_independent_status`:
  upload **1 PDF thật + 1 XLSX phi-tài-chính (sinh inline) + 1 DOCX generic
  đã có** tuần tự vào cùng 1 session, xác nhận: cả 3 nằm đúng 1
  `session_id`, mỗi `doc_id` riêng biệt không trùng/không gộp nhầm, mỗi
  document có `status`/`format` độc lập, response liệt kê không chứa từ
  khoá GTPS nào, mỗi document lấy được elements riêng theo đúng `doc_id`
  **không theo thứ tự upload**, và cuối cùng gọi `/api/gpts/map` tham
  chiếu tổ hợp bất kỳ 2-trong-3 `doc_id` này làm source + 1 làm target —
  xác nhận addressability không phụ thuộc thứ tự/định dạng upload (đúng
  yêu cầu #6 của user).
- **Verify lại bằng browser thật** (Playwright, cài tạm rồi gỡ đúng quy
  ước), lần này bám sát **đúng kịch bản chấp nhận user viết ra**: chọn
  cùng lúc 3 file PDF + XLSX + DOCX qua 1 lần chọn file (đúng path thực tế
  từng gây ra race trước đây) → xác nhận từng điểm một: cả 3 file đều lên
  "ready", cả 3 response upload trả về **đúng cùng 1 `session_id`**,
  không có chữ "Source"/"Target" nào, không có chữ "GTPS" nào trên màn
  hình upload, sang workspace thì Agent **đã mở khoá ngay**, Output pane
  vẫn "No output yet" (chưa chạy gì), FileRail liệt kê đủ cả 3 tài liệu
  riêng biệt, 0 lỗi console.

**Không đụng:** logic `applications/gpts/mapping_service.py` hay bất kỳ
route nào khác — chỉ thêm tài liệu tường minh + 1 test mới.

**Tests:** 90 → **91 passed**. `tsc -b` sạch. Playwright cài tạm đã gỡ,
không còn trong `package.json`/`package-lock.json`.

---

## ✅ ĐÃ GIẢI QUYẾT (2026-08-18, muộn hơn cùng ngày nữa): Triển khai `Foundation_UI_Spec_v1.0.md` — workspace AI-native thật, không chỉ đổi kiến trúc phía sau

**Bối cảnh:** kiến trúc generic (Perceive → user nêu ý định → Execute) đã
xong và verify kỹ ở các mục trên — phiên này là **frontend/UX thuần**,
triển khai `Foundation_UI_Spec_v1.0.md` (root repo) trên NỀN kiến trúc đó,
không đụng backend, không tái phá vỡ bất kỳ invariant nào đã chốt.

**Audit trước khi sửa:** phần lớn design token system (`index.css` — màu
sắc/typography khớp gần như y hệt §30-31 của spec), `HomePage`,
`StatusBadge`, `ConfidenceBadge` (đã có sẵn dải High/Medium/Low theo §25),
`AgentMessage` (đã render đúng pattern progress-steps ✓ theo §9/§34), 4
preset workspace (Agent/Inspect/Review/Compare) — **đã được 1 phiên trước
xây sẵn khớp spec** (thấy rõ qua comment "Palette per UI Spec §30" trong
`index.css`). Việc phiên này là đóng các gap CÒN LẠI, không xây lại từ đầu.

**Đã triển khai:**
- **Document Viewer format-aware (§16-17, gap lớn nhất):** trước đây CHỈ 1
  view phẳng cho mọi định dạng — XLSX/PDF thậm chí không được nhóm (không
  lưới, không trang). Thêm bộ chuyển chế độ Original/Elements/Split
  (`components/document/DocumentPane.tsx`):
  - **Original — XLSX:** lưới hàng/cột thật, parse từ `cell_address`
    (`parseCellAddress`/`colLetter`), nhóm theo sheet, header cột A/B/C...
    + số dòng, giống spreadsheet thật — không cần thư viện mới.
  - **Original — PDF:** nhóm theo `page`, đúng thứ tự `reading_order_index`,
    dạng "Page N" card — ghi rõ minh bạch "Page image preview isn't
    available in this deployment" (Poppler chưa cài, theo đúng STATUS.md
    cũ) thay vì giả vờ render ảnh trang.
  - **Original — DOCX:** flow hiện có, bọc trong page-card trắng có bóng,
    giống trang tài liệu thật hơn.
  - **Elements** = flow hiện có giữ nguyên (mọi định dạng). **Split** = 2
    view cạnh nhau.
  - CSS mới: `.view-mode-switch`, `.xlsx-grid-*`, `.document-page-card`,
    `.pdf-page-card`.
- **Element Explorer semantic hierarchy (§17-19):** `ElementsPane.tsx`'s
  `groupElements()` trước đây CHỈ nhóm DOCX (heading/table) — XLSX/PDF rơi
  hết vào 1 nhóm "Document" phẳng (662/968 phần tử dồn 1 chỗ). Sửa: XLSX
  nhóm theo sheet, PDF nhóm theo page — cùng logic ngữ nghĩa với Document
  Viewer's Original mode.
- **Giảm nhiễu confidence (§25):** trích xuất tất định → confidence luôn
  100%, hiển thị "100%" lặp lại ở MỌI dòng (662+ lần) đúng là "visual
  noise" spec cảnh báo. Ẩn badge trong danh sách khi confidence ≥ 99.9%
  (chỉ ẩn ở list — Inspector vẫn hiện đầy đủ khi chọn 1 phần tử).
- **Provenance/Trace (§23):** CSS `.provenance-chain`/`.provenance-step`
  đã có sẵn trong `index.css` từ trước nhưng **chưa từng được dùng ở đâu**
  — nay dùng thật trong `ResultsPane.tsx`: mỗi mapped-value card có nút
  "Provenance" mở chuỗi Output → Mapped to → Source → Confidence & time.
- **Giới hạn 10 file (§6):** bị rớt mất khi viết lại `workspaceStore.ts` ở
  phiên refactor kiến trúc trước — thêm lại, generic (không phân biệt
  role), đúng câu chữ spec ("You've reached the recommended limit...").
- **Agent composer context chip (§12):** thêm dòng "N documents in
  context" — CHỈ hiện thông tin có thật (số tài liệu), cố tình KHÔNG thêm
  chip "Elements"/"Context" giả vờ chọn được phần tử cụ thể, vì Agent chưa
  thật sự hỗ trợ retrieval đó — trung thực đúng nguyên tắc đã theo suốt dự
  án ("AgentPane honest placeholder").
- Sửa nhỏ: "Table 0" → "Table 1" (hiển thị 1-indexed, index nội bộ vẫn
  0-indexed).

**2 bug thật bắt được khi tự verify bằng browser (không phải chỉ tin
build/tsc xanh):**
1. **Infinite render loop thật** (`Maximum update depth exceeded`), chỉ lộ
   ra khi: tài liệu XLSX/PDF đang active + preset "Inspect" (Document +
   Elements cùng mount) + đúng lúc elements đang fetch (`elements ===
   null`, do cơ chế lazy-load đã xây ở phiên trước). Nguyên nhân gốc:
   `activeDoc?.elements ?? []` tạo mảng rỗng MỚI mỗi lần render khi
   `elements` là `null` → `useMemo`/`useEffect` (groups →
   `setExpandedGroups`) trong `ElementsPane` coi là dependency đổi liên
   tục → loop thật. Sửa bằng hằng số `EMPTY_ELEMENTS` dùng chung (tham
   chiếu ổn định) ở cả `ElementsPane.tsx` và `DocumentPane.tsx`. Kèm sửa
   phòng thủ thêm: `setHoveredElement` trong `workspaceStore.ts` giờ
   no-op nếu index không đổi (tránh render thừa khi hover), và lưới XLSX
   chuyển từ hàng nghìn handler `onMouseEnter`/`onMouseLeave` riêng lẻ mỗi
   ô sang **event delegation** (1 handler trên `<table>`, tra `data-el-index`)
   — vừa đúng nguyên nhân vừa tốt hơn về hiệu năng.
2. **Trạng thái "loading" hiển thị sai thành "trống vĩnh viễn":** trong lúc
   elements đang fetch (header đã hiện "Ready · N elements" nhưng
   Document/Elements pane vẫn `null`), UI cũ hiện "No document loaded"/
   "No elements extracted" — sai, vì elements THỰC SỰ sẽ tới, chỉ đang
   tải. Thêm trạng thái loading riêng ("Reading document…"/"Loading
   elements…", icon xoay) phân biệt rõ với "sẽ không bao giờ có gì" —
   thêm `iconClassName` prop cho `EmptyState.tsx` để hỗ trợ icon xoay.

**Verify bằng browser thật** (Playwright, cài tạm rồi gỡ đúng quy ước):
chụp toàn bộ luồng Home → New Task (3 file PDF+XLSX+DOCX thật) → Workspace
(Agent preset mặc định, Document ở chế độ Original) → chuyển Inspect
preset → đổi Original/Elements/Split cho cả 3 định dạng → chọn phần tử
(xác nhận đồng bộ Document ↔ Elements ↔ Inspector) → mở Applications
menu (GTPS) — **0 lỗi console** ở lần chạy cuối cùng, xác nhận từng ảnh
chụp màn hình bằng mắt.

**Không đụng:** backend (`api/`, `applications/`, `output/`,
`perception/`), kiến trúc generic document/session/task đã chốt ở các mục
trên, `GptsMappingState`/`runGptsMappingTask` vẫn nằm trong
`workspaceStore.ts` (technical debt đã biết, không di dời phiên này vì
không bắt buộc cho việc UI).

**Còn thiếu / deferred có chủ đích (P1/P2 theo spec, không phải bị bỏ
sót):** docking kéo-thả/nổi/snap thật (mới có resize qua
`react-resizable-panels`, gọi là "basic docking" theo đúng mức spec yêu
cầu P0); render pixel-chính-xác DOCX/XLSX/PDF (không có rendering engine
trong stack, dùng layout suy ra từ Anchor thay thế, đúng cho phép của
spec); Compare mode thật (vẫn placeholder "Source A/B"); History/Settings/
Diagnostics thật; command menu (Cmd+K); saved layouts/preset
customize-reset-save.

**Tests:** 91 → **91 passed** (không đổi test backend — phiên này thuần
frontend). `tsc -b` sạch, `npm run build` sạch, verify bằng browser thật
xác nhận 0 lỗi console qua toàn bộ luồng.
