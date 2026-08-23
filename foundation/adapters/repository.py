"""
Database & Repository Abstraction Layer (Phase DEPLOY-1)
=========================================================
Location: foundation/adapters/repository.py

Provides clean data access patterns isolating domain logic and HTTP routes
from underlying storage implementations (Local file-based vs Supabase Postgres).

Enforces:
    - User and session isolation across all entities.
    - Versioned document metadata.
    - Atomic proposal claim and replay prevention.
    - Zero plaintext sensitive leaks in lineage/pilot events.
    - Zero local filesystem dependencies in production mode.
"""
from __future__ import annotations

import abc
from datetime import datetime, timezone, timedelta
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from filelock import FileLock

from config import AppConfig, DatabaseBackend, get_config


class RepositoryError(RuntimeError):
    """Raised when a database/repository operation fails."""


# ============================================================================
# DOMAIN RECORDS
# ============================================================================

@dataclass
class SessionRecord:
    session_id: str
    user_id: str = "anonymous"
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DocumentRecord:
    doc_id: str
    session_id: str
    original_filename: str
    format: str
    user_id: str = "anonymous"
    status: str = "ready"  # ready, error, perceiving
    element_count: int = 0
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DocumentVersionRecord:
    version_id: str
    doc_id: str
    session_id: str
    sha256: str
    storage_path: str
    user_id: str = "anonymous"
    version_number: int = 1
    is_patched: bool = False
    element_count: int = 0
    size_bytes: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProposalRecord:
    action_id: str
    session_id: str
    doc_id: str
    element_id: str
    proposed_value: str
    user_id: str = "anonymous"
    doc_name: str = ""
    element_name: str = ""
    type: str = "update_element"
    requires_confirmation: bool = True
    target_anchor: Optional[Dict[str, Any]] = None
    current_value: Optional[str] = None
    rationale: Optional[str] = None
    doc_hash: Optional[str] = None
    value_fingerprint: Optional[str] = None
    status: str = "proposed"  # proposed, executing, applied, rejected, stale, expired
    ttl_seconds: int = 86400
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class LineageEventRecord:
    session_id: str
    target_anchor: str
    target_value_hash: str
    source_file: str
    source_anchor: str
    user_id: str = "anonymous"
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PilotEventRecord:
    event_type: str
    session_id: Optional[str] = None
    user_id: str = "anonymous"
    model_id: Optional[str] = None
    provider: Optional[str] = None
    status: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WorkflowRecord:
    """One workflow intake — the canonical state of a structured workflow session.

    Holds no document bytes: those stay in object storage. This row records which
    workflow a session is running and the period it is rolling forward into.
    """
    workflow_id: str
    session_id: str
    workflow_type: str
    user_id: str = "anonymous"
    target_fiscal_year: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WorkflowSlotAssignmentRecord:
    """One document occupying one workflow input slot, with its role verdict.

    `signals` carries the deterministic content profile the verdict was derived
    from, so a reloaded workflow never has to re-open the file to answer a
    readiness question. Still no document bytes — only facts about them.
    """
    workflow_id: str
    session_id: str
    slot_id: str
    document_id: str
    user_id: str = "anonymous"
    filename: str = ""
    file_format: str = ""
    file_hash: str = ""
    file_size: int = 0
    perception_status: str = "ready"
    element_count: Optional[int] = None
    artifact_id: Optional[str] = None
    validation_status: str = "PENDING"
    readiness_status: str = "EMPTY"
    detected_label: str = ""
    expected_label: str = ""
    reasons: List[str] = field(default_factory=list)
    signals: Dict[str, Any] = field(default_factory=dict)
    human_review_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# REPOSITORY INTERFACES
# ============================================================================

class ISessionRepository(abc.ABC):
    @abc.abstractmethod
    def get_or_create(self, session_id: str, user_id: str = "anonymous", metadata: Optional[Dict[str, Any]] = None) -> SessionRecord:
        """Retrieves or creates a session record."""

    @abc.abstractmethod
    def get(self, session_id: str, user_id: str = "anonymous") -> Optional[SessionRecord]:
        """Gets a session record by id with user isolation."""


class IDocumentRepository(abc.ABC):
    @abc.abstractmethod
    def save_document(self, doc: DocumentRecord) -> DocumentRecord:
        """Saves or updates a document metadata record."""

    @abc.abstractmethod
    def get_document(self, session_id: str, doc_id: str, user_id: str = "anonymous") -> Optional[DocumentRecord]:
        """Gets a document by session_id and doc_id with user isolation."""

    @abc.abstractmethod
    def list_documents(self, session_id: str, user_id: str = "anonymous") -> List[DocumentRecord]:
        """Lists all documents in a session with user isolation."""

    @abc.abstractmethod
    def update_document_status(
        self,
        session_id: str,
        doc_id: str,
        status: str,
        element_count: int = 0,
        error: Optional[str] = None,
        user_id: str = "anonymous",
    ) -> DocumentRecord:
        """Updates document status, element count, and error string."""

    @abc.abstractmethod
    def create_version(self, version: DocumentVersionRecord) -> DocumentVersionRecord:
        """Records an immutable document version entry."""

    @abc.abstractmethod
    def get_latest_version(
        self,
        session_id: str,
        doc_id: str,
        is_patched: Optional[bool] = None,
        user_id: str = "anonymous",
    ) -> Optional[DocumentVersionRecord]:
        """Retrieves the latest version record for a document."""


class IProposalRepository(abc.ABC):
    @abc.abstractmethod
    def save_proposal(self, proposal: ProposalRecord) -> ProposalRecord:
        """Saves a proposed action proposal."""

    @abc.abstractmethod
    def get_proposal(self, session_id: str, action_id: str, user_id: str = "anonymous") -> Optional[ProposalRecord]:
        """Retrieves a proposal, evaluating TTL expiration."""

    @abc.abstractmethod
    def claim_proposal_for_execution(self, session_id: str, action_id: str, user_id: str = "anonymous") -> ProposalRecord:
        """Atomically transitions status from 'proposed' to 'executing', preventing replays."""

    @abc.abstractmethod
    def update_proposal_status(self, session_id: str, action_id: str, status: str, user_id: str = "anonymous") -> ProposalRecord:
        """Updates proposal status (applied, rejected, stale, expired)."""

    @abc.abstractmethod
    def cleanup_stale_proposals(self, session_id: str, user_id: str = "anonymous") -> int:
        """Marks expired proposals as 'expired'."""


class ILineageRepository(abc.ABC):
    @abc.abstractmethod
    def log_mapping(self, record: LineageEventRecord) -> LineageEventRecord:
        """Persists a cryptographic lineage mapping record."""

    @abc.abstractmethod
    def get_by_session(self, session_id: str, user_id: str = "anonymous") -> List[LineageEventRecord]:
        """Retrieves lineage events for a session."""


class IPilotEventRepository(abc.ABC):
    @abc.abstractmethod
    def emit(self, event: PilotEventRecord) -> Optional[PilotEventRecord]:
        """Records a pilot observability event (fail-open guarantee)."""

    @abc.abstractmethod
    def get_all(self, session_id: Optional[str] = None, user_id: str = "anonymous") -> List[PilotEventRecord]:
        """Retrieves pilot events."""


class IWorkflowRepository(abc.ABC):
    """Canonical persistence for structured workflow intake state.

    The workflow a session is running, and which document holds which role in
    it, are production state: they must survive a browser refresh, a container
    restart and a redeploy. Document BYTES are not part of this contract — they
    stay in object storage and are referenced by document_id only.
    """

    @abc.abstractmethod
    def get_workflow(self, session_id: str, user_id: str = "anonymous") -> Optional[WorkflowRecord]:
        ...

    @abc.abstractmethod
    def save_workflow(self, workflow: WorkflowRecord) -> WorkflowRecord:
        ...

    @abc.abstractmethod
    def list_assignments(self, workflow_id: str,
                         user_id: str = "anonymous") -> List[WorkflowSlotAssignmentRecord]:
        ...

    @abc.abstractmethod
    def upsert_assignment(
        self, assignment: WorkflowSlotAssignmentRecord) -> WorkflowSlotAssignmentRecord:
        ...

    @abc.abstractmethod
    def delete_assignment(self, workflow_id: str, slot_id: str, document_id: str,
                          user_id: str = "anonymous") -> bool:
        ...

    @abc.abstractmethod
    def replace_assignments(self, workflow_id: str,
                            assignments: List[WorkflowSlotAssignmentRecord],
                            user_id: str = "anonymous") -> List[WorkflowSlotAssignmentRecord]:
        """Make the stored rows match `assignments` exactly: upsert, then prune."""
        ...

    @abc.abstractmethod
    def delete_workflow(self, session_id: str, user_id: str = "anonymous") -> bool:
        ...


@dataclass
class RepositoryBundle:
    sessions: ISessionRepository
    documents: IDocumentRepository
    proposals: IProposalRepository
    lineage: ILineageRepository
    pilot: IPilotEventRepository
    workflows: IWorkflowRepository
    check_health: Any


# ============================================================================
# LOCAL REPOSITORIES (DEV & TESTING)
# ============================================================================

class LocalSessionRepository(ISessionRepository):
    def __init__(self, upload_root: Path):
        self.upload_root = upload_root
        self._sessions: Dict[str, SessionRecord] = {}

    def get_or_create(self, session_id: str, user_id: str = "anonymous", metadata: Optional[Dict[str, Any]] = None) -> SessionRecord:
        if session_id in self._sessions:
            rec = self._sessions[session_id]
            if user_id != "anonymous" and rec.user_id != "anonymous" and rec.user_id != user_id:
                raise RepositoryError("User isolation violation: unauthorized session access.")
            return rec

        rec = SessionRecord(session_id=session_id, user_id=user_id, metadata=metadata or {})
        self._sessions[session_id] = rec
        return rec

    def get(self, session_id: str, user_id: str = "anonymous") -> Optional[SessionRecord]:
        rec = self._sessions.get(session_id)
        if rec and user_id != "anonymous" and rec.user_id != "anonymous" and rec.user_id != user_id:
            raise RepositoryError("User isolation violation: unauthorized session access.")
        return rec


class LocalDocumentRepository(IDocumentRepository):
    def __init__(self, upload_root: Path):
        self.upload_root = upload_root
        self._documents: Dict[Tuple[str, str], DocumentRecord] = {}
        self._versions: Dict[str, List[DocumentVersionRecord]] = {}

    def save_document(self, doc: DocumentRecord) -> DocumentRecord:
        self._documents[(doc.session_id, doc.doc_id)] = doc
        return doc

    def get_document(self, session_id: str, doc_id: str, user_id: str = "anonymous") -> Optional[DocumentRecord]:
        doc = self._documents.get((session_id, doc_id))
        if doc and user_id != "anonymous" and doc.user_id != "anonymous" and doc.user_id != user_id:
            raise RepositoryError("User isolation violation: unauthorized document access.")
        return doc

    def list_documents(self, session_id: str, user_id: str = "anonymous") -> List[DocumentRecord]:
        results = []
        for (s_id, _), doc in self._documents.items():
            if s_id == session_id:
                if user_id != "anonymous" and doc.user_id != "anonymous" and doc.user_id != user_id:
                    continue
                results.append(doc)
        return results

    def update_document_status(
        self,
        session_id: str,
        doc_id: str,
        status: str,
        element_count: int = 0,
        error: Optional[str] = None,
        user_id: str = "anonymous",
    ) -> DocumentRecord:
        doc = self.get_document(session_id, doc_id, user_id=user_id)
        if not doc:
            raise RepositoryError(f"Document '{doc_id}' not found in session '{session_id}'.")
        doc.status = status
        doc.element_count = element_count
        doc.error = error
        doc.updated_at = datetime.now(timezone.utc).isoformat()
        return doc

    def create_version(self, version: DocumentVersionRecord) -> DocumentVersionRecord:
        key = f"{version.session_id}:{version.doc_id}"
        if key not in self._versions:
            self._versions[key] = []
        self._versions[key].append(version)
        return version

    def get_latest_version(
        self,
        session_id: str,
        doc_id: str,
        is_patched: Optional[bool] = None,
        user_id: str = "anonymous",
    ) -> Optional[DocumentVersionRecord]:
        key = f"{session_id}:{doc_id}"
        versions = self._versions.get(key, [])
        filtered = [
            v for v in versions
            if (is_patched is None or v.is_patched == is_patched)
            and (user_id == "anonymous" or v.user_id == "anonymous" or v.user_id == user_id)
        ]
        return filtered[-1] if filtered else None


class LocalProposalRepository(IProposalRepository):
    def __init__(self, upload_root: Path):
        self.upload_root = upload_root
        self._proposals: Dict[Tuple[str, str], ProposalRecord] = {}

    def _lock(self, session_id: str) -> FileLock:
        lock_dir = self.upload_root / session_id
        lock_dir.mkdir(parents=True, exist_ok=True)
        return FileLock(str(lock_dir / "proposals.lock"), timeout=10)

    def save_proposal(self, proposal: ProposalRecord) -> ProposalRecord:
        with self._lock(proposal.session_id):
            self._proposals[(proposal.session_id, proposal.action_id)] = proposal
            return proposal

    def get_proposal(self, session_id: str, action_id: str, user_id: str = "anonymous") -> Optional[ProposalRecord]:
        with self._lock(session_id):
            p = self._proposals.get((session_id, action_id))
            if not p:
                return None
            if user_id != "anonymous" and p.user_id != "anonymous" and p.user_id != user_id:
                raise RepositoryError("User isolation violation: unauthorized proposal access.")

            # TTL evaluation
            try:
                created_dt = datetime.fromisoformat(p.created_at)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > (created_dt + timedelta(seconds=p.ttl_seconds)):
                    if p.status == "proposed":
                        p.status = "expired"
            except Exception:
                pass
            return p

    def claim_proposal_for_execution(self, session_id: str, action_id: str, user_id: str = "anonymous") -> ProposalRecord:
        with self._lock(session_id):
            p = self._proposals.get((session_id, action_id))
            if not p:
                raise ValueError(f"Action proposal '{action_id}' not found or has expired.")
            if user_id != "anonymous" and p.user_id != "anonymous" and p.user_id != user_id:
                raise RepositoryError("User isolation violation: unauthorized proposal access.")

            # Check TTL
            try:
                created_dt = datetime.fromisoformat(p.created_at)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > (created_dt + timedelta(seconds=p.ttl_seconds)):
                    p.status = "expired"
                    raise ValueError(f"Action proposal '{action_id}' has expired (TTL exceeded).")
            except Exception as exc:
                if "TTL exceeded" in str(exc):
                    raise

            if p.status == "applied":
                raise ValueError(f"Action proposal '{action_id}' has already been applied.")
            if p.status == "executing":
                raise ValueError(f"Action proposal '{action_id}' is already being executed.")
            if p.status == "rejected":
                raise ValueError(f"Action proposal '{action_id}' was rejected.")
            if p.status == "expired":
                raise ValueError(f"Action proposal '{action_id}' has expired (TTL exceeded).")
            if p.status == "stale":
                raise ValueError(f"Action proposal '{action_id}' is stale and cannot be executed.")
            if p.status != "proposed":
                raise ValueError(f"Action proposal '{action_id}' is not in 'proposed' state (status: '{p.status}').")

            # Transition to executing atomically under lock
            p.status = "executing"
            p.updated_at = datetime.now(timezone.utc).isoformat()
            return p

    def update_proposal_status(self, session_id: str, action_id: str, status: str, user_id: str = "anonymous") -> ProposalRecord:
        with self._lock(session_id):
            p = self._proposals.get((session_id, action_id))
            if not p:
                raise ValueError(f"Proposal '{action_id}' not found in session '{session_id}'.")
            if user_id != "anonymous" and p.user_id != "anonymous" and p.user_id != user_id:
                raise RepositoryError("User isolation violation: unauthorized proposal access.")
            p.status = status
            p.updated_at = datetime.now(timezone.utc).isoformat()
            return p

    def cleanup_stale_proposals(self, session_id: str, user_id: str = "anonymous") -> int:
        with self._lock(session_id):
            now = datetime.now(timezone.utc)
            count = 0
            for (s_id, _), p in self._proposals.items():
                if s_id == session_id and p.status == "proposed":
                    if user_id != "anonymous" and p.user_id != "anonymous" and p.user_id != user_id:
                        continue
                    try:
                        created_dt = datetime.fromisoformat(p.created_at)
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        if now > (created_dt + timedelta(seconds=p.ttl_seconds)):
                            p.status = "expired"
                            count += 1
                    except Exception:
                        pass
            return count


class LocalLineageRepository(ILineageRepository):
    def __init__(self, upload_root: Path):
        self.upload_root = upload_root
        self._events: List[LineageEventRecord] = []

    def log_mapping(self, record: LineageEventRecord) -> LineageEventRecord:
        self._events.append(record)
        return record

    def get_by_session(self, session_id: str, user_id: str = "anonymous") -> List[LineageEventRecord]:
        return [
            e for e in self._events
            if e.session_id == session_id
            and (user_id == "anonymous" or e.user_id == "anonymous" or e.user_id == user_id)
        ]


class LocalPilotEventRepository(IPilotEventRepository):
    def __init__(self, upload_root: Path):
        self.upload_root = upload_root
        self._events: List[PilotEventRecord] = []

    def emit(self, event: PilotEventRecord) -> Optional[PilotEventRecord]:
        try:
            self._events.append(event)
            return event
        except Exception:
            return None

    def get_all(self, session_id: Optional[str] = None, user_id: str = "anonymous") -> List[PilotEventRecord]:
        return [
            e for e in self._events
            if (session_id is None or e.session_id == session_id)
            and (user_id == "anonymous" or e.user_id == "anonymous" or e.user_id == user_id)
        ]


class LocalWorkflowRepository(IWorkflowRepository):
    """Development/test representation of workflow state, backed by a JSON file.

    Unlike the other Local repositories (which are in-memory and therefore reset
    with the process), this one persists to disk so local development matches the
    production guarantee a developer is testing: refresh the browser, restart the
    server, the workflow is still there.

    This is NOT the production authority — that is SupabaseWorkflowRepository.
    """

    FILENAME = "workflow_state.json"

    def __init__(self, upload_root: Path):
        self.upload_root = upload_root

    # -- file plumbing --------------------------------------------------

    def _dir(self, session_id: str) -> Path:
        return self.upload_root / session_id

    def _path(self, session_id: str) -> Path:
        return self._dir(session_id) / self.FILENAME

    def _lock(self, session_id: str) -> FileLock:
        directory = self._dir(session_id)
        directory.mkdir(parents=True, exist_ok=True)
        return FileLock(str(directory / "workflow_state.lock"), timeout=10)

    def _read(self, session_id: str) -> Dict[str, Any]:
        path = self._path(session_id)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, session_id: str, data: Dict[str, Any]) -> None:
        self._dir(session_id).mkdir(parents=True, exist_ok=True)
        self._path(session_id).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _session_for_workflow(self, workflow_id: str) -> Optional[str]:
        """Workflow ids are session-scoped; find the session that owns one."""
        if not self.upload_root.is_dir():
            return None
        for directory in self.upload_root.iterdir():
            if not directory.is_dir():
                continue
            data = self._read(directory.name)
            if data.get("workflow", {}).get("workflow_id") == workflow_id:
                return directory.name
        return None

    @staticmethod
    def _authorized(row_user: str, user_id: str) -> bool:
        return user_id == "anonymous" or row_user == "anonymous" or row_user == user_id

    # -- interface ------------------------------------------------------

    def get_workflow(self, session_id: str, user_id: str = "anonymous") -> Optional[WorkflowRecord]:
        row = self._read(session_id).get("workflow")
        if not row:
            return None
        if not self._authorized(row.get("user_id", "anonymous"), user_id):
            raise RepositoryError("User isolation violation: unauthorized workflow access.")
        return WorkflowRecord(**row)

    def save_workflow(self, workflow: WorkflowRecord) -> WorkflowRecord:
        with self._lock(workflow.session_id):
            data = self._read(workflow.session_id)
            existing = data.get("workflow")
            if existing and not self._authorized(existing.get("user_id", "anonymous"),
                                                 workflow.user_id):
                raise RepositoryError("User isolation violation: unauthorized workflow write.")
            workflow.updated_at = datetime.now(timezone.utc).isoformat()
            if existing:
                workflow.created_at = existing.get("created_at", workflow.created_at)
            data["workflow"] = asdict(workflow)
            data.setdefault("assignments", [])
            self._write(workflow.session_id, data)
        return workflow

    def list_assignments(self, workflow_id: str,
                         user_id: str = "anonymous") -> List[WorkflowSlotAssignmentRecord]:
        session_id = self._session_for_workflow(workflow_id)
        if session_id is None:
            return []
        rows = self._read(session_id).get("assignments", [])
        return [WorkflowSlotAssignmentRecord(**row) for row in rows
                if row.get("workflow_id") == workflow_id
                and self._authorized(row.get("user_id", "anonymous"), user_id)]

    def upsert_assignment(
        self, assignment: WorkflowSlotAssignmentRecord) -> WorkflowSlotAssignmentRecord:
        with self._lock(assignment.session_id):
            data = self._read(assignment.session_id)
            rows = data.get("assignments", [])
            assignment.updated_at = datetime.now(timezone.utc).isoformat()
            kept = []
            for row in rows:
                same = (row.get("workflow_id") == assignment.workflow_id
                        and row.get("slot_id") == assignment.slot_id
                        and row.get("document_id") == assignment.document_id)
                if same:
                    if not self._authorized(row.get("user_id", "anonymous"), assignment.user_id):
                        raise RepositoryError(
                            "User isolation violation: unauthorized assignment write.")
                    assignment.created_at = row.get("created_at", assignment.created_at)
                    continue
                kept.append(row)
            kept.append(asdict(assignment))
            data["assignments"] = kept
            self._write(assignment.session_id, data)
        return assignment

    def delete_assignment(self, workflow_id: str, slot_id: str, document_id: str,
                          user_id: str = "anonymous") -> bool:
        session_id = self._session_for_workflow(workflow_id)
        if session_id is None:
            return False
        with self._lock(session_id):
            data = self._read(session_id)
            rows = data.get("assignments", [])
            kept = [
                row for row in rows
                if not (row.get("workflow_id") == workflow_id
                        and row.get("slot_id") == slot_id
                        and row.get("document_id") == document_id
                        and self._authorized(row.get("user_id", "anonymous"), user_id))
            ]
            removed = len(kept) != len(rows)
            data["assignments"] = kept
            self._write(session_id, data)
        return removed

    def replace_assignments(self, workflow_id: str,
                            assignments: List[WorkflowSlotAssignmentRecord],
                            user_id: str = "anonymous") -> List[WorkflowSlotAssignmentRecord]:
        session_id = (assignments[0].session_id if assignments
                      else self._session_for_workflow(workflow_id))
        if session_id is None:
            return []
        with self._lock(session_id):
            data = self._read(session_id)
            previous = {
                (row.get("slot_id"), row.get("document_id")): row
                for row in data.get("assignments", [])
                if row.get("workflow_id") == workflow_id
            }
            now = datetime.now(timezone.utc).isoformat()
            rows = []
            for assignment in assignments:
                prior = previous.get((assignment.slot_id, assignment.document_id))
                if prior and not self._authorized(prior.get("user_id", "anonymous"), user_id):
                    raise RepositoryError(
                        "User isolation violation: unauthorized assignment write.")
                if prior:
                    assignment.created_at = prior.get("created_at", assignment.created_at)
                assignment.updated_at = now
                rows.append(asdict(assignment))

            # Rows belonging to other workflows in the same session are untouched.
            other = [row for row in data.get("assignments", [])
                     if row.get("workflow_id") != workflow_id]
            data["assignments"] = other + rows
            self._write(session_id, data)
        return assignments

    def delete_workflow(self, session_id: str, user_id: str = "anonymous") -> bool:
        with self._lock(session_id):
            data = self._read(session_id)
            row = data.get("workflow")
            if not row:
                return False
            if not self._authorized(row.get("user_id", "anonymous"), user_id):
                raise RepositoryError("User isolation violation: unauthorized workflow delete.")
            self._write(session_id, {"workflow": None, "assignments": []})
        return True


# ============================================================================
# SUPABASE REPOSITORIES (PRODUCTION)
# ============================================================================

class SupabaseRepository(ISessionRepository, IDocumentRepository, IProposalRepository, ILineageRepository, IPilotEventRepository):
    """Production Supabase Postgres repository adapter."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        if not self.config.supabase_url or not self.config.supabase_service_role_key:
            raise RepositoryError("SupabaseRepository requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")

        try:
            from supabase import create_client, Client
            self._client: Client = create_client(
                self.config.supabase_url,
                self.config.supabase_service_role_key,
            )
        except ImportError:
            raise RepositoryError("supabase-py library is not installed. Install with `pip install supabase`.")
        except Exception as exc:
            raise RepositoryError(f"Failed to initialize Supabase client: {exc}") from exc

    # -- Sessions --
    def get_or_create(self, session_id: str, user_id: str = "anonymous", metadata: Optional[Dict[str, Any]] = None) -> SessionRecord:
        try:
            res = self._client.table("sessions").select("*").eq("session_id", session_id).execute()
            if res.data:
                row = res.data[0]
                if user_id != "anonymous" and row.get("user_id") != "anonymous" and row.get("user_id") != user_id:
                    raise RepositoryError("User isolation violation: unauthorized session access.")
                return SessionRecord(**row)

            # Insert new
            new_row = {
                "session_id": session_id,
                "user_id": user_id,
                "status": "active",
                "metadata": metadata or {},
            }
            res_ins = self._client.table("sessions").insert(new_row).execute()
            return SessionRecord(**res_ins.data[0])
        except Exception as exc:
            raise RepositoryError(f"Supabase session get_or_create failed: {exc}") from exc

    def get(self, session_id: str, user_id: str = "anonymous") -> Optional[SessionRecord]:
        try:
            res = self._client.table("sessions").select("*").eq("session_id", session_id).execute()
            if not res.data:
                return None
            row = res.data[0]
            if user_id != "anonymous" and row.get("user_id") != "anonymous" and row.get("user_id") != user_id:
                raise RepositoryError("User isolation violation: unauthorized session access.")
            return SessionRecord(**row)
        except Exception as exc:
            raise RepositoryError(f"Supabase session get failed: {exc}") from exc

    # -- Documents --
    def save_document(self, doc: DocumentRecord) -> DocumentRecord:
        try:
            data = asdict(doc)
            self._client.table("documents").upsert(data).execute()
            return doc
        except Exception as exc:
            raise RepositoryError(f"Supabase save_document failed: {exc}") from exc

    def get_document(self, session_id: str, doc_id: str, user_id: str = "anonymous") -> Optional[DocumentRecord]:
        try:
            query = self._client.table("documents").select("*").eq("session_id", session_id).eq("doc_id", doc_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            return DocumentRecord(**res.data[0]) if res.data else None
        except Exception as exc:
            raise RepositoryError(f"Supabase get_document failed: {exc}") from exc

    def list_documents(self, session_id: str, user_id: str = "anonymous") -> List[DocumentRecord]:
        try:
            query = self._client.table("documents").select("*").eq("session_id", session_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            return [DocumentRecord(**row) for row in res.data]
        except Exception as exc:
            raise RepositoryError(f"Supabase list_documents failed: {exc}") from exc

    def update_document_status(
        self,
        session_id: str,
        doc_id: str,
        status: str,
        element_count: int = 0,
        error: Optional[str] = None,
        user_id: str = "anonymous",
    ) -> DocumentRecord:
        try:
            now = datetime.now(timezone.utc).isoformat()
            query = self._client.table("documents").update({
                "status": status,
                "element_count": element_count,
                "error": error,
                "updated_at": now,
            }).eq("session_id", session_id).eq("doc_id", doc_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            if not res.data:
                raise RepositoryError(f"Document '{doc_id}' not found in session '{session_id}'.")
            return DocumentRecord(**res.data[0])
        except Exception as exc:
            raise RepositoryError(f"Supabase update_document_status failed: {exc}") from exc

    def create_version(self, version: DocumentVersionRecord) -> DocumentVersionRecord:
        try:
            self._client.table("document_versions").insert(asdict(version)).execute()
            return version
        except Exception as exc:
            raise RepositoryError(f"Supabase create_version failed: {exc}") from exc

    def get_latest_version(
        self,
        session_id: str,
        doc_id: str,
        is_patched: Optional[bool] = None,
        user_id: str = "anonymous",
    ) -> Optional[DocumentVersionRecord]:
        try:
            query = self._client.table("document_versions").select("*").eq("session_id", session_id).eq("doc_id", doc_id)
            if is_patched is not None:
                query = query.eq("is_patched", is_patched)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.order("version_number", desc=True).limit(1).execute()
            return DocumentVersionRecord(**res.data[0]) if res.data else None
        except Exception as exc:
            raise RepositoryError(f"Supabase get_latest_version failed: {exc}") from exc

    # -- Proposals --
    def save_proposal(self, proposal: ProposalRecord) -> ProposalRecord:
        try:
            self._client.table("proposals").upsert(asdict(proposal)).execute()
            return proposal
        except Exception as exc:
            raise RepositoryError(f"Supabase save_proposal failed: {exc}") from exc

    def get_proposal(self, session_id: str, action_id: str, user_id: str = "anonymous") -> Optional[ProposalRecord]:
        try:
            query = self._client.table("proposals").select("*").eq("session_id", session_id).eq("action_id", action_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            if not res.data:
                return None
            p = ProposalRecord(**res.data[0])
            # TTL check
            try:
                created_dt = datetime.fromisoformat(p.created_at)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > (created_dt + timedelta(seconds=p.ttl_seconds)):
                    if p.status == "proposed":
                        self.update_proposal_status(session_id, action_id, "expired", user_id=user_id)
                        p.status = "expired"
            except Exception:
                pass
            return p
        except Exception as exc:
            raise RepositoryError(f"Supabase get_proposal failed: {exc}") from exc

    def claim_proposal_for_execution(self, session_id: str, action_id: str, user_id: str = "anonymous") -> ProposalRecord:
        try:
            proposal = self.get_proposal(session_id, action_id, user_id=user_id)
            if not proposal:
                raise ValueError(f"Action proposal '{action_id}' not found or has expired.")

            if proposal.status == "applied":
                raise ValueError(f"Action proposal '{action_id}' has already been applied.")
            if proposal.status == "executing":
                raise ValueError(f"Action proposal '{action_id}' is already being executed.")
            if proposal.status == "rejected":
                raise ValueError(f"Action proposal '{action_id}' was rejected.")
            if proposal.status == "expired":
                raise ValueError(f"Action proposal '{action_id}' has expired (TTL exceeded).")
            if proposal.status == "stale":
                raise ValueError(f"Action proposal '{action_id}' is stale and cannot be executed.")
            if proposal.status != "proposed":
                raise ValueError(f"Action proposal '{action_id}' is not in 'proposed' state (status: '{proposal.status}').")

            # Atomic conditional update: status must still be 'proposed'
            now = datetime.now(timezone.utc).isoformat()
            res = self._client.table("proposals").update({
                "status": "executing",
                "updated_at": now,
            }).eq("session_id", session_id).eq("action_id", action_id).eq("status", "proposed").execute()

            if not res.data:
                raise ValueError(f"Proposal '{action_id}' claim collision or state modified concurrently.")
            return ProposalRecord(**res.data[0])
        except ValueError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Supabase claim_proposal_for_execution failed: {exc}") from exc

    def update_proposal_status(self, session_id: str, action_id: str, status: str, user_id: str = "anonymous") -> ProposalRecord:
        try:
            now = datetime.now(timezone.utc).isoformat()
            query = self._client.table("proposals").update({
                "status": status,
                "updated_at": now,
            }).eq("session_id", session_id).eq("action_id", action_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            if not res.data:
                raise ValueError(f"Proposal '{action_id}' not found in session '{session_id}'.")
            return ProposalRecord(**res.data[0])
        except ValueError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Supabase update_proposal_status failed: {exc}") from exc

    def cleanup_stale_proposals(self, session_id: str, user_id: str = "anonymous") -> int:
        try:
            # Query proposals in 'proposed' state
            query = self._client.table("proposals").select("*").eq("session_id", session_id).eq("status", "proposed")
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            now = datetime.now(timezone.utc)
            expired_count = 0
            for row in res.data:
                try:
                    created_dt = datetime.fromisoformat(row["created_at"])
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                    if now > (created_dt + timedelta(seconds=row.get("ttl_seconds", 86400))):
                        self.update_proposal_status(session_id, row["action_id"], "expired", user_id=user_id)
                        expired_count += 1
                except Exception:
                    pass
            return expired_count
        except Exception:
            return 0

    # -- Lineage --
    def log_mapping(self, record: LineageEventRecord) -> LineageEventRecord:
        try:
            self._client.table("lineage_events").insert(asdict(record)).execute()
            return record
        except Exception as exc:
            raise RepositoryError(f"Supabase log_mapping failed: {exc}") from exc

    def get_by_session(self, session_id: str, user_id: str = "anonymous") -> List[LineageEventRecord]:
        try:
            query = self._client.table("lineage_events").select("*").eq("session_id", session_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.order("timestamp", desc=False).execute()
            return [LineageEventRecord(**row) for row in res.data]
        except Exception as exc:
            raise RepositoryError(f"Supabase get_by_session failed: {exc}") from exc

    # -- Pilot Events --
    def emit(self, event: PilotEventRecord) -> Optional[PilotEventRecord]:
        try:
            self._client.table("pilot_events").insert(asdict(event)).execute()
            return event
        except Exception:
            return None

    def get_all(self, session_id: Optional[str] = None, user_id: str = "anonymous") -> List[PilotEventRecord]:
        try:
            query = self._client.table("pilot_events").select("*")
            if session_id is not None:
                query = query.eq("session_id", session_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.order("timestamp", desc=False).execute()
            return [PilotEventRecord(**row) for row in res.data]
        except Exception:
            return []

    def check_health(self) -> Tuple[bool, str]:
        try:
            # Query sessions table with limit 1 to probe connection
            self._client.table("sessions").select("session_id").limit(1).execute()
            return True, "Supabase Postgres database is accessible."
        except Exception as exc:
            return False, f"Supabase Postgres health check failed: {exc}"


class SupabaseWorkflowRepository(IWorkflowRepository):
    """Production workflow-state adapter — Supabase Postgres.

    Tables: `workflow_sessions`, `workflow_slot_assignments`
    (see migrations/002_workflow_intake.sql).

    Nothing here stores document bytes; `document_id` references a row in
    `documents`, whose bytes live in Supabase Storage. Every read and write is
    scoped by user_id so one user's workflow is never visible to another.
    """

    WORKFLOWS = "workflow_sessions"
    ASSIGNMENTS = "workflow_slot_assignments"

    def __init__(self, config: Optional[AppConfig] = None, client: Any = None):
        self.config = config or get_config()
        if client is not None:
            self._client = client
            return
        if not self.config.supabase_url or not self.config.supabase_service_role_key:
            raise RepositoryError(
                "SupabaseWorkflowRepository requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        try:
            from supabase import create_client
            self._client = create_client(
                self.config.supabase_url, self.config.supabase_service_role_key)
        except ImportError:
            raise RepositoryError(
                "supabase-py library is not installed. Install with `pip install supabase`.")
        except Exception as exc:
            raise RepositoryError(f"Failed to initialize Supabase client: {exc}") from exc

    # -- helpers --------------------------------------------------------

    @staticmethod
    def _assignment_from_row(row: Dict[str, Any]) -> WorkflowSlotAssignmentRecord:
        known = {f for f in WorkflowSlotAssignmentRecord.__dataclass_fields__}
        payload = {k: v for k, v in row.items() if k in known}
        payload["reasons"] = payload.get("reasons") or []
        payload["signals"] = payload.get("signals") or {}
        return WorkflowSlotAssignmentRecord(**payload)

    @staticmethod
    def _workflow_from_row(row: Dict[str, Any]) -> WorkflowRecord:
        known = {f for f in WorkflowRecord.__dataclass_fields__}
        return WorkflowRecord(**{k: v for k, v in row.items() if k in known})

    # -- interface ------------------------------------------------------

    def get_workflow(self, session_id: str, user_id: str = "anonymous") -> Optional[WorkflowRecord]:
        try:
            query = self._client.table(self.WORKFLOWS).select("*").eq("session_id", session_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            return self._workflow_from_row(res.data[0]) if res.data else None
        except Exception as exc:
            raise RepositoryError(f"Supabase get_workflow failed: {exc}") from exc

    def save_workflow(self, workflow: WorkflowRecord) -> WorkflowRecord:
        try:
            workflow.updated_at = datetime.now(timezone.utc).isoformat()
            self._client.table(self.WORKFLOWS).upsert(
                asdict(workflow), on_conflict="workflow_id").execute()
            return workflow
        except Exception as exc:
            raise RepositoryError(f"Supabase save_workflow failed: {exc}") from exc

    def list_assignments(self, workflow_id: str,
                         user_id: str = "anonymous") -> List[WorkflowSlotAssignmentRecord]:
        try:
            query = self._client.table(self.ASSIGNMENTS).select("*").eq("workflow_id", workflow_id)
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.order("created_at", desc=False).execute()
            return [self._assignment_from_row(row) for row in res.data]
        except Exception as exc:
            raise RepositoryError(f"Supabase list_assignments failed: {exc}") from exc

    def upsert_assignment(
        self, assignment: WorkflowSlotAssignmentRecord) -> WorkflowSlotAssignmentRecord:
        try:
            assignment.updated_at = datetime.now(timezone.utc).isoformat()
            self._client.table(self.ASSIGNMENTS).upsert(
                asdict(assignment), on_conflict="workflow_id,slot_id,document_id").execute()
            return assignment
        except Exception as exc:
            raise RepositoryError(f"Supabase upsert_assignment failed: {exc}") from exc

    def delete_assignment(self, workflow_id: str, slot_id: str, document_id: str,
                          user_id: str = "anonymous") -> bool:
        try:
            query = (self._client.table(self.ASSIGNMENTS).delete()
                     .eq("workflow_id", workflow_id)
                     .eq("slot_id", slot_id)
                     .eq("document_id", document_id))
            if user_id != "anonymous":
                query = query.eq("user_id", user_id)
            res = query.execute()
            return bool(res.data)
        except Exception as exc:
            raise RepositoryError(f"Supabase delete_assignment failed: {exc}") from exc

    def replace_assignments(self, workflow_id: str,
                            assignments: List[WorkflowSlotAssignmentRecord],
                            user_id: str = "anonymous") -> List[WorkflowSlotAssignmentRecord]:
        try:
            now = datetime.now(timezone.utc).isoformat()
            for assignment in assignments:
                assignment.updated_at = now
            if assignments:
                self._client.table(self.ASSIGNMENTS).upsert(
                    [asdict(a) for a in assignments],
                    on_conflict="workflow_id,slot_id,document_id").execute()

            # Prune rows that are no longer part of the workflow. Done after the
            # upsert so a failure mid-way leaves the previous state readable
            # rather than a half-empty slot set.
            keep = {(a.slot_id, a.document_id) for a in assignments}
            for existing in self.list_assignments(workflow_id, user_id=user_id):
                if (existing.slot_id, existing.document_id) not in keep:
                    self.delete_assignment(workflow_id, existing.slot_id,
                                           existing.document_id, user_id=user_id)
            return assignments
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Supabase replace_assignments failed: {exc}") from exc

    def delete_workflow(self, session_id: str, user_id: str = "anonymous") -> bool:
        try:
            workflow = self.get_workflow(session_id, user_id=user_id)
            if workflow is None:
                return False
            assignments = self._client.table(self.ASSIGNMENTS).delete().eq(
                "workflow_id", workflow.workflow_id)
            if user_id != "anonymous":
                assignments = assignments.eq("user_id", user_id)
            assignments.execute()
            self._client.table(self.WORKFLOWS).delete().eq(
                "workflow_id", workflow.workflow_id).execute()
            return True
        except Exception as exc:
            raise RepositoryError(f"Supabase delete_workflow failed: {exc}") from exc


# ============================================================================
# FACTORY
# ============================================================================

# Where the local (development/test) repositories keep their state. Module-level
# so a test can point it at a temp directory before building the bundle.
UPLOAD_ROOT = Path(__file__).resolve().parents[1] / ".uploads"

_REPOSITORIES_BUNDLE: Optional[RepositoryBundle] = None


def get_repositories(config: Optional[AppConfig] = None) -> RepositoryBundle:
    """Returns the configured RepositoryBundle singleton."""
    global _REPOSITORIES_BUNDLE
    cfg = config or get_config()
    if _REPOSITORIES_BUNDLE is None:
        if cfg.database_backend == DatabaseBackend.SUPABASE.value:
            supa = SupabaseRepository(cfg)
            _REPOSITORIES_BUNDLE = RepositoryBundle(
                sessions=supa,
                documents=supa,
                proposals=supa,
                lineage=supa,
                pilot=supa,
                workflows=SupabaseWorkflowRepository(cfg),
                check_health=supa.check_health,
            )
        else:
            upload_root = UPLOAD_ROOT
            upload_root.mkdir(parents=True, exist_ok=True)
            sess = LocalSessionRepository(upload_root)
            docs = LocalDocumentRepository(upload_root)
            props = LocalProposalRepository(upload_root)
            line = LocalLineageRepository(upload_root)
            pilot = LocalPilotEventRepository(upload_root)
            flows = LocalWorkflowRepository(upload_root)

            def local_health() -> Tuple[bool, str]:
                return True, "Local in-memory/file repository is operational."

            _REPOSITORIES_BUNDLE = RepositoryBundle(
                sessions=sess,
                documents=docs,
                proposals=props,
                lineage=line,
                pilot=pilot,
                workflows=flows,
                check_health=local_health,
            )
    return _REPOSITORIES_BUNDLE


def reset_repositories() -> None:
    """Resets repository singleton (used for tests)."""
    global _REPOSITORIES_BUNDLE
    _REPOSITORIES_BUNDLE = None
