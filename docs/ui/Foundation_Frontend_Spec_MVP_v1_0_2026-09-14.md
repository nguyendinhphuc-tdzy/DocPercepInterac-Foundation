# FOUNDATION - ĐẶC TẢ FRONTEND MVP
**Professional Governed Review Workspace**  
**Ngày cập nhật:** 14/09/2026  
**Repo baseline:** `master@41c92f7c775b12bf2dac5cf3091924d7dc293d24`  
**Trạng thái:** Frontend Spec v1.0 cho U1+; kế thừa U0 principles nhưng thay information architecture theo business working logic đã validate qua HTML MVP và review stakeholder.

## 0. Product Goal

Frontend giúp reviewer làm ba việc chính:
1. cung cấp đúng input;
2. xử lý các change/exception thật sự cần quyết định;
3. nhận artifact + validation/audit result.

Frontend không phải:
- Word editor;
- technical pipeline dashboard;
- AI chat app;
- nơi tự tính source sufficiency/approval/release.

Backend luôn là authority.

## 1. UX Thesis

UI cần giữ visual simplicity của shell hiện tại nhưng **không mirror backend architecture thành nhiều screen**.

```text
GLOBAL NAVIGATION
  Home / Workspaces / History / Settings

WORKSPACE
  LEFT: Input / Work Queue
  CENTER: Business Decision
  RIGHT: Document / Evidence Viewer
```

Ba không gian business:
- **Input & Readiness**
- **Review & Resolution**
- **Result & Audit**

Technical Trace là progressive disclosure, không phải main navigation.

## 2. User Roles

### Người chuẩn bị hồ sơ / Associate
Mục tiêu:
- upload sources;
- xử lý standard change;
- request source;
- chuẩn bị working draft.

### Reviewer / Manager
Mục tiêu:
- xem material exceptions;
- approve/reject/defer;
- xác nhận mapping;
- kiểm tra release blockers.

### Auditor / Technical Support
Mục tiêu:
- xem exact lineage, locators, hashes, evaluator/config, audit timeline.
Technical detail chỉ hiện on-demand.

## 3. Information Architecture

### Global Navigation
- Trang chủ
- Không gian làm việc
- Lịch sử
- Cài đặt

### Workspace Header
- task/client/period;
- task status;
- release status;
- mock/live environment;
- Audit;
- Assistant;
- EN/VI.

### Left Rail
Context-sensitive:
- input roles ở Input;
- source requests/readiness ở Analyze;
- work queue ở Review;
- approved scope ở Result.

### Center
Luôn trả lời câu hỏi: **"User cần quyết định gì tiếp theo?"**

### Right Viewer
- original source/target document;
- jump to evidence/impact;
- DOCX/XLSX full reader;
- technical trace tab.

## 4. Screen 1 - Input & Readiness

### User goal
Cung cấp đúng source role, không cần hiểu internal modules.

Required roles:
- Master Template;
- Previous Local File;
- Current-year Sources;
- bổ sung sources tùy Source Requirement.

### UI behavior
Mỗi source card hiển thị:
- file name;
- role;
- period;
- preflight/read status;
- authority/scope khi backend có;
- blocker/remediation.

CTA:
- Thêm tài liệu;
- Thay tài liệu;
- Xem tài liệu;
- Bắt đầu phân tích.

"Continue" chỉ enabled theo `allowed_actions` backend.

## 5. Background Analyze state

Không tạo một technical Analyze screen riêng nếu user không cần.

UI hiển thị compact progress:
- Đang kiểm tra file;
- Đang đọc cấu trúc;
- Đang đánh giá nguồn;
- Đang chuẩn bị thay đổi.

Nếu blocked, hiển thị root cause + user action.

User vẫn đọc được original document dù semantic perception fail một phần.

## 6. Screen 2 - Review & Resolution Queue

Đây là center of gravity.

Queue categories:
- Sẵn sàng phê duyệt;
- Thiếu nguồn;
- Xung đột nguồn;
- Mapping chưa rõ;
- Cần đánh giá lại;
- Đã xử lý.

Filter/sort:
- materiality;
- section;
- root cause;
- source;
- status.

Không hiển thị AI confidence như verification.

## 7. Change Review Card

Main card phải có:

```text
Business Target
Section
Current Value
Proposed Value

SYSTEM VERDICT
  VERIFIED / BLOCKED / CONFLICTED / STALE / AMBIGUOUS

Evidence
  source document
  location
  observed value
  period / authority

AI Assessment
  explanation / hypothesis
  clearly auxiliary

Dependencies / Impact
  affected targets / occurrences

Allowed Actions
```

Actions từ backend:
- APPROVE
- REJECT
- DEFER
- REQUEST_MORE_SOURCE
- EDIT
- RESOLVE_MAPPING
- OPEN_EVIDENCE

Frontend không tự enable bằng local enum logic.

## 8. Source Request UX

Lifecycle hiển thị:
`Yêu cầu -> Tiếp nhận -> Đánh giá -> Bằng chứng -> Đề xuất mới`

### Yêu cầu
User thấy:
- thiếu gì;
- tại sao bắt buộc;
- source role/authority cần;
- target bị ảnh hưởng.

### Tiếp nhận
Upload source vào đúng request/task.

### Đánh giá
Backend runs SourceAssessment; UI chỉ hiển thị progress/result.

### Bằng chứng
Evidence mới xuất hiện với provenance.

### Đề xuất mới
Old proposal được mark superseded trong history; user review revision mới.

Không dùng modal "upload xong = verified".

## 9. Mapping Ambiguity UX

Mapping ambiguity nằm ở Review.

UI:
- show candidate target/section;
- highlight source evidence;
- highlight target candidates;
- explain why ambiguous;
- user chọn candidate hoặc defer/request info.

Selection does not directly mutate document.

## 10. Reviewer Edit & Reassessment UX

Flow:
1. user click Chỉnh sửa;
2. edit proposed business value/narrative;
3. reason required for material change;
4. Save tạo revised proposal;
5. UI state = "Đang đánh giá lại";
6. backend reruns affected checks;
7. proposal returns "Sẵn sàng rà soát" hoặc "Bị chặn";
8. Approve chỉ enabled after backend returns allowed action.

Không cho Edit -> Approve trong cùng client-only transaction.

## 11. Dependency Invalidation / Partial Re-run UX

Khi source/settings governed input thay đổi:
- banner nhỏ: "3 thay đổi cần đánh giá lại; 12 thay đổi vẫn giữ hiệu lực";
- queue marks affected cases;
- unaffected approvals remain;
- user không phải start over.

Click "Xem ảnh hưởng" mở dependency summary ở business level; technical refs ở drawer.

## 12. Screen 3 - Result & Audit

### Authorized scope
Show:
- number approved;
- blocked;
- deferred;
- execution-eligible.

Nếu `eligible=0`, user không được đi vào dead-end execution page; CTA quay lại Review.

### Processing Outcome
Hiển thị riêng:
- Chưa bắt đầu;
- Hoàn thành một phần;
- Hoàn thành;
- Từ chối.

### Release Status
Hiển thị riêng:
- Tạm giữ;
- Đủ điều kiện phát hành;
- Đã phát hành.

### Artifact
- Working Draft: chỉ nếu backend có real staged artifact.
- Final DOCX: chỉ enable khi backend says released/eligible theo policy.
- Không generate fake HTML download dưới tên DOCX.

## 13. Business Reconciliation View

Bảng theo fact:
- Business Fact;
- expected authoritative value;
- document occurrences/regions;
- result;
- blocker.

Ví dụ:
- Reporting period;
- Legal entity;
- NCP;
- Processing services;
- Benchmark conclusion;
- Regulation/template wording.

Click row -> right viewer jump to affected occurrence.

## 14. Golden Comparison UX

Chỉ có trong Evaluation/QA mode, không default production review.

Golden panel:
- Current workflow verdict;
- Expected reference;
- Match/difference;
- root cause remains unchanged.

Banner:
"Golden là nguồn đánh giá, không phải business evidence."

## 15. Document Viewer

### DOCX
- full reading surface;
- search;
- heading/table navigation;
- source highlight;
- target impact highlight;
- original language preserved.

### XLSX
- sheet tabs;
- virtualized grid;
- formula/value/both mode;
- cell address;
- source citation;
- merged/hidden/protected indication khi backend provides.

### Technical Trace
On demand:
- BusinessTargetID;
- SemanticReference;
- NativeLocator;
- binary hash;
- evaluator/config;
- proposal/review refs.

Không expose raw XML ở main review surface.

## 16. Assistant

Assistant là auxiliary:
- explain rule;
- summarize evidence;
- explain blocker;
- propose draft.

Assistant không:
- approve;
- mark verified;
- seal ChangeSet;
- execute;
- release.

Mọi AI output phải rõ label "AI assessment / proposal".

## 17. History & Audit

History không chỉ là recent tasks.

Task history:
- task/period;
- last activity;
- current blocker;
- processing outcome;
- release status;
- artifact availability.

Audit:
- immutable timeline;
- filter HUMAN / SYSTEM / AI / REPLAY_ENGINE / VALIDATOR;
- source request;
- supersession;
- review decision;
- invalidation;
- execution;
- validation;
- release.

## 18. Settings Scopes

### Personal / Workspace Settings
- language;
- density;
- viewer preferences.

### Task Settings
- user-selectable non-governance preferences;
- display/filter defaults.

### Governed Processing Configuration
- Target Contract;
- Rule Pack;
- evidence policies;
- capability profile.

Loại thứ ba không được edit như personal preference. Chỉ authorized workflow/config change.

## 19. Language & Terminology

Product phải hỗ trợ EN/VI switch toàn bộ interface chrome, status, actions, explanations.

Quy tắc:
- không dịch word-by-word;
- dùng tiếng Việt business;
- technical identifiers giữ nguyên khi cần audit;
- source document content giữ nguyên language gốc.

Ví dụ:
- Source Sufficiency -> "Mức độ đầy đủ và thẩm quyền của nguồn" trong explanation, nhưng technical drawer có thể giữ `SourceAssessment`.
- Release Withheld -> "Tạm giữ phát hành".
- ApprovedChangeSet -> "Phạm vi thay đổi đã được phê duyệt" trong UI chính, exact object name ở trace.

## 20. Responsive & Accessibility

Desktop-first:
- 1366x768 và 1280x800 là minimum professional target.
- panels collapsible;
- keyboard navigation;
- visible focus;
- WCAG AA contrast;
- no horizontal overflow trong main decision pane.

Tablet:
- Viewer thành drawer.

Mobile:
- read/review light mode; complex execution/reconciliation có thể recommend desktop nhưng vẫn không crash.

## 21. State Ownership

Zustand/client state chỉ giữ:
- panel open/close;
- selected case/doc;
- filters/search;
- local draft before submit.

Backend owns:
- task status;
- source/evidence verdict;
- allowed actions;
- proposal status;
- approval;
- execution;
- validation;
- release;
- artifact availability.

## 22. Loading / Empty / Error states

Không dùng disabled button im lặng.

Mỗi block state phải trả lời:
1. điều gì đang bị chặn;
2. vì sao;
3. scope ảnh hưởng;
4. user có thể làm gì;
5. phần nào vẫn tiếp tục được.

Examples:
- `SOURCE_CONFLICT`: show both values and request/reconcile actions.
- `SOURCE_MISSING`: show required source role.
- `MAPPING_AMBIGUITY`: show candidates.
- `EXECUTION_UNSUPPORTED`: explain manual path.
- `VALIDATION_FAILED`: quarantine result, show failed checks.

## 23. Frontend/API contract

Primary read APIs:
- readiness;
- ChangeCase list/detail;
- evidence source content;
- allowed actions;
- execution/validation/result;
- audit.

Mutation commands:
- upload;
- review decision;
- edit proposal;
- request source;
- resolve mapping;
- execute authorized set.

Client must not PATCH status/value directly.

## 24. Acceptance Criteria

| ID | Tiêu chí |
|---|---|
| FE-01 | User hoàn thành input với đúng source roles và hiểu blocker. |
| FE-02 | Review Queue group theo business exception, không theo technical module. |
| FE-03 | System verdict, AI assessment, Human decision được hiển thị tách biệt. |
| FE-04 | Edit bắt buộc đi qua reassessment trước approval. |
| FE-05 | Source Request lifecycle hiển thị đúng backend truth. |
| FE-06 | Mapping ambiguity resolve ở Review, không ở Execution. |
| FE-07 | Partial rerun chỉ đánh dấu affected cases. |
| FE-08 | Execution CTA không xuất hiện nếu zero eligible changes. |
| FE-09 | Processing Outcome và Release Status tách riêng. |
| FE-10 | Final DOCX chỉ download khi backend artifact thật tồn tại và policy cho phép. |
| FE-11 | Golden mode không thay workflow verdict. |
| FE-12 | DOCX/XLSX viewer đọc full content trong qualified display path. |
| FE-13 | EN/VI switch đổi toàn UI chrome, không dịch source content. |
| FE-14 | Mock/simulated mode luôn explicit. |
| FE-15 | Keyboard/focus/responsive pass. |

## 25. Migration từ frontend hiện tại

KEEP:
- visual shell;
- viewer components hữu ích;
- workflow intake UX concepts;
- generated contract types;
- server-authoritative intake pattern.

REFACTOR:
- `HomePage` positioning từ "Document Intelligence Workspace" sang governed workflow product;
- `workflowStore` sang v2 task/readiness API;
- workspace/agent stores thành UI state only;
- review/results components theo ChangeCase.

DEPRECATE:
- direct mutation UI/API;
- GPT/demo components có write authority;
- client-side readiness/approval calculations;
- recent history behavior không reopen exact task.

## 26. Nguồn

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
