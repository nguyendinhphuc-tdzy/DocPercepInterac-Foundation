# Document Perception & Interaction Foundation
## Master Context — Tổng hợp toàn bộ session
### KPMG Vietnam Innovation · Tháng 7/2026

---

> **Mục đích của file này:** Tài liệu context duy nhất cần đọc khi tiếp tục làm việc trên project này. Tổng hợp toàn bộ quyết định, kiến trúc, research, và trạng thái hiện tại.

---

## MỤC LỤC

1. [Tầm nhìn & Định vị](#1-tầm-nhìn--định-vị)
2. [Kiến trúc 4 Layer](#2-kiến-trúc-4-layer)
3. [Middle Output Flow — Cơ chế cốt lõi](#3-middle-output-flow--cơ-chế-cốt-lõi)
4. [Tech Stack — Quyết định cuối](#4-tech-stack--quyết-định-cuối)
5. [Anchor System — IP của dự án](#5-anchor-system--ip-của-dự-án)
6. [Output Strategy — 3 chế độ](#6-output-strategy--3-chế-độ)
7. [Research Findings — Tóm tắt](#7-research-findings--tóm-tắt)
8. [Tax Use Cases & Pipeline Position](#8-tax-use-cases--pipeline-position)
9. [Document Perception — Phạm vi Build hiện tại](#9-document-perception--phạm-vi-build-hiện-tại)
10. [Data Schemas](#10-data-schemas)
11. [Build Plan — 6 Phases](#11-build-plan--6-phases)
12. [ElementIndexViewer — Đã build](#12-elementindexviewer--đã-build)
13. [6 Tiêu chí thành công MVP1](#13-6-tiêu-chí-thành-công-mvp1)
14. [Open Questions — Chưa chốt](#14-open-questions--chưa-chốt)
15. [Deliverables Index](#15-deliverables-index)
16. [Thứ tự ưu tiên khi tiếp tục](#16-thứ-tự-ưu-tiên-khi-tiếp-tục)

---

## 1. Tầm nhìn & Định vị

### Foundation là gì

Một **lớp hạ tầng dùng chung** đóng vai trò "đôi mắt và đôi tay" cho mọi công cụ tài liệu AI. **Không phải** ứng dụng nghiệp vụ — là platform mà các ứng dụng dọc (dịch thuật, redlining, so sánh, trích xuất, agent) xây bên trên mà không cần rebuild phần xử lý tài liệu từ đầu.

**Nguyên tắc tuyệt đối:** AI không bao giờ thao tác trực tiếp lên file. AI chỉ *diễn đạt ý định*; Foundation là bên duy nhất thực thi — có kiểm soát phạm vi, có validate, có traceability.

### 3 Cam kết UX bất biến

| # | Cam kết | Ý nghĩa thực tế |
|---|---|---|
| 1 | **Input không đổi** | Nhận đúng file user đang có — không yêu cầu chuẩn bị thêm |
| 2 | **Output dùng được ngay** | File output mở trong Word/Excel nguyên vẹn format |
| 3 | **Không đẻ thêm bước** | Foundation chen ngang quy trình cũ, không thêm tác vụ |

### Định vị tránh

Không phải Word/Excel replacement. Đây là **review + bóc tách layer**. File xuất ra phải mở được trong Word/Excel nguyên vẹn format.

### Competitive gap

18 vendors Gartner MQ IDP 2025 đều cạnh tranh ở "extract → data → ERP". **Không vendor nào** làm governed write-back + interaction workspace độc lập. Đây là khoảng trống Foundation lấp.

---

## 2. Kiến trúc 4 Layer

```
┌──────────────────────────────────────────────────────────┐
│  Layer 4 — Applications & AI                             │
│  Translation · Redlining · Comparison · Business Tools   │
│  Agents                         [OUT OF SCOPE MVP1]      │
├──────────────────────────────────────────────────────────┤
│  Layer 3 — Document Understanding & Placement            │
│  Select · Extract · Interpret · Map · Place · Validate   │
│                                 [TỰ XÂY — risk cao]      │
├──────────────────────────────────────────────────────────┤
│  Layer 2 — Document Perception & Interaction Core        │
│  Detect · Parse · See · Locate · Read · Write            │
│  ── Substrate · Profiles · Runtime · Execution ──        │
│                     [50% OSS sẵn / 50% tự xây — IP]     │
├──────────────────────────────────────────────────────────┤
│  Layer 1 — Format Adapters                               │
│  DOCX · XLSX · PDF · PPTX · Images                      │
│                                 [Wrap Docling — dễ]      │
└──────────────────────────────────────────────────────────┘
          ↑ Access Layer: API · SDK · MCP · Connectors
```

### 4 thuộc tính nền

- **Profile-driven** — tri thức người dùng trở thành cấu hình tái sử dụng
- **Adapter-based** — swap format/parser không đụng core
- **Traceable** — mọi output có lineage về nguồn
- **Governed** — phạm vi ghi được kiểm soát, có validate

---

## 3. Middle Output Flow — Cơ chế cốt lõi

Đây là flow quan trọng nhất, được confirm trong conversation. Được mô tả từ diagram của user.

```
Input (DOCX / PDF)
        │
        ▼
Foundation parse toàn bộ elements
        │
        ▼
Middle Output: Element Index XLSX
┌─────┬──────────┬────────────┬───────────────────────────┬──────────────────────────────────┐
│  #  │ Section  │ Type       │ Element name              │ Anchor (JSON)                    │
├─────┼──────────┼────────────┼───────────────────────────┼──────────────────────────────────┤
│  1  │ —        │ heading    │ BALANCE SHEET AS AT...    │ {"para_idx":0,"style":"Heading1"} │
│  3  │ Assets   │ table      │ Table 1 — Current Assets  │ {"para_idx":5,"table_idx":0}      │
│  9  │ Assets   │ table      │ Table 2 — Non-Current     │ {"para_idx":20,"table_idx":1}     │
└─────┴──────────┴────────────┴───────────────────────────┴──────────────────────────────────┘
        │
        ▼  User request: "Take Table 2 out of this document"
        │
        ▼
Foundation lookup: element_name = "Table 2"
  → đọc Anchor {"para_idx":20, "table_idx":1}
  → roll back về file gốc tại vị trí đó
        │
        ▼
Output: Table 2 với full layout nguyên vẹn
```

### Tại sao XLSX là Middle Output đúng

1. **Index tra cứu nhanh** — Application layer query theo element_name, không scan lại toàn bộ file gốc mỗi lần
2. **User có thể đọc và edit** — mở được trong Excel, đây là Profile authoring tự nhiên nhất
3. **Anchor là cầu nối, không phải số trang** — Column "Position" = Anchor JSON (paragraph_index + style_id + fingerprint). Số trang thay đổi khi file bị chỉnh; Anchor thì không
4. **Reusable cho mọi use case** — cùng 1 Middle Output phục vụ Translation, Extraction, Redlining, Comparison, CIT workpaper

### Quy tắc quan trọng nhất

> **"Position" trong XLSX không được là số trang hay tọa độ pixel.** Phải là Anchor ID: `paragraph_index + style_id + text_fingerprint` (DOCX) hoặc `sheet_name + cell_address` (XLSX).

---

## 4. Tech Stack — Quyết định cuối

### Backend (Python 3.10+ — BẮT BUỘC)

| Thành phần | Thư viện | License | Vai trò |
|---|---|---|---|
| Parse engine | `docling` | MIT | **Core** — Detect+Parse+See. TableFormer 112k+ bảng BCTC. Local/air-gapped |
| DOCX object | `python-docx` | MIT | Build DocxAnchor — cần style_id, para_index |
| XLSX object | `openpyxl` + `defusedxml` | MIT | Build XlsxAnchor + ghi Element Index XLSX |
| API server | `fastapi` + `uvicorn` | MIT | Access Layer — POST /perception/parse |
| Validation | `pydantic` v2 | MIT | Schema cho FoundationDocument + Anchor |
| File upload | `python-multipart` | MIT | Required cho FastAPI file upload |
| File detect | `python-magic` | MIT | MIME type detection chính xác |
| Database dev | `aiosqlite` | Public domain | Dev — migrate Postgres khi scale |

### Frontend (React + TypeScript)

| Thành phần | Thư viện | License | Vai trò |
|---|---|---|---|
| Document viewer | Extend UI (`@extend/*`) | MIT | DOCX+PDF+XLSX viewer + bounding box citations — tiết kiệm 2-3 tuần |
| Bounding box | `@extend/bounding-box-citations` | MIT | Highlight element trên document |
| Element Index | `ElementIndexViewer.jsx` | Internal | ✅ Đã build — Excel-like viewer + export |
| Excel export | `xlsx` (SheetJS) | Apache 2.0 | Export XLSX từ ElementIndexViewer |
| State | `zustand` | MIT | Lightweight state management |
| API client | `@tanstack/react-query` | MIT | Fetch + cache API responses |
| PDF render | `pdfjs-dist` | Apache 2.0 | PDF rendering trong browser |

### Không dùng — lý do

| Loại bỏ | Lý do |
|---|---|
| sisap / docnet | Không có library tương đương trong Python stack |
| Marker-PDF | GPL-3.0 code — review pháp lý kỹ trước khi dùng trong sản phẩm KPMG |
| DocLayout-YOLO | AGPL-3.0 — không phù hợp thương mại; Docling đã có chức năng tương đương |
| Bất kỳ API ngoài | KPMG policy: air-gapped; Docling chạy 100% local |

---

## 5. Anchor System — IP của dự án

Anchor = địa chỉ ổn định của một element xuyên qua các phiên bản tài liệu. Không có OSS nào làm sẵn — đây là IP thực sự của Foundation.

### Schema theo format

```python
# DOCX — 3 trường kết hợp đảm bảo ổn định
{
  "format": "docx",
  "paragraph_index": 5,           # vị trí tuyệt đối
  "style_id": "Heading1",         # ổn định khi thêm/xóa paragraph khác
  "text_fingerprint": "a3f2b1c0", # sha256(text[:50])[:8]
  # optional — chỉ khi element nằm trong table:
  "table_index": 0,
  "row_index": 1,
  "col_index": 2
}

# XLSX — cell address đủ ổn định cho digital files
{
  "format": "xlsx",
  "sheet_name": "BCTC",
  "cell_address": "B5",           # A1 notation
  "named_range": "Revenue_2025"   # nếu có → ưu tiên hơn cell_address
}

# PDF — page + bbox + reading order
{
  "format": "pdf",
  "page": 1,
  "bbox": {"x": 0.1, "y": 0.2, "w": 0.8, "h": 0.05},  # relative [0,1]
  "reading_order_index": 3
}
```

### Resolve strategy (priority)

```
Strategy 1: style_id + text_fingerprint khớp → return  ← TỐT NHẤT, ổn định nhất
Strategy 2: paragraph_index + style_id khớp  → return  ← fallback
Strategy 3: paragraph_index only             → warn + return ← fallback cuối
FAIL:       Không resolve được               → raise ValueError ← KHÔNG ghi mù
```

### Milestone bắt buộc P3-04

> Insert paragraph vào đầu file → re-parse → resolve anchor cũ → **phải vẫn trả về đúng text**.
> Phải PASS trước khi tiếp tục sang Phase 4. Không negotiate.

---

## 6. Output Strategy — 3 chế độ

| Chế độ | Trigger | Cơ chế |
|---|---|---|
| **Clone & Replace** | Translation đơn file | Clone toàn bộ structure gốc → replace text tại anchors → save as new file. Format 100% giống input |
| **Profile-driven Template** | Multi-input, template có sẵn | Map content từ input(s) vào template Profile đã define. Thomson Reuters Ready to Review dùng cách này |
| **Negotiated Template** | Multi-input, không có template | Foundation propose template từ structure of inputs → user adjust trên Screen 2 → generate output |

### Lưu ý text reflow tiếng Việt

Tiếng Việt dài hơn tiếng Anh ~20-30%. Clone & Replace cho translation có thể gây text tràn box. Xử lý ở layer Translation application, không phải Foundation core.

---

## 7. Research Findings — Tóm tắt

### Parse / Perception (Layer 1-2)

- **Docling** (IBM, MIT, 63.9k★ GitHub 7/2026): engine chính, không có thay thế. TableFormer train 112k+ bảng FinTabNet. Local/air-gapped. Cần Python 3.10+.
- **python-docx + openpyxl**: write-back engines. Không có library nào làm cả đọc+ghi — phải ghép Docling (đọc/hiểu) + python-docx/openpyxl (ghi).
- **Anchor System**: không có OSS sẵn — hoàn toàn tự xây. Đây là effort lớn nhất và là IP.

### UI

- **Extend UI** (MIT, 6/2026): phát hiện quan trọng nhất. React component đầu tiên có PDF/DOCX/XLSX viewer + bounding box citations + HumanReviewBlock. Tiết kiệm 2-3 tuần build UI.
- **react-pdf-highlighter-extended** (MIT): backup nếu Extend UI không đủ cho PDF annotation.

### Market

- **18 vendors Gartner MQ IDP 2025**: tất cả cạnh tranh ở "extract → data → ERP".
- **DataSnipper** ($1.4B savings 2025): gần nhất về concept nhưng nhúng vào Excel, không có governed write-back độc lập.
- **Thomson Reuters Ready to Review**: prior-year return làm Profile → 80-90% auto-draft. Đây chính xác là Profile-driven concept của Foundation.
- **Khoảng trống**: "interaction + governed write-back độc lập" — CÓ THẬT và chưa bị lấp đầy.

### Format-Preserving Translation

- **BabelDOC** (ACL 2026): tách visual layout metadata khỏi semantic content, dịch, re-anchor về layout gốc. Đây là approach đúng.
- **XLIFF standard** (OASIS v2.2, 3/2025): intermediate representation tách text có thể dịch khỏi structure — ánh xạ trực tiếp vào Substrate + Middle Output của Foundation.

---

## 8. Tax Use Cases & Pipeline Position

### Foundation trong E2E Pipeline (8 bước)

```
Bước 1:   Document intake (client portal, email, ERP)
           ↓
Bước 2-3: [FOUNDATION — Layer 1+2] OCR + Layout Understanding + Classification
           ↓
Bước 4:   [FOUNDATION — Layer 3]   Data Extraction
           ↓
Bước 5:   Validation & reconciliation (Foundation cung cấp Trace)
           ↓
Bước 6:   Expert review (Tax professional / Auditor)
           ↓
Bước 7-8: Workflow, signoff, DMS/Repository
```

Foundation = **bước 2-4**. Đây là chỗ có đòn bẩy cao nhất — mọi application ở bước 4+ tái dùng Foundation mà không rebuild.

### Tax Use Cases theo độ ưu tiên

| Use case | Priority | Lý do |
|---|---|---|
| CIT Finalization workpaper prep | **MVP** | Upload BCTC → extract revenue/expenses/deferred tax → map vào CIT template → 80% hoàn thành. Pain point #1 của Tax Associates |
| BCTC Translation (EN→VI format-preserving) | **MVP** | Layout/trang giữ nguyên, glossary-locked, thuật ngữ nhất quán |
| Transfer Pricing YoY redlining | Next | TP failure = audit trigger #1 Vietnam 2026 |
| VAT reconciliation | Next | Monthly/quarterly batch processing |
| Pillar Two / GloBE / QDMTT | Post-MVP | Vietnam Decree 236 effective 15/10/2025 |

### Vietnam Regulatory Context 2026

- **CIT Law 67/2025/QH15 + Circular 20/2026/TT-BTC**: hậu kiểm thay tiền kiểm → tăng demand document evidence + audit trail
- **GDT audit plan 4/2026**: target doanh nghiệp lỗ 2023-2024; focus CIT finalization, VAT timing, TP
- **Transfer pricing**: audit trigger #1
- **Global Minimum Tax** (QDMTT, Decree 236): effective 15/10/2025

### Industry Evidence (cho slide / pitch)

- EY: 150 AI agents phục vụ 80,000 nhân viên tax (2026)
- KPMG Workbench (mid-2025): multi-agent, documentation + accountability log mỗi bước
- PwC: TP AI agents automate data collection + report preparation
- 93% large tax/accounting firms đang dùng/xem xét AI (2025 survey)

---

## 9. Document Perception — Phạm vi Build hiện tại

Document Perception = **Layer 1 + Detect/Parse/See/Locate của Layer 2**.

### 4 Capabilities theo thứ tự build

| # | Capability | Mô tả | Output |
|---|---|---|---|
| 1 | **Detect** | Nhận dạng file format, MIME type | `{format: "docx", mime: "..."}` |
| 2 | **Parse** | Docling → DoclingDocument JSON (Substrate thô) | JSON với đầy đủ element tree |
| 3 | **See** | Classify elements → typed FoundationDocument | `[{type: "heading", text: "...", bbox: {...}}, ...]` |
| 4 | **Locate** | Build Anchor ổn định cho mỗi element | `{para_idx:5, style_id:"Heading1", fingerprint:"abc123"}` |

**Output cuối:** `POST /perception/parse` → FoundationDocument JSON + Element Index XLSX download URL

### Cấu trúc Project

```
foundation/
├── perception/                  # 👁️ BUILD TRƯỚC
│   ├── models.py                # ⭐ Build đầu tiên — mọi thứ depend vào đây
│   ├── detector.py              # detect_format(path) → {format, mime, size}
│   ├── parser.py                # Singleton DocumentConverter → DoclingDocument JSON
│   ├── element_classifier.py    # classify_elements(doc, path) → FoundationDocument
│   ├── anchor_builder.py        # ⭐ IP — enrich_docx_anchors(), resolve_anchor()
│   └── index_writer.py          # write_element_index(doc, path) → XLSX Middle Output
│
├── adapters/                    # Layer 1
│   ├── base.py                  # Abstract: read() → Substrate, write() → path
│   ├── docx_adapter.py          # DOCX: Docling read + python-docx write
│   ├── xlsx_adapter.py          # XLSX: Docling read + openpyxl write
│   └── pdf_adapter.py           # PDF: read only — write() → NotImplementedError
│
├── api/
│   ├── main.py                  # FastAPI app, preload Docling model on startup
│   └── routes/perception.py     # POST /perception/parse, GET /perception/index/{id}
│
├── tests/
│   ├── fixtures/                # ⚠️ BLOCKED — cần KPMG cung cấp 3 files ẩn danh
│   └── test_perception.py       # Unit + integration, kể cả anchor stability test
│
└── requirements.txt

frontend/
└── src/components/
    ├── ElementIndexViewer.jsx   # ✅ ĐÃ BUILD — chỉ cần kết nối API thật
    └── DocumentViewer.tsx       # Phase 4B — Extend UI wrapper
```

### Fixtures cần (BLOCKED)

| File | Loại | Challenges phải test |
|---|---|---|
| `fixture_bcdt.docx` | Bảng cân đối tài sản VAS | Heading hierarchy, merged cells, tiếng Việt |
| `fixture_cit.xlsx` | Template quyết toán CIT | Named ranges, merged cells, formula, multiple sheets |
| `fixture_report.pdf` | Báo cáo kiểm toán (digital PDF) | Multi-column, footnotes, table extraction |

---

## 10. Data Schemas

### FoundationElement (Pydantic)

```python
class ElementType(str, Enum):
    HEADING = "heading"; PARAGRAPH = "paragraph"; TABLE = "table"
    TABLE_CELL = "table_cell"; LIST_ITEM = "list_item"; PICTURE = "picture"
    GLOSSARY = "glossary"; FOOTER = "footer"; HEADER = "header"; CAPTION = "caption"

class BoundingBox(BaseModel):
    page: int
    x: float; y: float; w: float; h: float  # relative [0, 1]

class DocxAnchor(BaseModel):
    format: Literal["docx"] = "docx"
    paragraph_index: int
    style_id: Optional[str]       # e.g. "Heading 1", "Normal"
    text_fingerprint: str          # sha256(text[:50])[:8]
    table_index: Optional[int]
    row_index: Optional[int]
    col_index: Optional[int]

class XlsxAnchor(BaseModel):
    format: Literal["xlsx"] = "xlsx"
    sheet_name: str
    cell_address: str              # A1 notation: "B5"
    named_range: Optional[str]    # ưu tiên hơn cell_address nếu có

class PdfAnchor(BaseModel):
    format: Literal["pdf"] = "pdf"
    page: int
    bbox: BoundingBox
    reading_order_index: int

Anchor = DocxAnchor | XlsxAnchor | PdfAnchor

class FoundationElement(BaseModel):
    element_id: str                # uuid4
    type: ElementType
    text: Optional[str]            # None cho picture
    level: Optional[int]           # 1=H1, 2=H2...
    section: Optional[str]         # section cha từ heading hierarchy
    anchor: Anchor                 # 📍 quan trọng nhất
    bbox: Optional[BoundingBox]
    confidence: float = 1.0        # < 0.85 → cần user confirm
    style: dict = {}
    children: list[str] = []
    metadata: dict = {}

class FoundationDocument(BaseModel):
    doc_id: str; source_path: str; format: str
    title: Optional[str]; page_count: int
    elements: list[FoundationElement]
    created_at: str; docling_version: str
```

### Element Index XLSX — 9 Columns

| Col | Tên | Nội dung | Ghi chú |
|---|---|---|---|
| A | # | Row number (1-based) | Thứ tự trong document |
| B | Section | Tên section cha | Từ heading hierarchy; "—" nếu không detect |
| C | Element type | heading / table / table_cell / ... | Application layer filter theo cột này |
| D | Element name | Text truncated 80 ký tự | Human-readable |
| E | Anchor ID | element_id[:8] | Full anchor ở column I |
| F | Page | Số trang (1-based) | Trong document gốc |
| G | Style | Style name từ python-docx | "Heading 1", "Normal", "Table Grid" |
| H | Confidence | 0.00 – 1.00 | < 0.85 → user review |
| **I** | **Anchor (JSON)** | **Full JSON của Anchor** | **📍 CỘT QUAN TRỌNG NHẤT — Foundation đọc cột này để roll back về file gốc** |

---

## 11. Build Plan — 6 Phases

| Phase | Label | Focus | Deliverable | Risk |
|---|---|---|---|---|
| Phase 0 | Pre-build | Env setup + fixture files | Python 3.10 + Docling OK; 3 fixtures sẵn | **BLOCKED** cho đến khi có fixtures |
| Phase 1 | Tuần 1 | Detect + Parse | `parse_document("file.docx")` → JSON | Thấp |
| Phase 2 | Tuần 2 | See (Classification) | `classify_elements()` → typed elements | Trung bình — edge cases |
| Phase 3 | Tuần 3 | Locate (Anchor) | `resolve_anchor()` đúng 100% | **CAO — IP quan trọng nhất** |
| Phase 4A | Tuần 4A | Element Index + API | `POST /perception/parse` end-to-end | Thấp |
| Phase 4B | Tuần 4B | Frontend Viewer | ElementIndexViewer + DocumentViewer | Thấp |

### Tasks quan trọng nhất

| Task ID | Mô tả | Effort | Status |
|---|---|---|---|
| P0-03 | 3 fixture files KPMG ẩn danh | 1d | **BLOCKED** |
| P1-01 | `models.py` — tất cả schemas | 1d | Build đầu tiên |
| P1-03 | `parser.py` — Docling singleton | 1d | |
| P2-01 | `element_classifier.py` | 1.5d | |
| P3-01 | `enrich_docx_anchors()` | 1.5d | |
| P3-02 | `resolve_anchor()` 3-strategy | 1.5d | |
| **⭐ P3-04** | **Anchor stability test** | **2d** | **MILESTONE bắt buộc** |
| P4A-01 | `index_writer.py` → XLSX | 1d | |
| P4A-02 | `POST /perception/parse` | 1d | |
| P4B-01 | Kết nối ElementIndexViewer + API | 1d | |
| P4B-02 | DocumentViewer (Extend UI) | 2d | |
| **⭐ P4B-04** | **Final 6/6 sign-off** | **1d** | **Không bỏ qua** |

### Lệnh cài đặt đầy đủ

```bash
# Python environment
python3.10 -m venv .venv && source .venv/bin/activate

# Backend — tất cả trong 1 lệnh
pip install docling python-docx openpyxl defusedxml \
  fastapi "uvicorn[standard]" pydantic python-multipart python-magic aiosqlite

# Verify
python -c "
from docling.document_converter import DocumentConverter; print('Docling OK')
from docx import Document; print('python-docx OK')
from openpyxl import Workbook; print('openpyxl OK')
"

# Run API
uvicorn api.main:app --reload --port 8000

# Test parse
curl -X POST http://localhost:8000/perception/parse \
  -F 'file=@tests/fixtures/fixture_bcdt.docx' | python -m json.tool

# Download Element Index
curl http://localhost:8000/perception/index/{doc_id} -o element_index.xlsx

# Frontend
cd frontend && npm install
npx shadcn@latest add @extend/docx-viewer @extend/pdf-viewer @extend/bounding-box-citations
npm run dev

# Chạy tests
python -m pytest tests/ -v --tb=short
python -m pytest tests/test_perception.py::test_anchor_stability -v
```

---

## 12. ElementIndexViewer — Đã build

**File:** `ElementIndexViewer.jsx` — React component hoàn chỉnh, production-ready, dùng ngay được.

### Features đã implement

- Excel-like layout: column letters A-H, row numbers bên trái, sticky header + sticky footer total row
- Filter theo Type (Heading, Table, Cell, Paragraph, Glossary, Picture...) — click toggle
- Search tự do theo element_name / section / type
- Checkbox select từng row hoặc select-all (respects current filter)
- **Export XLSX** thật — `SheetJS` download `element_index.xlsx`; nếu có rows đang select thì chỉ export những rows đó
- Confidence indicator: dot màu xanh ≥95% / vàng ≥85% / đỏ <85% + %
- Anchor detail panel: click copy-icon → panel tối góc phải, JSON đẹp + Copy button
- Toast notification sau copy/export
- Dark mode compatible (CSS variables)
- Alternate row colors, freeze panes behavior

### Việc còn lại (Phase 4B — P4B-01)

Thay `MOCK_DATA` array bằng data thật từ API:

```javascript
// Hiện tại (mock data):
const DATA = [
  { id: 1, section: "—", type: "heading", element_name: "BALANCE SHEET...", ... },
  ...
]

// Cần thay bằng (react-query):
const { data, isLoading } = useQuery({
  queryKey: ['elements', docId],
  queryFn: async () => {
    const res = await fetch(`/perception/parse`, {
      method: 'POST',
      body: formData
    })
    return res.json()
  }
})
const DATA = data?.elements || []
```

---

## 13. 6 Tiêu chí thành công MVP1

Upload `fixture_bcdt.docx` lên `POST /perception/parse` — tất cả 6 phải PASS:

| # | Tiêu chí | Pass condition | Fail → action |
|---|---|---|---|
| 1 | Performance | < 60s CPU / < 15s GPU (file 50 trang) | Profile bottleneck: Docling hay classifier? → optimize |
| 2 | Heading detection | ≥90% headings đúng type; không heading nào bị classify là paragraph | Kiểm tra DOCLING_TYPE_MAP |
| 3 | Table detection | Số bảng khớp; mỗi bảng đủ table_cell (row × col) | Debug Docling table extraction + TableFormer |
| 4 | Element Index XLSX | Mở Excel; đủ 9 columns A-I; Anchor JSON valid trong column I; freeze panes | Debug index_writer.py |
| 5 | Anchor resolve | resolve_anchor() trả đúng text; không exception; log strategy | Debug anchor_builder.py |
| 6 | Anchor stability | Anchor cũ vẫn đúng sau insert paragraph đầu file | Redesign resolution priority nếu fail |

```
✅ 6/6 PASS → Document Perception DONE → Chuyển sang Interaction UI
❌ Bất kỳ 1 fail → KHÔNG tiếp tục → Fix và re-test
```

---

## 14. Open Questions — Chưa chốt

| # | Câu hỏi | Tác động | Đề xuất mặc định | Owner | Status |
|---|---|---|---|---|---|
| Q1 | Python 3.10+ trong dev env? | Docling bắt buộc — không thể bắt đầu | Docker python:3.10-slim nếu cần | Team Lead | OPEN |
| Q2 | GPU hay CPU-only? | CPU ~60s/file; GPU ~15s | Start CPU; thêm GPU nếu chậm | Infra | OPEN |
| **Q3** | **3 fixture files — ai cung cấp + ẩn danh?** | **BLOCKER Phase 0** | BCTC (DOCX) + CIT (XLSX) + Audit (PDF); ẩn danh: replace tên client + số liệu | **KPMG Expert** | **BLOCKED** |
| Q4 | HuggingFace access trong dev env? | Docling download ~200MB lần đầu | Internet: OK. Air-gapped: pre-download, set `TRANSFORMERS_CACHE` | Infra/IT | OPEN |
| Q5 | API output: JSON only hay JSON + XLSX URL? | API design + frontend integration | JSON + URL download XLSX riêng | Tech Lead | OPEN |
| Q6 | Confidence threshold? | Element nào cần user confirm | `CONFIDENCE_THRESHOLD=0.85` env var | Product | OPEN |
| Q7 | React: Next.js hay Vite? | Routing, auth integration | Vite nếu SPA; Next.js nếu cần KPMG auth | Frontend | OPEN |
| Q8 | Docling model storage khi deploy? | Container restart → download ~200MB | Mount Docker volume `/root/.cache/huggingface` | DevOps | OPEN |

---

## 15. Deliverables Index

| File | Mô tả | Notes |
|---|---|---|
| `Document-Foundation-Project-Context.md` | Vision, pain points, 3 UX commitments, kiến trúc tham chiếu, MVP1 scope ban đầu | Baseline document |
| `Document-Foundation-Research.md` | Research lần 1: tech landscape, competitive analysis | |
| `Document_Foundation_Deep_Research_V2.xlsx` | Research V2: 7 sheets — Parse Tools, UI Studio, Competitive, Mapping 4 Layers, Industry Numbers, Sources | |
| `Foundation_Build_Proposal.md` | Build approach theo từng layer, timeline 10 tuần, risk table | |
| `Document_Perception_Build_Materials.md` | Tech stack chi tiết, project structure, full code examples cho tất cả modules | Tài liệu kỹ thuật |
| **`ElementIndexViewer.jsx`** | **React component: Excel-like Middle Output viewer, filter, search, select, export XLSX, Anchor detail panel** | **✅ Đã build — sẵn sàng dùng** |
| **`Document_Perception_Build_Plan.xlsx`** | **8 sheets: Overview, Tech Stack, Project Structure, Build Tasks (27 tasks + acceptance criteria), Data Schemas, Success Criteria, Setup Commands, Open Questions** | **📋 Tài liệu build chính — dùng để track progress** |
| **`Foundation_Master_Context.md`** | **File này** | **📖 Đọc file này trước khi làm bất cứ thứ gì** |

---

## 16. Thứ tự ưu tiên khi tiếp tục

### Làm ngay — trước khi viết bất kỳ dòng code nào

1. **Trả lời Q1 (Python version) và Q3 (fixture files)** — hai thứ này là blockers thật. Không có chúng thì Phase 0 không thể bắt đầu.

2. **P1-01: models.py là file đầu tiên** — thiết kế xong Pydantic schemas trước, code sau. Mọi module khác depend vào đây.

### Build order bắt buộc

```
models.py → detector.py → parser.py → element_classifier.py
    → anchor_builder.py → [P3-04 PASS] → index_writer.py
    → FastAPI routes → ElementIndexViewer connect API → DocumentViewer
```

### Các quy tắc không được phá vỡ

- **P3-04 Anchor Stability Test PHẢI PASS** trước khi chuyển sang Phase 4. Nếu fail — fix, không tiếp tục.
- **6/6 criteria PHẢI PASS** trước khi nói "Document Perception done". Không đủ 6/6 thì chưa xong.
- **Layer 4 Applications chỉ sau khi 6/6 sign-off** — không đặt deadline cho Translation/CIT workpaper app khi Perception chưa xong.
- **ElementIndexViewer.jsx không cần viết lại** — đã đủ features, chỉ kết nối API thật.
- **Không dùng API ngoài** — mọi thứ local, air-gapped. Không thêm dependency ngoài danh sách đã chốt.
