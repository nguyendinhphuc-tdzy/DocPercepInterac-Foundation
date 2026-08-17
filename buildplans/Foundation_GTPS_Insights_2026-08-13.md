# Foundation × GTPS — Strategic Insights

**Ngày:** 13/08/2026  
**Ngữ cảnh:** MVP codebase audit + meeting GTPS (anh Huy) + next steps gửi anh Khang  
**Mục tiêu:** Định hướng ưu tiên build và demo cho use case Local File roll-forward

---

## 1. Insight chiến lược: GTPS đang kéo Foundation về “đúng chỗ”

Mentor muốn thấy **thị trường dừng ở đâu / Foundation advance ở đâu**.  
GTPS use case lại đang đòi hỏi đúng 3 capability Foundation claim sở hữu:

| GTPS cần (từ anh Huy) | Foundation mechanism | Trạng thái codebase (12/08) |
|---|---|---|
| Số FA + RPT **chính xác tuyệt đối** | Deterministic geometry + governed write (không để AI đụng số) | Geometry DOCX/PDF có; **XLSX chưa**; Output engine chưa |
| Narrative có thể review | Element Index reviewable + label “judgment” → exclude auto-write | Schema có; UI scaffold có; **chưa nối data** |
| Roll-forward năm trước → năm nay | Profile-driven Fill + Anchor ổn định qua structure drift | **Anchor = 0 dòng code** — IP cốt lõi vẫn trống |

**Kết luận:** Đây không còn là “demo generic document processing”. Đây là **first real acceptance test** cho thesis “substrate layer”. Nếu pass 2 tiêu chí số liệu của anh Huy → Foundation có case study nội bộ mạnh hơn bất kỳ benchmark public nào.

---

## 2. Gap nguy hiểm nhất trong next steps hiện tại

Next steps gửi anh Khang hợp lý về thứ tự, nhưng có **1 điểm lệch ưu tiên** so với codebase audit.

### Next steps đã gửi

1. Dùng fixture anh Huy  
2. Sửa Input Viewer nhận 2–3 file  
3. Viết thuật toán  
4–7. Working level + align + test  

### Thực tế codebase (12/08)

| Hạng mục | Status | Ảnh hưởng demo GTPS |
|---|---|---|
| `parse_xlsx()` | **0 dòng** | Chặn luôn Local File Excel trung gian (FA&RPTs) |
| `parse_docx()` / `parse_pdf()` | Có | OK cho FS PDF / LF DOCX |
| Anchor builder | **0 dòng** | Không chứng minh được “structure drift year-on-year” |
| Output engine (Patch/Fill) | **0 dòng** | Không ghi được số vào đúng ô / đúng đoạn |
| Flask API | **Rỗng** | Frontend 4-pane không nhận data thật |
| Multi-file intake | Frontend chưa hỗ trợ | Đúng như ghi ở bước 2 |

**Insight:**  
Sửa Input Viewer nhận 2–3 file (bước 2) **không tạo value** nếu backend chưa có:

- parse XLSX (file FA&RPTs)
- map số từ Excel → đúng locus trong Local File 2024
- write có lineage

UI multi-file là **cosmetic**. Thuật toán + `parse_xlsx` + 1 path write-back mới là **blocking path** cho demo GTPS.

---

## 3. Định nghĩa lại “thuật toán” cho đúng acceptance criteria

Anh Huy nói rõ 2 tiêu chí:

> Số liệu financial analysis + số liệu giao dịch liên kết phải **chính xác tuyệt đối**.  
> Narrative có thể cần review.

Vậy MVP demo **không cần** full Agent / full OCR / full classification trước.

### Minimum viable path cho GTPS

```
Local File 2023 (DOCX/PDF)  ──┐
Local File 2024 template     ──┼──→ Element Index (2 file)
FA&RPTs Excel (năm nay)      ──┘         │
                                         ▼
                              Profile / mapping rules
                                         │
                                         ▼
                              Patch write số vào đúng locus
                                         │
                                         ▼
                              Output + lineage (ô nào lấy từ đâu)
```

**Không cần AI** cho path số liệu.  
AI (nếu bật) chỉ cho narrative / classification — và phải có thể **tắt bằng feature flag**.

Đây khớp governance principle: *“AI never touches the file”* — đặc biệt quan trọng khi acceptance = absolute number accuracy.

---

## 4. Insight từ UI Spec v2 vs codebase

UI Spec v2 đổi framing:

> Document → Elements → Agent → Results

Codebase frontend vẫn scaffold theo tên cũ (InputViewer / ElementIndex / IntentMapping / OutputTrace).

**Insight:**  
Đừng refactor UI naming lúc này.  
Với GTPS, **Pane 3 (Agent) gần như không cần** trong demo đầu.

Thứ GTPS quan tâm:

| Pane | GTPS value | Ưu tiên demo |
|---|---|---|
| Document | Xem FS / LF gốc + bbox | Trung bình |
| Elements | Review số đã extract / map | **Cao** |
| Agent | Hỏi “tại sao số này” | Thấp (sau) |
| Results | Excel/DOCX output + trace lineage | **Cao nhất** |

Demo thắng khi reviewer GTPS nhìn **Results** và thấy:

> “Số FA dòng X = đúng số trong Excel FA&RPTs sheet Y, ô Z — có lineage”.

---

## 5. Đề xuất điều chỉnh thứ tự next steps

Giữ tinh thần email gửi anh Khang, nhưng **re-order theo blocking path**:

| # | Việc | Lý do | Phụ thuộc working level? |
|---|---|---|---|
| **1** | Lock fixture set: Excel FA&RPTs + LF 2023 + LF 2024 | Không có fixture chuẩn → mọi thuật toán đều ảo | Không |
| **2** | Viết `parse_xlsx()` + test trên đúng FA&RPTs | File trung gian quan trọng nhất của GTPS là Excel | Không |
| **3** | Định nghĩa mapping rules thủ công (hard-coded profile) cho 1–2 sheet FA/RPT | Chứng minh “số chính xác tuyệt đối” trước khi có Anchor đầy đủ | Không |
| **4** | 1 path write-back tối thiểu (Excel → đúng chỗ trong LF hoặc output worksheet) + lineage log | Đóng acceptance criteria anh Huy | Không |
| **5** | Multi-file intake (UI + API nhận 2–3 file) | Cần cho demo live | Không |
| **6** | Reach out working level | Hiểu edge case (merged cells, sheet lạ, narrative) | Có |
| **7** | Anchor + structure-drift test (P3-04 style) trên LF 2023 vs 2024 | IP thật của Foundation; làm sau khi số đã đúng | Không bắt buộc cho demo đầu |

**Khác với email gốc:**  
Bước “sửa Input Viewer multi-file” **lùi sau** `parse_xlsx` + mapping số.  
Vì UI đẹp mà số sai → GTPS reject ngay theo tiêu chí anh Huy.

---

## 6. Insight về “Profile” trong ngữ cảnh GTPS

Trong meeting foundation, Profile được nói như cấu hình tái sử dụng.  
Với GTPS roll-forward, Profile có thể cụ thể hóa thành:

```
Profile: "LocalFile_FA_RPT_v2024"
  - source: FA&RPTs.xlsx
      sheet: "Financial data" → map cells → LF sections
      sheet: "APT summary"    → map → RPT tables
  - target: LocalFile_2024.docx (hoặc worksheet trung gian)
  - rules: absolute match on labels + row headers
  - residual: narrative blocks → flag review
```

**Insight:**  
Đừng đợi Anchor “ổn định qua insert/delete” hoàn hảo mới demo.  
Với GTPS năm N → N+1, structure **gần giống** (roll-forward assumption).  
Hard-coded profile + label match đã đủ chứng minh value.  
Anchor full chỉ cần khi client đổi template mạnh hoặc multi-client scale.

---

## 7. Rủi ro cần nói thẳng với anh Khang / team

1. **Fixture quality**  
   Audit hiện tại: fixture DOCX là scan giả (65 ảnh), 1 PDF scan 0 text, chỉ 1 PDF digital tốt.  
   Nếu bộ file anh Huy cũng “dirty” (scan, merge cell loạn, named range thiếu) → cần làm sạch fixture trước khi claim accuracy.

2. **Poppler / pdf2image vẫn Waiting**  
   Geometry PDF digital (`pdfplumber`) đã chạy; render ảnh cho UI bbox có thể bị chặn policy.  
   Demo GTPS nên **ưu tiên path Excel + DOCX digital** trước, tránh phụ thuộc Waiting ticket.

3. **Working level meeting là bắt buộc, nhưng không phải blocker bước 1–4**  
   Email đúng hướng: làm phần fixture + thuật toán song song xin contact.  
   Nếu chờ working level xong mới code → mất momentum.

4. **UI Spec v2 (Agent-centric) vs GTPS reality**  
   Spec mới đẩy Agent lên trung tâm.  
   GTPS acceptance lại là **số liệu + lineage**.  
   Đừng để UI Spec kéo MVP sang chatbot trước khi path số liệu đóng.

---

## 8. Một câu định vị cho demo GTPS

Khi demo lại với GTPS / anh Huy, framing nên là:

> “Foundation không thay các bạn làm Local File.  
> Foundation cho phép lấy FA&RPTs năm nay map vào đúng chỗ trong package roll-forward,  
> với số liệu tuyệt đối chính xác và lineage đầy đủ — narrative để các bạn review.”

Câu này:

- Khớp acceptance criteria anh Huy  
- Khớp positioning “substrate, not Tax app”  
- Tránh over-promise end-to-end automation  

---

## 9. Việc nên làm trong 48–72h tới

1. **Inventory bộ file anh Huy** — liệt kê sheet name, named range, sample cells FA/RPT, so sánh LF 2023 vs 2024 structure diff.  
2. **`parse_xlsx()` + 3–5 unit test** trên đúng file FA&RPTs.  
3. **1 mapping table thủ công** (CSV/YAML cũng được): `source_cell → target_anchor/label`.  
4. **Script offline** (chưa cần Flask): đọc Excel → apply map → ghi output Excel/DOCX nhỏ + log lineage.  
5. **Chỉ khi 1–4 chạy được trên fixture thật** mới nâng multi-file UI.

---

## 10. Tóm tắt ưu tiên

| Ưu tiên | Việc | Lý do một dòng |
|---|---|---|
| P0 | Fixture lock + `parse_xlsx` | Không có thì không demo được số |
| P0 | Hard-coded map FA/RPT → output + lineage | Đóng acceptance “số tuyệt đối đúng” |
| P1 | Multi-file intake | Cần cho demo live 2–3 file |
| P1 | Working level contact | Edge case thật, không chỉ góc quản lý |
| P2 | Anchor stability / structure drift | IP dài hạn; không chặn demo số liệu đầu |
| P2 | Agent pane / full UI Spec v2 | Sau khi path số liệu đã tin cậy |

---

*Tài liệu này tổng hợp từ: codebase audit 12/08/2026, GTPS workflow analysis, meeting notes/transcript Foundation, UI Spec v2, và next steps đã gửi anh Khang.*
