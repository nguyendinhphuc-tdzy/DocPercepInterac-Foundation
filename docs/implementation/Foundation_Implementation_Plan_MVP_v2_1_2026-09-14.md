# FOUNDATION - KẾ HOẠCH TRIỂN KHAI MVP CẬP NHẬT
**Governed Document Transformation | Transfer Pricing Local File Roll-Forward**  
**Ngày cập nhật:** 14/09/2026  
**Repo baseline:** `master@41c92f7c775b12bf2dac5cf3091924d7dc293d24`  
**Trạng thái:** Kế hoạch triển khai v2.1, thay thế Implementation Plan 07/09/2026 ở cấp delivery plan. Không thay thế Foundation Contract v0.1.0 nếu chưa có phê duyệt contract change.

## 0. Tóm tắt điều hành

Foundation tiếp tục được xây như một **nền tảng chuyển đổi tài liệu có kiểm soát**, không phải AI Agent tự đọc rồi tự sửa Word/Excel. Kết luận mới sau audit repo và review với anh Khang là: **đơn vị công việc nên là Business Target / Change Case, không phải toàn document**. Document là nơi chứa evidence và là artifact nhận mutation; business decision phải được quản lý theo từng thay đổi.

MVP vẫn giữ nguyên nguyên tắc **vertical-complete**: không cắt bỏ Source Sufficiency, Evidence, Human Review, Native Identity, ApprovedChangeSet, Controlled Replay, Validation và Audit. Tuy nhiên business breadth được giới hạn vào 3-5 Business Targets thật để sớm tạo một lát cắt end-to-end có thể chạy.

Business Logic của Foundation được khóa theo nguyên tắc: một thay đổi chỉ có thể đi tới execution khi đồng thời xác định được Business Target, source/evidence đủ căn cứ, mapping/binding đủ rõ, operation được capability hỗ trợ, reviewer có authority đã phê duyệt và mọi dependency còn hiệu lực.

Working Logic tương ứng không xử lý document như một khối duy nhất. Hệ thống duy trì các record bất biến theo từng `BusinessTargetID`, tạo các assessment/proposal theo revision, và chỉ invalidate/re-run những record downstream bị ảnh hưởng khi source, policy, target binding hoặc user edit thay đổi.

### Kết luận delivery

- Backend không tiếp tục build theo kiểu hoàn thiện toàn bộ từng tầng rồi mới nối E2E. Từ sau B1.2R, delivery chuyển sang **vertical slice + architecture gates**.
- Frontend không mirror 8-10 backend module thành 8-10 màn hình. UI tập trung vào **Input / Review & Resolution / Result & Audit**, với Document Viewer làm evidence surface.
- Current Foundation Contract v0.1 đã hỗ trợ nhiều logic mới hơn tưởng tượng ban đầu: `REQUEST_MORE_SOURCE`, supersession, approval invalidation, partial/blocking workflow và release status đã có trong contract. Vì vậy **không mở Contract v0.2 chỉ để phục vụ UI**. Chỉ mở contract change khi working logic không thể biểu diễn đúng bằng record/event hiện có.
- Actual Final DOCX chỉ được gọi là Foundation-generated khi đã đi qua ApprovedChangeSet, Controlled Replay và Independent Validation. HTML demo không được fake capability này.

## 1. Baseline hiện tại sau audit repository

Repo được rà soát tại `master@41c92f7c775b12bf2dac5cf3091924d7dc293d24`. Phương pháp audit dùng ba lớp: 
(1) `docs/CURRENT_BASELINE.md`, ADR và Foundation Contract v0.1 làm nguồn thẩm quyền; 
(2) audit component-level đã có tại `docs/backend/B0_REPOSITORY_AUDIT.md`; 
(3) so sánh toàn bộ delta từ B0 accepted đến current master và đọc lại các file active được thêm/sửa trong B1 và Frontend U0. 
Cách làm này cho phép bao phủ repository-wide mà không coi code legacy hoặc prototype là kiến trúc hiện hành.

| Khu vực | Trạng thái xác nhận | Ý nghĩa |
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

### 1.1 Documentation drift cần xử lý ngay

`docs/PROJECT_PHASE.md` vẫn mô tả current B1 iteration là B1.0 + B1.1 + B1.2A, trong khi master đã chứa bounded DEFLATE, resource-safe preflight, B1.2R harness và representative qualification profile. Đây là **governance risk**, không chỉ là vấn đề tài liệu, vì agent/developer có thể đọc nhầm project state và mở workstream sai thứ tự.

### 1.2 Gate đang mở quan trọng nhất

Public representative summary vẫn là `CORPUS_NOT_PROVIDED / INSUFFICIENT_EVIDENCE / PROVISIONAL_CONTINUE`. Do đó B1.2R chưa đóng. Formal Run-002, SME fidelity review, coverage review và sanitized public conclusion vẫn là gate trước khi production Docling adapter được promote.

## 2. Business Logic mục tiêu

### 2.1 Đơn vị xử lý: Business Target / Change Case

Mỗi `BusinessTargetID` được theo dõi như một **Change Case** ở application/read-model layer. Change Case không phải execution authority và không cần trở thành object mới trong Frozen Contract. Nó là projection giúp backend và frontend nhìn cùng một business problem.

Một Change Case cần tổng hợp:
- target/business meaning;
- source requirements và source assessment hiện hành;
- evidence records/checks;
- mapping proposal hoặc ambiguity;
- native binding/capability;
- proposed/current value;
- human review state;
- dependency validity;
- execution/validation result nếu đã chạy;
- allowed actions được backend tính.

### 2.2 Source Request lifecycle

User flow yêu cầu `Request -> Intake -> Assessment -> Evidence -> Revised Proposal`. Contract v0.1 có thể biểu diễn bằng:
1. `ReviewDecision.REQUEST_MORE_SOURCE` + `requested_source_requirement_refs`;
2. `SOURCE_REQUESTED` AuditEvent;
3. DocumentVersion mới được intake;
4. SourceAssessment mới chạy deterministic;
5. EvidenceRecord / EvidenceCheck / EvidenceAssessment mới;
6. MappingProposal/ChangeProposal cũ được supersede nếu governing input thay đổi;
7. proposal revision mới đi lại review.

UI được phép hiển thị lifecycle trên như một business projection. Không tạo mutable "source request row" có thể rewrite history nếu chưa có nhu cầu vận hành/SLA đủ mạnh để justify contract object mới.

### 2.3 Reviewer Edit và Reassessment

`EDIT` là **application command**, không phải approval outcome. Khi reviewer sửa proposed value:
1. proposal đang review không được mutate in-place;
2. proposal cũ được supersede;
3. proposal mới được tạo ở trạng thái DRAFT/BLOCKED tùy evidence;
4. deterministic source/evidence checks chạy lại cho phần bị ảnh hưởng;
5. chỉ khi đủ evidence và binding thì proposal mới `READY_FOR_REVIEW`;
6. approval cũ không được reuse.

UI có thể hiển thị "Đang đánh giá lại", nhưng backend không được thêm enum mới chỉ để phục vụ copy UI.

### 2.4 Dependency graph và partial re-run

Dependency Graph là capability bắt buộc để thực hiện feedback "chỉ chạy lại phần bị ảnh hưởng". MVP không cần graph database. Backend tạo `DependencyIndex` từ các Ref hiện có và một số application-level dependency edges.

Ví dụ:
`DocumentVersion -> SourceAssessment -> EvidenceAssessment -> MappingProposal -> ChangeProposal -> ReviewDecision -> ApprovedChangeSet`

Khi một node upstream thay đổi, hệ thống:
- tạo assessment/proposal revision mới;
- đánh dấu downstream record cũ là superseded/invalidated theo contract;
- chỉ schedule lại AnalysisRun liên quan;
- giữ nguyên các Business Target không phụ thuộc upstream change.

### 2.5 Mapping Ambiguity

Mapping Ambiguity phải được resolve **trước** formal executable ChangeProposal/ApprovedChangeSet. UI có thể hiển thị một Change Case ở trạng thái "Mapping chưa rõ", nhưng không được coi đó là execution blocker ở Step 4 sau khi ChangeSet đã seal.

### 2.6 Processing Outcome và Release Status

Hai khái niệm tách riêng:
- **Processing Outcome**: tác vụ đã xử lý được bao nhiêu scope, ví dụ complete/partial/refused.
- **Release Status**: `WITHHELD -> ELIGIBLE -> RELEASED` theo contract.

Một partial artifact có thể tồn tại ở STAGED nhưng release vẫn WITHHELD. User có thể tải working draft chỉ nếu product policy cho phép và artifact được gắn nhãn rõ; Final Released DOCX chỉ xuất hiện sau independent validation và release gate.

### 2.7 Golden Output

Golden file là evaluation oracle, không phải workflow evidence. Golden comparison:
- không thay `SourceAssessment.outcome`;
- không thay `EvidenceAssessment.status`;
- không tự resolve conflict;
- không cấp execution authority;
- chỉ dùng để đo output alignment và root-cause diagnosis trong evaluation.

## 3. Working Logic end-to-end

```text
INPUT INTAKE
  -> VERSION + HASH + ROLE
  -> CAPABILITY PREFLIGHT
  -> SEMANTIC PERCEPTION + NATIVE ENRICHMENT
  -> TARGET CONTRACT / RULE PACK
  -> SOURCE REQUIREMENTS
  -> SOURCE ASSESSMENT
  -> EVIDENCE
  -> MAPPING / BOUNDED AI
  -> NATIVE BINDING
  -> REVIEW QUEUE
       -> APPROVE
       -> REJECT
       -> DEFER
       -> REQUEST_MORE_SOURCE
       -> EDIT -> SUPERSEDE -> REASSESS
  -> DEPENDENCY CHECK
  -> APPROVED CHANGESET
  -> CONTROLLED REPLAY
  -> INDEPENDENT VALIDATION
  -> BUSINESS RECONCILIATION
  -> PROCESSING OUTCOME
  -> RELEASE STATUS
  -> ARTIFACT + AUDIT
```

### 3.1 Target baseline cho output

Ba input business gồm Prior Local File, Master Template và Current-year Sources. Để Controlled Replay có một exact target binary:
- hệ thống đăng ký Master Template như `TEMPLATE`;
- tạo một byte-identical staged copy làm `TARGET` baseline, có DocumentVersion riêng và `derived_from` trỏ tới template version;
- prior-year Local File chỉ là historical source, không tự động được copy toàn bộ vào target;
- mọi carry-forward phải là rule-governed proposal;
- trong vertical slice đầu, output được phép là **Governed Working Draft / PARTIALLY_COMPLETED**, release WITHHELD nếu mandatory content chưa đủ.

Cách này cho phép tạo actual DOCX sớm mà không giả vờ rằng full Local File đã hoàn tất.

## 4. Scope vertical slice đầu tiên

| Business Target | Mục tiêu học | Exit |
|---|---|---|
| Kỳ báo cáo FY2024 | Text update đơn giản + source period | Đủ evidence, mapping rõ, replay text, validation pass. |
| NCP 6,08% | Derived fact + formula/value evidence + cross-region consistency | Xác minh numeric fact nhưng không tự suy ra arm's-length conclusion. |
| Mua nguyên liệu/công cụ | RPT amount trong bảng + current-year XLSX evidence | Replay một table-cell/text target có native locator rõ. |
| Regulatory wording / template-controlled text | Target Contract + template authority | Cập nhật wording đúng template, không tự diễn giải pháp luật. |
| Processing services conflict | Negative path: two current observations conflict | Không auto-select; Request More Source hoặc partial result; release vẫn WITHHELD nếu mandatory. |

Phạm vi này cố ý có cả positive path và negative path. MVP không được chỉ chứng minh happy path.

## 5. Kế hoạch triển khai theo phase

### P0 - Đồng bộ governance và khóa working logic
**Business outcome:** team có một source of truth chung trước khi tiếp tục code.

Backend:
- cập nhật `PROJECT_PHASE.md`;
- bổ sung ADR/decision record cho Change Case projection, dependency invalidation, source request projection, reviewer edit/reassessment và target baseline;
- xác nhận những phần nào dùng được Contract v0.1, phần nào thực sự cần contract change;
- khóa 3-5 Business Target của vertical slice.

Frontend:
- freeze HTML v4 làm UX research artifact;
- chuyển business flow thành acceptance criteria, không đưa fixture logic vào production store;
- xác định terminology tiếng Việt/English chính thức.

**Exit:** Business Logic + Working Logic được approved; không còn documentation drift.

### P1 - Đóng Representative Perception Gate
**Business outcome:** biết Docling có đủ semantic fidelity cho representative Local File hay không.

- chạy formal Run-002 trên approved private corpus;
- SME review theo exact observation digest;
- coverage review;
- sanitized public conclusion;
- nếu không đạt, phân loại semantic-required vs native-required loss;
- chỉ promote production adapter khi gate scoped pass.

**Exit:** quyết định rõ CONTINUE / CONTINUE_WITH_LIMITS / DO_NOT_PROMOTE theo scope.

### P2 - Target Contract + Rule Pack cho vertical slice
**Business outcome:** hệ thống biết cái gì cần đổi và cần bằng chứng gì.

- onboard Target Contract từ master template;
- tạo BusinessTargetID cho 3-5 target;
- define source requirement, rule type, mutability, validation rule;
- tạo Target baseline version;
- xác định mandatory vs non-blocking target.

**Exit:** mỗi target có contract, source requirement, rule và expected validation.

### P3 - Native Identity + Semantic Binding theo use case
**Business outcome:** mỗi candidate có exact execution target hoặc fail closed.

- triển khai thin DOCX native reader;
- XLSX native enrichment chỉ cho evidence cần formula/cell identity;
- qualify locator types cần thiết cho vertical slice;
- semantic -> native binding;
- ambiguity/duplicate/changed-binary negative tests.

**Exit:** target supported resolve uniquely; ambiguity route review/refusal.

### P4 - Source/Evidence Control Plane + Dependency Invalidation
**Business outcome:** hệ thống biết khi nào được tin dữ liệu và re-run đúng phần.

- SourceRequirementRegistry;
- SourceAssessment deterministic;
- Evidence checks: period, authority, freshness, consistency, value type/unit/formula khi cần;
- Source Request projection;
- DependencyIndex;
- invalidation engine;
- partial rerun scheduler.

**Exit:** thay một source chỉ invalidates đúng affected Change Cases; conflict không auto-resolve.

### P5 - Review Service + Frontend U1
**Business outcome:** reviewer xử lý exception/change thay vì đọc lại toàn file.

Backend:
- ChangeCase query/read model;
- allowed_actions;
- review decision service;
- reviewer authority;
- edit -> supersede -> reassessment;
- request more source.

Frontend:
- Inputs & Readiness;
- Review/Resolution Queue;
- change review card;
- source request/reassessment flow;
- right-side document/evidence viewer.

**Exit:** reviewer có thể hoàn thành full review flow trên backend truth, không local business state.

### P6 - ApprovedChangeSet + Controlled Replay
**Business outcome:** actual DOCX được thay đổi chỉ trong approved scope.

- materialize ApprovedChangeSet;
- hash/version/precondition check;
- replay adapter sau `ReplayExecutor`;
- typed operations chỉ trong qualified vocabulary;
- staging output;
- idempotency/concurrency/refusal.

**Exit:** selected supported changes được áp dụng vào target baseline và tạo STAGED DocumentVersion.

### P7 - Independent Validation + Business Reconciliation + Artifact
**Business outcome:** chứng minh output đúng và phần ngoài scope không bị thay đổi.

- package/schema validation;
- package and intra-part blast-radius diff;
- protected scope preservation;
- semantic re-perception;
- business reconciliation;
- validation report;
- release eligibility;
- output artifact lifecycle.

**Exit:** staged output được RELEASED hoặc WITHHELD với reason; không có ambiguous success.

### P8 - E2E Business Validation
- chạy real Local File case;
- so Manual vs General LLM vs Foundation;
- đo preparation time, reviewer time, rework, false acceptance, correct abstention, unauthorized change;
- test missing/conflict/edit/re-run.

**Exit:** chứng minh business value hoặc xác định hypothesis chưa đạt.

### P9 - Production Hardening
- access control, retention, data residency;
- malware/sandbox/external relationship/macro policy;
- telemetry/SLO;
- upgrade regression/SBOM;
- runbook và support model.

## 6. Frontend delivery track

Frontend không cần chờ toàn bộ backend nhưng mỗi action phải capability-gated.

| Frontend phase | Scope | Backend dependency |
|---|---|---|
| F0 | Clean shell, terminology, responsive, EN/VI architecture | Không có business authority; mock phải explicit |
| F1 | Input roles + real preflight/readiness | DocumentVersion + Preflight |
| F2 | Review Queue + Evidence Viewer | ChangeCase projection + Source/Evidence |
| F3 | Source Request + Edit/Reassessment + partial re-run | Review Service + DependencyIndex |
| F4 | Approved scope + execution progress | ApprovedChangeSet + Replay |
| F5 | Validation, Release, Final Artifact, Audit | Validator + release governance + artifact store |

## 7. Không mở Contract v0.2 nếu chưa cần

Current Contract v0.1 đã có:
- `REQUEST_MORE_SOURCE`;
- supersession;
- approval invalidation;
- `ReleaseStatus`;
- blocked/partial task progress;
- immutable revisions và audit events.

Do đó ưu tiên **application projections/services**:
- `ChangeCaseView`;
- `DependencyIndex`;
- `SourceRequestView`;
- `ReleaseDecisionView`;
- `AllowedActionSet`.

Chỉ đề xuất Contract v0.2 khi implementation chứng minh cần một shared durable object/lifecycle mà v0.1 không thể biểu diễn chính xác. Mọi contract change cần ADR, migration/compatibility test và update `CURRENT_BASELINE.md`.

## 8. Test & Evaluation Strategy

Test theo bốn lớp:
1. **Contract/State:** schema, transition, invariant, idempotency, supersession.
2. **Capability/Perception:** preflight, Docling representative, native locator/binding.
3. **Business:** source sufficiency, evidence, conflict, rules, dependency invalidation, review.
4. **Execution/Outcome:** replay, preservation, validation, reconciliation, release.

Non-negotiable:
- zero unauthorized business/structural change cho operation declared supported;
- stale/changed input phải block;
- Golden không được influence workflow verdict;
- reviewer edit phải invalidate approval;
- partial rerun không được invalidate unrelated target.

## 9. Business Metrics

- Preparation time.
- Reviewer time / change.
- Tổng cycle time.
- % Business Targets tự verified.
- % exception cần human.
- Source request turnaround.
- False acceptance.
- Correct abstention.
- Rework / fallback manual.
- Target mutation accuracy.
- Unauthorized change rate.
- Business reconciliation pass rate.
- Release-withheld rate theo root cause.

## 10. Definition of Done cho MVP cập nhật

MVP chỉ hoàn thành khi ít nhất một constrained Local File vertical slice:
- dùng real/anonymized documents;
- có exact input versions;
- đi qua preflight, perception, native binding, source/evidence gates;
- có real human review;
- materialize ApprovedChangeSet;
- tạo actual DOCX bằng Controlled Replay;
- pass independent validation hoặc bị WITHHELD có lý do;
- audit tái dựng được source -> assessment -> proposal -> decision -> execution -> validation;
- chứng minh business metric tốt hơn hoặc xác định rõ hypothesis không đạt.

## 11. Immediate backlog

1. Sync `PROJECT_PHASE.md` và project-status docs.
2. Formal Run-002 + SME review.
3. Khóa vertical-slice targets và Target Contract.
4. Build ChangeCase projection + DependencyIndex design.
5. Native Identity/Binding cho targets đã chọn.
6. Source/Evidence evaluators.
7. Review Service + frontend U1.
8. ApprovedChangeSet/Replay/Validation narrow path.
9. E2E evaluation.

## 12. Nguồn và evidence register

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
