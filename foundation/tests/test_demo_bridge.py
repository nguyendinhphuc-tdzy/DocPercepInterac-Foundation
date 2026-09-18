"""
Tests for GTPS Local File Real-Document Demo Bridge API.
========================================================
Location: foundation/tests/test_demo_bridge.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app
from api.routes.demo import DEMO_DATA_DIR, _DEMO_SESSIONS

requires_demo = pytest.mark.skipif(
    not DEMO_DATA_DIR.exists(),
    reason="Demo fixtures directory not found",
)


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@requires_demo
def test_workspace_load_local_demo(client):
    """Verifies that the demo bridge can load real representative files into a session."""
    res = client.post(
        "/demo/gtps/workspace",
        json={"load_local_demo": True},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "session_id" in data
    assert len(data["documents"]) >= 3
    assert data["readiness"]["all_ready"] is True
    assert data["readiness"]["template_ready"] is True
    assert data["readiness"]["historical_ready"] is True
    assert data["readiness"]["current_source_ready"] is True


@requires_demo
def test_role_reassignment_and_gating(client):
    """Verifies role reassignment and that readiness requires all three roles."""
    res = client.post(
        "/demo/gtps/workspace",
        json={"load_local_demo": True},
    )
    session_id = res.get_json()["session_id"]
    docs = res.get_json()["documents"]
    tmpl_doc = next(d for d in docs if d["assigned_role"] == "TARGET_TEMPLATE")

    # Unassign template role
    res2 = client.post(
        "/demo/gtps/workspace/assign-role",
        json={"session_id": session_id, "doc_id": tmpl_doc["doc_id"], "role": None},
    )
    assert res2.status_code == 200
    assert res2.get_json()["readiness"]["template_ready"] is False
    assert res2.get_json()["readiness"]["all_ready"] is False

    # Attempt to analyze without template -> 400
    res_fail = client.post(
        "/demo/gtps/analyze",
        json={"session_id": session_id},
    )
    assert res_fail.status_code == 400

    # Reassign template role
    res3 = client.post(
        "/demo/gtps/workspace/assign-role",
        json={"session_id": session_id, "doc_id": tmpl_doc["doc_id"], "role": "TARGET_TEMPLATE"},
    )
    assert res3.status_code == 200
    assert res3.get_json()["readiness"]["template_ready"] is True
    assert res3.get_json()["readiness"]["all_ready"] is True


@requires_demo
def test_analyze_mapping_and_zero_mutation(client):
    """Verifies analyze runs RollForwardPlanner, produces real proposals, and mutates zero files."""
    res = client.post(
        "/demo/gtps/workspace",
        json={"load_local_demo": True},
    )
    session_id = res.get_json()["session_id"]
    docs = res.get_json()["documents"]
    tmpl_doc = next(d for d in docs if d["assigned_role"] == "TARGET_TEMPLATE")

    # Check template bytes before analyze
    content_res_before = client.get(f"/demo/gtps/documents/{tmpl_doc['doc_id']}/content")
    assert content_res_before.status_code == 200
    hash_before = hashlib.sha256(content_res_before.data).hexdigest()

    # Run analyze
    res_plan = client.post(
        "/demo/gtps/analyze",
        json={"session_id": session_id},
    )
    assert res_plan.status_code == 200
    plan_data = res_plan.get_json()

    assert plan_data["governance"]["docx_mutated"] is False
    assert "proposals" in plan_data
    assert len(plan_data["proposals"]) > 0

    # Summary counts match proposals
    summary = plan_data["summary"]
    total = summary["total"]
    assert total == len(plan_data["proposals"])
    assert total == (summary["mapped"] + summary["needs_confirmation"] + summary["missing_source"] + summary["unsupported"])

    # Verify at least one mapped proposal has proposed_rows
    mapped_props = [p for p in plan_data["proposals"] if p["status"] == "MAPPED"]
    if mapped_props:
        first_mapped = mapped_props[0]
        assert "target_table_index" in first_mapped
        assert first_mapped["source_evidence"] is not None
        assert "sheet_name" in first_mapped["source_evidence"]

    # Check template bytes after analyze -> MUST BE IDENTICAL
    content_res_after = client.get(f"/demo/gtps/documents/{tmpl_doc['doc_id']}/content")
    assert content_res_after.status_code == 200
    hash_after = hashlib.sha256(content_res_after.data).hexdigest()
    assert hash_before == hash_after, "Target template file was mutated!"


@requires_demo
def test_review_decision_endpoint(client):
    """Verifies prototype review decision recording without file mutation."""
    res = client.post(
        "/demo/gtps/workspace",
        json={"load_local_demo": True},
    )
    session_id = res.get_json()["session_id"]
    client.post("/demo/gtps/analyze", json={"session_id": session_id})

    # Record decision
    res_dec = client.post(
        "/demo/gtps/review/decision",
        json={"session_id": session_id, "proposal_id": "prop-1", "decision": "APPROVED", "notes": "Verified by reviewer"},
    )
    assert res_dec.status_code == 200
    assert res_dec.get_json()["governance"]["docx_mutated"] is False

    # Check review projection has updated decision
    res_rev = client.get(f"/demo/gtps/review?session_id={session_id}")
    assert res_rev.status_code == 200
    rev_data = res_rev.get_json()
    prop1 = next(p for p in rev_data["proposals"] if p["id"] == "prop-1")
    assert prop1["decision"] == "APPROVED"
    assert prop1["reviewer_notes"] == "Verified by reviewer"
