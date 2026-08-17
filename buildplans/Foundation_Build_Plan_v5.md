# Build Plan — Document Perception & Interaction Foundation
## v5 — Tổng hợp đầy đủ: kiến trúc 2+1 nhánh (Geometry / OCR / Classification), rà soát license, model bake-off

*Chuẩn bị bởi Nguyễn Đình Phục · KPMG Vietnam Innovation · Tháng 8/2026*
*Thay thế toàn bộ các bản v3, v4. Đây là bản build plan hợp nhất — không cần tham chiếu ngược các bản cũ.*

---

## 0. Cách đọc tài liệu này

### 0.1 Đổi gì so với v4 — 4 điểm

1. **OCR chính thức vào scope.** Input có thể là PDF scan (không có text layer) — đây là thực tế vận hành, không phải trường hợp hiếm. Thêm nhánh xử lý riêng, xem mục 3.3.
2. **Loại bỏ PyMuPDF khỏi mọi cân nhắc** — dù được một Dev Senior đề xuất thay `pdfplumber`/`pdf2image`, PyMuPDF chỉ có 2 lựa chọn license (AGPL-3.0 hoặc thương mại trả phí Artifex, ~10.000-50.000 USD/năm) — **vi phạm trực tiếp quy tắc "không dùng GPL/AGPL" đã đặt ra từ chính tài liệu kiến trúc đầu tiên của dự án.**
3. **Danh sách model Workbench đầy đủ hơn nhiều** so với giả định cũ (`gpt-4o-2024-08-06` đơn lẻ) — công ty thực tế có quyền dùng cả dòng GPT-5 (5, 5.1, 5.2, 5.4), o3/o4-mini, GPT-4.1. Chiến lược chọn model cần đo thật, không suy diễn từ benchmark mạng — benchmark OCR online cho cùng 1 model (GPT-5.2) mâu thuẫn nhau nghiêm trọng giữa các nguồn.
4. **`opencv-python` → `Pillow`/`scikit-image`/`scikit-learn`** — swap an toàn, đã xác nhận cả 3 nằm trong CRADL approved.

### 0.2 Bức tranh tổng thể hiện tại

- **Kiến trúc gồm 3 nhánh, không phải 2:** Geometry (PDF digital, tất định) — OCR (PDF scan, có AI nhưng bị giới hạn chặt) — Classification (phân loại ngữ nghĩa, có AI, có rào). Cả 3 đều gán Anchor trước khi thao tác AI diễn ra, không có ngoại lệ.
- **Compliance:** `pdfplumber`/`pdf2image` vẫn "waiting for approval" — deadline tự đặt 2 tuần đã qua một phần, cần theo sát. PyMuPDF bị loại hẳn, không phải phương án dự phòng.
- **Chưa làm:** model bake-off cho nhánh OCR (có code mẫu ở mục 10, chưa chạy vì chưa có fixture scan thật).
- **Không đổi:** Element/Anchor schema, 3 chế độ output, Client Intake/Scale Pipeline, ranh giới Foundation/Application, kế hoạch build UI thật, yêu cầu Template Authoring (Phase 2), use case demo "Local File Roll-Forward" (đối chiếu với deck GTPS).

---

## 1. Tổng quan phạm vi

**Foundation (core) chỉ gồm 2 năng lực**, không đổi từ các bản trước:

| # | Năng lực | Mô tả |
|---|---|---|
| A | Tương tác file chuẩn | Đọc mọi element trong tài liệu (kể cả khi phải OCR), biết vị trí (Anchor), biết cách thao tác |
| B | Hỗ trợ tạo template | Từ N mẫu input hoặc yêu cầu output, hỗ trợ dựng template tái sử dụng |

**Application layer** (extraction, translation, mapping, comparison, summarize) xây trên core, không viết logic use-case vào package core.

**Use case demo gần nhất:** Local File Roll-Forward (Excel FA&RPTs worksheet → DOCX Local File), đối chiếu với workflow thật của team GTPS. Scope kỹ thuật demo: **DOC only trước**, chưa mở rộng đa định dạng.

**OCR nằm ở đâu trong bức tranh này:** OCR không phải một use case riêng — nó là **một nhánh bắt buộc phải có trong Layer 1 (Format Adapters) cho PDF**, vì input tài liệu tài chính thật (báo cáo scan, hóa đơn scan) không thể giả định luôn là digital. Demo GTPS gần nhất không cần đến nhánh này (input là Excel/DOCX), nhưng **kiến trúc Foundation nói chung phải có nhánh OCR ngay từ đầu**, không để dồn lại sau.

---

## 2. Tech stack — bảng đầy đủ, đã rà soát license từng dòng

| Layer | Package | Vai trò | Trạng thái |
|---|---|---|---|
| L1 DOCX | `python-docx` | Đọc/ghi | ✅ Approved |
| L1 XLSX | `openpyxl`, `defusedxml` | Đọc/ghi an toàn | ✅ Approved |
| L1 PDF — geometry (digital) | `pdfplumber`, `pdf2image` | Text/bbox thật, render ảnh | ⏳ Waiting for approval |
| L1 PDF — OS dependency | Poppler | `pdf2image` cần binary này ở tầng OS | ⚠️ Cần hỏi IT riêng |
| ~~L1 PDF — thay thế~~ | ~~PyMuPDF (`fitz`)~~ | ~~Đọc/render PDF~~ | ❌ **Loại bỏ — AGPL-3.0 hoặc thương mại trả phí, vi phạm quy tắc GPL/AGPL đã có từ đầu dự án** |
| L1 PDF — ảnh/hình học cho OCR | `Pillow` (thay `opencv-python`) | Xử lý ảnh cơ bản | ✅ Approved |
| L1 PDF — phân vùng ảnh cho OCR | `scikit-image` (thay `opencv-python`) | Connected components, phát hiện vùng text theo hình học thuần | ✅ Approved |
| L3 — helper thống kê | `scikit-learn`, `numpy`, `pandas` | Hỗ trợ heuristic gom cụm | ✅ Approved |
| L3 classification & OCR | `openai` | Client gọi Workbench | ✅ Approved |
| L3 auth | `azure-identity`, `msal`, `azure-core` | Auth Workbench | ✅ Approved |
| L3 validate | `pydantic`, `pydantic_core`, `jsonschema` | Chặn hallucination | ✅ Approved |
| L3 resilience | `tenacity`, `cachetools` | Retry, cache | ✅ Approved |
| L2 storage | `sqlite3` (stdlib) | Profile store, execution log | ✅ Stdlib |
| Access layer | `Flask`, `Werkzeug` | Thay FastAPI (đang chờ duyệt) | ✅ Approved |
| **Cấm dùng — model bên ngoài** | Docling, `torch`, `transformers`, PaddleOCR, `docling-ibm-models`, Tesseract/EasyOCR/RapidOCR (đều cần tải model) | — | Không có trong danh sách |
| **Cấm dùng — license** | PyMuPDF, Marker-PDF (GPL), DocLayout-YOLO (AGPL) | — | AGPL/GPL, vi phạm quy tắc dự án |

### 2.1 Danh sách model Workbench thật — không phải giả định nữa

| Model deployment | Loại | Vai trò đề xuất |
|---|---|---|
| `gpt-5-4-2026-03-05-gs-ae` | Full, mới nhất | Ứng viên chính cho nhánh OCR |
| `gpt-5-2-2025-12-11-gs-ae` | Full | Ứng viên OCR — benchmark mạng mâu thuẫn, cần tự đo |
| `gpt-5-2025-08-07-gs-ae`, `gpt-5-1-2025-11-13-gs-ae` | Full | Mốc so sánh |
| `o4-mini-2025-04-16-gs-ae`, `o3-2025-04-16-gs-ae` | Reasoning + vision | Ứng viên OCR — giả thuyết mạnh cho chữ mờ/viết tay nhờ khả năng suy luận theo ngữ cảnh |
| `gpt-4-1-2025-04-14-gs-ae` | Full | Mốc so sánh — có tiền lệ tốt trong nghiên cứu khác (~88% acceptable transcription toán viết tay với prompt đúng) |
| `gpt-4o-2024-08-06-gs-ae`, `gpt-4o-2024-11-20-std-ae` | Full | Không ưu tiên — benchmark cho thấy thua cả OCR chuyên biệt lẫn các bản GPT-5 |
| `gpt-5-4-mini`, `gpt-5-mini`, `gpt-5-nano`, `gpt-4o-mini`, `gpt-4-1-mini`, `gpt-4-1-nano` | Mini/nano | **Dành cho Classification Layer** — khối lượng cao, chi phí thấp, rủi ro thấp vì luôn có người xác nhận |
| `text-embedding-3-large/small` | Embedding | Chưa dùng ở MVP1 — có thể dùng sau cho fingerprint/similarity matching nếu cần |

**Nguyên tắc pin model:** Classification Layer dùng bản mini/nano (rẻ, khối lượng cao). Nhánh OCR dùng bản full, chọn qua bake-off thật (mục 10), không suy diễn từ benchmark mạng.

---

## 3. Kiến trúc pipeline — 3 nhánh

### 3.1 Sơ đồ tổng thể

```
file_intake
    │
    ├─ PDF? → thử pdfplumber trích text
    │              │
    │        [GATE 1: đủ text không?]  (đếm ký tự trích được / diện tích trang)
    │              │đủ (digital)              │không đủ (scan)
    │              ▼                          ▼
    │        GEOMETRY LAYER              OCR BRANCH (mục 3.3)
    │        (mục 3.2, tất định)         (có AI, bị giới hạn chặt)
    │              │                          │
    │              └──────────┬───────────────┘
    │                         ▼
    │              ★ ANCHOR CỐ ĐỊNH TẠI ĐÂY (cả 2 nhánh đều gán ở đây)
    │                         │
    │                   [GATE 2: cần phân loại AI?]
    │                         │yes            │no
    │                         ▼                ▼
    │              CLASSIFICATION LAYER   type = UNCLASSIFIED
    │              (mục 3.4, có rào)           │
    │                         └───────merge────┘
    │                                   ▼
    │                       NORMALIZATION LAYER (tất định)
    │                                   ▼
    │           versioned_profile → map_and_act → output_and_trace
    │
    └─ DOCX/XLSX → Geometry Layer tương ứng (python-docx/openpyxl), không qua Gate 1
```

### 3.2 Geometry Layer (PDF digital) — không đổi từ bản trước

```python
import pdfplumber

def extract_geometry(pdf_path: str) -> list[RawTextBlock]:
    """Tất định 100%. Chạy 2 lần cho cùng input phải ra kết quả y hệt."""
    ...

def has_enough_text(pdf_path: str, threshold: float = 0.02) -> bool:
    """GATE 1 — tỉ lệ ký tự trích được trên diện tích trang.
    Dưới ngưỡng → coi là scan, chuyển sang OCR Branch.
    Ngưỡng cần đo thật trên fixture — 0.02 chỉ là giá trị khởi điểm."""
    ...
```

### 3.3 OCR Branch (PDF scan) — MỚI

Nguyên tắc: **giữ tất định nhiều nhất có thể**, AI chỉ làm đúng một việc hẹp nhất — transcribe nội dung của một vùng ảnh đã được khoanh sẵn, không giao việc "đọc hiểu cả trang" cho AI.

```python
from PIL import Image
from skimage import measure, filters
import numpy as np

def render_page_to_image(pdf_path: str, page_num: int) -> Image.Image:
    """pdf2image — chỉ dùng để có ảnh, không dùng để trích xuất."""
    ...

def segment_regions(page_image: Image.Image) -> list[RegionBBox]:
    """Phân vùng trang bằng hình học thuần túy — KHÔNG AI.
    Dùng scikit-image: nhị phân hóa (threshold), connected components
    để nhóm pixel liền kề thành từng khối, mỗi khối là 1 candidate region.
    Đơn giản hơn: chia theo dải ngang có nội dung (projection profile)."""
    gray = np.array(page_image.convert("L"))
    binary = gray < filters.threshold_otsu(gray)
    labeled = measure.label(binary)
    regions = measure.regionprops(labeled)
    return [RegionBBox(bbox=r.bbox, area=r.area) for r in regions if r.area > MIN_AREA]

def assign_anchors_from_regions(regions: list[RegionBBox], page_num: int) -> list[FoundationElement]:
    """Gán Anchor NGAY TẠI ĐÂY — trước khi AI chạm vào bất cứ gì.
    Giống hệt nguyên tắc ở Geometry Layer digital."""
    ...

def transcribe_region(client, region_image: Image.Image, model: str) -> str:
    """AI CHỈ nhận ảnh đã crop của 1 vùng nhỏ — không bao giờ nhận cả trang.
    Prompt chuyên biệt cho OCR, KHÔNG dùng chung prompt với Classification Layer."""
    import base64
    from io import BytesIO
    buf = BytesIO()
    region_image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": "Bạn là công cụ OCR. Chỉ transcribe chính xác từng ký tự trong ảnh. KHÔNG diễn giải, KHÔNG tóm tắt, KHÔNG thêm bớt. Nếu không đọc được, trả về [UNCLEAR]."},
            {"role": "user", "content": [
                {"type": "text", "text": "Transcribe toàn bộ text trong ảnh sau, giữ nguyên định dạng số/ngày tháng:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]},
        ],
    )
    return response.choices[0].message.content
```

**Vì sao cắt vùng nhỏ, không gửi cả trang:** (1) chính xác hơn — model dễ đọc đúng 1 đoạn nhỏ hơn cả trang dày chữ; (2) giảm bề mặt dữ liệu gửi ra ngoài core — đúng nguyên tắc "AI chỉ thấy đúng phần cần thiết", không gửi toàn bộ số liệu tài chính trong 1 lần gọi.

**Ràng buộc bắt buộc, không thương lượng:**
- Anchor của element nguồn gốc OCR vẫn đủ 3 trường (`page`, `bbox_relative`, `reading_order_index`) — không có schema riêng cho "element từ OCR" khác với "element từ text layer". Chỉ khác ở `confidence` — luôn thấp hơn và có cờ `source: "ocr"` để phân biệt khi cần.
- Ngưỡng confidence cho nhánh OCR phải **chặt hơn** nhánh Classification — vì sai 1 chữ số trong báo cáo tài chính nghiêm trọng hơn sai nhãn phân loại.

### 3.4 Classification Layer — không đổi từ v4

Nhận text + bbox đã có sẵn (từ Geometry Layer hoặc từ OCR Branch), chỉ trả về nhãn (heading/table/paragraph...). `temperature=0`, cache, retry, validate schema — xem chi tiết code mẫu đã có ở các bản trước, không lặp lại ở đây.

### 3.5 Normalization Layer — không đổi từ v4

Chuẩn hóa định dạng (VND/VNĐ, ngày tháng) — tất định, rule KPMG tự định nghĩa, không AI.

---

## 4. Data model

Schema `Anchor`/`FoundationElement` — không đổi cấu trúc cốt lõi, chỉ bổ sung cờ nguồn gốc:

```python
class FoundationElement(BaseModel):
    anchor: Anchor
    text: str
    text_normalized: str | None = None
    type: ElementType
    confidence: float | None = None
    source: Literal["text_layer", "ocr", "manual"] = "text_layer"   # MỚI
```

Profile schema (có `formula: str | None` dành chỗ cho Template Authoring — xem mục 8 trong v4, không lặp lại).

---

## 5. Ranh giới Foundation / Application

Không đổi từ v4 — Foundation chỉ làm năng lực A và B (mục 1). Mapping/translate/compare là application, gọi vào core qua API.

---

## 6. Build UI thật

Không đổi từ v4 — 4 pane (Input Viewer / Element Index / Intent-Mapping / Output+Trace), `zustand` cho sync, `react-resizable-panels`, kết nối API Flask thật. Xem chi tiết component breakdown, build order ở bản v4 nếu cần tra lại — kiến trúc UI không bị ảnh hưởng bởi thay đổi OCR/license lần này.

---

## 7. Template Authoring (Phase 2, chưa build)

Không đổi từ v4 — yêu cầu template "động" (biến, công thức, kéo-thả) từ anh Quốc, chưa thiết kế chi tiết, chỉ đảm bảo schema không chặn đường mở rộng.

---

## 8. Định vị cạnh tranh nội bộ (Digital Gateway, Copilot)

Chưa làm — vẫn là việc cần research trước buổi Partners giữa tháng 9, không đổi từ v4.

---

## 9. Lựa chọn hạ tầng máy local cô lập mạng

Chưa quyết định — vẫn cần cost-out theo yêu cầu anh Quốc, không đổi từ v4. Lưu ý: nếu hướng này được chọn cho khối lượng hóa đơn/PDF không nhạy cảm, nó có thể **thay thế nhánh OCR qua Workbench** bằng model OCR chuyên biệt chạy local (không vướng compliance vì cô lập mạng) — đáng cân nhắc chung với quyết định OCR nếu máy local được duyệt.

---

## 10. Model bake-off cho nhánh OCR — MỚI, chưa chạy

### 10.1 Vì sao phải bake-off, không chọn theo benchmark mạng

Cùng một model (GPT-5.2), 2 nguồn benchmark 2026 cho kết luận gần như đối lập — một nguồn mô tả tích cực định tính, nguồn kia đo được CER 0.271 (~27% ký tự sai) và **xếp cuối bảng trong 16 model**. Sự mâu thuẫn này là bằng chứng đủ mạnh: **không dùng benchmark online để quyết định, phải đo trên đúng dữ liệu và đúng model deployment của mình.**

### 10.2 Danh sách rút gọn để test

`gpt-5-4-2026-03-05-gs-ae` · `gpt-5-2-2025-12-11-gs-ae` · `o4-mini-2025-04-16-gs-ae` · `gpt-4-1-2025-04-14-gs-ae`

Không đưa các bản mini/nano vào bake-off OCR — dành riêng cho Classification Layer.

### 10.3 Code mẫu chạy bake-off

```python
import difflib
from dataclasses import dataclass

@dataclass
class BakeoffResult:
    model: str
    cer_text: float      # Character Error Rate trên đoạn text thường
    cer_numbers: float   # CER riêng cho chữ số — quan trọng nhất cho use case này
    latency_s: float
    cost_estimate: float

def compute_cer(hypothesis: str, ground_truth: str) -> float:
    matcher = difflib.SequenceMatcher(None, ground_truth, hypothesis)
    ops = matcher.get_opcodes()
    errors = sum((i2 - i1) for tag, i1, i2, j1, j2 in ops if tag != "equal")
    return errors / max(len(ground_truth), 1)

def run_bakeoff(fixture_pages: list[tuple[Image.Image, str]], models: list[str], client):
    """fixture_pages: list of (region_image, ground_truth_text) đã gõ tay chuẩn.
    Chạy từng model qua toàn bộ fixture, tách riêng CER cho phần chứa số."""
    results = []
    for model in models:
        cer_text_list, cer_num_list = [], []
        for region_img, truth in fixture_pages:
            hypothesis = transcribe_region(client, region_img, model)
            cer_text_list.append(compute_cer(hypothesis, truth))
            truth_numbers = "".join(c for c in truth if c.isdigit())
            hyp_numbers = "".join(c for c in hypothesis if c.isdigit())
            cer_num_list.append(compute_cer(hyp_numbers, truth_numbers))
        results.append(BakeoffResult(
            model=model,
            cer_text=sum(cer_text_list) / len(cer_text_list),
            cer_numbers=sum(cer_num_list) / len(cer_num_list),
            latency_s=..., cost_estimate=...,
        ))
    return sorted(results, key=lambda r: r.cer_numbers)   # ưu tiên đúng số, không phải đúng text chung
```

### 10.4 Việc cần làm để chạy được mục này

- [ ] Lấy 5-10 trang scan tài chính tiếng Việt thật, đã ẩn danh.
- [ ] Gõ tay ground truth cho từng trang (chuẩn 100%, làm thủ công).
- [ ] Chạy `run_bakeoff()`, chọn model theo `cer_numbers` thấp nhất — không chọn theo `cer_text` chung chung.
- [ ] Ghi lại số đo thật vào bản build plan tiếp theo, thay cho bảng "đề xuất" ở mục 10.2.

---

## 11. Test plan

Giữ nguyên toàn bộ test đã có (geometry tất định, P3-04 chạy cả khi AI bật/tắt, classification consistency, normalization consistency) — bổ sung:

- [ ] **GATE 1 threshold test** — chạy `has_enough_text()` trên hỗn hợp fixture digital + scan, đo tỷ lệ phân loại đúng (không lẫn digital thành scan hoặc ngược lại).
- [ ] **OCR Branch anchor stability** — P3-04 áp dụng riêng cho nhánh OCR: chèn 1 vùng mới vào ảnh trang scan, resolve lại anchor cũ, kỳ vọng vẫn đúng (dù confidence có thể khác, vị trí anchor không được đổi).
- [ ] **Model bake-off** — mục 10, chạy trước khi pin model chính thức cho nhánh OCR.

---

## 12. MVP1 scope

| | Trạng thái |
|---|---|
| Geometry Layer (PDF digital) | Trong scope, chưa build xong |
| OCR Branch | **Trong scope kiến trúc** — thiết kế đầy đủ ở mục 3.3, nhưng **chưa bắt buộc hoàn thiện cho demo GTPS** (input demo là Excel/DOCX, không cần OCR) |
| Classification Layer | Trong scope |
| Normalization Layer | Trong scope |
| Use case demo GTPS (Local File Roll-Forward) | Trong scope, DOC only |
| Template Authoring | Phase 2, ngoài MVP1 |
| Máy local cô lập mạng | Nghiên cứu song song, ngoài MVP1 |

**Lưu ý quan trọng:** OCR được thiết kế đầy đủ ngay từ bây giờ (không hoãn thiết kế), nhưng **việc build/test thật có thể làm sau MVP1 demo đầu tiên**, vì use case ưu tiên nhất (GTPS) không cần đến nó. Tránh để việc build OCR làm chậm demo đầu tiên.

---

## 13. Assumptions — bổ sung

| Assumption | Kiểm tra ở đâu |
|---|---|
| Ngưỡng GATE 1 (đủ text hay không) phân loại đúng digital/scan | Đo trên fixture hỗn hợp, mục 11 |
| Ít nhất 1 trong 4 model bake-off đạt CER số đủ thấp để dùng được cho tài liệu tài chính | Chạy mục 10, chưa có số thật |
| scikit-image đủ để phân vùng trang scan mà không cần computer-vision phức tạp hơn | Đo trên fixture scan thật — nếu bố cục quá phức tạp (nhiều cột, bảng lồng), có thể cần heuristic mạnh hơn |
| Chi phí gọi Workbench cho nhánh OCR (nhiều lần gọi/trang do crop từng vùng) chấp nhận được | Đo cùng lúc với bake-off mục 10 |

Các assumption khác (client cung cấp mẫu, coverage 70-80%...) — không đổi từ v4.

---

## 14. Risk — bổ sung

| Rủi ro | Trạng thái | Mitigation |
|---|---|---|
| **PyMuPDF được đề xuất nhưng vi phạm quy tắc AGPL đã có từ đầu dự án** | ✅ Đã phát hiện, đã loại bỏ khỏi cân nhắc | Không dùng trừ khi Legal xác nhận chấp nhận AGPL hoặc công ty mua license thương mại Artifex |
| **Benchmark OCR online mâu thuẫn nhau, không đáng tin để chọn model** | 🔶 Đã xác nhận qua research | Bake-off thật theo mục 10, không suy diễn |
| **Độ chính xác OCR trên tài liệu tài chính tiếng Việt là ẩn số** | 🚫 Chưa đo | Ngưỡng confidence chặt hơn Classification Layer, bắt buộc người review khi confidence thấp |
| **Chi phí nhánh OCR cao hơn nhiều so với Classification** (crop nhiều vùng/trang, cần model full-size) | 🔶 Chưa đo | Đo song song với bake-off, cân nhắc máy local (mục 9) nếu chi phí quá cao |
| Các rủi ro khác (anchor quy mô lớn, SOP linh hoạt, KLax precedent...) | Không đổi | Xem chi tiết ở các bản trước |

---

## 15. Roadmap

| Bước | Việc | Ghi chú |
|---|---|---|
| 0 | Hỏi senior câu phân biệt pdfplumber + hỏi Poppler | Không đổi từ v4, vẫn ưu tiên cao nhất |
| 1 | MVP codebase — DOC only, use case GTPS | 3-5 ngày, không cần chờ OCR |
| 1b | Song song: chuẩn bị fixture scan thật + ground truth cho bake-off | Không chặn bước 1 |
| 2 | UAT testing use case GTPS | ~1 tuần |
| 3 | Build UI thật | Song song bước 1-2 |
| 4 | Chạy model bake-off OCR (mục 10) khi có fixture | Song song, không chặn demo đầu tiên |
| 5 | Present Partners | Giữa tháng 9 |
| 6 | Build OCR Branch thật (sau khi có kết quả bake-off) | Sau Partners, không phải trước |

---

## 16. Vận hành nhận dự án

Không đổi — xem `Foundation_Intake_Guideline_Scale_Pipeline.docx`.

---

## 17. Demo acceptance criteria

Không đổi từ v4 cho use case GTPS (DOC only, không cần OCR). Khi build OCR Branch xong (sau Partners), bổ sung tiêu chí riêng:
- [ ] GATE 1 phân loại đúng digital vs scan trên fixture hỗn hợp
- [ ] Model đã chọn qua bake-off có CER số dưới ngưỡng chấp nhận được (ngưỡng cụ thể xác định sau khi có số đo thật)
- [ ] Anchor ổn định cho element nguồn gốc OCR, đúng test ở mục 11

---

## 18. Việc cần làm ngay — thứ tự ưu tiên cuối cùng

1. Hỏi senior câu phân biệt pdfplumber + Poppler (mục 0, không đổi, vẫn treo).
2. Build MVP DOC-only cho use case GTPS — không phụ thuộc OCR.
3. Song song: thu thập fixture scan thật + gõ tay ground truth, chuẩn bị cho bake-off mục 10.
4. Khi có fixture: chạy bake-off, chọn model OCR chính thức bằng số đo thật.
5. Research Digital Gateway/Copilot (mục 8) — vẫn treo từ v4, cần xong trước Partners.
6. Build OCR Branch thật — **sau** khi demo GTPS đã chạy được, không làm trước.

---

*Tài liệu tham chiếu: `index.html` (mockup UI) · `Foundation_Market_Benchmark.md` · `Foundation_Intake_Guideline_Scale_Pipeline.docx` · `CRADL_OSS_Packages.xlsx` · `GTPS_Deck_Analysis.docx`.*
