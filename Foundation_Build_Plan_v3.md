# Build Plan — Document Perception & Interaction Foundation
## v3 — Kiến trúc pdfplumber + pdf2image + Workbench (openai client)

*Chuẩn bị bởi Nguyễn Đình Phúc · KPMG Vietnam Innovation · Tháng 8/2026*
*Thay thế bản build plan trước. Khớp với `Foundation_Team_Presentation_v2.pptx` (34 slide).*

---

## 0. Cách đọc tài liệu này

| Section | Khớp slide deck v2 | Nội dung |
|---|---|---|
| 3. Kiến trúc 2 lớp | Slide 8, 9 | Geometry tất định + Classification có rào |
| 4. Data model | Slide 12, 13 | Element/Anchor — nguyên tắc "anchor trước, nhãn sau" |
| 6. Output engine | Slide 15-17 | 3 mode, Patch/Build, Cover&Note |
| 9. Test plan | Slide 8, 30 | Geometry determinism, P3-04, classification consistency |
| 11. Risk | Slide 24 | 3 nhóm rủi ro đã cập nhật |
| 12. Roadmap | Slide 31 | Bước 0 = hỏi senior, không phải code |
| 13. Vận hành | Slide 29 | Client Intake / Scale Pipeline |

### 0.1 Bức tranh tổng thể

- **Kiến trúc mặc định:** `pdfplumber` + `pdf2image` (geometry tất định) + `openai` client gọi Workbench nội bộ (classification có rào, tắt được). Docling đã loại bỏ hoàn toàn.
- **Điều kiện tiên quyết chưa đóng:** `pdfplumber`/`pdf2image` đang "waiting for approval" trong CRADL. Đã gửi câu hỏi phân biệt "thuần code vs model" cho senior — deadline tự đặt 2 tuần.
- **Không đổi:** Element Index, Anchor schema, 3 chế độ output, Cover & Note, 4 màn hình UI, use case Tax, Client Intake Guideline.
- **Nguyên tắc thiết kế bắt buộc, không thương lượng:** Anchor được gán ở mức hình học (word/line bbox từ pdfplumber), **trước** khi có bất kỳ phân loại nào. AI không bao giờ nhận file gốc — chỉ nhận text + bbox đã trích xuất, và chỉ trả về nhãn.
- **Phương án dự phòng (Path C):** nếu pdfplumber bị từ chối, thay bằng parser tự viết (`zlib` stdlib) ở đúng vị trí Geometry Layer — phần Classification Layer không đổi gì (xem mục 15).

---

## 1. Tổng quan phạm vi

Scope build lần này = Layer 1 (Format Adapters) + Layer 2 (Perception & Interaction Core) đầy đủ + Layer 3 (Understanding & Placement) một phần (chỉ Select + Map/Place cơ bản theo Profile có sẵn).

**Không build đợt này:** OCR cho scanned PDF, negotiated template tự động (mode 3 không cần người), Align capability, production API gateway/SDK/MCP server, fine-tune model qua Workbench, mở rộng ngoài Tax.

---

## 2. Tech stack — trạng thái duyệt từng dòng

| Layer | Package | Vai trò | Duyệt |
|---|---|---|---|
| L1 DOCX | `python-docx` | Đọc/ghi | ✅ Approved |
| L1 XLSX | `openpyxl`, `defusedxml` | Đọc/ghi an toàn | ✅ Approved |
| L1 PDF — geometry | `pdfplumber`, `pdf2image` | Text/bbox thật, render ảnh cho Screen 1 | ⏳ Waiting for approval |
| L1 PDF — OS dependency | **Poppler** (`pdftoppm`/`pdftocairo`) | `pdf2image` gọi binary này ở tầng OS, không tự chạy nếu thiếu | ⚠️ Chưa hỏi — cần xác nhận với IT có cần duyệt riêng không |
| L2 core | Tự viết — Element Index, Anchor resolver | IP | Không cần duyệt |
| L2 storage | `sqlite3` (stdlib) | Profile store, execution log | ✅ Stdlib |
| L3 classification | `openai` | Client gọi Workbench | ✅ Approved |
| L3 auth | `azure-identity`, `msal`, `azure-core` | Auth Workbench | ✅ Approved |
| L3 validate | `pydantic`, `pydantic_core`, `jsonschema` | Chặn hallucination bằng schema | ✅ Approved |
| L3 resilience | `tenacity` (retry), `cachetools` (cache) | Gọi Workbench ổn định, giảm gọi lặp | ✅ Approved |
| L3 heuristic | `numpy`, `pandas` | Gom cụm tọa độ thành bảng | ✅ Approved |
| Access layer | `Flask`, `Werkzeug` | Thay FastAPI (đang chờ duyệt) | ✅ Approved |
| **Cấm dùng** | Docling, `torch`, `transformers`, PaddleOCR | Model bên ngoài | Không có trong danh sách |

---

## 3. Kiến trúc 2 lớp — chi tiết implement

### 3.1 Nguyên tắc

> Geometry Layer trả lời "cái gì, ở đâu" — tất định, không AI.
> Classification Layer trả lời "nó là loại gì" — có AI, có rào, tắt được.
> Anchor được gán ở cuối Geometry Layer, trước khi Classification Layer chạy.

### 3.2 Setup — làm trước khi viết logic

| Việc | Chi tiết |
|---|---|
| Cài `pdfplumber` + `pdf2image` | Sau khi CRADL duyệt |
| **Cài Poppler ở tầng OS** | `pdf2image` chỉ là wrapper — không chạy được nếu thiếu Poppler binary. Xác nhận với IT đây có tính là "package cần duyệt" không |
| Cấu hình `openai` client trỏ Workbench | `base_url` override, auth qua `azure-identity`, KHÔNG dùng public OpenAI key |
| Xác nhận Workbench hỗ trợ `temperature=0` + JSON mode | Nếu không, tự parse text response + validate thủ công |

### 3.3 Geometry Layer — code mẫu `adapters/pdf_adapter.py`

```python
import pdfplumber
from pydantic import BaseModel
from perception.models import AnchorPDF, FoundationElement, ElementType

class RawTextBlock(BaseModel):
    text: str
    page: int
    bbox_relative: tuple[float, float, float, float]  # x0,y0,x1,y1 theo tỷ lệ 0-1
    reading_order_index: int

def extract_geometry(pdf_path: str) -> list[RawTextBlock]:
    """Tất định 100%. Không model, không AI. Chạy 2 lần cho cùng input
    phải trả về danh sách y hệt nhau — đây là điều kiện bắt buộc,
    kiểm tra bằng test ở mục 9.1."""
    blocks = []
    order = 0
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            pw, ph = page.width, page.height
            # word-level, không phải char-level — đơn vị nhỏ nhất còn có ý nghĩa
            for word in page.extract_words(use_text_flow=True):
                blocks.append(RawTextBlock(
                    text=word["text"],
                    page=page_num,
                    bbox_relative=(
                        word["x0"] / pw, word["top"] / ph,
                        word["x1"] / pw, word["bottom"] / ph,
                    ),
                    reading_order_index=order,
                ))
                order += 1
    return blocks

def group_into_elements(blocks: list[RawTextBlock]) -> list[list[RawTextBlock]]:
    """Gom word/line thành 'element' (đoạn văn, dòng bảng) bằng heuristic
    HÌNH HỌC THUẦN TÚY (khoảng cách dòng, căn lề) — KHÔNG dùng AI ở đây.
    Đây là bước quyết định 'cái gì là 1 element', nên phải tất định."""
    # ví dụ tối giản — thực tế cần xử lý theo y-coordinate clustering
    ...

def assign_anchors(groups: list[list[RawTextBlock]]) -> list[FoundationElement]:
    """Gán Anchor NGAY TẠI ĐÂY — trước khi có bất kỳ phân loại ngữ nghĩa nào.
    element_type mặc định = UNCLASSIFIED, được điền sau bởi Classification Layer,
    nhưng Anchor không đổi dù element_type có đổi."""
    elements = []
    for g in groups:
        first, last = g[0], g[-1]
        x0 = min(b.bbox_relative[0] for b in g)
        y0 = min(b.bbox_relative[1] for b in g)
        x1 = max(b.bbox_relative[2] for b in g)
        y1 = max(b.bbox_relative[3] for b in g)
        anchor = AnchorPDF(
            page=first.page,
            bbox_relative=(x0, y0, x1, y1),
            reading_order_index=first.reading_order_index,
        )
        elements.append(FoundationElement(
            anchor=anchor,
            text=" ".join(b.text for b in g),
            type=ElementType.UNCLASSIFIED,  # Classification Layer điền sau
        ))
    return elements
```

**Vai trò của `pdf2image`:** chỉ để render ảnh trang cho Screen 1 (input viewer + bounding box overlay). **Không** dùng ảnh này để gửi cho Workbench — vi phạm nguyên tắc "AI không bao giờ nhận file gốc".

### 3.4 Classification Layer — code mẫu `perception/classifier.py`

```python
from openai import AzureOpenAI  # hoặc client trỏ Workbench nội bộ
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import LRUCache
import hashlib

class ClassificationResult(BaseModel):
    element_type: str  # heading | paragraph | table_cell | caption | ...
    confidence: float

_cache: LRUCache = LRUCache(maxsize=10_000)

def _cache_key(text: str, bbox: tuple) -> str:
    return hashlib.sha256(f"{text}|{bbox}".encode()).hexdigest()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def classify_element(client, text: str, bbox: tuple, model_version: str) -> ClassificationResult:
    key = _cache_key(text, bbox)
    if key in _cache:
        return _cache[key]

    # QUAN TRỌNG: chỉ gửi text + bbox, KHÔNG gửi file, KHÔNG gửi ảnh trang
    response = client.chat.completions.create(
        model=model_version,           # pin cứng, không dùng "latest"
        temperature=0,                  # giảm (không loại bỏ hoàn toàn) non-determinism
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Phân loại đoạn text tài chính. Trả JSON: {element_type, confidence}."},
            {"role": "user", "content": f"Text: {text}\nBBox: {bbox}"},
        ],
    )
    try:
        result = ClassificationResult.model_validate_json(response.choices[0].message.content)
    except ValidationError as e:
        # SAI SCHEMA = LỖI, không tự đoán/sửa
        raise ClassificationSchemaError(f"Workbench trả sai schema: {e}")

    _cache[key] = result
    return result
```

### 3.5 Cổng gate — feature flag độc lập

```python
class FoundationConfig(BaseModel):
    ai_classification_enabled: bool = True   # tắt để demo technical / audit

def process_document(path: str, config: FoundationConfig) -> FoundationDocument:
    blocks = extract_geometry(path)                    # luôn chạy
    groups = group_into_elements(blocks)                # luôn chạy
    elements = assign_anchors(groups)                   # luôn chạy — anchor cố định tại đây

    if config.ai_classification_enabled:
        for el in elements:
            result = classify_element(client, el.text, el.anchor.bbox_relative, MODEL_VERSION)
            if result.confidence >= CONFIDENCE_THRESHOLD:
                el.type = result.element_type
            else:
                el.needs_human_review = True
    # Nếu tắt AI: mọi element giữ type=UNCLASSIFIED, vẫn có đủ Anchor + text
    # → Layer 1-2-3 (trừ phân loại) vẫn hoàn thành, đúng yêu cầu demo technical

    return FoundationDocument(elements=elements)
```

---

## 4. Data model — không đổi so với bản trước, giữ nguyên

```python
class AnchorDOCX(BaseModel):
    format: Literal["docx"] = "docx"
    paragraph_index: int
    style_id: str
    text_fingerprint: str

class AnchorXLSX(BaseModel):
    format: Literal["xlsx"] = "xlsx"
    sheet_name: str
    cell_address: str
    named_range: str | None = None

class AnchorPDF(BaseModel):
    format: Literal["pdf"] = "pdf"
    page: int
    bbox_relative: tuple[float, float, float, float]
    reading_order_index: int

Anchor = AnchorDOCX | AnchorXLSX | AnchorPDF
```

Resolution ladder giữ nguyên: (1) style+fingerprint match (2) paragraph_index+style (3) paragraph_index only, cảnh báo (4) không resolve được → raise error, không ghi mù.

---

## 5. Runtime flow

```
file_intake → GEOMETRY LAYER (tất định, luôn chạy)
                  → extract_geometry (pdfplumber)
                  → group_into_elements (heuristic hình học)
                  → assign_anchors  ← ANCHOR CỐ ĐỊNH TẠI ĐÂY
                        ↓
                  [GATE: ai_classification_enabled?]
                        │yes                    │no
                        ↓                        ↓
              CLASSIFICATION LAYER          element.type = UNCLASSIFIED
              (Workbench, có rào)                ↓
                        └──────────merge─────────┘
                                    ↓
                versioned_profile → map_and_act → output_and_trace
```

Execution log record: `{timestamp, actor: "system"|"ai_agent"|"human", step, input_ref, output_ref, old_value, new_value, model_version, cache_hit: bool}`.

---

## 6. Output engine — không đổi

3 mode (Clone & Replace / Profile-driven Fill / Task-shaped), Patch mode + Build mode, guaranteed floor (rung 2 luôn thành công), cơ chế Cover & Note trong 1 sheet Excel — toàn bộ giữ nguyên từ bản trước, không phụ thuộc quyết định geometry layer.

---

## 7. Capability Align — chưa build, nhưng schema phải tương thích

Không build trong MVP1. Khi build sau này: `AnchorPDF` hiện tại (page + bbox + reading_order) đã đủ để join 2 Element Index của 2 tài liệu khác nhau mà không cần đổi schema — vì anchor được gán độc lập với phân loại (mục 3.3-3.5).

---

## 8. API — Flask, không đổi so với bản trước

`/documents/upload`, `/documents/{id}/perceive`, `/documents/{id}/elements/{index}` (PATCH), `/documents/{id}/anchors/{anchor}/resolve`, `/documents/{id}/write`, `/executions/{document_id}`. Mọi call ghi bắt buộc ghi execution log.

---

## 9. Test plan

### 9.1 Test tất định của Geometry Layer — chạy TRƯỚC mọi thứ khác

```
Chạy extract_geometry() 2 lần trên cùng 1 file PDF.
Kết quả bắt buộc: 2 danh sách RawTextBlock giống hệt nhau (so sánh từng bbox).
Nếu khác nhau dù chỉ 1 giá trị → dừng lại, không build tiếp.
```

### 9.2 P3-04 — Anchor stability test, chạy cả khi AI bật lẫn khi AI tắt

```
1. Parse fixture, lưu anchor của 1 element.
2. Chèn 1 đoạn văn vào đầu file.
3. Parse lại → CHẠY 2 LẦN: một lần config.ai_classification_enabled=True,
   một lần =False.
4. Resolve anchor cũ ở cả 2 lần chạy.
Kết quả bắt buộc: cả 2 lần đều trả về đúng element cũ — chứng minh anchor
không phụ thuộc trạng thái AI.
```

### 9.3 Đo tính ổn định của Classification Layer — đo thật, không dùng số của người khác

```
Chọn 20 đoạn text đại diện từ fixture Tax.
Gọi classify_element() 5 lần/đoạn (xóa cache giữa các lần).
Tính tỷ lệ đồng thuận (agreement rate) thật.
Ghi số đo được vào build plan — KHÔNG dùng số Kappa 0.91 từ paper khác,
đó là domain khác (forum post), không phải tài liệu tài chính.
```

### 9.4 Checklist MUST PROVE

- [ ] Geometry tất định (9.1) pass trên toàn bộ fixture PDF
- [ ] P3-04 pass cả khi AI bật và tắt (9.2)
- [ ] Classification consistency đo được, ghi số thật (9.3)
- [ ] Element Index + anchor cho từng element, heading/table detection đo trên fixture Tax thật
- [ ] Đọc–ghi an toàn cho DOCX/XLSX; PDF read-only theo thiết kế
- [ ] 2 use case Tax chạy end-to-end
- [ ] Execution log đầy đủ, có `model_version` và `cache_hit`

---

## 10. MVP1 scope — không đổi

Thành công = "lõi và interaction contract có vững, bền, mở rộng được không" — không phải số giờ tiết kiệm trên 1 báo cáo.

---

## 11. Assumptions

| Assumption | Kiểm tra ở đâu |
|---|---|
| Geometry tất định (9.1) | Chạy ngay tuần đầu, trước mọi thứ khác |
| Poppler có sẵn/được phép cài ở môi trường deploy | Hỏi IT song song với câu hỏi pdfplumber |
| Workbench hỗ trợ temperature=0 + JSON mode | Xác nhận với team hạ tầng trước khi viết `classifier.py` |
| Classification consistency đủ dùng cho tài liệu tài chính | Đo thật theo 9.3, không suy diễn |
| Client (Tax) cung cấp ≥100 mẫu + template | Điều kiện tiên quyết Scale Pipeline |
| Client duy trì kỷ luật cập nhật dữ liệu | Đánh giá ở Guideline intake |

---

## 12. Risk & mitigation

| Rủi ro | Mitigation |
|---|---|
| pdfplumber/pdf2image vẫn "waiting for approval" | Deadline 2 tuần tự đặt, sau đó tự chuyển Path C (mục 15) |
| Poppler binary chưa rõ có cần duyệt riêng | Hỏi IT cùng lúc với câu hỏi pdfplumber, đừng để phát hiện muộn |
| Anchor chưa có tiền lệ quy mô lớn | Test 9.1 + 9.2 là cổng cứng |
| Rule-based yếu hơn model ở category "Financial" (theo arXiv 2410.09871) | Đo thật theo 9.4, không cam kết % trước khi đo |
| Non-determinism của Workbench | temperature=0 + cache + schema validate + đo thật theo 9.3; anchor tách khỏi phân loại nên traceability không bị đe dọa |
| Workbench endpoint không thật sự air-gapped | Audit network trước khi có dữ liệu client thật chạm hệ thống |

---

## 13. Roadmap

| Bước | Việc | Ghi chú |
|---|---|---|
| 0 | Hỏi senior câu phân biệt "thuần code vs model" + hỏi IT về Poppler | Đòn bẩy cao nhất hiện tại, deadline 2 tuần |
| 1 | MVP codebase (~1 tuần) | Song song bước 0, không chờ |
| 1b | Test với document thật (+3-5 ngày) | Bao gồm 9.1, 9.2, 9.3 |
| 2 | Present team — chốt quyết định | Bao gồm quyết định kiến trúc mới |
| 3 | Vận hành thật với Tax | Scale Pipeline trên engagement thật |
| 4 | Function thứ 2 (Audit) | Chạy lại toàn bộ Scale Pipeline, không giả định tổng quát hóa |

---

## 14. Vận hành nhận dự án mới

Không đổi — xem `Foundation_Intake_Guideline_Scale_Pipeline.docx`: Guideline → Scale Pipeline → Đàm phán 20-30% → xác minh Starting Point → map Process Coverage.

---

## 15. Phương án dự phòng — nếu pdfplumber bị từ chối (Path C)

**Chỉ mục 3.3 (Geometry Layer) thay đổi.** Thay `extract_geometry()` bằng parser tự viết dùng `zlib` (stdlib, không cần duyệt):

```python
import zlib
# Tự đọc cross-reference table, giải nén content stream bằng zlib,
# tự parse operator Tj/TJ + ma trận Tm để tính bbox.
# Effort cao hơn nhiều — đặc biệt xử lý font encoding cho tiếng Việt có dấu.
```

**Mục 3.4, 3.5 (Classification Layer, gate) không đổi một dòng nào** — vì chúng chỉ nhận `text + bbox`, không quan tâm nguồn gốc. Đây là lý do tách 2 lớp: đổi công cụ geometry không kéo theo viết lại phần AI.

---

## 16. Demo acceptance criteria

**Demo Technical:**
- [ ] Chạy 9.1 live — 2 lần parse cùng file, cho xem diff = rỗng
- [ ] Chạy P3-04 live với AI bật và tắt (9.2)
- [ ] Cho xem request thật gửi tới Workbench — chỉ có text+bbox, không có file
- [ ] Execution log phân biệt actor, có `model_version`

**Demo Application:** không đổi — upload báo cáo thật, Element Index, yêu cầu ngôn ngữ thường, output Excel có traceability.

---

## 17. Việc cần làm ngay

1. Gửi câu hỏi phân biệt "thuần code vs model" cho senior — kèm câu hỏi Poppler.
2. Refactor `perception/parser.py`: tách interface Geometry Layer khỏi Docling, chuẩn bị chỗ cắm `pdfplumber` hoặc parser tự viết.
3. Viết `group_into_elements()` thật (mục 3.3) — đây là phần chưa có code mẫu đầy đủ ở trên, cần thiết kế heuristic cụ thể dựa trên fixture thật.
4. Cung cấp fixture XLSX còn thiếu.
5. Chạy test 9.1 ngay khi geometry layer xong — trước khi viết `classifier.py`.
6. Chỉ viết `classifier.py` (mục 3.4) sau khi 9.1 và P3-04 (phần không-AI) đã pass.

---

*Tài liệu tham chiếu: `Foundation_Team_Presentation_v2.pptx` · `Foundation_Market_Benchmark.md` · `Foundation_Intake_Guideline_Scale_Pipeline.docx` · `CRADL_OSS_Packages.xlsx`.*
