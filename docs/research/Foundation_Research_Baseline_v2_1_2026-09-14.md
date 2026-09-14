# FOUNDATION - TỔNG HỢP NGHIÊN CỨU VÀ KIẾN TRÚC SẢN PHẨM CẬP NHẬT
**Governed Document Transformation | Local File Roll-Forward**  
**Ngày cập nhật:** 14/09/2026  
**Repo baseline:** `master@41c92f7c775b12bf2dac5cf3091924d7dc293d24`  
**Trạng thái:** Research baseline v2.1, tổng hợp evidence kỹ thuật, audit repository, HTML MVP và feedback sau review với anh Khang.

## 0. Kết luận nghiên cứu

**FACT:** Foundation Contract v0.1 đã tách rõ perception, business intent, evidence, human authority, native identity, execution và validation. Current repository đã có governance foundation, fail-closed preflight và representative qualification harness, nhưng chưa có production Native Identity, Source/Evidence engine, Review Service, Replay hoặc Independent Validation end-to-end.

**INFERENCE:** Problem lớn nhất hiện tại không còn là "có đọc được DOCX/XLSX không", mà là **có quản trị đúng một business change xuyên nhiều source, nhiều assessment và nhiều revision hay không**.

**RECOMMENDATION:** Định vị Foundation như một **lớp quản trị thay đổi có evidence cho tài liệu**. Document perception và Office engines là enabling technology. Differentiation nằm ở:
`Business Target -> Evidence -> Decision -> Dependency -> Controlled Change -> Validation -> Audit`.

**ASSUMPTION cần validate:** Exception-first review và partial re-run sẽ giảm reviewer effort đủ lớn để tạo ROI mà không tăng false acceptance.

## 1. Business Problem

Local File Roll-Forward tốn effort vì người làm phải đồng thời:
- hiểu cấu trúc file năm trước;
- nhận biết template hiện tại thay đổi gì;
- tìm current-year facts trong Excel/tài liệu hỗ trợ;
- quyết định source nào authoritative;
- giữ consistency của cùng một fact ở nhiều vùng;
- sửa Word mà không phá formatting/fields;
- review lại output.

General LLM giúp interpretation nhanh nhưng Claude experiment trước đây cho thấy các failure đáng chú ý: stale benchmark vẫn dẫn tới conclusion, NCP mới/cũ coexist, current sources thiếu nhưng model vẫn tiếp tục, và legal/FAR/transaction facts không nhất quán.

### Root cause

Không phải "AI chưa đủ thông minh". Root cause là bốn lớp bị trộn:
1. semantic perception;
2. business evidence;
3. human authority;
4. native mutation.

Nếu pipeline cho một component làm cả bốn, lỗi khó audit và khó biết phải sửa ở đâu.

## 2. Evidence từ current repository

Repo được rà soát tại `master@41c92f7c775b12bf2dac5cf3091924d7dc293d24`. Phương pháp audit dùng ba lớp: 
(1) `docs/CURRENT_BASELINE.md`, ADR và Foundation Contract v0.1 làm nguồn thẩm quyền; 
(2) audit component-level đã có tại `docs/backend/B0_REPOSITORY_AUDIT.md`; 
(3) so sánh toàn bộ delta từ B0 accepted đến current master và đọc lại các file active được thêm/sửa trong B1 và Frontend U0. 
Cách làm này cho phép bao phủ repository-wide mà không coi code legacy hoặc prototype là kiến trúc hiện hành.

| Khu vực | Current fact | Research implication |
|---|---|---|
| Governance / Contract | Foundation Contract v0.1.0 FROZEN; state engine, invariant engine, AuditEvent mechanics đã có | Không thay enum/object contract tùy tiện; mọi thay đổi shared contract cần ADR và versioning rõ. |
| Capability Preflight | B1.1 + resource-safe + bounded DEFLATE đã được merge trong qualified scope | Đây là capability mạnh nhất hiện tại; tránh tiếp tục hardening ngang nếu không có representative blocker mới. |
| Docling semantic perception | Synthetic qualification PROVISIONAL_CONTINUE; production adapter chưa có | Formal representative Run-002 + SME review vẫn là gate mở. |
| Representative profile | Profile qualification-only đã merge; private preflight CORE 7/7, CHALLENGE 3/3; chưa có public representative conclusion | Không được suy ra production semantic fidelity từ profile/capacity pass. |
| Native Identity / Binding | Có contract + port, chưa có production adapter | Đây là dependency chính để biến semantic candidate thành exact execution target. |
| Business control plane | SourceRequirement/Evidence/Rule/Proposal contracts có; engines/services production chưa có | Cần build theo BusinessTarget, không theo toàn document. |
| Human Review / ApprovedChangeSet | Contract mạnh, service/materialization chưa có | Frontend hiện chỉ có thể mock review; backend phải là authority. |
| Controlled Replay / Validation | Ports/contracts có; production executor/validator chưa có | Chưa thể tạo Foundation-generated Final DOCX thật. |
| Frontend | U0 principles/contracts accepted; code production vẫn chứa nhiều legacy store/API; clean HTML v4 là prototype UX | U1 nên migrate theo business workspace, không tiếp tục mirror technical pipeline. |

### Research finding mới: contract hiện tại mạnh hơn product prototype

Meeting feedback đề xuất Source Request lifecycle, reviewer edit/reassessment, partial rerun và outcome/release separation. Audit contract cho thấy:
- `REQUEST_MORE_SOURCE` đã là `ReviewOutcome`;
- `SourceAssessment` có lifecycle riêng và source business outcome riêng;
- `ChangeProposal` và `MappingProposal` có `SUPERSEDED`;
- `ApprovedChangeSet` có `INVALIDATED`;
- `FoundationTask` có `release_status`;
- `ReleaseStatus` đã tách `WITHHELD / ELIGIBLE / RELEASED`;
- Audit events đã có `SOURCE_REQUESTED`, `DECISION_SUPERSEDED`, `APPROVAL_INVALIDATED`, `RELEASE_WITHHELD`, `OUTPUT_RELEASED`.

**INFERENCE:** Phần lớn product state machine mới có thể được xây bằng application service + read model trên Contract v0.1, không cần mở rộng contract ngay.

## 3. Thesis cập nhật: Business Target / Change Case là unit of work

Document vẫn là immutable evidence/artifact boundary. Nhưng user không làm việc theo "document stage"; user xử lý các câu hỏi như:
- NCP FY2024 có đúng không?
- Processing service amount nào authoritative?
- Legal name có đủ current evidence chưa?
- Prior row này có nên remove không?

Do đó application layer nên tạo `ChangeCaseView` theo `BusinessTargetID`.

Change Case là projection, không phải execution authority. Nó hợp nhất:
- source requirement;
- source sufficiency;
- evidence;
- mapping;
- native binding;
- proposal;
- review;
- dependencies;
- execution/validation.

Điều này làm backend và frontend cùng nói một business language mà không phá frozen domain model.

## 4. Source Request và Manual Evidence

### 4.1 Source Request

User-facing lifecycle:
`Yêu cầu -> Tiếp nhận -> Đánh giá -> Bằng chứng -> Đề xuất mới`.

Working logic chuẩn:
- `REQUEST_MORE_SOURCE` chỉ ghi yêu cầu;
- file mới luôn trở thành immutable DocumentVersion;
- SourceAssessment cũ không bị sửa;
- assessment mới đánh giá authority/period/freshness/completeness;
- evidence mới tạo record mới;
- proposal cũ được supersede nếu applicability thay đổi;
- review cũ không được tự carry forward.

### 4.2 Manual input

Manual value không phải "override". Nếu user nhập một fact:
- actor và timestamp phải được ghi;
- target/period/scope phải rõ;
- source authority phải được xác định;
- rationale/supporting attachment phải trace được;
- deterministic Evidence Gate vẫn quyết định nó có đủ điều kiện không.

**RECOMMENDATION:** Nếu manual fact không gắn được authority phù hợp, nó chỉ là claim cần review, không phải VERIFIED evidence.

## 5. Dependency Graph và Partial Re-run

Meeting feedback "không chạy lại toàn bộ" tạo một research requirement mới.

### Business need

Nếu chỉ một source bổ sung thay đổi legal address, NCP đã verified từ financial workbook không nên bị re-run hoặc mất approval.

### Working thesis

Repository đã có nhiều explicit Ref giữa SourceAssessment, Evidence, MappingProposal, ChangeProposal, ReviewDecision và ApprovedChangeSet. Có thể tạo `DependencyIndex` từ các Ref này, không cần graph database.

### Invalidation examples

| Upstream thay đổi | Downstream phải invalidate/reassess | Không nên invalidate |
|---|---|---|
| Current source binary | assessment/evidence/proposal/review/ACS phụ thuộc source đó | target khác không dùng source |
| Target binary | NativeLocator/Binding, proposal, ACS của target | source evidence không phụ thuộc target binary |
| Rule Pack | RuleEvaluation và dependent proposal/review/ACS | unrelated document perception |
| Target Contract | Target regions, mapping, locator binding, dependent proposal | current source raw evidence |
| Reviewer Edit | proposal revision, evidence compatibility, prior approval | unrelated cases |
| AI model/prompt | AI assessment/hypothesis cần reproduce | deterministic source/evidence facts nếu unchanged |

**ASSUMPTION:** DependencyIndex từ immutable refs đủ cho MVP scale. Chỉ cân nhắc graph DB khi query/scale thực tế chứng minh cần.

## 6. Correctness không phải một score

Nghiên cứu cập nhật đề xuất bốn tầng correctness:

1. **Perception correctness:** hệ thống đọc đúng content/structure chưa?
2. **Evidence correctness:** source có đúng business meaning, period và authority chưa?
3. **Execution correctness:** có mutate đúng native object, đúng scope chưa?
4. **Release correctness:** output đã pass required validation/reconciliation và đủ điều kiện phát hành chưa?

Một model benchmark cao không thay được tầng 2-4.

## 7. Document Perception: current evidence

Docling-slim vẫn phù hợp làm semantic substrate, nhưng current public representative status chưa đủ để kết luận production.

B1 progress đã giải quyết nhiều infrastructure blockers:
- resource-safe OOXML preflight;
- bounded DEFLATE;
- narrow OPC Growth Hint;
- representative qualification-only capacity profile.

Nhưng đây chỉ làm corpus có thể đi vào semantic qualification. Nó **không chứng minh semantic fidelity**.

### Research gate kế tiếp

Run-002 phải trả lời:
- semantic structure có stable qua 3 runs không;
- narrative/table/hierarchy có đúng theo SME không;
- DOCX native-only constructs nào bị mất;
- XLSX formula/name/chart/drawing identity nào cần Native View;
- loss nào `SEMANTIC_REQUIRED`, loss nào `NATIVE_REQUIRED`.

## 8. Native Identity: scope theo use case

Không nên đặt objective "locate mọi object trong Office". MVP cần:
- locate exact objects cho selected Business Targets;
- explicit ambiguous/unsupported;
- operation-specific capability.

Ưu tiên:
- DOCX paragraph/run;
- SDT/content control nếu template có;
- simple table cell;
- bookmark khi reliable;
- XLSX cell/range/formula identity cho evidence.

Các construct complex như SmartArt, arbitrary drawing text, structural table clone chỉ mở khi có business need và qualification.

## 9. Mapping, AI và Evidence

AI được dùng khi semantic interpretation tạo value:
- semantic classification;
- candidate mapping;
- ambiguity analysis;
- narrative drafting.

AI không được:
- invent current evidence;
- chọn arbitrary target ngoài candidate set;
- approve itself;
- resolve source conflict bằng confidence;
- mutate file.

**Research principle:** Similarity/AI quyết định "xem đâu trước"; Evidence Gate quyết định "có được tin không".

### Mapping Ambiguity

Mapping ambiguity là review-stage problem. Nếu native target hoặc semantic association chưa resolve, executable ChangeProposal chưa đủ điều kiện. Không đẩy ambiguity xuống execution layer.

## 10. Reviewer Edit và Reassessment

Current `ReviewOutcome` không có EDIT, và điều này hợp lý: Edit không nên là approval decision.

**Working model:**
- user Edit là application command;
- proposal hiện tại superseded;
- revised proposal tạo mới;
- checks rerun theo dependency;
- proposal quay lại review khi đủ evidence.

UI label "Đang đánh giá lại" là projection; không bắt backend thêm status nếu frozen lifecycle đã biểu diễn được bằng DRAFT/BLOCKED + AnalysisRun.

## 11. Target Baseline và actual DOCX output

Research cũ đúng khi nói prior Local File không phải current Target Contract. Nhưng workflow ba input tạo một câu hỏi thực tế: Controlled Replay cần exact target binary nào?

### Recommendation

Master Template là contract/structure source. Hệ thống tạo một byte-identical `TARGET` baseline derived from Template. Prior Local File là historical source.

Mọi carry-forward vào target phải là governed proposal. Điều này dẫn tới hai loại artifact:
- **Working Draft / PARTIALLY_COMPLETED:** một số target đã execute, mandatory target khác unresolved; release WITHHELD.
- **Final Released DOCX:** mọi release gate bắt buộc pass.

Cách này cho phép MVP tạo actual DOCX sớm mà không giả full completeness.

## 12. Validation và Business Reconciliation

Post-output flow phải tách:
- Technical Validation: package/schema, locators, protected scope, blast radius.
- Semantic Validation: re-perception.
- Business Reconciliation: cùng một business fact xuyên document phải nhất quán.
- Release Governance: output có được release không.

Ví dụ NCP 6,08% phải được tìm ở mọi current-year target thuộc rule scope; nếu 14,18% còn tồn tại ở một vùng bắt buộc update, Validation phải fail dù target mutation chính xác.

## 13. Frontend research: UI là Decision Workspace

HTML v4 cho thấy visual shell clean hiệu quả hơn multi-screen technical UI. User không cần nhìn "Preflight Screen", "Mapping Screen", "Evidence Screen", "Replay Screen" như các module riêng.

### Product model

**Không gian 1 - Input / Readiness**
- source roles;
- file status;
- missing source;
- preflight blocker.

**Không gian 2 - Review / Resolution**
- change queue theo business target;
- verified / source conflict / missing / mapping ambiguity;
- side-by-side current/proposed/evidence;
- actions.

**Không gian 3 - Result / Audit**
- approved scope;
- processing outcome;
- validation;
- release status;
- artifact;
- audit.

Document Viewer ở bên phải là evidence surface xuyên suốt.

### Change-centric UI

Default card nên trả lời:
- đang nói về business fact nào;
- current value;
- proposed value;
- source/evidence ở đâu;
- System Verdict là gì;
- AI Assessment nói gì;
- dependencies/impact;
- user được phép làm gì.

## 14. Technology Adoption Map cập nhật

| Capability | Direction | Lý do |
|---|---|---|
| Semantic perception | ADOPT Docling-slim theo pin đã qualify | Không tự build generic parser |
| Native identity | BUILD thin sidecar | Business/replay identity không đủ trong Docling |
| Source/Evidence/Rule | BUILD | Đây là business differentiation |
| AI semantics | ADAPT/GOVERN | Value cao ở interpretation, authority thấp |
| Replay | ADOPT candidate behind interface | Không tự build full Office serializer |
| Validation | HYBRID | Cần độc lập với replay self-report |
| Dependency invalidation | BUILD application service/index | Core working logic cho partial rerun |
| Frontend state | ADAPT current shell, replace business logic | Backend remains authoritative |

## 15. MVP learning agenda

| Hypothesis | Cách validate | Failure signal |
|---|---|---|
| Representative perception đủ cho selected targets | Run-002 + SME | semantic-required loss cao |
| Change-centric review giảm effort | timed user test | reviewer vẫn phải đọc toàn file |
| Evidence gates giảm false acceptance | conflict/missing cases | system auto-accepts unsupported fact |
| Dependency partial rerun đúng | source/config mutation tests | unrelated cases bị invalidated |
| Native binding đủ an toàn | positive/duplicate/stale tests | fuzzy resolution hoặc wrong target |
| Controlled replay preserve scope | golden diff | unauthorized change > 0 |
| Business value > manual/general LLM | benchmark | cycle time/reviewer burden không tốt hơn |

## 16. Research gaps còn mở

- Formal representative semantic conclusion.
- SME validation của 3-5 Business Targets.
- Native locator stability sau benign edits.
- Exact target baseline/carry-forward policy cho broader Local File.
- Deterministic evidence policy cho source authority/conflict priority.
- Reviewer edit/reassessment UX với audit trace.
- Dependency invalidation correctness.
- Replay A/B trên selected operations.
- Artifact release policy cho partial working draft.
- Business benchmark với actual practitioners.

## 17. Kết luận kiến trúc cập nhật

**FINAL RESEARCH THESIS:** Foundation không tạo lợi thế bằng việc đọc nhiều format hơn hoặc dùng model mới hơn. Foundation tạo business value bằng việc quản trị từng thay đổi: biết target nào cần update, source nào đủ authority, AI được phép diễn giải ở đâu, dependency nào bị ảnh hưởng, ai có quyền approve, native object nào được phép mutate, và validation nào chứng minh output đúng.

Đây là hướng đủ thực tế để build MVP nhanh hơn nhưng vẫn giữ production integrity.

## 18. Nguồn và Evidence Register

| Nguồn | Vai trò |
|---|---|
| GitHub repository `master@41c92f7` | Current implementation evidence và source code audit. |
| `docs/CURRENT_BASELINE.md` | Architecture authority hiện hành. |
| `docs/contracts/*` + ADR-001...ADR-005 | Frozen contract, identity, state, authority và replay boundaries. |
| `docs/backend/B0_REPOSITORY_AUDIT.md` | Component-level migration/audit baseline. |
| B1 implementation/qualification reports + representative summary | Current preflight/perception evidence và open gates. |
| UI Product Principles + UI Backend Dependency Matrix | Accepted frontend authority boundary và capability availability. |
| Foundation Research Consolidated 07/09/2026 | Research/technical baseline trước meeting. |
| Foundation Implementation Plan 07/09/2026 | Plan baseline trước cập nhật. |
| Project Summary after Khang Review 10/09/2026 | Meeting decisions, corrections và product direction. |
| Foundation Clean MVP v4 | UX/prototype evidence; không phải production capability. |
