"""
Workflow state persistence (Phase PROD-UX-1 hardening, P0-1).

Which document holds which workflow role is production state. Render's
filesystem is ephemeral, so these tests pin the guarantees that make the
workflow survive:

    * a reload of the process reads the same state back (browser refresh)
    * a brand-new repository instance reads it back (container restart/redeploy)
    * one user cannot see or overwrite another user's workflow
    * no document bytes are ever written into the state store

Both implementations are covered: the JSON-backed local repository used in
development and tests, and the Supabase adapter used in production (driven
against an in-memory stub client — no network).
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, List

import pytest

from adapters.repository import (
    LocalWorkflowRepository,
    RepositoryError,
    SupabaseWorkflowRepository,
    WorkflowRecord,
    WorkflowSlotAssignmentRecord,
)

warnings.filterwarnings("ignore")


def _workflow(session_id: str = "sess-1", user_id: str = "user-a",
              workflow_id: str = "wf-1") -> WorkflowRecord:
    return WorkflowRecord(
        workflow_id=workflow_id,
        session_id=session_id,
        user_id=user_id,
        workflow_type="LOCAL_FILE_ROLL_FORWARD",
        target_fiscal_year=None,
    )


def _assignment(slot_id: str, document_id: str, session_id: str = "sess-1",
                user_id: str = "user-a", workflow_id: str = "wf-1",
                **overrides) -> WorkflowSlotAssignmentRecord:
    record = WorkflowSlotAssignmentRecord(
        workflow_id=workflow_id,
        session_id=session_id,
        user_id=user_id,
        slot_id=slot_id,
        document_id=document_id,
        filename=f"{document_id}.docx",
        file_format="docx",
        file_hash="a" * 64,
        validation_status="ROLE_CONFIRMED",
        readiness_status="SATISFIED",
        signals={"fiscal_year": 2023, "format": "DOCX"},
    )
    for key, value in overrides.items():
        setattr(record, key, value)
    return record


# ===========================================================================
# LOCAL REPOSITORY — development/test representation
# ===========================================================================

@pytest.fixture
def local_repo(tmp_path) -> LocalWorkflowRepository:
    return LocalWorkflowRepository(tmp_path)


def test_workflow_round_trips(local_repo):
    saved = local_repo.save_workflow(_workflow())
    loaded = local_repo.get_workflow("sess-1", user_id="user-a")

    assert loaded is not None
    assert loaded.workflow_id == saved.workflow_id
    assert loaded.workflow_type == "LOCAL_FILE_ROLL_FORWARD"


def test_state_survives_a_new_repository_instance(local_repo, tmp_path):
    """A restarted process re-reads the same state — nothing lives in memory."""
    local_repo.save_workflow(_workflow())
    local_repo.upsert_assignment(_assignment("HISTORICAL_LOCAL_FILE", "doc-hist"))
    local_repo.upsert_assignment(_assignment("CURRENT_YEAR_SOURCES", "doc-src"))

    restarted = LocalWorkflowRepository(tmp_path)
    workflow = restarted.get_workflow("sess-1", user_id="user-a")
    assert workflow is not None

    slots = {a.slot_id: a.document_id
             for a in restarted.list_assignments(workflow.workflow_id, user_id="user-a")}
    assert slots == {"HISTORICAL_LOCAL_FILE": "doc-hist", "CURRENT_YEAR_SOURCES": "doc-src"}


def test_upsert_updates_in_place_and_keeps_created_at(local_repo):
    local_repo.save_workflow(_workflow())
    first = local_repo.upsert_assignment(_assignment("HISTORICAL_LOCAL_FILE", "doc-hist"))
    updated = local_repo.upsert_assignment(_assignment(
        "HISTORICAL_LOCAL_FILE", "doc-hist", validation_status="ROLE_MISMATCH"))

    rows = local_repo.list_assignments("wf-1", user_id="user-a")
    assert len(rows) == 1
    assert rows[0].validation_status == "ROLE_MISMATCH"
    assert updated.created_at == first.created_at


def test_replace_assignments_prunes_removed_rows(local_repo):
    local_repo.save_workflow(_workflow())
    local_repo.upsert_assignment(_assignment("CURRENT_YEAR_SOURCES", "doc-a"))
    local_repo.upsert_assignment(_assignment("CURRENT_YEAR_SOURCES", "doc-b"))

    local_repo.replace_assignments(
        "wf-1", [_assignment("CURRENT_YEAR_SOURCES", "doc-b")], user_id="user-a")

    assert [a.document_id for a in local_repo.list_assignments("wf-1", user_id="user-a")] \
        == ["doc-b"]


def test_delete_assignment_and_workflow(local_repo):
    local_repo.save_workflow(_workflow())
    local_repo.upsert_assignment(_assignment("MASTER_TEMPLATE", "doc-tpl"))

    assert local_repo.delete_assignment("wf-1", "MASTER_TEMPLATE", "doc-tpl", user_id="user-a")
    assert local_repo.list_assignments("wf-1", user_id="user-a") == []
    assert local_repo.delete_workflow("sess-1", user_id="user-a")
    assert local_repo.get_workflow("sess-1", user_id="user-a") is None


def test_user_b_cannot_read_user_a_workflow(local_repo):
    local_repo.save_workflow(_workflow(user_id="user-a"))
    with pytest.raises(RepositoryError):
        local_repo.get_workflow("sess-1", user_id="user-b")


def test_user_b_cannot_overwrite_user_a_workflow(local_repo):
    local_repo.save_workflow(_workflow(user_id="user-a"))
    with pytest.raises(RepositoryError):
        local_repo.save_workflow(_workflow(user_id="user-b"))


def test_user_b_cannot_see_user_a_assignments(local_repo):
    local_repo.save_workflow(_workflow(user_id="user-a"))
    local_repo.upsert_assignment(_assignment("HISTORICAL_LOCAL_FILE", "doc-hist"))
    assert local_repo.list_assignments("wf-1", user_id="user-b") == []


def test_state_store_never_holds_document_bytes(local_repo, tmp_path):
    local_repo.save_workflow(_workflow())
    local_repo.upsert_assignment(_assignment("HISTORICAL_LOCAL_FILE", "doc-hist"))

    raw = (tmp_path / "sess-1" / LocalWorkflowRepository.FILENAME).read_text(encoding="utf-8")
    assert "doc-hist" in raw           # the reference is stored
    assert "base64" not in raw.lower()  # the bytes are not
    for field in ("content", "bytes", "blob", "data_uri"):
        assert f'"{field}"' not in raw


# ===========================================================================
# SUPABASE ADAPTER — production, driven against an in-memory stub client
# ===========================================================================

class _StubQuery:
    """Minimal postgrest-style query object over a list of dict rows."""

    def __init__(self, table: "_StubTable", operation: str, payload: Any = None):
        self.table = table
        self.operation = operation
        self.payload = payload
        self.filters: List[tuple] = []

    def eq(self, column: str, value: Any) -> "_StubQuery":
        self.filters.append((column, value))
        return self

    def order(self, *_args, **_kwargs) -> "_StubQuery":
        return self

    def limit(self, *_args) -> "_StubQuery":
        return self

    def _matches(self, row: Dict[str, Any]) -> bool:
        return all(row.get(column) == value for column, value in self.filters)

    def execute(self):
        if self.operation == "select":
            return type("Result", (), {"data": [r for r in self.table.rows if self._matches(r)]})
        if self.operation == "delete":
            removed = [r for r in self.table.rows if self._matches(r)]
            self.table.rows = [r for r in self.table.rows if not self._matches(r)]
            return type("Result", (), {"data": removed})
        if self.operation == "insert":
            payload = self.payload if isinstance(self.payload, list) else [self.payload]
            self.table.rows.extend(dict(row) for row in payload)
            return type("Result", (), {"data": payload})
        if self.operation == "update":
            # Conditional update: only rows matching every filter change, and the
            # result reports what actually changed — that is what makes the
            # adapter's compare-and-set on state_version meaningful.
            changed = []
            for row in self.table.rows:
                if self._matches(row):
                    row.update(self.payload)
                    changed.append(row)
            return type("Result", (), {"data": changed})
        # upsert
        payload = self.payload if isinstance(self.payload, list) else [self.payload]
        for new_row in payload:
            key = tuple(new_row.get(k) for k in self.table.primary_key)
            existing = next(
                (r for r in self.table.rows
                 if tuple(r.get(k) for k in self.table.primary_key) == key), None)
            if existing:
                existing.update(new_row)
            else:
                self.table.rows.append(dict(new_row))
        return type("Result", (), {"data": payload})


class _StubTable:
    def __init__(self, primary_key):
        self.primary_key = primary_key
        self.rows: List[Dict[str, Any]] = []

    def select(self, *_columns):
        return _StubQuery(self, "select")

    def upsert(self, payload, on_conflict=None):
        return _StubQuery(self, "upsert", payload)

    def insert(self, payload):
        return _StubQuery(self, "insert", payload)

    def update(self, payload):
        return _StubQuery(self, "update", payload)

    def delete(self):
        return _StubQuery(self, "delete")


class _StubClient:
    def __init__(self):
        self.tables = {
            SupabaseWorkflowRepository.WORKFLOWS: _StubTable(("workflow_id",)),
            SupabaseWorkflowRepository.ASSIGNMENTS:
                _StubTable(("workflow_id", "slot_id", "document_id")),
        }

    def table(self, name: str) -> _StubTable:
        return self.tables[name]


@pytest.fixture
def supabase_repo() -> SupabaseWorkflowRepository:
    from config import AppConfig

    config = AppConfig(environment="testing", storage_backend="local", database_backend="local")
    return SupabaseWorkflowRepository(config=config, client=_StubClient())


def test_supabase_adapter_round_trips_a_workflow(supabase_repo):
    supabase_repo.save_workflow(_workflow())
    loaded = supabase_repo.get_workflow("sess-1", user_id="user-a")
    assert loaded is not None and loaded.workflow_id == "wf-1"


def test_supabase_adapter_scopes_reads_by_user(supabase_repo):
    supabase_repo.save_workflow(_workflow(user_id="user-a"))
    assert supabase_repo.get_workflow("sess-1", user_id="user-b") is None


def test_supabase_adapter_replaces_assignments_atomically(supabase_repo):
    supabase_repo.save_workflow(_workflow())
    supabase_repo.replace_assignments("wf-1", [
        _assignment("CURRENT_YEAR_SOURCES", "doc-a"),
        _assignment("CURRENT_YEAR_SOURCES", "doc-b"),
    ], user_id="user-a")
    supabase_repo.replace_assignments(
        "wf-1", [_assignment("CURRENT_YEAR_SOURCES", "doc-b")], user_id="user-a")

    rows = supabase_repo.list_assignments("wf-1", user_id="user-a")
    assert [r.document_id for r in rows] == ["doc-b"]


def test_supabase_adapter_writes_no_document_bytes(supabase_repo):
    supabase_repo.save_workflow(_workflow())
    supabase_repo.upsert_assignment(_assignment("HISTORICAL_LOCAL_FILE", "doc-hist"))

    stored = supabase_repo._client.tables[SupabaseWorkflowRepository.ASSIGNMENTS].rows[0]
    assert set(stored) <= set(WorkflowSlotAssignmentRecord.__dataclass_fields__)
    assert "document_id" in stored
    assert not any(k in stored for k in ("content", "bytes", "blob"))


def test_supabase_adapter_deletes_workflow_and_its_assignments(supabase_repo):
    supabase_repo.save_workflow(_workflow())
    supabase_repo.upsert_assignment(_assignment("MASTER_TEMPLATE", "doc-tpl"))

    assert supabase_repo.delete_workflow("sess-1", user_id="user-a") is True
    assert supabase_repo.get_workflow("sess-1", user_id="user-a") is None
    assert supabase_repo.list_assignments("wf-1", user_id="user-a") == []
