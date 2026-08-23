"""
Local File Roll-Forward workflow intake (Phase PROD-UX-1).

Covers the intake contract end to end against real fixtures:
    * the three hardcoded input ROLES and their cardinality/format contract
    * content-derived role detection (never the filename)
    * cross-slot period re-validation
    * the readiness summary over source domains
    * required-input gating
    * the structured Agent context
    * the no-mutation / no-approval guarantees of this phase
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from applications.rollforward.source_intake import ArtifactFormat, RecalculatedReadiness
from applications.rollforward.workflow_intake import (
    SLOT_SPECS,
    Cardinality,
    DomainStatus,
    SlotId,
    SlotReadinessStatus,
    SlotValidationStatus,
    WorkflowIntakeError,
    WorkflowIntakeSession,
    WorkflowType,
)

warnings.filterwarnings("ignore")

DEMO = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files"
HISTORICAL_FY2023 = DEMO / "Compare LF" / "HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx"
FINAL_FY2024 = DEMO / "Compare LF" / "HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx"
TEMPLATE = (DEMO / "Compare LF"
            / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 "
              "(Decree 20-2025).docx")
FA_RPT = DEMO / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"
APPENDIX_I = (DEMO / "FA&RPTS & Appendix I" / "Appendix I"
              / "HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx")

pytestmark = pytest.mark.skipif(
    not HISTORICAL_FY2023.exists(),
    reason="demo fixtures are not present in this checkout",
)


def _assign(session: WorkflowIntakeSession, slot: SlotId, doc_id: str, path: Path,
            element_count: int = 0):
    return session.assign_document(slot, doc_id, path, path.name, element_count=element_count)


@pytest.fixture
def session() -> WorkflowIntakeSession:
    return WorkflowIntakeSession("sess-test")


@pytest.fixture
def complete_session(session: WorkflowIntakeSession) -> WorkflowIntakeSession:
    _assign(session, SlotId.HISTORICAL_LOCAL_FILE, "doc-hist", HISTORICAL_FY2023, 1200)
    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-farpt", FA_RPT, 800)
    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-app1", APPENDIX_I, 4000)
    _assign(session, SlotId.MASTER_TEMPLATE, "doc-tpl", TEMPLATE, 900)
    return session


# ---------------------------------------------------------------------------
# 1. SLOT CONTRACT
# ---------------------------------------------------------------------------

def test_workflow_declares_exactly_three_hardcoded_roles(session):
    assert session.workflow_type is WorkflowType.LOCAL_FILE_ROLL_FORWARD
    assert set(session.slots) == {
        SlotId.HISTORICAL_LOCAL_FILE, SlotId.CURRENT_YEAR_SOURCES, SlotId.MASTER_TEMPLATE}


def test_slot_cardinality_and_accepted_formats():
    historical = SLOT_SPECS[SlotId.HISTORICAL_LOCAL_FILE]
    sources = SLOT_SPECS[SlotId.CURRENT_YEAR_SOURCES]
    template = SLOT_SPECS[SlotId.MASTER_TEMPLATE]

    assert historical.cardinality is Cardinality.EXACTLY_ONE
    assert historical.accepted_formats == (ArtifactFormat.DOCX,)
    assert template.cardinality is Cardinality.EXACTLY_ONE
    assert template.accepted_formats == (ArtifactFormat.DOCX,)

    assert sources.cardinality is Cardinality.ONE_OR_MORE
    assert set(sources.accepted_formats) == {
        ArtifactFormat.XLSX, ArtifactFormat.DOCX, ArtifactFormat.CSV}
    assert all(spec.required for spec in SLOT_SPECS.values())


def test_current_year_sources_accepts_more_than_two_files(session):
    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-farpt", FA_RPT)
    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-app1", APPENDIX_I)
    slot = session.slot(SlotId.CURRENT_YEAR_SOURCES)
    assert len(slot.assignments) == 2
    assert slot.spec.accepts_multiple


def test_single_file_slot_replaces_rather_than_accumulates(session):
    _assign(session, SlotId.HISTORICAL_LOCAL_FILE, "doc-a", HISTORICAL_FY2023)
    _assign(session, SlotId.HISTORICAL_LOCAL_FILE, "doc-b", FINAL_FY2024)
    assert session.slot(SlotId.HISTORICAL_LOCAL_FILE).assigned_document_ids == ["doc-b"]


# ---------------------------------------------------------------------------
# 2. CONTENT-DERIVED ROLE DETECTION
# ---------------------------------------------------------------------------

def test_historical_local_file_is_confirmed_from_its_stated_period(session):
    assignment = _assign(session, SlotId.HISTORICAL_LOCAL_FILE, "doc-hist", HISTORICAL_FY2023)
    assert assignment.validation_status is SlotValidationStatus.ROLE_CONFIRMED
    assert assignment.signals.fiscal_year == 2023
    assert "FY2023" in assignment.detected_label


def test_master_template_is_confirmed_by_placeholders_not_by_name(session):
    assignment = _assign(session, SlotId.MASTER_TEMPLATE, "doc-tpl", TEMPLATE)
    assert assignment.validation_status is SlotValidationStatus.ROLE_CONFIRMED
    assert assignment.signals.fiscal_year is None
    assert assignment.signals.placeholder_hits > 10
    assert assignment.detected_label == "Blank Local File template"


def test_completed_local_file_in_template_slot_is_a_mismatch(session):
    assignment = _assign(session, SlotId.MASTER_TEMPLATE, "doc-wrong", HISTORICAL_FY2023)
    assert assignment.validation_status is SlotValidationStatus.ROLE_MISMATCH
    assert assignment.expected_label == "Master Template"
    assert "FY2023" in assignment.detected_label


def test_current_year_source_is_confirmed_from_the_datasets_it_satisfies(session):
    assignment = _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-farpt", FA_RPT)
    assert assignment.validation_status is SlotValidationStatus.ROLE_CONFIRMED
    assert assignment.signals.supplies_current_year_data
    assert assignment.signals.fiscal_year == 2024


def test_local_file_document_in_the_sources_slot_is_a_mismatch(session):
    assignment = _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-lf", HISTORICAL_FY2023)
    assert assignment.validation_status is SlotValidationStatus.ROLE_MISMATCH


def test_workbook_in_a_docx_only_slot_is_format_rejected(session):
    assignment = _assign(session, SlotId.MASTER_TEMPLATE, "doc-xlsx", FA_RPT)
    assert assignment.validation_status is SlotValidationStatus.FORMAT_REJECTED
    assert session.slot(SlotId.MASTER_TEMPLATE).readiness_status is SlotReadinessStatus.BLOCKED


def test_current_year_final_local_file_in_the_historical_slot_is_a_mismatch(complete_session):
    """The spec's headline case: same-period Local File, detected from content."""
    assignment = _assign(complete_session, SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", FINAL_FY2024)

    assert assignment.validation_status is SlotValidationStatus.ROLE_MISMATCH
    assert assignment.expected_label == "Historical Local File"
    assert assignment.detected_label == "FY2024 Final Local File"
    assert complete_session.slot(SlotId.HISTORICAL_LOCAL_FILE).readiness_status \
        is SlotReadinessStatus.BLOCKED


def test_a_rejected_historical_file_does_not_invalidate_the_sources(complete_session):
    _assign(complete_session, SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", FINAL_FY2024)
    sources = complete_session.slot(SlotId.CURRENT_YEAR_SOURCES)
    assert sources.readiness_status is SlotReadinessStatus.SATISFIED
    assert all(a.validation_status is SlotValidationStatus.ROLE_CONFIRMED
               for a in sources.assignments)


def test_periods_are_re_checked_when_later_evidence_arrives(session):
    """A verdict made with less evidence is revisited, not frozen."""
    first = _assign(session, SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", FINAL_FY2024)
    assert first.validation_status is SlotValidationStatus.ROLE_CONFIRMED  # nothing to contradict it

    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-farpt", FA_RPT)
    assert session.slot(SlotId.HISTORICAL_LOCAL_FILE).assignments[0].validation_status \
        is SlotValidationStatus.ROLE_MISMATCH


# ---------------------------------------------------------------------------
# 3. HUMAN REVIEW — explicit, never silent
# ---------------------------------------------------------------------------

def test_keeping_a_flagged_file_is_recorded_and_downgrades_it_to_human_review(complete_session):
    _assign(complete_session, SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", FINAL_FY2024)
    assignment = complete_session.acknowledge_for_review(
        SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", actor="tester")

    assert assignment.validation_status is SlotValidationStatus.HUMAN_REVIEW
    assert assignment.human_review_acknowledged
    assert assignment.acknowledged_by == "tester"
    assert any("manual review" in reason for reason in assignment.reasons)
    assert complete_session.slot(SlotId.HISTORICAL_LOCAL_FILE).readiness_status \
        is SlotReadinessStatus.NEEDS_REVIEW


def test_a_format_rejection_cannot_be_kept_for_review(session):
    _assign(session, SlotId.MASTER_TEMPLATE, "doc-xlsx", FA_RPT)
    with pytest.raises(WorkflowIntakeError):
        session.acknowledge_for_review(SlotId.MASTER_TEMPLATE, "doc-xlsx")


def test_an_acknowledged_decision_survives_revalidation(complete_session):
    _assign(complete_session, SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", FINAL_FY2024)
    complete_session.acknowledge_for_review(SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong")
    complete_session.revalidate_all()
    assignment = complete_session.slot(SlotId.HISTORICAL_LOCAL_FILE).assignments[0]
    assert assignment.validation_status is SlotValidationStatus.HUMAN_REVIEW


# ---------------------------------------------------------------------------
# 4. READINESS SUMMARY
# ---------------------------------------------------------------------------

def test_every_domain_is_missing_before_any_source_arrives(session):
    assert {row.status for row in session.readiness_summary()} == {DomainStatus.MISSING_SOURCE}


def test_readiness_reflects_what_the_sources_actually_satisfy(complete_session):
    rows = {row.display_name: row.status for row in complete_session.readiness_summary()}
    assert rows["Related-party transactions"] is DomainStatus.SUPPORTED
    assert rows["Financial information"] is DomainStatus.SUPPORTED
    assert rows["Benchmarking"] is DomainStatus.BLOCKED
    assert rows["FAR"] is DomainStatus.BLOCKED
    assert rows["Organisation"] is DomainStatus.BLOCKED


def test_readiness_rows_expose_no_internals(complete_session):
    for row in complete_session.readiness_summary():
        payload = row.to_dict()
        assert "_" not in payload["display_name"]
        assert "ROLE" not in payload["detail"].upper()
        assert "READINESS" not in payload["detail"].upper()


def test_a_domain_supplied_only_by_a_flagged_file_reads_as_human_review(session):
    """A file kept for manual review never makes a domain Ready."""
    _assign(session, SlotId.HISTORICAL_LOCAL_FILE, "doc-hist", HISTORICAL_FY2023)
    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-farpt", FA_RPT)
    assignment = session.slot(SlotId.CURRENT_YEAR_SOURCES).assignments[0]
    assignment.validation_status = SlotValidationStatus.HUMAN_REVIEW
    assignment.human_review_acknowledged = True

    rows = {row.display_name: row.status for row in session.readiness_summary()}
    assert rows["Related-party transactions"] is DomainStatus.HUMAN_REVIEW


# ---------------------------------------------------------------------------
# 5. GATING
# ---------------------------------------------------------------------------

def test_gate_names_the_first_missing_input(session):
    gate = session.execution_gate()
    assert gate["execution_allowed"] is False
    assert gate["message"] == "Upload Previous Local File to continue."

    _assign(session, SlotId.HISTORICAL_LOCAL_FILE, "doc-hist", HISTORICAL_FY2023)
    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-farpt", FA_RPT)
    assert session.execution_gate()["message"] == "Upload Master Template to continue."


def test_gate_opens_only_when_all_three_slots_hold_a_usable_file(complete_session):
    gate = complete_session.execution_gate()
    assert gate["execution_allowed"] is True
    assert gate["plan_approval_allowed"] is True
    assert gate["missing_slots"] == [] and gate["blocked_slots"] == []


def test_gate_closes_again_when_a_slot_becomes_invalid(complete_session):
    _assign(complete_session, SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", FINAL_FY2024)
    gate = complete_session.execution_gate()
    assert gate["execution_allowed"] is False
    assert "Previous Local File" in gate["message"]


def test_mutation_is_never_allowed_by_intake(complete_session):
    assert complete_session.execution_gate()["mutation_allowed"] is False


# ---------------------------------------------------------------------------
# 6. AGENT CONTEXT
# ---------------------------------------------------------------------------

def test_agent_receives_roles_as_document_ids(complete_session):
    context = complete_session.agent_workflow_context()
    assert context["workflow"] == "LOCAL_FILE_ROLL_FORWARD"
    assert context["historical_document_id"] == "doc-hist"
    assert context["current_source_document_ids"] == ["doc-farpt", "doc-app1"]
    assert context["template_document_id"] == "doc-tpl"
    assert context["target_fiscal_year"] == 2024
    assert context["historical_fiscal_year"] == 2023
    assert context["inputs_complete"] is True


def test_agent_context_omits_a_file_whose_role_was_rejected(complete_session):
    _assign(complete_session, SlotId.HISTORICAL_LOCAL_FILE, "doc-wrong", FINAL_FY2024)
    context = complete_session.agent_workflow_context()
    assert context["historical_document_id"] is None
    assert context["inputs_complete"] is False


# ---------------------------------------------------------------------------
# 7. PERSISTENCE + GOVERNANCE
# ---------------------------------------------------------------------------

def test_state_round_trips_without_reprofiling_the_files(complete_session):
    restored = WorkflowIntakeSession.from_state_dict(complete_session.state_to_dict())

    assert restored.execution_gate()["execution_allowed"] is True
    assert restored.agent_workflow_context() == complete_session.agent_workflow_context()
    assert ([row.status for row in restored.readiness_summary()]
            == [row.status for row in complete_session.readiness_summary()])


def test_intake_never_emits_a_forbidden_readiness_value(complete_session):
    counts = complete_session.recalculate_readiness()
    assert set(counts) <= {value.value for value in RecalculatedReadiness}
    for forbidden in ("APPROVED", "EXECUTING", "AUTO_MUTATION_READY", "COMPLETED"):
        assert forbidden not in counts


def test_registering_a_source_leaves_the_file_untouched(session, tmp_path):
    copy = tmp_path / FA_RPT.name
    copy.write_bytes(FA_RPT.read_bytes())
    before = copy.stat().st_mtime_ns, copy.stat().st_size

    _assign(session, SlotId.CURRENT_YEAR_SOURCES, "doc-copy", copy)

    assert (copy.stat().st_mtime_ns, copy.stat().st_size) == before
    assert session.registry._mutation_count == 0
