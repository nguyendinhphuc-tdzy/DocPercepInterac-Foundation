# P0 — Khóa Business Logic và Working Logic

Ngày: 2026-09-14. Foundation v2; Frozen Contract **0.1.0 không thay đổi**.
Trạng thái: quyết định working logic trong scope P0 được giao; không phải ADR mới,
không phải bằng chứng đã triển khai service hoặc hoàn thành B1.

## Authority và phạm vi

Theo chỉ thị cho đợt P0 này: Frozen Contract > CURRENT_BASELINE / accepted ADR >
accepted implementation evidence > tài liệu planning/spec/research hiện hành >
prototype. Các danh sách precedence cũ trong AGENTS, baseline và ADR index có
thứ tự khác; không dùng chúng để hạ quyền Frozen Contract hoặc sửa contract.
Đây là cách áp dụng chỉ thị hiện hành, không sửa lại quyết định lịch sử.

Nguồn chính: [domain model](../contracts/domain-model.md),
[status model](../contracts/status-model.md), [invariants](../contracts/invariants.md),
[event model](../contracts/event-model.md),
[Backend Spec](../backend/Foundation_Backend_Spec_MVP_v1_0_2026-09-14.md) và
[Implementation Plan](../implementation/Foundation_Implementation_Plan_MVP_v2_1_2026-09-14.md).
Các tên application view dưới đây không bổ sung ObjectType, enum hay API vào
Frozen Contract. Không phát hiện CONTRACT_GAP_CANDIDATE cần mở v0.2 trong P0.

## 12 quyết định làm việc

1. **Business Target / Change Case là đơn vị công việc ứng dụng.** Người dùng
   quyết định một vấn đề kinh doanh, với các vùng đích, nguồn, bằng chứng và
   blocker liên quan. Một target có thể cần nhiều thay đổi native; không đồng
   nhất BusinessTargetID với SemanticReference hoặc NativeLocator.

2. **ChangeCaseView là projection/read model.** View tổng hợp các Ref có revision
   từ contract; không có quyền thực thi. SourceRequestView, ReleaseDecisionView
   và AllowedActionSet cũng là application projection dự kiến, chưa triển khai.

3. **Yêu cầu nguồn đi qua Request → Intake → Assessment → Evidence → Revised
   Proposal.** REQUEST_MORE_SOURCE ghi ReviewDecision với requirement refs và
   SOURCE_REQUESTED event. Intake đăng ký version nguồn mới; SourceAssessment
   và EvidenceCheck đánh giá lại đúng policy, period và freshness. Upload hoặc
   người dùng trả lời không tự biến nguồn thành SUFFICIENT/VERIFIED. Giữ nguyên
   lịch sử trước đó; không tạo IN_REVIEW giả cho proposal vốn đang BLOCKED.

4. **Reviewer Edit là command, không sửa trực tiếp payload đã duyệt.** Supersede
   proposal cũ bằng revision/event hợp lệ; tạo proposal mới, reassessment rồi
   review mới. SUPERSEDED không chuyển ngược về DRAFT trên cùng lifecycle.
   ReviewDecision cũ và evidence máy/AI không bị viết lại. Nếu đã có authorization
   phụ thuộc nội dung cũ thì authorization đó phải bị invalidated trước khi dùng
   nội dung mới. Edit không bypass thiếu nguồn, protected scope hay unsupported.

5. **DependencyIndex hỗ trợ partial rerun.** Dựng quan hệ từ pinned Ref và
   dependency ứng dụng, gồm source, evaluator/configuration, rule, target version,
   binding, proposal, review, authorization và validation. Chỉ reassess các
   downstream thực sự phụ thuộc input đổi; không invalidate target độc lập chỉ
   vì cùng task. Tuy nhiên ApprovedChangeSet là nội dung niêm phong nguyên khối:
   một change bị ảnh hưởng làm cả set không còn dùng được; phần không bị ảnh
   hưởng cần authorization mới nếu muốn thực thi riêng. Khi binary TARGET đổi,
   mọi locator trên version cũ đều stale, kể cả target có nguồn độc lập.

6. **Resolve mapping ambiguity trước authorization thực thi.** Cụm “executable
   ChangeProposal” trong working plan chỉ mô tả readiness; Frozen Contract không
   có ChangeProposal nào có execution authority, kể cả status APPROVED. Mapping
   chưa rõ ở MappingProposal/view; proposal cụ thể chỉ được tạo khi đủ trường
   contract và phải BLOCKED nếu guard chưa đạt. Exact native resolution và
   fingerprint phải hợp lệ trước ApprovedChangeSet; không fuzzy fallback.

7. **Processing Outcome tách ReleaseStatus.** PARTIALLY_COMPLETED là nhãn tổng
   hợp ứng dụng, không phải TaskStatus mới. Khi một mandatory target bị chặn,
   subset đủ điều kiện có thể đi BLOCKED → READY_FOR_EXECUTION → EXECUTING →
   VALIDATING → BLOCKED theo guard hiện có; release toàn task vẫn WITHHELD.
   Replay SUCCEEDED không chứng minh validation PASSED; validation PASSED không
   tự cấp RELEASED. Chỉ policy đã duyệt mới xác định mandatory/non-blocking.

8. **Golden comparison không đổi workflow verdict.** Golden Output chỉ là
   EVALUATION_ONLY oracle. Không cấp source authority, giải quyết conflict,
   tạo evidence VERIFIED hoặc thay thế independent validation. Kết quả golden
   được trình bày riêng với verdict của workflow.

9. **Master Template → byte-identical TARGET baseline → governed changes.**
   Template và TARGET có DocumentArtifact/DocumentVersion riêng, role riêng,
   cùng hash khi byte-identical và lineage `derived_from` được ghi rõ. Copy
   không phải replay và không phải Final DOCX. Từ “staged copy” trong planning
   mô tả thao tác chuẩn bị, không tự gán DocumentStatus STAGED cho input TARGET;
   input đi REGISTERED → PREFLIGHTING → READY theo contract. Chỉ output của
   Controlled Replay và Independent Validation mới được gọi Foundation-generated,
   với release gate được kiểm riêng.

10. **Prior Local File là HISTORICAL_SOURCE.** Dùng cho đối chiếu kỳ trước và
    ngữ cảnh; không mặc nhiên là current-year authority hoặc target baseline.
    Current source, template và historical reference phải phân vai rõ ràng.

11. **Backend sở hữu allowed_actions và workflow truth.** Backend tính guard
    từ pinned refs, source/evidence, capability, protection, review và version;
    từ chối command stale kể cả UI từng hiển thị nút hợp lệ. Frontend không gọi
    replay service. ReplayRequest nội bộ chỉ có execution_id và
    approved_change_set_ref; không có locator/operation/payload override.

12. **Frontend là Decision Workspace.** Trình bày vấn đề kinh doanh, khác biệt
    đề xuất, nguồn/bằng chứng, lý do blocker, quyết định và next action. Chi tiết
    kỹ thuật phục vụ inspection/audit khi cần; prototype không quyết định state,
    source sufficiency hay native execution.

## Các gate chưa đóng

SME fidelity/coverage review của B1.2R phải hoàn tất trước forward recommendation.
B1.2B, B1.3 và B1.4 vẫn là gate riêng. Scope năm target được khóa tại
[vertical-slice scope](../implementation/FOUNDATION_VERTICAL_SLICE_SCOPE_v0.1.md);
source authority, mandatory policy, evaluator/configuration và target bindings
phải được phê duyệt trong gate tiếp theo, không suy ra từ prototype.

Không cần ADR mới để ghi những application decisions này. Nếu implementation
sau này chứng minh frozen primitives không đủ, dừng, ghi CONTRACT_GAP_CANDIDATE
với bằng chứng và migration impact; không sửa contract cho tiện UI.
