# Build Plan — Document Perception & Interaction Foundation
## v4 — Sau buổi họp chuẩn bị Partners (10/08) + Build UI thật (không chỉ mockup)

*Chuẩn bị bởi Nguyễn Đình Phục · KPMG Vietnam Innovation · Tháng 8/2026*
*Thay thế bản v3. Tích hợp feedback của anh Quốc, anh Đạt trong buổi chuẩn bị trình bày Partners (giữa tháng 9). Bổ sung mục 7 — Build UI thật, dựa trên mockup `index.html` đã present.*

---

## 0. Cách đọc tài liệu này — và điều gì thật sự đổi so với v3

**Không đổi:** kiến trúc 2 lớp (Geometry tất định + Classification có rào), Element/Anchor schema, 3 chế độ output, Client Intake/Scale Pipeline, nguyên tắc AI-optional.

**Đổi thật sự — 6 điểm, tất cả đến từ buổi họp 10/08:**

1. **Ranh giới Foundation vs Application bị siết chặt hơn.** Anh Quốc chỉ rõ: Foundation chỉ trả lời 2 câu — "tương tác với file cho chuẩn" và "hỗ trợ tạo template". Extract/translate/mapping/comparison là **application layer**, không phải core. Code phải phản ánh đúng ranh giới này, không lẫn logic use-case vào core.
2. **Thêm bước Normalization** vào pipeline — chuẩn hóa định dạng (VND/VNĐ, ngày tháng...) trước khi vào Profile. Đây là gap thật, lấy từ kinh nghiệm pipeline cũ của anh Đạt.
3. **Template phải "động"** — không chỉ là schema tĩnh. User cần tự tạo biến, công thức dẫn xuất (V5 = V1+V4), kéo-thả layout. Đây là yêu cầu mới, chưa có trong kiến trúc `Profile` hiện tại — xem mục 9.
4. **Compliance status đổi:** `pdfplumber`/`pdf2image` **có thể không hề bị từ chối** — chỉ là gợi ý thay thế dựa trên kinh nghiệm cá nhân, chưa phải quyết định chính thức. Anh Quốc đang tự hỏi lại Risk và xin danh sách approved chính thức từ global.
5. **Thêm lựa chọn hạ tầng thứ ba:** máy local KPMG, cô lập mạng hoàn toàn, chạy model open/local, dành riêng cho khối lượng tài liệu không nhạy cảm (hóa đơn giấy/PDF, ước tính 30-40% khối lượng công việc toàn KPMG). Cần cost-out trước khi propose.
6. **Scope demo thu hẹp:** chỉ file DOC trước, 3 module (extract, translate, summarize), giữ nguyên tắc 80/20 — tránh "thành trung tâm nghiên cứu".

### 0.1 Việc cần làm ngay — cập nhật theo đúng thứ tự họp đã chốt

1. Research định vị so với **Digital Gateway** và **Copilot** (công cụ nội bộ đã có) — bắt buộc phải có trong Executive Summary trước buổi Partners.
2. Xác nhận lại với anh Quốc: `pdfplumber`/`pdf2image` có thật sự bị chặn không, hay chỉ là gợi ý — đừng tiếp tục giả định "bị từ chối" trong tài liệu.
3. Build MVP theo scope đã chốt: DOC only, extract + translate + summarize, 3-5 ngày.
4. Test 3-5 ngày với tài liệu thật, đo benchmark 3 kịch bản: không AI / AI general (Workbench) / AI fine-tune local.
5. Bắt đầu build UI thật (mục 7) song song, không chờ MVP core xong hẳn — hai việc độc lập nhau về mặt engineering.

---

## 1. Tổng quan phạm vi — siết lại theo đúng ranh giới anh Quốc nêu

**Foundation (core) chỉ gồm đúng 2 năng lực:**

| # | Năng lực | Mô tả |
|---|---|---|
| A | Tương tác file chuẩn | Đọc mọi element trong tài liệu, biết vị trí (Anchor), biết cách thao tác (đọc/ghi/xóa/thay thế) với từng element — không phụ thuộc use case |
| B | Hỗ trợ tạo template | Từ N mẫu input hoặc yêu cầu output, hỗ trợ user dựng ra một template (input và/hoặc output) có thể tái sử dụng |

**Application layer (KHÔNG phải core, xây trên Foundation):** extraction, translation, mapping, comparison, summarize. Mọi logic riêng của use case Tax/GPTS/Audit đứng ở tầng này, gọi vào Foundation qua API — **không viết trực tiếp vào code Layer 1-2**.

**Scope MVP1 (đã thu hẹp theo họp 10/08):** chỉ định dạng **DOC** (Word). XLSX/PDF là giai đoạn sau, không mở rộng đa định dạng ngay từ đầu — đúng chỉ đạo *"em đừng có tham vọng quá, đừng có làm tùm lum loại file, em làm file doc thôi."*

**3 module demo:** extract, translate, summarize. Không làm comparison/mapping phức tạp ở vòng demo đầu.

---

## 2. Tech stack — không đổi so với v3, xem chi tiết ở đó

`python-docx` (đã duyệt), `openpyxl`+`defusedxml` (đã duyệt, dùng sau khi mở rộng XLSX), geometry PDF (`pdfplumber`/`pdf2image` — trạng thái duyệt **cần xác nhận lại**, xem mục 0), `openai` client qua Workbench (đã duyệt), `pydantic`/`jsonschema`/`tenacity`/`cachetools` (đã duyệt), `Flask`/`Werkzeug` (đã duyệt) thay FastAPI.

**Vì MVP1 giờ chỉ cần DOC**, lớp geometry PDF không còn là phụ thuộc cứng cho việc bắt đầu — có thể build và demo trọn vẹn use case DOC trước khi câu hỏi pdfplumber được trả lời.

---

## 3. Kiến trúc pipeline — cập nhật thêm bước Normalization

```
file_intake → GEOMETRY LAYER (tất định)
                  → extract_geometry
                  → group_into_elements
                  → assign_anchors  ★ anchor cố định tại đây
                        │
                  [GATE: cần phân loại AI?]
                        │yes                    │no
                        ↓                        ↓
              CLASSIFICATION LAYER          type = UNCLASSIFIED
              (Workbench, có rào)                │
                        └──────────merge──────────┘
                                    ↓
                        ★ NORMALIZATION LAYER (MỚI)
                        chuẩn hóa định dạng: tiền tệ, ngày tháng,
                        đơn vị đo, viết hoa/thường — quy tắc do
                        KPMG định nghĩa, tất định, không AI
                                    ↓
                versioned_profile → map_and_act → output_and_trace
```

**Vì sao Normalization phải là bước riêng, không lồng vào Classification:** đây là logic **tất định, dựa trên rule KPMG tự định nghĩa** (ví dụ: "VNĐ", "VND", "đồng" → chuẩn hóa về "VND"), không cần AI, và phải áp dụng nhất quán cho mọi pipeline — tách riêng để dễ audit, dễ test, và để không lẫn với phần có AI.

```python
class NormalizationRule(BaseModel):
    field_pattern: str        # regex hoặc field_type để áp dụng rule
    rule_type: Literal["currency", "date", "unit", "text_case"]
    canonical_form: str       # định dạng chuẩn KPMG

def normalize(element: FoundationElement, rules: list[NormalizationRule]) -> FoundationElement:
    """Tất định 100%. Không gọi AI. Rule do KPMG định nghĩa và version hóa
    riêng — thay đổi rule không cần build lại pipeline."""
    ...
```

Phần còn lại của kiến trúc 2 lớp (Geometry/Classification), Anchor schema, resolution ladder — **giữ nguyên hoàn toàn từ v3**, không lặp lại ở đây.

---

## 4. Data model — Element/Anchor không đổi, Profile cần mở rộng (xem mục 9)

Schema `AnchorDOCX`/`AnchorXLSX`/`AnchorPDF`, `FoundationElement`, resolution ladder — giữ nguyên từ v3. Bổ sung field cho Normalization:

```python
class FoundationElement(BaseModel):
    anchor: Anchor
    text: str
    text_normalized: str | None = None   # MỚI — kết quả sau Normalization Layer
    type: ElementType
    confidence: float | None = None
```

---

## 5. Output engine — không đổi

3 mode (Clone & Replace / Profile-driven Fill / Task-shaped), Patch/Build mode, guaranteed floor, Cover & Note — giữ nguyên từ v3.

---

## 6. Ranh giới Foundation / Application — ví dụ cụ thể để tránh nhầm khi code

| Việc | Thuộc Foundation (core) | Thuộc Application (trên core) |
|---|---|---|
| Đọc DOCX, tách element, gán anchor | ✅ | |
| Phân loại heading/table/paragraph | ✅ | |
| Chuẩn hóa VND/VNĐ | ✅ | |
| "Dịch đoạn văn này sang tiếng Việt" | | ✅ — gọi Foundation lấy element, tự xử lý dịch, ghi lại qua Foundation |
| "So sánh 2 báo cáo TP" | | ✅ — gọi Foundation lấy 2 Element Index, tự làm Align/diff |
| "Map dữ liệu GPTS vào template Doc" | | ✅ — use case cụ thể, dùng Task-shaped output của Foundation |
| Template authoring (kéo-thả, biến, công thức) | Một phần — xem mục 9 | Một phần |

Quy tắc viết code: **module nào cần biết "đây là use case Tax" hay "đây là GPTS" thì không được nằm trong package core** (`perception/`, `adapters/`). Đặt ở package riêng (`applications/tax/`, `applications/gpts/`).

---

## 7. Build UI thật — dựa trên mockup `index.html` đã present, không dùng static HTML nữa

### 7.1 Đánh giá mockup hiện tại

Mockup đã làm đúng 4 việc quan trọng, giữ nguyên trong bản thật:
- **Một màn hình, 4 pane** (không phải 4 tab rời) — Input Viewer / Element Index / Intent-Mapping / Output+Trace, chia bằng splitter kéo được (`h-splitter`, `v-splitter`).
- **Đồng bộ hover xuyên pane** (`sync-target` + `data-sync`) — trỏ vào 1 dòng Element Index thì bounding box tương ứng sáng lên ở Input Viewer, và dòng trace tương ứng sáng lên ở Output+Trace.
- **Confidence bar + badge "Review"** cho element có độ tin cậy thấp — đúng cơ chế human-confirm đã thiết kế.
- **Trace log dạng timeline**, ghi rõ từng bước: Geometry Layer → Classification Layer → User Action → Output Engine — khớp đúng execution log đã định nghĩa ở backend.

Đây là spec tốt để chuyển thẳng thành component thật — không cần thiết kế lại UX, chỉ cần kỹ thuật hóa.

### 7.2 Tech stack Frontend

| Package | Vai trò |
|---|---|
| React + TypeScript | Nền tảng component |
| `zustand` | State toàn cục — đặc biệt cho cơ chế sync xuyên pane (mục 7.4) |
| `react-query` (`@tanstack/react-query`) | Gọi API Flask, cache, refetch |
| `pdfjs-dist` | Render PDF ở Input Viewer (khi mở rộng ngoài DOC) |
| `mammoth` hoặc render DOCX phía server thành ảnh/HTML | Hiển thị DOCX ở Input Viewer — DOCX không có renderer JS thuần tốt, cân nhắc convert phía backend |
| `xlsx` (SheetJS) | Hiển thị Output Excel-like ở Pane 4 |
| `react-resizable-panels` | Thay cho `h-splitter`/`v-splitter` tự viết bằng JS thuần trong mockup — thư viện có sẵn, ổn định hơn |
| Tailwind CSS hoặc giữ nguyên CSS variables đã có trong mockup | Styling — mockup đã có design token rõ ràng (`--primary: #00338D` theo màu KPMG), giữ nguyên token này khi chuyển sang component |

### 7.3 Component breakdown — map trực tiếp từ mockup

```
src/
  components/
    layout/
      DashboardLayout.tsx        # 4-pane grid + react-resizable-panels
      PaneHeader.tsx              # tiêu đề pane, dùng chung 4 nơi
    input-viewer/
      InputViewer.tsx             # Pane 1
      DocumentCanvas.tsx          # render trang tài liệu
      BoundingBoxOverlay.tsx      # vẽ bbox từ Anchor, nhận hover state
    element-index/
      ElementIndexTable.tsx       # Pane 2
      ConfidenceBar.tsx
      ReviewBadge.tsx
      ElementRow.tsx              # 1 dòng, phát sự kiện hover/click
    intent-mapping/
      IntentInput.tsx             # Pane 3, ô nhập yêu cầu ngôn ngữ tự nhiên
      MappingVisual.tsx           # sơ đồ source→dest, giữ animation mockup
      MappingNode.tsx
    output-trace/
      OutputGrid.tsx              # Pane 4, preview Excel-like bằng SheetJS
      TraceLog.tsx                # timeline, đọc từ /executions/{id}
      TraceItem.tsx
  state/
    syncStore.ts                  # zustand — thay cơ chế data-sync bằng JS thuần
  api/
    client.ts                     # react-query hooks gọi Flask backend
```

### 7.4 Cơ chế đồng bộ xuyên pane — thiết kế thật thay cho JS thuần trong mockup

Mockup dùng `data-sync` + query DOM trực tiếp (`querySelectorAll`) — cách này không scale khi component re-render theo React. Thay bằng `zustand` store dùng chung:

```typescript
interface SyncState {
  activeElementId: string | null;
  setActive: (id: string | null) => void;
}

const useSyncStore = create<SyncState>((set) => ({
  activeElementId: null,
  setActive: (id) => set({ activeElementId: id }),
}));

// Trong ElementRow.tsx, BoundingBoxOverlay.tsx, TraceItem.tsx — mọi component
// đều đọc `activeElementId` từ store này để tự quyết định có highlight hay không,
// thay vì query DOM chéo giữa các pane.
```

### 7.5 API contract — nối UI với backend Flask đã định nghĩa ở mục 8 (v3)

| UI cần | Endpoint |
|---|---|
| Input Viewer load tài liệu + bbox | `GET /documents/{id}/perceive` |
| Element Index hiển thị + sửa nhãn | `GET/PATCH /documents/{id}/elements/{index}` |
| Intent/Mapping gửi yêu cầu | Endpoint mới cần thêm: `POST /documents/{id}/intent` — nhận câu lệnh ngôn ngữ tự nhiên, trả về mapping đề xuất (source anchor → dest anchor) |
| Output + Trace | `GET /executions/{document_id}` |

**Việc cần làm thêm ở backend:** endpoint `/intent` chưa có trong build plan v3 — đây là API mới phục vụ đúng Pane 3, cần thiết kế riêng (nhận natural language, gọi Classification Layer/Workbench để diễn giải ý định, KHÔNG tự ý ghi file — chỉ trả về đề xuất mapping để user xác nhận qua UI).

### 7.6 Build order cho UI — làm song song với core, không phụ thuộc hoàn toàn

| Bước | Việc | Phụ thuộc backend? |
|---|---|---|
| 1 | `DashboardLayout` + 4 pane rỗng, dùng `react-resizable-panels` | Không |
| 2 | `ElementIndexTable` với dữ liệu giả (mock), giữ đúng cột như mockup | Không |
| 3 | `syncStore` + kết nối hover giữa Pane 1-2 | Không |
| 4 | Nối `ElementIndexTable` với API thật `GET /documents/{id}/perceive` | Có — cần Geometry Layer xong |
| 5 | `InputViewer` render DOCX thật (qua ảnh convert từ backend) + bbox thật | Có |
| 6 | `TraceLog` nối API `/executions` | Có — cần execution log implement xong |
| 7 | `IntentInput` + endpoint `/intent` mới | Có — cần Classification Layer + endpoint mới |
| 8 | `OutputGrid` nối kết quả ghi thật | Có — cần Output engine xong |

Bước 1-3 làm được ngay tuần này, không cần chờ backend — đúng tinh thần "làm song song" đã chốt trong họp.

---

## 8. Yêu cầu mới: Template phải "động" — Template Authoring

Đây là mở rộng scope thật, phát sinh từ họp 10/08, **chưa thiết kế chi tiết, chỉ đóng khung yêu cầu ở đây**:

**Yêu cầu từ anh Quốc:**
- User tự định nghĩa biến (`V1`, `V2`...) gắn với 1 hoặc nhiều Anchor.
- User tự tạo biến dẫn xuất bằng công thức (`V5 = V1 + V4`).
- User tự sắp xếp layout output bằng kéo-thả, merge cell tùy ý.
- Việc này **là trách nhiệm của user** (theo đúng lời anh Quốc: *"cái template của output thì đó chắc chắn là trách nhiệm của họ"*) — Foundation chỉ cung cấp **công cụ**, không tự động hóa việc tạo template.

**Đánh giá sơ bộ, chưa commit:**
- Đây gần như là một mini low-code designer — độ phức tạp cao hơn hẳn phần còn lại của MVP1.
- Đề xuất: **không đưa vào MVP1**. Ghi nhận là Phase 2, thiết kế riêng sau khi core (Foundation 2 năng lực ở mục 1) đã chứng minh được.
- Việc cần làm ngay: chỉ đảm bảo schema `Profile`/`ProfileField` (mục 3.4 build plan v3) **không thiết kế theo cách chặn khả năng mở rộng này sau** — cụ thể, thêm sẵn field mở:

```python
class ProfileField(BaseModel):
    field_name: str
    match_rule: Literal["label", "structural", "fingerprint"]
    anchor_pattern: dict
    formula: str | None = None   # MỚI, để trống ở MVP1 — chỗ dành cho công thức dẫn xuất sau này
```

---

## 9. Định vị cạnh tranh nội bộ — Digital Gateway & Copilot (bổ sung bắt buộc trước Partners)

Manager yêu cầu rõ: Executive Summary phải trả lời **Digital Gateway và Copilot hiện cover gì, thiếu gì, Foundation giải quyết đúng chỗ nào trong đó.** Đây là việc research cần làm, **chưa có câu trả lời trong tài liệu này** — liệt kê như một việc cần làm:

- [ ] Xác định phạm vi thật của Digital Gateway (nội bộ KPMG) — nó xử lý loại tài liệu gì, dừng ở bước nào.
- [ ] Xác định Copilot (Microsoft 365 Copilot hay công cụ nội bộ khác?) đang được dùng cho việc gì liên quan tài liệu.
- [ ] Viết 1 slide/đoạn so sánh 3 cột: Digital Gateway / Copilot / Foundation — theo đúng khung đã dùng cho Market Benchmark (đã có ở `Foundation_Market_Benchmark.md`), áp dụng lại cho đối thủ nội bộ.

---

## 10. Lựa chọn hạ tầng thứ ba — máy local cô lập mạng, chưa quyết định

Đề xuất của anh Quốc: 1 máy KPMG cấp, cô lập hoàn toàn khỏi mạng KPMG, chạy model local/open (kể cả model mã nguồn mở), dành riêng cho tài liệu **không nhạy cảm** (hóa đơn giấy/PDF — ước tính 30-40% khối lượng công việc toàn KPMG).

**Việc cần làm trước khi propose (do anh Quốc giao trực tiếp):**
1. Benchmark: model general (qua Workbench) thay thế được bao nhiêu % khả năng của model chuyên biệt (kiểu Docling) cho OCR/layout detection.
2. Tính chi phí Workbench (theo lượng gọi) so với chi phí phần cứng 1 máy cấp riêng.
3. Trình bày kết quả cho anh Đạt verify trước khi đề xuất chính thức.

**Chưa đưa vào MVP1** — đây là hướng nghiên cứu song song, không chặn tiến độ MVP.

---

## 11. Test plan — bổ sung Normalization test, còn lại giữ nguyên v3

Thêm vào checklist MUST PROVE (v3 mục 9.4):
- [ ] Normalization rule áp dụng nhất quán — test với 5+ biến thể format tiền tệ/ngày tháng, tất cả phải quy về đúng 1 canonical form
- [ ] Benchmark 3 kịch bản theo đúng yêu cầu cuối buổi họp: không AI / AI general (Workbench) / AI fine-tune local — đo cả độ chính xác lẫn tốc độ

Test 9.1 (geometry tất định), 9.2 (P3-04 anchor stability), 9.3 (classification consistency) từ v3 — giữ nguyên, không đổi.

---

## 12. Assumptions — cập nhật

Thêm vào bảng assumptions v3:

| Assumption | Kiểm tra ở đâu |
|---|---|
| Foundation/Application tách được sạch trong code, không rò rỉ logic use-case vào core | Code review trước khi merge — checklist theo mục 6 |
| Digital Gateway/Copilot thật sự có gap mà Foundation lấp được | Research mục 9, xong trước khi viết Executive Summary |
| pdfplumber/pdf2image thật sự "chờ duyệt" chứ không phải đã từ chối | Xác nhận lại với anh Quốc — đừng tiếp tục viết "bị từ chối" nếu chưa chắc |
| Model general (Workbench) đủ thay thế 1 phần Docling cho OCR/layout | Benchmark theo mục 10, trước khi propose máy local |

---

## 13. Risk — bổ sung case study KLax

Thêm vào bảng risk v3 (nhóm User Adoption):

| Rủi ro | Bằng chứng | Mitigation |
|---|---|---|
| **Độ trễ thích ứng khi quy định đổi khiến user quay về làm thủ công và không quay lại** | **Tiền lệ có thật:** dự án KLax của anh Quốc từng gặp đúng vấn đề này — template chính phủ đổi 3-4 lần/năm, kỹ thuật sửa được nhưng bị delay, user chuyển hẳn sang manual và không dùng lại solution | Thiết kế template "động" (mục 8) để user tự điều chỉnh mà không cần chờ dev — đây chính là lý do yêu cầu Template Authoring xuất hiện, không phải tính năng thừa |

---

## 14. Roadmap — cập nhật mốc thời gian theo đúng họp

| Bước | Việc | Thời lượng |
|---|---|---|
| 0 | Research Digital Gateway/Copilot + xác nhận lại trạng thái pdfplumber | Song song, trước Partners |
| 1 | MVP codebase — DOC only, extract+translate+summarize | 3-5 ngày (đã chốt lại, không phải 1 tuần như v3) |
| 2 | UAT testing + thu thập bộ test case | Thêm ~1 tuần |
| 3 | Build UI thật (mục 7), song song bước 1-2 | Không chặn MVP core |
| 4 | Chọn use case đơn giản nhất để demo, đo coverage thật | Cuối giai đoạn 2 tuần |
| 5 | Present Partners | Giữa tháng 9 |

**Lưu ý quan trọng đã nhắc lại 2 lần trong họp:** đây **chưa phải cam kết MVP hoàn chỉnh** — chỉ là "có gì đó để mọi người next step". Đừng hứa quá ở mốc 2 tuần.

---

## 15. Vận hành nhận dự án — không đổi

Xem `Foundation_Intake_Guideline_Scale_Pipeline.docx`.

---

## 16. Demo acceptance criteria — cập nhật

Giữ nguyên criteria kỹ thuật từ v3 (geometry tất định, P3-04, execution log). Bổ sung:
- [ ] Demo chỉ trên file DOC, không mở rộng định dạng
- [ ] Có bảng so sánh 3 kịch bản AI (không/general/fine-tune) với số đo thật, không chỉ mô tả lý thuyết
- [ ] Ngôn ngữ trình bày cho Partners: hạn chế thuật ngữ kỹ thuật, ưu tiên mô tả "dùng để làm gì" thay vì "dùng công nghệ gì"

---

*Tài liệu tham chiếu: `Foundation_Build_Plan_v3.md` (kiến trúc 2 lớp, data model, API — không lặp lại chi tiết ở đây) · `index.html` (mockup UI đã present, dùng làm spec cho mục 7) · `Foundation_Market_Benchmark.md` · `Foundation_Intake_Guideline_Scale_Pipeline.docx` · `CRADL_OSS_Packages.xlsx`.*
