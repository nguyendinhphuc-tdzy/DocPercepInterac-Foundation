# Build Plan — Document Perception & Interaction Foundation
## Khớp trực tiếp với Foundation_Team_Presentation_FULL.pptx (31 slide)

*Chuẩn bị bởi Nguyễn Đình Phúc · KPMG Vietnam Innovation · Tháng 8/2026*
*Cập nhật trạng thái lần gần nhất: Đối chiếu với `foundation/STATUS.md` của repo `DocPercepInterac-Foundation`, sau khi Detect+Parse (P1) hoàn thành.*

---

## 0. Cách đọc tài liệu này

Mọi mục trong build plan này trỏ ngược về đúng slide đã present cho team. Không có mục nào phát sinh khái niệm mới ngoài deck — nếu team đã duyệt slide nào ở buổi present, phần build tương ứng coi như đã được approve về mặt định hướng.

**Chú giải trạng thái dùng xuyên suốt tài liệu:** ✅ Xong · 🟡 Đang làm · ⬜ Chưa bắt đầu · 🔴 Blocked · ⚠️ Rủi ro mới phát sinh (chưa có trong deck gốc)

### 0.1 Bức tranh tổng thể hiện tại (một câu mỗi ý)

- **Đã xong:** môi trường + hạ tầng, air-gapped xác nhận bằng code thật, schema Element/Anchor/Profile (đã đối chiếu lại theo đúng mục 3 bên dưới), `detector.py`, `parser.py`.
- **Đang đứng trước cổng cứng:** `element_classifier.py` và `anchor_builder.py` — module IP quan trọng nhất — **chưa bắt đầu**. Bài test P3-04 (mục 9.1) do đó **chưa được chạy lần nào**.
- **Blocked thật:** 1 test PDF fail vì thiếu C++ compiler trên máy dev (môi trường, không phải logic); fixture XLSX chưa có, chặn toàn bộ nhánh XLSX của cả anchor lẫn use case CIT.
- **Kết luận ngắn:** tiến độ đúng thứ tự build order đã định, nhưng **chưa qua được điểm rủi ro cao nhất**. Chưa nên báo cáo "gần xong Layer 2" với team.

| Build plan section | Khớp slide # | Nội dung |
|---|---|---|
| 2. Tech stack theo layer | Slide 7 | Docling, Element Index+Anchor, Profile/Align |
| 3. Data model | Slide 9, 10 | Element Index schema, Anchor schema |
| 4. Runtime flow | Slide 8 | Core flow + AI branch có cổng |
| 5. Output engine | Slide 11, 12, 13 | 3 mode, Patch/Build, cover&note |
| 6. Module Align | Slide 12 | Compare = dataset |
| 7. API | — (suy ra từ slide 7-13) | Access layer |
| 8. UI scope | Slide 14 | 4 màn hình, MVP1 chỉ build 2 |
| 9. Test plan | Slide 10, 28 | Anchor acceptance test, MUST PROVE |
| 10. MVP1 scope chốt | Slide 6, 28 | Layer 1 + nửa Layer 2 |
| 11. Assumptions | Slide 26 | Kỹ thuật + nghiệp vụ |
| 12. Risk & mitigation | Slide 20 | Kỹ thuật / Policy / Adoption |
| 13. Roadmap & estimate | Slide 27 | 1 tuần + 3-5 ngày, rồi scale |
| 14. Vận hành nhận dự án | Slide 25 | Client Intake / Scale Pipeline |
| 15. Demo acceptance | Slide 24 | Technical demo + Application demo |

---

## 1. Tổng quan phạm vi

**Scope build lần này = đúng slide 6 và slide 28.** Không hơn.

- Layer 1 (Format Adapters): DOCX, XLSX, PDF (digital, không scan)
- Layer 2 (Perception & Interaction Core): toàn bộ — Detect, Parse, See, Locate, Read, Write, Transform + Substrate/Profiles/Runtime/Execution
- Layer 3 (Understanding & Placement): **chỉ Select + Map/Place cơ bản** theo Profile đã có sẵn. Interpret tự động (auto-label) và Align **không nằm trong build lần này**.
- Layer 4 (Applications & AI): **không build.** Hai use case Tax (CIT workpaper, dịch báo cáo) là fixture kiểm thử Layer 1-3, không phải ứng dụng hoàn chỉnh.

**Không build trong đợt này** (đúng cột "CHƯA LÀM" slide 28):
- OCR cho scanned PDF
- Negotiated template tự động (mode 3 sinh template không cần con người)
- Comparison/reconciliation deliverable đầy đủ + capability Align
- Production API gateway, SDK, MCP server
- Bất kỳ tích hợp nào ngoài Tax

---

## 2. Tech stack theo từng layer (khớp slide 7)

| Layer | Công nghệ | Vì sao |
|---|---|---|
| L1 — Format Adapters | **Docling** (IBM, MIT license) cho parse chung; `python-docx` cho ghi DOCX; `openpyxl` + `defusedxml` cho đọc/ghi XLSX an toàn (chống XML bomb) | Đã có benchmark công khai (~88% F1), MIT license, self-host được, air-gapped |
| L2 — Perception Core | Tự viết: Element Index builder, Anchor resolver, Substrate/Profile/Runtime/Execution store | Đây là IP — không có sẵn trên thị trường (đã xác nhận ở phần Market Benchmark) |
| L2 — Storage | `aiosqlite` cho MVP1 (Profile store, Execution log). Không dùng graph DB/registry service ở giai đoạn này | Đủ cho scope hẹp; graph DB nằm trong "chưa làm" |
| L2/L3 — API | `FastAPI` + `pydantic v2` cho schema validation nghiêm ngặt của Element/Anchor | Validate schema là bắt buộc — Anchor sai định dạng phải bị chặn ở tầng API, không chặn ở tầng logic |
| L2 — File upload | `python-multipart`, `python-magic` (nhận diện MIME thật, không tin đuôi file) | Chống giả mạo định dạng file |
| Frontend (Screen 1-2 MVP1) | React + TypeScript, `zustand` (state), `react-query` (data fetching), `pdfjs-dist` (preview PDF), `xlsx`/SheetJS (hiển thị Element Index dạng Excel) | Khớp yêu cầu "Element Index reviewable như Excel" ở slide 9 |
| **Cấm dùng** | Marker-PDF (GPL), DocLayout-YOLO (AGPL), bất kỳ SDK gọi API ngoài | Vi phạm license hoặc vi phạm air-gapped (rủi ro Policy đã nêu ở slide 20) |

---

## 3. Data model — khớp slide 9 (Element Index) và slide 10 (Anchor)

> **Đã đối chiếu với code thật (2026-08-07):** schema dưới đây đã được implement nguyên vẹn trong `foundation/perception/models.py`, thay thế bản `FoundationElement`/`FoundationDocument` cũ (đặt trước khi có build plan này). `AnchorDOCX` giữ thêm 3 field optional (`table_index`, `row_index`, `col_index`) so với pseudocode gốc — cần thiết để một `Element` type `cell` trỏ đúng vào ô trong bảng DOCX, không phá vỡ phần còn lại của schema.

### 3.1 Element (một dòng trong Element Index)

```python
class Element(BaseModel):
    index: int                     # # — thứ tự trong tài liệu
    section: str | None            # Section — vd "Assets", "Notes"
    type: Literal["heading", "table", "cell", "para", "picture", "glossary"]
    name: str                      # Tên element — vd "Table 2", "Note 1: basis"
    anchor: Anchor                 # xem 3.2
    confidence: float | None       # None nếu auto-label không chạy (MVP1 mặc định None)
```

### 3.2 Anchor — theo đúng 3 định dạng ở slide 10, KHÔNG BAO GIỜ dùng số trang

```python
class AnchorDOCX(BaseModel):
    format: Literal["docx"] = "docx"
    paragraph_index: int
    style_id: str
    text_fingerprint: str          # sha256[:8] của nội dung text

class AnchorXLSX(BaseModel):
    format: Literal["xlsx"] = "xlsx"
    sheet_name: str
    cell_address: str              # vd "B14"
    named_range: str | None = None

class AnchorPDF(BaseModel):
    format: Literal["pdf"] = "pdf"
    page: int
    bbox_relative: tuple[float, float, float, float]  # tỷ lệ 0-1, KHÔNG phải pixel tuyệt đối
    reading_order_index: int

Anchor = AnchorDOCX | AnchorXLSX | AnchorPDF
```

### 3.3 Resolution ladder — implement đúng thứ tự, dừng ở bước đầu tiên match được

```
1. style_id + text_fingerprint match  → resolve, confidence=high
2. paragraph_index + style_id match   → resolve, confidence=medium (fallback)
3. paragraph_index only match         → resolve, confidence=low, LOG WARNING
4. không bước nào match               → raise AnchorResolutionError
                                         (không bao giờ ghi mù — đúng nguyên tắc slide 10)
```

### 3.4 Profile (versioned, sinh ra từ Element Index đã được review)

```python
class ProfileField(BaseModel):
    field_name: str
    match_rule: Literal["label", "structural", "fingerprint"]
    anchor_pattern: dict           # mẫu để nhận diện field này ở tài liệu cùng loại

class Profile(BaseModel):
    profile_id: str
    version: int                   # v+1 mỗi lần reviewer clarify field mới (slide 13)
    document_type: str
    fields: list[ProfileField]
    coverage_pct: float | None     # tính từ Scale Pipeline, xem mục 14
```

---

## 4. Runtime flow — khớp slide 8 nguyên văn

Implement đúng state machine 6 bước core + 4 bước nhánh AI, có cổng rẽ nhánh rõ ràng — đây là bằng chứng kỹ thuật cho claim "AI tắt được" ở slide 20/demo technical.

```
CORE FLOW (bắt buộc, không phụ thuộc AI):
  file_intake → perception → select_and_label → [GATE: cần AI?]
       │no                                            │yes
       ↓                                               ↓
  versioned_profile → map_and_act → output_and_trace   AI BRANCH:
                          ↑                             glossary_lock → build_context
                          └──────────────merge─────────← kpmg_internal_ai
                                                          → validate_and_write_back
```

**Yêu cầu implement bắt buộc:**
- Cổng `[GATE: cần AI?]` phải là một **feature flag độc lập**, không phải logic if/else lẫn trong core flow. Lý do: demo technical (slide 24) yêu cầu **tắt hẳn AI branch bằng flag và chạy lại toàn bộ** — nếu AI logic lẫn vào core, không tách ra tắt được.
- `Control plane` (profiles · policy · validation · review · execution history) là một module riêng, mọi bước trong cả hai luồng đều ghi log vào đây — không được ghi log rải rác từng module.
- Execution log record tối thiểu: `{timestamp, actor: "system"|"ai_agent"|"human", step, input_ref, output_ref, old_value, new_value}` — để phân biệt được "AI đề xuất" vs "người xác nhận" (yêu cầu demo technical bước 5).

---

## 5. Output engine — khớp slide 11, 12, 13

### 5.1 Ba mode xác định shape trước khi ghi

```python
class OutputMode(str, Enum):
    CLONE_REPLACE = "clone_replace"      # mode 1 — anchor = write target
    PROFILE_FILL = "profile_fill"        # mode 2 — 2 tập anchor (nguồn + đích)
    TASK_SHAPED = "task_shaped"          # mode 3 — anchor = provenance only
```

**Ràng buộc bắt buộc:** trước khi gọi writer, hệ thống phải xác định `OutputMode` tường minh và log lại. Cấm silent-fallback giữa các mode.

### 5.2 Writer — 2 entry point, dùng chung 1 engine (khớp slide 11 bảng dưới)

```python
class Writer(Protocol):
    def patch(self, file: Path, writes: list[AnchorWrite]) -> Path: ...
    def build(self, render_spec: RenderSpec, result_set: ResultSet) -> Path: ...
```

- `patch()` dùng cho mode 1 và mode 2 — mở file có sẵn, ghi tại từng anchor, lưu.
- `build()` dùng cho mode 3 — **KHÔNG có trong MVP1** (thuộc "chưa làm" ở slide 28), nhưng interface phải được định nghĩa ngay từ đầu để không phải sửa lại schema Element Index sau này khi mở rộng.

### 5.3 Guaranteed floor — implement rung 2 là bắt buộc, không phải nice-to-have

```
rung 1: firm-standard deliverable đã tồn tại — parse làm render spec
rung 2: KHÔNG có gì để dựa vào — emit raw result set (LUÔN LUÔN THÀNH CÔNG — đây là floor)
rung 3: reviewer format 1 lần trong Excel — parse lại thành render spec v1.0
```

Test bắt buộc: gọi `build()` với `render_spec=None` phải luôn trả về một file hợp lệ (rung 2), không bao giờ raise exception hay trả về rỗng.

### 5.4 Profile-driven Fill: cơ chế Cover & Note (khớp slide 13 — đã được duyệt riêng)

Đây là phần **quan trọng nhất cần implement đúng 100% theo thiết kế đã duyệt**, vì nó là claim "guaranteed floor áp dụng cho cả mode 2, không riêng mode 3".

```python
def profile_driven_fill(doc_elements: list[Element], profile: Profile) -> OutputWorkbook:
    covered, noted = [], []
    for el in doc_elements:
        match = match_against_profile(el, profile)   # ladder: label → structural → fingerprint
        if match:
            covered.append((el, match.target_cell))
        else:
            noted.append(el)     # KHÔNG BAO GIỜ drop — luôn xuất hiện ở vùng NOTED

    wb = OutputWorkbook()
    wb.write_zone("COVERED", covered)   # map thẳng vào ô đã định nghĩa trong Profile
    wb.write_zone("NOTED", noted)       # cùng 1 sheet, khối riêng bên dưới, giữ nguyên anchor
    return wb
```

**Ràng buộc bắt buộc:**
- COVERED và NOTED **luôn nằm trong cùng 1 sheet** (đã xác nhận, không phải sheet phụ).
- Mọi dòng ở cả 2 vùng đều giữ cột Anchor gốc — kể cả dòng NOTED.
- Khi reviewer clarify một field NOTED (gán nó vào Profile), hệ thống sinh `Profile version+1`. Tài liệu cùng loại lần sau, field đó tự động rơi vào vùng COVERED — đây là test chấp nhận bắt buộc (xem mục 9).

---

## 6. Capability Align — khớp slide 12

**Không build trong MVP1** (thuộc "chưa làm" — slide 28), nhưng **schema Element Index phải thiết kế để không loại trừ nó** — đây là yêu cầu tường minh, không phải tùy chọn.

Khi build (giai đoạn sau MVP1), Align implement đúng ladder đã trình bày:

```
1. label match         — cả 2 tài liệu có Profile → match theo label
2. structural match     — cùng section path, cùng vị trí bảng
3. fingerprint similarity — đủ gần để ghép, gắn cờ "suy ra" (không tự tin tuyệt đối)
4. unmatched            — đẩy lên reviewer, KHÔNG BAO GIỜ âm thầm bỏ qua
```

Yêu cầu tương thích ngược ngay từ MVP1: `Element.anchor` phải serialize được độc lập với `Element.index` trong cùng tài liệu, để khi Align xuất hiện, nó join được 2 Element Index của 2 file khác nhau mà không cần đổi schema.

---

## 7. API (Access layer tối thiểu cho MVP1)

Không build production API gateway (thuộc "chưa làm"), nhưng MVP1 cần các endpoint nội bộ tối thiểu để Screen 1 và Screen 2 gọi được:

| Endpoint | Method | Mô tả |
|---|---|---|
| `/documents/upload` | POST | Nhận file, nhận diện MIME thật bằng `python-magic`, trả `document_id` |
| `/documents/{id}/perceive` | POST | Chạy Layer 1-2, trả về Element Index đầy đủ |
| `/documents/{id}/elements/{index}` | PATCH | Reviewer sửa label/type của 1 element — cập nhật Profile |
| `/documents/{id}/anchors/{anchor}/resolve` | GET | Chạy resolution ladder, trả `{resolved: bool, confidence, element}` |
| `/documents/{id}/write` | POST | Gọi `patch()` — chỉ mode 1 và 2 trong MVP1 |
| `/executions/{document_id}` | GET | Trả execution log đầy đủ cho tài liệu đó |

Không cần auth phức tạp ở MVP1 (single-tenant nội bộ), nhưng **mọi call ghi (`PATCH`, `POST /write`) bắt buộc phải ghi vào execution log** — không có ngoại lệ, kể cả khi test nội bộ.

---

## 8. UI scope — khớp slide 14, chỉ build 2/4 màn hình

| Màn hình | Build trong MVP1? | Lý do |
|---|---|---|
| 1. Input & Perception | **Có** | Cần để review element đã phát hiện đúng chưa |
| 2. Element Index | **Có** | Cần để reviewer sửa nhãn, kích hoạt vòng lặp Profile học |
| 3. Agent Chat | **Không** | Thuộc Layer 4, đi cùng ứng dụng đầu tiên, không thuộc MVP1 |
| 4. Final Output | **Không** (chỉ cần xem output qua Excel/Word thật, không cần preview riêng trong app) | MVP1 test bằng cách mở trực tiếp file output — không cần build UI riêng |

Component tối thiểu cho Screen 1-2:
- File viewer (PDF via `pdfjs-dist`; DOCX/XLSX render đơn giản, không cần WYSIWYG đầy đủ)
- Bounding box overlay lên từng element đã detect (Screen 1)
- Bảng Element Index dạng spreadsheet, inline edit được cột `type`/`name` (Screen 2), dùng `xlsx`/SheetJS để export/import khớp định dạng Excel thật

---

## 9. Test plan — khớp slide 10 (acceptance test) và slide 28 (MUST PROVE)

**Trạng thái mục này (thật, từ `foundation/STATUS.md`):** 12/13 unit test pass ở tầng Detect+Parse, cộng 6/6 test schema mới (`test_models.py`) pass sau khi đối chiếu lại theo mục 3. Bài test P3-04 ở mục 9.1 bên dưới **chưa chạy** — nó phụ thuộc `anchor_builder.py`, module còn ⬜ chưa bắt đầu. Không coi bất kỳ kết quả pass nào ở trên là bằng chứng cho P3-04.

### 9.1 Bài test bắt buộc phải pass trước khi build bất cứ gì lên trên (cổng cứng) — 🔴 CHƯA CHẠY

```
Bước 1: Parse một tài liệu thật (fixture), lưu anchor của 1 bảng cụ thể.
Bước 2: Chèn 1 đoạn văn mới vào ĐẦU file (trước mọi nội dung hiện có).
Bước 3: Parse lại file đã đổi.
Bước 4: Resolve anchor cũ đã lưu ở bước 1.
Kết quả bắt buộc: phải trả về ĐÚNG bảng đó, không phải bảng khác, không lỗi.
```

Test này chạy tự động trên **cả 3 định dạng** (DOCX, XLSX, PDF) — không coi là pass nếu chỉ 1 định dạng qua được.

### 9.2 Checklist MUST PROVE — trạng thái thật (nâng cấp lên đúng 6 Success Criteria trong repo, cụ thể hơn bản gốc slide 28)

- [x] ✅ Fixture DOCX + PDF đã có đã ẩn danh (`fixture_bcdt.docx`, `fixture_report.pdf`, `fixture_report_2.pdf`) — [ ] 🔴 **fixture XLSX (`fixture_cit.xlsx`) chưa có — blocker phụ, cần được cung cấp trước khi test nhánh XLSX**
- [ ] ⬜ Element Index + anchor cho từng element, heading detection ≥90%, table detection khớp — chờ `element_classifier.py` (chưa bắt đầu)
- [ ] 🔴 Anchor sống sót qua bài test chèn đầu file (P3-04) — chờ `anchor_builder.py` (chưa bắt đầu, risk đánh giá **Cao**)
- [ ] ⬜ Đọc–ghi an toàn tối thiểu cho mọi format — PDF chỉ định read-only theo thiết kế adapter (`write()` → `NotImplementedError`), DOCX/XLSX chờ `index_writer.py` + adapters
- [ ] ⬜ 2 use case Tax: CIT workpaper + dịch báo cáo — chưa bắt đầu, phụ thuộc toàn bộ chuỗi phía trên
- [ ] ⬜ Execution log traceability đầy đủ — chưa bắt đầu (thuộc control plane, sau adapters)
- [x] ✅ Performance < 60s CPU cho parse DOCX — đã xác nhận trong `STATUS.md`. PDF chưa đo được vì test đang fail vì môi trường (mục 12 cập nhật)

### 9.3 Test riêng cho cơ chế Cover & Note (mục 5.4)

```
1. Xử lý fixture A với Profile chỉ có 3/5 field thật của tài liệu.
2. Xác nhận: 3 field đúng nằm ở COVERED, 2 field còn lại nằm ở NOTED — cùng sheet.
3. Reviewer clarify 1 field NOTED — Profile version tăng lên.
4. Xử lý fixture B (cùng loại tài liệu, có field vừa clarify) với Profile mới.
5. Xác nhận: field đó giờ nằm ở COVERED tự động, không cần clarify lại.
```

---

## 10. MVP1 scope chốt — không thương lượng thêm nếu chưa xong

Theo đúng slide 6 + 28: **thành công của MVP1 là câu hỏi "lõi và interaction contract có vững, bền, mở rộng được không" — không phải "tiết kiệm bao nhiêu giờ trên 1 báo cáo".**

Không bắt đầu bất kỳ hạng mục nào ở cột "CHƯA LÀM" (mục 1) cho tới khi toàn bộ checklist mục 9.2 pass.

---

## 11. Assumptions — khớp slide 26, mỗi assumption cần một điểm kiểm tra sớm

| Assumption | Loại | Kiểm tra ở đâu trong build |
|---|---|---|
| Tài liệu digital-native đạt kết quả tương đương benchmark công khai Docling | Kỹ thuật | Chạy Docling trên fixture Tax thật ngay tuần 1, so với 88% F1 công bố — nếu lệch nhiều, phải biết sớm |
| Anchor mechanism tổng quát hóa ra ngoài bài test chèn-đầu-file | Kỹ thuật | Mở rộng test mục 9.1 với thêm 2 kiểu edit khác: xóa đoạn giữa, đổi thứ tự bảng |
| KPMG internal AI sẵn sàng tích hợp khi cần | Kỹ thuật | Xác nhận endpoint/API internal AI tồn tại trước khi implement AI branch (mục 4) — nếu chưa có, AI branch chỉ dừng ở interface, không implement thật |
| Hạ tầng cho phép deploy air-gapped thật sự | Kỹ thuật | Audit network call — kiểm tra bằng cách chạy toàn bộ pipeline trong môi trường **tắt internet hoàn toàn**, phải không lỗi |
| Client (Tax) cam kết cung cấp ≥100 mẫu + template | Nghiệp vụ | Điều kiện tiên quyết trước khi chạy Scale Pipeline (mục 14) — không giả lập bằng fixture tổng hợp |
| Quy trình client có phần lõi nhận diện được (70-80% khả thi) | Nghiệp vụ | Đo thật trên 100 mẫu đầu tiên, không giả định trước |
| Client chấp nhận đàm phán 3 lựa chọn cho 20-30% | Nghiệp vụ | Xác nhận bằng văn bản trước khi build phần "core template" cho use case đó |
| Client duy trì kỷ luật cập nhật dữ liệu | Nghiệp vụ | Đánh giá trong Guideline intake (mục 14), không chờ tới khi Profile lệch mới phát hiện |

---

## 12. Risk & mitigation trong quá trình build — khớp slide 20 + rủi ro mới phát sinh thật

| Rủi ro | Trạng thái | Mitigation implement được |
|---|---|---|
| Anchor chưa có tiền lệ ở quy mô lớn | 🔴 Chưa test được — module chưa build | Bài test mục 9.1 là cổng cứng — fail sớm, rẻ, thay vì phát hiện ở tháng 6. **Đây vẫn là rủi ro cao nhất chưa được đo, không phải rủi ro đã kiểm soát.** |
| Docling/parser không đạt benchmark trên tài liệu KPMG thật (VAS/tiếng Việt) | 🟡 Một phần — DOCX pass, PDF chưa đo được vì lỗi môi trường | Cần tách rõ 2 câu hỏi: (a) Docling có parse đúng nội dung tiếng Việt không — CHƯA biết; (b) môi trường có chạy được không — biết rồi, đang fail vì thiếu compiler |
| Dữ liệu client rời khỏi hạ tầng nội bộ | ✅ Đã xác nhận bằng code — model local, không gọi HF Hub runtime | Không cần audit thêm ở bước này, nhưng nên re-verify khi thêm AI branch (Layer 4) |
| SOP client linh hoạt hơn brief ban đầu — core template khó đạt 70-80% | ⬜ Chưa tới giai đoạn này | Không hard-code target 70-80% trong code |
| Thiếu kỷ luật dữ liệu phía client | ⬜ Chưa tới giai đoạn này | Đánh giá ở bước Guideline (mục 14) |
| ⚠️ **Mới:** môi trường dev thiếu MSVC C++ Build Tools — `torch.compile` trong Docling pipeline fail JIT-compile khi parse PDF | 🔴 Blocking PDF path trên máy dev hiện tại | Cần xác nhận: môi trường deploy cuối cùng là gì? Nếu Linux server nội bộ, rủi ro có thể tự hết khi đổi môi trường — không nên tốn công cài Visual Studio Build Tools trên máy dev nếu deploy đích không phải Windows. Nếu vẫn deploy Windows, cần cài C++ workload hoặc tắt `torch.compile`/inductor trong pipeline options của Docling. |
| ⚠️ **Mới:** fixture XLSX vẫn thiếu dù đã cảnh báo từ bản build plan đầu tiên | 🔴 Blocking nhánh XLSX (anchor + use case CIT) | Đây là phụ thuộc cứng duy nhất đã nêu từ đầu — cần 1 file CIT-template thật đã ẩn danh, có named range/merged cell/formula để test đúng edge case |

---

## 13. Roadmap & estimate — khớp slide 27, chỉ là estimate

| Giai đoạn | Thời lượng | Đầu ra |
|---|---|---|
| 0. MVP codebase | **~1 tuần** | Layer 1-2 chạy được trên DOCX/XLSX/PDF, Element Index sinh ra |
| 0b. Test với document thật | **+3-5 ngày** | Chạy full checklist mục 9.2 trên fixture Tax thật |
| 1. Present team — chốt quyết định | sau MVP | Team review, approve/thay đổi trước khi mở rộng |
| 2. Vận hành thật với Tax | sau bước 1 | Chạy Scale Pipeline (mục 14) trên 1-2 engagement Tax thật |
| 3. Function thứ 2 (đề xuất: Audit) | sau bước 2 | Chạy lại TOÀN BỘ Scale Pipeline từ đầu — không copy nguyên kết quả từ Tax |
| 4. Rút Playbook liên-function | sau ≥2 function | Chỉ rút pattern chung sau khi có ít nhất 2 function thật, tránh khái quát hóa sớm |

**Nguyên tắc kỹ thuật đứng sau roadmap:** Layer 1-3 không đổi khi mở rộng sang function khác — chỉ Layer 4 (Output Profile riêng từng function) đổi. Đây là lý do kiến trúc 4-layer (mục 2) phải giữ đúng ranh giới ngay từ MVP1, không được để logic Tax-specific lọt vào Layer 2-3.

---

## 14. Vận hành: nhận 1 dự án mới — khớp slide 25

Quy trình 5 bước, dùng lại cho mọi client/function sau này — không phải bước build phần mềm, mà là **quy trình nghiệp vụ implement song song với code**:

1. **Guideline** — gửi client: Foundation làm được gì, cần cung cấp template input/output hoặc ≥100 mẫu raw.
2. **Scale Pipeline** — phân tích mẫu → core template → coverage %, mục tiêu 70-80%.
3. **Đàm phán 20-30%** — 3 lựa chọn: chấp nhận (note lại), đổi quy trình, hoặc không làm.
4. **Xác minh Starting Point** — truy ngược điểm bắt đầu thật, verify với client, không tin brief bề mặt.
5. **Map Process Coverage** — xác nhận Foundation cover đúng bao nhiêu bước trong SOP thật, không ngầm định "end-to-end".

Chi tiết đầy đủ nằm ở tài liệu riêng `Foundation_Intake_Guideline_Scale_Pipeline.docx` — build plan này chỉ tham chiếu, không lặp lại toàn bộ.

---

## 15. Demo acceptance criteria — khớp slide 24

### Demo Technical (đủ điều kiện present khi):
- [ ] Upload fixture thật, Element Index sinh ra không có 1 lệnh gọi model nào (log network trống)
- [ ] Bài test chèn-đầu-file (mục 9.1) chạy live, pass
- [ ] Ghi tại 1 anchor, mở output bằng Word thật, so sánh trước/sau không vỡ định dạng
- [ ] Tắt AI module bằng feature flag, lặp lại toàn bộ luồng — Layer 1-3 vẫn hoàn thành
- [ ] Execution log hiển thị rõ `actor: "ai_agent"` vs `actor: "human"` cho cùng 1 tài liệu

### Demo Application (đủ điều kiện present khi):
- [ ] Upload báo cáo tài chính client đúng định dạng thật, không chuẩn bị trước
- [ ] Element Index sinh ra — doanh thu, chi phí, thuế hoãn lại định vị đúng
- [ ] Yêu cầu ngôn ngữ thường → map qua anchor vào đúng ô workpaper CIT
- [ ] Mở kết quả bằng Excel thật — mọi số liệu truy ngược được về đúng ô nguồn
- [ ] Cả 2 demo chạy trên cùng 3 fixture — không dùng tài liệu tổng hợp

---

## 16. Việc cần làm ngay — cập nhật theo trạng thái thật, không còn là "tuần 1" nữa

~~1. Setup repo~~ ✅ Xong. ~~2. Schema Element/Anchor~~ ✅ Xong (đối chiếu lại theo mục 3, đã update `models.py` + `test_models.py`, 6/6 pass). ~~3. Fixture DOCX/PDF~~ ✅ Xong (XLSX vẫn thiếu, xem #3 mới). ~~5. Đo benchmark Docling~~ 🟡 Một phần (DOCX đo được, PDF bị chặn bởi #1 mới).

**Việc cần làm ngay, theo đúng thứ tự ưu tiên hiện tại:**

1. **Quyết định môi trường deploy đích** (Windows hay Linux) trước khi tấn công fix `torch.compile`/MSVC — quyết định này ảnh hưởng có nên fix ngay hay bỏ qua tạm thời để không chặn tiến độ.
2. **Cung cấp fixture XLSX** (`fixture_cit.xlsx`, có named range/merged cell/formula) — phụ thuộc cứng duy nhất còn lại, y hệt cảnh báo từ bản build plan đầu tiên.
3. **Build `anchor_builder.py`** — đúng build order đã định, module rủi ro cao nhất, IP quan trọng nhất.
4. **Chạy P3-04 (mục 9.1) ngay khi anchor_builder xong** — đây là cổng cứng thật sự đầu tiên của cả dự án. Không viết `index_writer.py`, không viết API routes, không đụng vào frontend cho tới khi P3-04 pass trên cả 3 định dạng.
5. Sau P3-04 pass: `index_writer.py` → adapters → API routes → kết nối `ElementIndexViewer.jsx` (đã build sẵn, chỉ thay `MOCK_DATA` bằng fetch thật, **không viết lại**).

---

*Tài liệu này là build plan kỹ thuật đi kèm `Foundation_Team_Presentation_FULL.pptx`. Xem `foundation/STATUS.md` cho snapshot trạng thái code hiện tại — hai file này nên được cập nhật song song, không để trôi lệch nhau.*
