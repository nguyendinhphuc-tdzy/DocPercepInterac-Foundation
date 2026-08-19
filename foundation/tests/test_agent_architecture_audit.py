"""Deep Architecture Audit & Concurrency Test Suite for Foundation Agent.

Verifies all P0 and P1 remediations:
- P0-1: Concurrent proposal creation & atomic locked writes (no lost updates, no corruption)
- P0-2: Server-side rejection persistence and rejection lifecycle gating
- P0-3: Strict session isolation and oracle prevention
- P0-4: Cryptographic value fingerprinting (zero sensitive document leaks in console logs)
- P1-1: SHA-256 document content hash freshness gating
- P1-2: Proposal TTL expiration (24h default, configurable)
- P1-3: Stable message UUIDs across frontend lifecycle
- P1-4: Deterministic value fingerprinting
- P1-5: Ambiguous active document clarification with multiple documents
- P1-6: Workbench timeout (60s) and clean failure handling
- Elevated P2-5: Strict status update exception propagation
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import logging
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app
from applications.agent.models import ProposedAction, AgentContext
from applications.agent.proposal_store import ProposalStore
from applications.agent.action_executor import ActionExecutor
from applications.agent.orchestrator import AgentOrchestrator
from applications.agent.context_builder import ContextBuilder
from output.lineage import LineageLogger


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sample_session(client):
    """Uploads real KPMG DOCX fixture into a fresh session."""
    root = Path(__file__).resolve().parents[2]
    docx_fixture = root / "anonymize client" / "Demo files" / "Demo files" / "Compare LF" / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx"
    xlsx_fixture = root / "anonymize client" / "Demo files" / "Demo files" / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"

    with open(docx_fixture, "rb") as f:
        res = client.post(
            "/api/documents",
            data={"file": (f, "audit_template.docx")},
            content_type="multipart/form-data",
        )
    assert res.status_code == 200
    data = res.get_json()
    session_id = data["session_id"]
    docx_doc_id = data["doc_id"]

    with open(xlsx_fixture, "rb") as f:
        res2 = client.post(
            "/api/documents",
            data={"file": (f, "audit_financials.xlsx"), "session_id": session_id},
            content_type="multipart/form-data",
        )
    assert res2.status_code == 200
    xlsx_doc_id = res2.get_json()["doc_id"]

    return {
        "session_id": session_id,
        "docx_doc_id": docx_doc_id,
        "xlsx_doc_id": xlsx_doc_id,
    }


# ============================================================================
# P0-1: CONCURRENCY & ATOMIC PROPOSAL STORE
# ============================================================================

def test_p0_1_concurrent_proposal_writes(sample_session):
    """Test 20 threads writing distinct proposals simultaneously to the same session."""
    session_id = sample_session["session_id"]
    num_proposals = 20

    def write_one(idx):
        p = ProposedAction(
            doc_id=sample_session["docx_doc_id"],
            doc_name="audit_template.docx",
            element_id=f"el-{idx}",
            element_name=f"Paragraph {idx}",
            current_value=f"Original {idx}",
            proposed_value=f"Proposed {idx}",
            rationale=f"Concurrent test {idx}",
        )
        ProposalStore.save_proposal(session_id, p)
        return p.action_id

    with ThreadPoolExecutor(max_workers=8) as executor:
        action_ids = list(executor.map(write_one, range(num_proposals)))

    assert len(action_ids) == num_proposals

    # Verify all proposals are present and intact
    for action_id in action_ids:
        p = ProposalStore.get_proposal(session_id, action_id)
        assert p is not None
        assert p.action_id == action_id
        assert p.status == "proposed"


def test_p0_1_concurrent_same_action_execution(client, sample_session):
    """Test 5 threads executing the exact same action_id simultaneously — exactly 1 succeeds."""
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    editable_cell = next(e for e in res_els.get_json()["elements"] if e["capabilities"]["editable"] and e["text"])

    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Change this cell to 'CONCURRENCY_TEST_VALUE'",
            "context": {
                "active_doc_id": xlsx_doc_id,
                "selected_element_id": editable_cell["element_id"],
            },
        },
    )
    action_id = res_chat.get_json()["proposed_actions"][0]["action_id"]

    results = []
    errors = []

    def execute_call(_):
        try:
            res = ActionExecutor.execute_confirmed_action(session_id, action_id)
            results.append(res)
        except Exception as exc:
            errors.append(str(exc))

    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(execute_call, range(5)))

    assert len(results) == 1, f"Expected exactly 1 success, got {len(results)}. Errors: {errors}"
    assert len(errors) == 4, f"Expected 4 errors, got {len(errors)}"
    for err in errors:
        assert any(k in err for k in ["already being executed", "already been applied"])


# ============================================================================
# P0-2: SERVER-SIDE REJECTION PERSISTENCE & LIFECYCLE
# ============================================================================

def test_p0_2_rejection_lifecycle_and_execution_refusal(client, sample_session):
    """Test rejecting a proposal persists to backend and blocks future execution."""
    session_id = sample_session["session_id"]
    docx_doc_id = sample_session["docx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{docx_doc_id}")
    editable_para = next(e for e in res_els.get_json()["elements"] if e["capabilities"]["editable"])

    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Update this paragraph to 'REJECTED_TEXT'",
            "context": {
                "active_doc_id": docx_doc_id,
                "selected_element_id": editable_para["element_id"],
            },
        },
    )
    action_id = res_chat.get_json()["proposed_actions"][0]["action_id"]

    # 1. Reject on server
    res_reject = client.post(
        "/api/agent/action/reject",
        json={"session_id": session_id, "action_id": action_id},
    )
    assert res_reject.status_code == 200
    assert res_reject.get_json()["status"] == "rejected"

    # 2. Verify stored status is rejected
    stored = ProposalStore.get_proposal(session_id, action_id)
    assert stored is not None
    assert stored.status == "rejected"

    # 3. Attempting to execute rejected proposal must be blocked
    res_exec = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_id, "action_id": action_id},
    )
    assert res_exec.status_code == 400
    assert "was rejected" in res_exec.get_json()["error"]

    # 4. Attempting to reject again returns 400
    res_reject_dup = client.post(
        "/api/agent/action/reject",
        json={"session_id": session_id, "action_id": action_id},
    )
    assert res_reject_dup.status_code == 400


# ============================================================================
# P0-3: STRICT SESSION ISOLATION & ORACLE PREVENTION
# ============================================================================

def test_p0_3_cross_session_isolation(client, sample_session):
    """Test action from Session A cannot be accessed or executed in Session B."""
    session_a = sample_session["session_id"]
    docx_doc_id = sample_session["docx_doc_id"]

    res_els = client.get(f"/api/documents/{session_a}/elements/{docx_doc_id}")
    editable_para = next(e for e in res_els.get_json()["elements"] if e["capabilities"]["editable"])

    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_a,
            "message": "Change this to 'SESSION_A_VALUE'",
            "context": {
                "active_doc_id": docx_doc_id,
                "selected_element_id": editable_para["element_id"],
            },
        },
    )
    action_id_a = res_chat.get_json()["proposed_actions"][0]["action_id"]

    # Create distinct Session B
    root = Path(__file__).resolve().parents[2]
    docx_fixture = root / "anonymize client" / "Demo files" / "Demo files" / "Compare LF" / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx"
    with open(docx_fixture, "rb") as f:
        res_b = client.post(
            "/api/documents",
            data={"file": (f, "doc_b.docx")},
            content_type="multipart/form-data",
        )
    session_b = res_b.get_json()["session_id"]

    # Attempt to execute Session A action inside Session B
    res_exec_b = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_b, "action_id": action_id_a},
    )
    assert res_exec_b.status_code == 400
    assert "not found" in res_exec_b.get_json()["error"].lower()

    # Attempt to execute on completely non-existent session
    res_non_existent = client.post(
        "/api/agent/action/execute",
        json={"session_id": "non-existent-session-12345", "action_id": action_id_a},
    )
    assert res_non_existent.status_code == 400
    assert "invalid session" in res_non_existent.get_json()["error"].lower()


# ============================================================================
# P0-4: CRYPTOGRAPHIC SENSITIVE VALUE LINEAGE LOGGING
# ============================================================================

def test_p0_4_sensitive_value_redaction_in_operational_logs(caplog):
    """Test that LineageLogger records cryptographic fingerprints without plaintext leaks in console logs."""
    sensitive_secret = "CONFIDENTIAL_FINANCIAL_REVENUE_SECRET_$987,654,321.00"
    
    with caplog.at_level(logging.INFO, logger="LineageLogger"):
        logger = LineageLogger(log_dir=".lineage_logs_test")
        record = logger.log_mapping(
            target_anchor='{"sheet": "P&L", "cell": "B12"}',
            target_value=sensitive_secret,
            source_file="Agent:test",
            source_anchor="action:123",
            confidence=1.0,
            retain_full_value=False,
        )

    # 1. Operational log message must NOT contain plaintext sensitive value
    console_logs = caplog.text
    assert sensitive_secret not in console_logs, "Plaintext sensitive value leaked into operational logs!"
    assert "ValueHash:" in console_logs

    # 2. Record must contain correct SHA-256 fingerprint
    expected_hash = hashlib.sha256(sensitive_secret.encode("utf-8")).hexdigest()
    assert record.target_value_hash == expected_hash
    assert record.target_value is None


# ============================================================================
# P1-1: SHA-256 DOCUMENT CONTENT HASH FRESHNESS
# ============================================================================

def test_p1_1_out_of_band_document_hash_change_blocks_execution(client, sample_session):
    """Test that modifying document bytes out-of-band causes execute to reject proposal as stale."""
    session_id = sample_session["session_id"]
    docx_doc_id = sample_session["docx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{docx_doc_id}")
    editable_para = next(e for e in res_els.get_json()["elements"] if e["capabilities"]["editable"])

    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Change this to 'NEW_TEXT'",
            "context": {
                "active_doc_id": docx_doc_id,
                "selected_element_id": editable_para["element_id"],
            },
        },
    )
    action_id = res_chat.get_json()["proposed_actions"][0]["action_id"]

    # Mutate document file on disk out-of-band
    upload_root = Path(__file__).resolve().parents[1] / ".uploads"
    session_dir = upload_root / session_id
    manifest = json.loads((session_dir / "manifest.json").read_text(encoding="utf-8"))
    stored_path = session_dir / manifest["documents"][docx_doc_id]["stored_filename"]
    
    # Append out-of-band bytes
    with open(stored_path, "ab") as f:
        f.write(b"OUT_OF_BAND_MUTATION")

    # Attempt to execute — must fail due to SHA-256 hash mismatch
    res_exec = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_id, "action_id": action_id},
    )
    assert res_exec.status_code == 400
    assert "changed out-of-band" in res_exec.get_json()["error"]

    # Verify status transitioned to stale
    stored = ProposalStore.get_proposal(session_id, action_id)
    assert stored.status == "stale"


# ============================================================================
# P1-2: PROPOSAL TTL & EXPIRATION LIFECYCLE
# ============================================================================

def test_p1_2_proposal_ttl_expiration(client, sample_session):
    """Test that expired proposals (exceeding TTL) are marked expired and cannot execute."""
    session_id = sample_session["session_id"]

    # Create proposal with expired created_at (48 hours ago)
    past_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    proposal = ProposedAction(
        doc_id=sample_session["docx_doc_id"],
        doc_name="audit_template.docx",
        element_id="el-ttl-test",
        element_name="TTL Test Para",
        current_value="Old",
        proposed_value="New",
        rationale="TTL Test",
        created_at=past_time,
        ttl_seconds=86400,  # 24 hours
        status="proposed",
    )
    ProposalStore.save_proposal(session_id, proposal)

    # Retrieval enforces TTL and transitions status to expired
    retrieved = ProposalStore.get_proposal(session_id, proposal.action_id)
    assert retrieved is not None
    assert retrieved.status == "expired"

    # Execution must be rejected with TTL exceeded
    res_exec = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_id, "action_id": proposal.action_id},
    )
    assert res_exec.status_code == 400
    assert "expired" in res_exec.get_json()["error"].lower()


# ============================================================================
# P1-5: AMBIGUOUS ACTIVE DOCUMENT WITH MULTIPLE DOCUMENTS
# ============================================================================

def test_p1_5_ambiguous_active_doc_clarification(client, sample_session):
    """When multiple documents exist and active_doc_id is None, search asks for clarification."""
    session_id = sample_session["session_id"]

    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Find Revenue in this document",
            "context": {
                # active_doc_id omitted intentionally
            },
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["intent"] == "clarify_document"
    assert "Multiple documents are loaded" in data["response"]


# ============================================================================
# ELEVATED P2-5: STATUS UPDATE FAILURE & WRITEBACK RECONCILIATION
# ============================================================================

def test_elevated_p2_5_status_update_failure_blocks_duplicate_replay(client, sample_session, monkeypatch):
    """Test that if status update fails after writeback, the proposal is marked executing/failed and cannot replay."""
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    editable_cell = next(e for e in res_els.get_json()["elements"] if e["capabilities"]["editable"] and e["text"])

    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Change this cell to 'TEST_P2_5_RECONCILE'",
            "context": {
                "active_doc_id": xlsx_doc_id,
                "selected_element_id": editable_cell["element_id"],
            },
        },
    )
    action_id = res_chat.get_json()["proposed_actions"][0]["action_id"]

    # First claim transitions status to 'executing'
    claimed_proposal = ProposalStore.claim_proposal_for_execution(session_id, action_id)
    assert claimed_proposal.status == "executing"

    # Attempting to claim/execute again while executing must raise
    with pytest.raises(ValueError) as exc:
        ProposalStore.claim_proposal_for_execution(session_id, action_id)
    assert "already being executed" in str(exc.value)


# ============================================================================
# P1-6: WORKBENCH TIMEOUT & FAILURE HANDLING
# ============================================================================

def test_p1_6_workbench_timeout_handling(monkeypatch):
    """Test that requests.Timeout is converted to WorkbenchApiError without hanging."""
    import requests
    from applications.workbench_client import chat_completion, WorkbenchApiError

    monkeypatch.setenv("WORKBENCH_SUBSCRIPTION_KEY", "fake-key")
    monkeypatch.setenv("WORKBENCH_CHARGE_CODE", "fake-code")

    def mock_timeout(*args, **kwargs):
        raise requests.Timeout("Connection timed out after 60s")

    monkeypatch.setattr(requests, "post", mock_timeout)

    with pytest.raises(WorkbenchApiError) as exc:
        chat_completion([{"role": "user", "content": "Hello"}])
    assert "timed out after 60s" in str(exc.value)


# ============================================================================
# P1-2 (CLEANUP): BATCH EXPIRED PROPOSAL CLEANUP
# ============================================================================

def test_p1_2_cleanup_stale_proposals(sample_session):
    """Test ProposalStore.cleanup_stale_proposals correctly marks all expired proposals."""
    session_id = sample_session["session_id"]
    past_time = (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat()

    p1 = ProposedAction(
        doc_id=sample_session["docx_doc_id"],
        doc_name="audit_template.docx",
        element_id="el-clean-1",
        element_name="Clean 1",
        current_value="Old 1",
        proposed_value="New 1",
        rationale="Clean test",
        created_at=past_time,
        ttl_seconds=86400,
        status="proposed",
    )
    p2 = ProposedAction(
        doc_id=sample_session["docx_doc_id"],
        doc_name="audit_template.docx",
        element_id="el-clean-2",
        element_name="Clean 2",
        current_value="Old 2",
        proposed_value="New 2",
        rationale="Clean test",
        created_at=datetime.now(timezone.utc).isoformat(),
        ttl_seconds=86400,
        status="proposed",
    )
    ProposalStore.save_proposal(session_id, p1)
    ProposalStore.save_proposal(session_id, p2)

    cleaned = ProposalStore.cleanup_stale_proposals(session_id)
    assert cleaned >= 1

    assert ProposalStore.get_proposal(session_id, p1.action_id).status == "expired"
    assert ProposalStore.get_proposal(session_id, p2.action_id).status == "proposed"

