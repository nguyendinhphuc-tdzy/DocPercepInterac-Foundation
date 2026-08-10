# Document Perception — Build Status

Trạng thái thực tế của `foundation/` tính đến thời điểm này. Đối chiếu với
`../Foundation_Build_Plan.md` (bản khớp slide đã duyệt, mục 9 & 16) và
`Foundation_Master_Context.md` (bản gốc, tham khảo lịch sử). Cập nhật file
này mỗi khi có module mới hoàn thành — đừng để nó trôi khỏi thực tế code.

---

## ⚠️ PIVOT KIẾN TRÚC ĐANG TREO (2026-08-07) — đọc trước khi làm gì tiếp

`../Foundation_Build_Plan_v3.md` thay thế toàn bộ cách parse PDF: bỏ Docling,
dùng **Geometry Layer** (`pdfplumber`+`pdf2image`, tất định, không AI) +
**Classification Layer** (`openai` client gọi Workbench nội bộ, có AI, tắt
được bằng feature flag). Access layer đổi FastAPI → Flask. Chi tiết đầy đủ,
xem file đó.

**Trạng thái duyệt (CRADL):** `pdfplumber`/`pdf2image` đang **⏳ waiting for
approval** — CHƯA chính thức được duyệt. Đã cài vào venv để code song song
theo yêu cầu tường minh, **không phải vì đã có xác nhận duyệt**. Không dùng
làm căn cứ để deploy/ship.

**Đã cài thêm (2026-08-07), xác nhận thật bằng `pip list`:**
`pdfplumber 0.11.10`, `pdf2image 1.17.0`, `openai 2.53.0`, `azure-identity
1.25.3`, `msal 1.37.0`, `azure-core 1.41.0`, `jsonschema 4.26.0`, `tenacity
9.1.4`, `cachetools 7.1.7`, `numpy 2.4.6`, `pandas 3.0.5`, `flask 3.1.3`,
`werkzeug 3.1.8`. Docling vẫn giữ nguyên trong venv/requirements.txt làm
track song song, **chưa gỡ**.

**2 phát hiện thật khi test — quan trọng, không có trong build plan v3:**

| # | Phát hiện | Chi tiết |
|---|---|---|
| 1 | **`fixture_report.pdf` là PDF scan ảnh, không phải digital** | `pdfplumber` trích được 0 chars/0 words trên mọi trang kiểm tra; trang có 8 image, một cái kích thước gần khớp cả trang (595×841pt = A4), 0 vector lines/rects. Điều này **mâu thuẫn với comment cũ trong `parser.py`** ("fixture PDFs are born-digital, not scanned images"). OCR nằm ngoài scope build hiện tại (cả bản cũ lẫn v3) → fixture này **không dùng được** cho Geometry Layer mới cho tới khi có quyết định về OCR. `fixture_report_2.pdf` mới là fixture PDF digital thật (test thấy 305-369 words/trang). |
| 2 | **Poppler chưa cài trên máy dev** | `pdf2image.convert_from_path()` fail thật: `PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?`. `pdfplumber` (dùng để trích text/bbox) hoạt động bình thường không cần Poppler — chỉ `pdf2image` (render ảnh trang cho Screen 1) bị chặn. Đúng như build plan v3 mục 2 đã cảnh báo: Poppler là OS-level binary, chưa rõ có cần duyệt riêng với IT không. |

**Việc cần làm ngay theo build plan v3 mục 17 (chưa làm, không tự ý làm khi chưa hỏi):**
1. Gửi câu hỏi "thuần code vs model" + câu hỏi Poppler cho senior/IT — **bạn cần tự gửi**, không phải việc code.
2. Refactor `perception/parser.py` tách interface Geometry Layer khỏi Docling — việc kỹ thuật có thể làm ngay, không cần chờ duyệt, chưa bắt đầu.

---

## Đã làm được

### Môi trường & hạ tầng
- Git repo khởi tạo, đẩy lên GitHub (`nguyendinhphuc-tdzy/DocPercepInterac-Foundation`).
- `.gitignore` chuẩn cho Python/Node, loại trừ `.venv`, `__pycache__`, secrets.
- Venv Python 3.11 tại `foundation/.venv`, cài đủ `requirements.txt` (docling,
  python-docx, openpyxl, fastapi, pydantic v2, aiosqlite...).
- Model Docling (~1.4GB: layout, tableformer, code-formula, OCR) đã tải sẵn,
  đóng gói và publish qua **GitHub Release `models-v1`** (không commit binary
  vào git — vượt giới hạn 100MB/file). Xem `foundation/models/README.md`.
- `perception/parser.py` tự động detect `foundation/models/` và trỏ Docling
  vào đó — **chạy hoàn toàn offline sau khi giải nén model**, không gọi
  HuggingFace Hub lúc runtime.

### Code — Layer 2: Detect + Parse (P1)
| Module | Trạng thái | Ghi chú |
|---|---|---|
| `perception/models.py` | ✅ Done | Pydantic schemas theo `Foundation_Build_Plan.md` mục 3 (đã đối chiếu lại 2026-08-07, thay bản cũ khớp Master Context mục 10): `ElementType`, `AnchorDOCX`/`AnchorXLSX`/`AnchorPDF`, `Element`, `ElementIndex`, `Profile`/`ProfileField` |
| `perception/detector.py` | ✅ Done | `detect_format()` — kiểm tra extension + MIME (libmagic), raise nếu mismatch/corrupt |
| `perception/parser.py` | ✅ Done | `get_converter()` singleton (`lru_cache`) + `parse_document()`; OCR tắt (fixture là PDF digital, không phải scan); đã wire local model artifacts |

### Tests — đã chạy thật, kết quả 12 passed / 1 failed
```
python -m pytest tests/ -v --tb=short
============ 1 failed, 12 passed in 174.96s (0:02:54) ============
```
| File | Trạng thái |
|---|---|
| `tests/test_models.py` | ✅ Pass |
| `tests/test_detector.py` | ✅ Pass |
| `tests/test_parser.py` | ⚠️ 3/4 pass — `test_parse_pdf_does_not_crash` FAIL |

**Lỗi cụ thể:** `torch._inductor.exc.InductorError: InvalidCxxCompiler: Compiler: cl is not found.`
Khi parse `fixture_report.pdf`, một model con trong pipeline Docling cố JIT-compile
bằng `torch.compile`, cần trình biên dịch C++ (`cl.exe` từ MSVC Build Tools),
nhưng máy dev này chưa cài. **Đây là vấn đề môi trường (thiếu Visual C++ Build
Tools trên Windows), không phải bug logic của `parse_document()`** — parse
DOCX chạy bình thường, dưới 60s CPU budget. Cần cài
[Visual Studio Build Tools (C++ workload)](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
hoặc tìm cách tắt `torch.compile` trong pipeline để fix trước khi tiếp tục
làm việc với PDF.

### Fixtures (mục Q3 — từng liệt kê BLOCKED trong Master Context)
Đã có sẵn trong `tests/fixtures/`:
- `fixture_bcdt.docx`
- `fixture_report.pdf`
- `fixture_report_2.pdf`

**Còn thiếu:** fixture XLSX (template CIT — `fixture_cit.xlsx` theo kế hoạch
gốc) để test named ranges/merged cells/formula. Chưa có test nào cho nhánh
XLSX.

---

## Vấn đề cần fix trước (không thuộc build order, nhưng chặn PDF path)

| # | Vấn đề | Impact | Đề xuất |
|---|---|---|---|
| 1 | `test_parse_pdf_does_not_crash` FAIL — thiếu MSVC C++ compiler (`cl.exe`) cho `torch.compile` | Không parse được PDF trên máy dev này | Cài Visual Studio Build Tools (C++ workload), hoặc set config tắt `torch.compile`/inductor trong pipeline options nếu Docling hỗ trợ |

## Chuẩn bị làm (theo đúng build order trong `Foundation_Build_Plan.md` mục 16)

Build order bắt buộc: `models.py → detector.py → parser.py →
element_classifier.py → anchor_builder.py → [P3-04 PASS] → index_writer.py
→ FastAPI routes → ElementIndexViewer connect API → DocumentViewer`

Đã xong 3 module đầu. Tiếp theo:

| # | Module | Capability | Mô tả | Risk |
|---|---|---|---|---|
| 1 | `perception/element_classifier.py` | **See** | `classify_elements(doc, path)` — DoclingDocument JSON thô → `FoundationDocument` (typed elements: heading/paragraph/table/...) | Trung bình — edge case classify |
| 2 | `perception/anchor_builder.py` | **Locate** | `enrich_docx_anchors()`, `resolve_anchor()` 3-strategy fallback — **đây là IP quan trọng nhất của cả project**, chưa có OSS nào làm sẵn | **Cao** |
| 3 | **P3-04 — Anchor stability test** | — | Insert paragraph đầu file → re-parse → resolve anchor cũ → phải vẫn trả đúng text. **Milestone bắt buộc, không negotiate**, phải PASS trước khi làm tiếp | Milestone chặn |
| 4 | `perception/index_writer.py` | Middle Output | `write_element_index(doc, path)` → XLSX 9 cột (Section/Type/Element name/Anchor JSON...) | Thấp |
| 5 | `adapters/base.py` + `docx_adapter.py`/`xlsx_adapter.py`/`pdf_adapter.py` | Layer 1 | Abstract `read()`/`write()`; PDF chỉ read (write → `NotImplementedError`) | Thấp |
| 6 | `api/main.py` + `api/routes/perception.py` | Access Layer | `POST /perception/parse`, `GET /perception/index/{doc_id}`; preload Docling model lúc startup | Thấp |
| 7 | Kết nối `ElementIndexViewer.jsx` (đã build sẵn, production-ready) với API thật | Frontend | Thay `MOCK_DATA` bằng `react-query` fetch thật | Thấp |
| 8 | `DocumentViewer.tsx` (Extend UI wrapper) | Frontend | PDF/DOCX/XLSX viewer + bounding box citations | Phase 4B |
| 9 | Fixture XLSX còn thiếu | Blocker phụ | Cần 1 file `.xlsx` mẫu (CIT template hoặc tương đương) để test nhánh XLSX | Cần cung cấp |
| 10 | **6/6 Success Criteria sign-off** | — | Performance <60s CPU, heading detection ≥90%, table detection khớp, Element Index XLSX đủ 9 cột, anchor resolve đúng, anchor stability pass | Gate cuối trước khi coi Document Perception "done" |

### Quy tắc không được phá vỡ (nhắc lại từ Master Context)
- P3-04 phải PASS trước khi sang Phase 4.
- Không dùng API ngoài — mọi thứ chạy local/air-gapped (đã đảm bảo với model Docling local).
- Không viết lại `ElementIndexViewer.jsx` — chỉ kết nối API.
