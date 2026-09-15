# Foundation vertical slice — Learning scope v0.1

Ngày: 2026-09-14. Foundation v2; contract schema **0.1.0, frozen**.
Khóa đúng năm Business Targets dưới đây cho learning scope kế tiếp. Đây không
phải TargetContractDefinition/RulePack production, không xác nhận source authority
và không cấp quyền mutation. Tên v0.1 của scope không đổi version contract.

## Quy ước và guard chung

Các ID dưới đây là **PROVISIONAL_SCOPE_ID**, theo dạng BusinessTargetID chữ hoa
và dấu chấm của contract/ADR-002; chưa là registry entry được duyệt. B1.2R dùng
role evaluation riêng; không relabel manifest thành DocumentRole của business task.

Business task dự kiến có TEMPLATE, bản TARGET byte-identical riêng, CURRENT_SOURCE,
HISTORICAL_SOURCE và EVALUATION_ONLY cho golden. TARGET có version/hash/lineage
riêng; các definition dùng lại không chứa task-owned refs. TargetContractInstance
và TargetRegion bind đúng task và version sau khi native identity được qualified.

Mọi positive path đều có điều kiện: source sufficiency + evidence verification,
mapping/binding chính xác, operation-specific capability SUPPORTED, không protected,
human approval, sealed ApprovedChangeSet, Controlled Replay và independent validation.
Các operation nêu dưới chỉ là candidate trong vocabulary 0.1.0, chưa qualified.
Không fabricate locator để khóa scope. Period và freshness là hai policy riêng;
mọi deterministic evaluation phải pin evaluator/version/configuration.

Mandatory/non-blocking của **cả năm target vẫn OPEN**, chờ approved business policy.
Không hard-code amount BT3, benchmark, rounding threshold hay source precedence.
Golden không phải evidence. Không target nào được đánh dấu VERIFIED trong P0.

## BT1 — FY2024 Reporting Period

| Trường | Scope được khóa |
| --- | --- |
| Business label / ID | FY2024 Reporting Period — `VN_LOCAL_FILE.REPORTING.PERIOD` (PROVISIONAL_SCOPE_ID) |
| Mục đích | Cập nhật đúng kỳ FY2024 trong các vùng được liệt kê của Local File |
| Document roles | TARGET từ TEMPLATE; CURRENT_SOURCE xác định kỳ; HISTORICAL_SOURCE chỉ đối chiếu |
| Evidence requirement | Nguồn kỳ báo cáo được phê duyệt, version/hash, period và phạm vi các lần xuất hiện cần đổi |
| Source authority question | Ai xác nhận kỳ áp dụng và vùng nào cần giữ nguyên kỳ lịch sử? |
| Expected mapping | Một business period tới nhiều text regions có ngữ cảnh; phân biệt nhắc lại lịch sử |
| Native identity | B1.3 xác định exact DOCX run hoặc content control trên đúng version; B1.4 bind từng vùng |
| Candidate operation | REPLACE_RUN_TEXT hoặc REPLACE_SDT_TEXT, chỉ khi cấu trúc tương ứng qualified |
| Validation | Đúng FY2024 ở mọi vùng thuộc scope; giữ nguyên kỳ lịch sử và nội dung ngoài scope; package/intra-part/protection checks độc lập |
| Path | Positive, có điều kiện theo guard chung |
| Open assumptions | Approved period authority, danh sách vùng, mandatory policy và capability chưa chốt |
| Out of scope | Global find/replace; thay kỳ lịch sử; tạo locator theo fuzzy match |
| MVP learning | Period evidence, semantic mapping đơn giản, text replacement và cross-region validation |

## BT2 — Net Cost Plus (NCP) FY2024

| Trường | Scope được khóa |
| --- | --- |
| Business label / ID | NCP FY2024 — `VN_LOCAL_FILE.FINANCIAL.NCP` (PROVISIONAL_SCOPE_ID) |
| Mục đích | Đưa current-year derived fact vào các vùng NCP đúng scope |
| Document roles | TARGET; CURRENT_SOURCE FY2024; HISTORICAL_SOURCE kỳ trước; golden EVALUATION_ONLY |
| Evidence requirement | Candidate demo 6.08%, historical reference 14.18%; phải chứng minh từ actual approved evidence, formula lineage/input và displayed/cached value; không coi số demo là VERIFIED |
| Source authority question | Nguồn tính nào authoritative, kỳ nào, formula/cache nào và policy trình bày/rounding nào đã duyệt? |
| Expected mapping | Derived numeric business fact tới narrative/table regions; bảo toàn đơn vị phần trăm và ý nghĩa công thức |
| Native identity | Exact XLSX cell/range/formula identity phía evidence sau B1.3; exact DOCX run/control/simple cell phía target |
| Candidate operation | REPLACE_RUN_TEXT, REPLACE_SDT_TEXT hoặc REPLACE_SIMPLE_TABLE_CELL_TEXT; không sửa XLSX formula |
| Validation | Giá trị phần trăm đúng approved representation, consistency mọi vùng NCP, provenance formula/value, independent preservation checks |
| Path | Positive chỉ khi actual evidence đủ |
| Open assumptions | Authoritative current-year calculation, freshness, rounding/display policy, vùng đích và mandatory policy |
| Out of scope | Suy ra arm's-length conclusion từ 6.08%; dùng golden làm evidence; benchmark giả; formula recalculation engine |
| MVP learning | Derived fact, formula/value distinction, evidence trace và cross-region consistency |

## BT3 — Related-party Purchase of Raw Materials / Tools

| Trường | Scope được khóa |
| --- | --- |
| Business label / ID | RPT purchase of raw materials/tools — `VN_LOCAL_FILE.RPT.RAW_MATERIALS_TOOLS` (PROVISIONAL_SCOPE_ID) |
| Mục đích | Chuyển một current-year RPT amount từ structured FY2024 evidence vào đúng vùng Local File |
| Document roles | TARGET; CURRENT_SOURCE workbook FY2024; HISTORICAL_SOURCE đối chiếu |
| Evidence requirement | Exact source version, cell/range, business category, amount/currency, period, completeness và reconciliation theo policy được duyệt |
| Source authority question | Dòng/tổng nào phản ánh đúng raw materials/tools và nguồn nào là bản approved? |
| Expected mapping | Structured row/cell/range tới business concept rồi narrative/simple table cell |
| Native identity | Source cell/range chính xác và target run hoặc simple cell chính xác; không lấy Docling ID làm address |
| Candidate operation | REPLACE_SIMPLE_TABLE_CELL_TEXT hoặc REPLACE_RUN_TEXT khi qualified |
| Validation | Amount, currency, category và period khớp approved evidence; không đổi dòng/số khác; independent diff/protection checks |
| Path | Positive, có điều kiện |
| Open assumptions | Amount chưa formally confirmed; authority, aggregation, units, mapping và mandatory policy cần duyệt |
| Out of scope | Hard-code amount; tự gộp category; toàn bộ RPT schedule; sửa workbook |
| MVP learning | XLSX evidence → business concept → exact native target → numeric validation |

## BT4 — Template / Regulatory Controlled Wording

| Trường | Scope được khóa |
| --- | --- |
| Business label / ID | Current template controlled wording — `VN_LOCAL_FILE.TEMPLATE.CONTROLLED_WORDING` (PROVISIONAL_SCOPE_ID) |
| Mục đích | Áp dụng wording thuộc current Master Template đã được business owner phê duyệt |
| Document roles | TEMPLATE làm nguồn quy định target contract; TARGET bản copy có lineage; CURRENT_SOURCE nếu có approved wording instruction |
| Evidence requirement | Exact template/instruction version, vùng áp dụng và replacement wording được duyệt |
| Source authority question | Template owner nào duyệt phiên bản hiện hành và wording nào thay nội dung lỗi thời? |
| Expected mapping | Template-controlled rule tới đúng semantic region, không suy luận pháp lý tự do |
| Native identity | Exact DOCX run/control hoặc qualified simple cell; bảo toàn cấu trúc và scope ngoài vùng được duyệt |
| Candidate operation | REPLACE_RUN_TEXT, REPLACE_SDT_TEXT hoặc REPLACE_SIMPLE_TABLE_CELL_TEXT; chọn theo cấu trúc qualified |
| Validation | Đúng approved wording, obsolete wording chỉ được thay trong scope, giữ nguyên native structure/protected scope và các phần khác |
| Path | Positive, có điều kiện |
| Open assumptions | Template authority, wording/version, applicability và mandatory policy; có thể đã đúng trong baseline nên không cần mutation |
| Out of scope | Legal AI authority; insert/delete native structure; clone section; arbitrary rewrite. Nếu cần structural removal, giữ BLOCKED và mở gate operation riêng |
| MVP learning | Template là policy source, deterministic controlled wording và truthful no-change/refusal |

## BT5 — Processing Services Conflict

| Trường | Scope được khóa |
| --- | --- |
| Business label / ID | Processing services source conflict — `VN_LOCAL_FILE.RPT.PROCESSING_SERVICES` (PROVISIONAL_SCOPE_ID) |
| Mục đích | Biểu diễn negative path khi current sources có amount/meaning xung đột |
| Document roles | TARGET; các CURRENT_SOURCE có conflict; HISTORICAL_SOURCE chỉ ngữ cảnh; golden EVALUATION_ONLY |
| Evidence requirement | Giữ hai observations và provenance riêng trong private evidence; assessment CONSISTENCY/authority; yêu cầu nguồn giải trình có thẩm quyền |
| Source authority question | Hai observations có cùng business scope không, nguồn nào được duyệt, và tài liệu nào giải thích chênh lệch? |
| Expected mapping | Hai hypotheses vào cùng business concept; không tự chọn một số |
| Native identity | Capture/bind đúng vùng khi B1.3/B1.4 đủ; exact binding không làm source conflict biến mất |
| Candidate operation | Không dispatch khi conflict; sau nguồn hợp lệ và review mới có thể xét REPLACE_RUN_TEXT hoặc REPLACE_SIMPLE_TABLE_CELL_TEXT |
| Validation | Trước giải quyết: không ACS/replay cho change bị chặn, REQUEST_MORE_SOURCE có refs, history bất biến; sau này kiểm approved amount và preservation độc lập |
| Path | Negative: SourceAssessment COMPLETED/CONFLICTING, evidence chưa VERIFIED; partial processing chỉ cho subset độc lập đủ guard |
| Open assumptions | Các demo observations chưa được adjudicated; mandatory/non-blocking, authority, scope equivalence và remediation evidence còn mở |
| Out of scope | Public hóa private amount; dùng golden chọn số; auto-resolve conflict; human bypass blocking source |
| MVP learning | Source sufficiency refusal, explicit source request, partial rerun và WITHHELD nếu target mandatory |

## Điều kiện sang engineering gate kế tiếp

Cả năm target đã khóa về business/learning intent, chưa khóa production authority.
Không mở registry, RulePack, native identity, replay hoặc P2–P7 implementation
trong task này. Sau bound SME review và scoped B1.2R recommendation, xin explicit
gate cho B1.2B/B1.3; P2 cần approved source/mandatory policy và executable scope
phù hợp capability trước khi materialize TargetContract/RulePack.

Áp dụng [P0 working logic](../decisions/P0_BUSINESS_WORKING_LOGIC_2026-09-14.md).
Một subset pass không làm whole task releasable khi required target còn BLOCKED;
không gọi bản copy/prototype/golden là Foundation-generated Final DOCX.
