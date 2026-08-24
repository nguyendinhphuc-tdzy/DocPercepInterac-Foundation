"""
Deterministic workflow intent classification (Phase PROD-RF-1)
=============================================================
Location: foundation/applications/agent/workflow_intents.py

A request made inside a structured workflow is routed by the WORKFLOW, not by a
language model. The authority is:

    workflow.workflow_type      (from the workflow repository)
    workflow slot assignments
    workflow readiness

and a fixed lexicon of execution/planning phrasings. Nothing here calls a model,
so classification is instant and identical on every run.

Why this exists
---------------
Before it, "roll forward local file từ 2023 lên 2024 đi" matched none of the
Agent's keyword branches (edit / summarize / search / compare) and fell through
to GENERAL DOCUMENT QUERY: an ~18-second model round trip that returned prose
claiming the roll-forward had been completed, while no governed execution had run
at all. Intent for a workflow the server already knows about must never be a
model's guess.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class WorkflowIntent(str, Enum):
    """Workflow-scoped intents the Agent dispatches deterministically."""
    ROLL_FORWARD = "roll_forward"
    ROLL_FORWARD_STATUS = "roll_forward_status"


# Phrasings that mean "run/plan the roll-forward", in the languages this product
# is used in. Matching is accent-insensitive, so "thực hiện" also matches
# "thuc hien". These are whole phrases, not single words: "forward" alone, or
# "file" alone, must never trigger a workflow execution route.
_EXECUTION_PHRASES = (
    "roll forward",
    "rollforward",
    "roll-forward",
    "roll fwd",
    "cuon so",          # "cuốn sổ" — colloquial VN for carrying the file forward
    "chuyen tiep local file",
    "cap nhat local file",
    "lam local file moi",
)

# A request that asks ABOUT the roll-forward rather than for it.
_STATUS_PHRASES = (
    "status",
    "trang thai",
    "san sang chua",
    "ready",
    "readiness",
    "con thieu gi",
    "what is missing",
    "what's missing",
    "blockers",
)

# Explicit approval is its own gesture and never a chat phrase: approval happens
# through the governed endpoint, so no lexicon here can ever approve anything.


def _normalise(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace and dashes.

    Accent stripping is what lets one lexicon serve "thực hiện" and "thuc hien";
    it never changes meaning because every phrase above is matched whole.
    """
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"[\s\-_]+", " ", stripped).strip()


@dataclass(frozen=True)
class IntentDecision:
    """Why a request was routed the way it was — auditable, not a black box."""
    intent: Optional[WorkflowIntent]
    matched_phrase: Optional[str] = None
    workflow_type: Optional[str] = None
    reason: str = ""

    @property
    def is_workflow_request(self) -> bool:
        return self.intent is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value if self.intent else None,
            "matched_phrase": self.matched_phrase,
            "workflow_type": self.workflow_type,
            "reason": self.reason,
            "classifier": "deterministic",
        }


class WorkflowIntentClassifier:
    """Routes a request by the active workflow. No model is consulted."""

    ROLL_FORWARD_WORKFLOW = "LOCAL_FILE_ROLL_FORWARD"

    @classmethod
    def classify(cls, message: str,
                 workflow: Optional[Dict[str, Any]]) -> IntentDecision:
        """Decide whether this message is a workflow request, and which one.

        `workflow` is the server's own structured workflow context (see
        api/routes/workflow.py). Absent it, there is no workflow to route into
        and the generic Agent branches keep their existing behaviour.
        """
        if not workflow:
            return IntentDecision(None, reason="no structured workflow is active for this session")

        workflow_type = workflow.get("workflow")
        if workflow_type != cls.ROLL_FORWARD_WORKFLOW:
            return IntentDecision(
                None, workflow_type=workflow_type,
                reason=f"active workflow '{workflow_type}' has no deterministic dispatch")

        text = _normalise(message)

        for phrase in _EXECUTION_PHRASES:
            if phrase in text:
                # A status question about the roll-forward is still a
                # roll-forward request; both are answered from workflow state,
                # and neither may fabricate a result.
                if any(status in text for status in _STATUS_PHRASES):
                    return IntentDecision(
                        WorkflowIntent.ROLL_FORWARD_STATUS, phrase, workflow_type,
                        "asks about roll-forward readiness inside an active roll-forward workflow")
                return IntentDecision(
                    WorkflowIntent.ROLL_FORWARD, phrase, workflow_type,
                    "roll-forward execution request inside an active roll-forward workflow")

        return IntentDecision(
            None, workflow_type=workflow_type,
            reason="no roll-forward execution phrasing in the request")


__all__ = ["WorkflowIntent", "IntentDecision", "WorkflowIntentClassifier"]
