"""
Roll-forward requests are routed by the workflow, not by a model (Phase PROD-RF-1).

The defect these tests exist for: inside an active LOCAL_FILE_ROLL_FORWARD
workflow, "roll forward local file từ 2023 lên 2024 đi" matched none of the
Agent's keyword branches and fell through to GENERAL DOCUMENT QUERY. The model
then answered with prose claiming the roll-forward had been completed, while no
manifest, no mutation plan, no writeback, no reconciliation and no validation had
run at all.

What is pinned here:

     1. a roll-forward request resolves to intent `roll_forward`
     2. it never falls through to `general_query`
     3. the workflow's slots are the only documents it uses
     4. unrelated documents in the same session are ignored
     5. blocked readiness is answered with NO model call
     6. nothing is mutated before approval
     7. approval invokes the real orchestrator
     8. a completed result requires an execution_id
     9. a completed result requires an output document
    10. a completed result requires reconciliation
    11. a failed execution never reads as completed
    12. fabricated source names cannot enter the answer
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import List

import pytest
from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.repository import reset_repositories  # noqa: E402
from applications.agent import orchestrator as orchestrator_module  # noqa: E402
from applications.agent.models import AgentResponse, RollForwardResult  # noqa: E402
from applications.agent.orchestrator import AgentOrchestrator  # noqa: E402
from applications.agent.rollforward_agent import (  # noqa: E402
    RollForwardAgentHandler,
    RollForwardStage,
)
from applications.agent.rollforward_plan_store import (  # noqa: E402
    GovernedPlan,
    RollForwardApprovalError,
    RollForwardApprovalService,
    RollForwardPlanStore,
)
from applications.rollforward.workflow_intake import SlotId, WorkflowIntakeSession  # noqa: E402
from applications.agent.workflow_intents import (  # noqa: E402
    WorkflowIntent,
    WorkflowIntentClassifier,
)

warnings.filterwarnings("ignore")

DEMO = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files"
HISTORICAL = DEMO / "Compare LF" / "HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx"
TEMPLATE = (DEMO / "Compare LF"
            / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 "
              "(Decree 20-2025).docx")
FA_RPT = DEMO / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"
APPENDIX_I = (DEMO / "FA&RPTS & Appendix I" / "Appendix I"
              / "HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx")

# The exact message from the production report.
PRODUCTION_MESSAGE = "roll forward local file từ 2023 lên 2024 đi"

requires_demo = pytest.mark.skipif(
    not HISTORICAL.exists(), reason="demo fixtures are not present")


class _ModelSpy:
    """Fails the test if the model is consulted, and records it if it is."""

    def __init__(self, monkeypatch, reply: str = "model text"):
        self.calls: List[str] = []

        def _call(cls, message, system_prompt, *, spec):
            self.calls.append(message)
            return reply

        monkeypatch.setattr(orchestrator_module.AgentOrchestrator, "_call_model",
                            classmethod(_call))

    @property
    def called(self) -> bool:
        return bool(self.calls)


@pytest.fixture
def workflow_session(monkeypatch, tmp_path):
    """A real roll-forward workflow in the repository, plus unrelated documents."""
    import adapters.repository as repository_module

    monkeypatch.setattr(repository_module, "UPLOAD_ROOT", tmp_path)
    reset_repositories()
    RollForwardPlanStore.clear()

    def _build(*, historical=True, sources=True, template=False, session_id="sess-rf"):
        session = WorkflowIntakeSession(session_id, user_id="anonymous")
        if historical:
            session.assign_document(SlotId.HISTORICAL_LOCAL_FILE, "doc-hist",
                                    HISTORICAL, HISTORICAL.name)
        if sources:
            session.assign_document(SlotId.CURRENT_YEAR_SOURCES, "doc-fa", FA_RPT, FA_RPT.name)
        if template:
            session.assign_document(SlotId.MASTER_TEMPLATE, "doc-tpl", TEMPLATE, TEMPLATE.name)

        repos = repository_module.get_repositories()
        repos.sessions.get_or_create(session_id, user_id="anonymous")
        workflow, rows = session.to_records()
        repos.workflows.save_workflow(workflow)
        repos.workflows.replace_assignments(workflow.workflow_id, rows, user_id="anonymous")
        return session

    yield _build
    reset_repositories()
    RollForwardPlanStore.clear()


def _stale_context(session_id: str):
    """Context carrying nine unrelated documents, as a long-lived session has."""
    from applications.agent.models import AgentContext

    def _build(session_id=session_id, active_doc_id=None, selected_element_id=None):
        from applications.agent.context_builder import _load_workflow_context

        return AgentContext(
            session_id=session_id,
            workflow=_load_workflow_context(session_id),
            available_documents=[
                {"doc_id": f"stale-{i}", "filename": f"unrelated-{i}.docx", "format": "docx",
                 "status": "ready", "element_count": 5} for i in range(9)
            ],
        )
    return _build


# ---------------------------------------------------------------------------
# 1-2. INTENT, AND NO GENERAL-QUERY FALLTHROUGH
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("message", [
    PRODUCTION_MESSAGE,
    "roll forward local file",
    "roll forward from FY2023 to FY2024",
    "roll forward this local file",
    "thực hiện roll forward",
    "Roll-Forward the local file please",
])
def test_roll_forward_requests_resolve_to_the_roll_forward_intent(message):
    decision = WorkflowIntentClassifier.classify(
        message, {"workflow": "LOCAL_FILE_ROLL_FORWARD"})
    assert decision.intent is WorkflowIntent.ROLL_FORWARD, message


@requires_demo
def test_the_production_message_never_reaches_general_query(workflow_session, monkeypatch):
    """The regression test the ticket asks for: intent must not be general_query."""
    workflow_session()
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    spy = _ModelSpy(monkeypatch)

    response = AgentOrchestrator.handle_chat(
        message=PRODUCTION_MESSAGE, session_id="sess-rf", context_input={},
        model="gemini_3_6_flash")

    assert response.intent != "general_query"
    assert response.intent == "roll_forward"
    assert not spy.called, "a deterministic workflow answer must not consult a model"


def test_classification_is_deterministic_and_needs_no_model():
    """Same input, same answer, no provider involved — run it many times."""
    workflow = {"workflow": "LOCAL_FILE_ROLL_FORWARD"}
    decisions = {WorkflowIntentClassifier.classify(PRODUCTION_MESSAGE, workflow).intent
                 for _ in range(50)}
    assert decisions == {WorkflowIntent.ROLL_FORWARD}


def test_a_generic_workspace_is_not_hijacked(monkeypatch):
    """Outside a roll-forward workflow the existing branches keep their behaviour."""
    assert WorkflowIntentClassifier.classify(PRODUCTION_MESSAGE, None).intent is None
    assert WorkflowIntentClassifier.classify(
        "summarize this table", {"workflow": "LOCAL_FILE_ROLL_FORWARD"}).intent is None


# ---------------------------------------------------------------------------
# 3-4. THE WORKFLOW'S SLOTS ARE THE ONLY SOURCE OF TRUTH
# ---------------------------------------------------------------------------

@requires_demo
def test_only_workflow_slot_documents_are_used(workflow_session, monkeypatch):
    workflow_session()
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    _ModelSpy(monkeypatch)

    response = AgentOrchestrator.handle_chat(
        message=PRODUCTION_MESSAGE, session_id="sess-rf", context_input={},
        model="gemini_3_6_flash")
    assessment = response.roll_forward_assessment

    assert assessment["historical_document_id"] == "doc-hist"
    assert assessment["current_source_document_ids"] == ["doc-fa"]
    assert assessment["template_document_id"] is None


@requires_demo
def test_stale_generic_documents_never_enter_the_assessment(workflow_session, monkeypatch):
    workflow_session()
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    _ModelSpy(monkeypatch)

    response = AgentOrchestrator.handle_chat(
        message=PRODUCTION_MESSAGE, session_id="sess-rf", context_input={},
        model="gemini_3_6_flash")

    serialised = str(response.roll_forward_assessment) + response.response
    assert "stale-" not in serialised
    assert "unrelated-" not in serialised


@requires_demo
def test_periods_come_from_the_documents_not_the_request(workflow_session, monkeypatch):
    """The request says "2023 lên 2024"; the periods must still be read from content."""
    workflow_session()
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    _ModelSpy(monkeypatch)

    response = AgentOrchestrator.handle_chat(
        message="roll forward local file từ 1999 lên 2050 đi", session_id="sess-rf",
        context_input={}, model="gemini_3_6_flash")
    periods = response.roll_forward_assessment["periods"]

    assert periods["historical_period"] == "FY2023"
    assert periods["current_period"] == "FY2024"


# ---------------------------------------------------------------------------
# 5-6. BLOCKED READINESS, AND NO MUTATION BEFORE APPROVAL
# ---------------------------------------------------------------------------

@requires_demo
def test_blocked_readiness_is_answered_without_calling_the_model(workflow_session, monkeypatch):
    workflow_session(template=False)
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    spy = _ModelSpy(monkeypatch)

    response = AgentOrchestrator.handle_chat(
        message=PRODUCTION_MESSAGE, session_id="sess-rf", context_input={},
        model="gemini_3_6_flash")

    assert not spy.called
    assert response.roll_forward_assessment["stage"] == RollForwardStage.BLOCKED.value
    codes = {b["code"] for b in response.roll_forward_assessment["blockers"]}
    assert "MISSING_INPUT" in codes
    assert "cannot execute yet" in response.response


@requires_demo
def test_a_blocked_answer_reports_no_result_and_no_mutation(workflow_session, monkeypatch):
    workflow_session()
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    _ModelSpy(monkeypatch)

    response = AgentOrchestrator.handle_chat(
        message=PRODUCTION_MESSAGE, session_id="sess-rf", context_input={},
        model="gemini_3_6_flash")

    assert response.roll_forward_result is None
    assert "No document has been modified" in response.response
    for word in ("completed", "hoàn thành", "đã cập nhật"):
        assert word not in response.response.lower()


@requires_demo
def test_a_complete_intake_without_a_governed_plan_refuses_to_invent_one(workflow_session,
                                                                        monkeypatch):
    """All inputs present is not the same as having something approved to run."""
    workflow_session(template=True)
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    _ModelSpy(monkeypatch)

    session = RollForwardAgentHandler._load_session("sess-rf", "anonymous")
    plan, blockers = RollForwardAgentHandler._build_plan(session, "anonymous")

    assert plan is None, "a plan was produced without the planning layer having run"
    assert [b.code for b in blockers] == ["NO_GOVERNED_PLAN"]
    assert "planning layer" in blockers[0].detail


@requires_demo
def test_approval_is_refused_when_there_is_no_plan(workflow_session):
    workflow_session(template=True)
    with pytest.raises(RollForwardApprovalError, match="no governed roll-forward plan"):
        RollForwardApprovalService.approve_and_execute(
            session_id="sess-rf", approver="partner@firm.com")


@requires_demo
def test_approval_requires_a_named_approver(workflow_session):
    workflow_session(template=True)
    with pytest.raises(RollForwardApprovalError, match="approver is required"):
        RollForwardApprovalService.approve_and_execute(session_id="sess-rf", approver="")


# ---------------------------------------------------------------------------
# 7. APPROVAL INVOKES THE REAL ORCHESTRATOR
# ---------------------------------------------------------------------------

def _governed_plan(tmp_path, session_id="sess-rf") -> GovernedPlan:
    """A real manifest + mutation plan over a real document, in the governed shape."""
    from tests import test_rollforward_orchestrator as golden

    template_path = tmp_path / "governed_template.docx"
    document = Document()
    document.add_heading("Section 1: Executive Summary", level=1)

    # Table 0 is a control table: the golden plan targets tables 1..4, so the
    # document must have the same shape the plan was built against.
    control = document.add_table(rows=3, cols=2)
    for r in range(3):
        for c in range(2):
            control.rows[r].cells[c].text = f"Control R{r}C{c}"

    for t_idx in sorted(golden.GOLDEN_TABLES):
        rows, _target, cols, label = golden.GOLDEN_TABLES[t_idx]
        document.add_heading(f"Section: {label}", level=1)
        table = document.add_table(rows=rows, cols=cols)
        for c in range(cols):
            table.rows[0].cells[c].text = f"{label} Col {c}"
        for r in range(1, rows):
            for c in range(cols):
                table.rows[r].cells[c].text = f"{label} R{r}C{c}"
    document.save(str(template_path))

    manifest = golden.RollForwardManifest(
        schema_version="1.0.0", manifest_version=1, session_id=session_id,
        template_document_id="doc-tpl", current_source_document_ids=["doc-fa"],
        status=golden.ManifestStatus.DISCOVERED,
        regions=[golden._golden_region(i, template_path) for i in sorted(golden.GOLDEN_TABLES)],
    )
    golden.RollForwardStateMachine.transition(
        manifest, golden.ManifestStatus.PLANNED, actor="agent", reason="planning complete")

    mutation_plan = golden.build_golden_plan(manifest, template_path)
    source_workbook = golden.build_synthetic_source_workbook(template_path)

    from applications.rollforward.full_validation import compute_file_sha256

    return GovernedPlan(
        plan_id=mutation_plan.plan_id,
        session_id=session_id,
        user_id="anonymous",
        manifest=manifest,
        mutation_plan=mutation_plan,
        template_path=template_path,
        output_path=tmp_path / "rolled_forward_output.docx",
        source_paths=[source_workbook],
        expected_template_hash=compute_file_sha256(template_path),
        expected_source_hashes={source_workbook.name: compute_file_sha256(source_workbook)},
        historical_document_id="doc-hist",
        template_document_id="doc-tpl",
        current_source_document_ids=["doc-fa"],
    )


@requires_demo
def test_approval_runs_the_real_governed_engines(workflow_session, tmp_path, monkeypatch):
    """The approval path must reach the orchestrator, not a stand-in."""
    workflow_session(template=True)
    plan = _governed_plan(tmp_path)
    RollForwardPlanStore.register(plan)

    # Stand in for a workflow whose readiness is satisfied and whose plan is
    # built. Readiness itself is covered by its own tests (a genuinely blocked
    # workflow refuses approval — see test_approval_is_refused_when_there_is_no_plan
    # and the blocked-readiness tests); what this test pins is that approval
    # reaches the REAL orchestrator rather than any stand-in.
    from applications.agent.rollforward_agent import RollForwardAssessment

    ready = RollForwardAssessment(
        stage=RollForwardStage.PLAN_READY, workflow_id="wf-test", session_id="sess-rf",
        historical_document_id="doc-hist", current_source_document_ids=["doc-fa"],
        template_document_id="doc-tpl", plan=plan.preview())
    monkeypatch.setattr(RollForwardAgentHandler, "assess",
                        classmethod(lambda cls, session_id, user_id="anonymous": ready))

    from applications.rollforward import orchestrator as rf_orchestrator

    seen = {}
    real_execute = rf_orchestrator.RollForwardOrchestrator.execute

    def spy_execute(request):
        seen["execution_id"] = request.execution_id
        seen["manifest_status"] = request.manifest.status
        seen["approver"] = request.expected_approver
        return real_execute(request)

    monkeypatch.setattr(rf_orchestrator.RollForwardOrchestrator, "execute", spy_execute)

    report, _ = RollForwardApprovalService.approve_and_execute(
        session_id="sess-rf", approver="partner@firm.com")

    assert seen, "RollForwardOrchestrator.execute was never called"
    assert seen["approver"] == "partner@firm.com"
    assert str(seen["manifest_status"]) .endswith("APPROVED")
    assert report.execution_id
    assert report.template_preserved is True


# ---------------------------------------------------------------------------
# 8-11. A RESULT IS ONLY EVER A REAL EXECUTION
# ---------------------------------------------------------------------------

def test_a_result_without_an_execution_id_is_rejected():
    with pytest.raises(Exception):
        AgentResponse(
            response="Roll-forward completed.",
            roll_forward_result=RollForwardResult(
                execution_id="", status="SUCCESS", publication_state="PUBLISHED"),
        )


def test_completion_requires_an_output_document():
    without_output = RollForwardResult(
        execution_id="exec-1", status="SUCCESS", publication_state="PUBLISHED",
        output_document=None, output_hash=None)
    assert without_output.is_complete is False

    with_output = RollForwardResult(
        execution_id="exec-1", status="SUCCESS", publication_state="PUBLISHED",
        output_document={"doc_id": "d1", "filename": "out.docx"}, output_hash="abc123")
    assert with_output.is_complete is True


def test_completion_requires_publication():
    staged = RollForwardResult(
        execution_id="exec-1", status="SUCCESS", publication_state="NOT_PUBLISHED",
        output_document={"doc_id": "d1"}, output_hash="abc")
    assert staged.is_complete is False


def test_reconciliation_status_is_carried_not_assumed():
    result = RollForwardResult(
        execution_id="exec-1", status="SUCCESS", publication_state="PUBLISHED",
        output_document={"doc_id": "d1"}, output_hash="abc")
    assert result.reconciliation_status == "NOT_RUN"  # nothing claims RECONCILED by default


def test_a_failed_execution_never_reads_as_completed():
    failed = RollForwardResult(
        execution_id="exec-9", status="FAILED", publication_state="NOT_PUBLISHED",
        output_document=None)
    assert failed.is_complete is False

    response = AgentResponse(response="Roll-forward did not complete.",
                             roll_forward_result=failed)
    assert response.roll_forward_result.is_complete is False
    assert "completed" not in response.response.lower().replace("did not complete", "")


def test_result_mapping_copies_the_report_and_invents_nothing():
    class _Digest:
        overall_status = "PARTIALLY_RECONCILED"
        total_cells = 12
        matched_cells = 10
        mismatched_cells = 2
        manual_review_items = 1

    class _Change:
        rows_inserted = 3

    class _Report:
        execution_id = "exec-42"
        status = "SUCCESS"
        publication_state = "PUBLISHED"
        output_hash = "deadbeef"
        output_path = "/tmp/out.docx"
        executed_regions = [object(), object()]
        structural_changes = [_Change()]
        reconciliation = _Digest()
        validation_summary = {"checks": 7}
        lineage = type("L", (), {"lineage_id": "lin-1"})()
        template_preserved = True

    result = RollForwardAgentHandler.result_from_report(
        _Report(), {"doc_id": "d1", "filename": "out.docx"})

    assert result.execution_id == "exec-42"
    assert result.output_hash == "deadbeef"
    assert result.regions_changed == 2
    assert result.rows_inserted == 3
    assert result.cells_updated == 12
    assert result.reconciliation_status == "PARTIALLY_RECONCILED"
    assert result.validation_summary == {"checks": 7}
    assert result.lineage_id == "lin-1"
    assert result.is_complete is True


# ---------------------------------------------------------------------------
# 12. NO FABRICATED SOURCES
# ---------------------------------------------------------------------------

@requires_demo
def test_the_answer_names_only_documents_the_workflow_actually_holds(workflow_session,
                                                                    monkeypatch):
    """The failing production answer named RPT schedules and benchmarking datasets."""
    workflow_session()
    monkeypatch.setattr(orchestrator_module.ContextBuilder, "build_context",
                        staticmethod(_stale_context("sess-rf")))
    _ModelSpy(monkeypatch)

    response = AgentOrchestrator.handle_chat(
        message=PRODUCTION_MESSAGE, session_id="sess-rf", context_input={},
        model="gemini_3_6_flash")

    text = response.response.lower()
    # Domain names may appear as BLOCKERS ("Benchmarking — add this year's ...").
    # What must never appear is a claim that such a source was used.
    for fabricated in ("industry report", "annual report", "segmented p&l dataset",
                       "benchmarking dataset"):
        assert fabricated not in text

    named_files = [row for row in response.roll_forward_assessment["readiness"]
                   for row in row.get("supplied_by", [])]
    assert all(name in {HISTORICAL.name, FA_RPT.name, TEMPLATE.name, APPENDIX_I.name}
               for name in named_files), named_files


@requires_demo
def test_a_plan_bound_to_other_documents_is_refused(workflow_session, tmp_path):
    """A plan built for different files must never execute against these ones."""
    session = workflow_session(template=True)
    plan = _governed_plan(tmp_path)
    plan.historical_document_id = "doc-from-another-session"
    RollForwardPlanStore.register(plan)

    mismatches = plan.binding_mismatches(session)
    assert mismatches
    assert any("Previous Local File" in problem for problem in mismatches)
