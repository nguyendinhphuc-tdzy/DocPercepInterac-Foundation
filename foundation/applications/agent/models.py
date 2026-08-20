"""Domain models for the Foundation Agent Architecture and Intent Layer.

Canonical identities are strictly (doc_id, element_id). `index` is only
display metadata and is never used to address or execute targets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Authoritative reference to a specific document element."""
    doc_id: str
    element_id: str
    element_name: str
    type: str
    text_snippet: Optional[str] = None
    doc_name: Optional[str] = None


class AgentStep(BaseModel):
    """User-visible execution summary step (no hidden chain-of-thought)."""
    label: str
    status: Literal["done", "active", "pending"] = "done"


class ProposedAction(BaseModel):
    """Structured proposal for document mutation — requires explicit user confirmation."""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["update_element", "batch_update"] = "update_element"
    doc_id: str
    doc_name: str
    element_id: str
    element_name: str
    current_value: str
    proposed_value: str
    rationale: str
    requires_confirmation: bool = True
    status: Literal["proposed", "executing", "applied", "rejected", "expired", "stale", "failed"] = "proposed"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl_seconds: int = 86400
    doc_hash: Optional[str] = None
    value_fingerprint: Optional[str] = None
    target_anchor: Optional[dict[str, Any]] = None


class AgentIntent(BaseModel):
    """Classified user intent."""
    intent_type: Literal["summarize", "inspect", "compare", "propose_edit", "query", "navigate"]
    target_doc_id: Optional[str] = None
    target_element_id: Optional[str] = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class AgentContext(BaseModel):
    """Structured document context supplied to the Agent."""
    session_id: Optional[str] = None
    active_doc_id: Optional[str] = None
    selected_element: Optional[dict[str, Any]] = None
    available_documents: list[dict[str, Any]] = Field(default_factory=list)
    relevant_elements: list[dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# CENTRAL MODEL REGISTRY (single source of truth for backend + /api/agent/models)
# ----------------------------------------------------------------------------
# The frontend only ever sends an application-level model id from this table.
# Raw provider deployment/model names are resolved server-side and are never
# accepted from, nor echoed to, the browser.
#
# HARD RULE: there is no fallback anywhere in this layer. If the selected
# model's provider fails, the request fails with an explicit error. The system
# never picks a different model on the user's behalf.
# ============================================================================

ProviderId = Literal["workbench", "gemini"]

AgentModelId = Literal[
    "workbench_luna",
    "workbench_sol",
    "gemini_3_6_flash",
    "gemini_3_5_flash",
]


@dataclass(frozen=True)
class AgentModelSpec:
    """One user-selectable model: its provider and provider-native model name."""
    model_id: AgentModelId
    provider: ProviderId
    model: str          # provider-native deployment/model name — server-side only
    label: str          # user-facing name
    description: str    # user-facing subtitle
    group: str          # selector grouping label


AGENT_MODELS: dict[AgentModelId, AgentModelSpec] = {
    "workbench_luna": AgentModelSpec(
        model_id="workbench_luna",
        provider="workbench",
        model="gpt-5-6-luna-2026-07-09-gs-ae",
        label="Luna",
        description="Fast · Everyday tasks",
        group="Workbench",
    ),
    "workbench_sol": AgentModelSpec(
        model_id="workbench_sol",
        provider="workbench",
        model="gpt-5-6-sol-2026-07-09-gs-ae",
        label="Sol",
        description="Deep reasoning · Complex analysis",
        group="Workbench",
    ),
    "gemini_3_6_flash": AgentModelSpec(
        model_id="gemini_3_6_flash",
        provider="gemini",
        model="gemini-3.6-flash",
        label="Gemini 3.6 Flash",
        description="Fast · Local/demo",
        group="Gemini",
    ),
    "gemini_3_5_flash": AgentModelSpec(
        model_id="gemini_3_5_flash",
        provider="gemini",
        model="gemini-3.5-flash",
        label="Gemini 3.5 Flash",
        description="Gemini · Alternative",
        group="Gemini",
    ),
}

# Selector display order. Gemini 3.6 Flash is listed above Gemini 3.5 Flash
# purely as a presentation preference (it is the preferred Gemini option for
# local/demo use). Order carries NO routing or fallback meaning.
AGENT_MODEL_ORDER: tuple[AgentModelId, ...] = (
    "workbench_luna",
    "workbench_sol",
    "gemini_3_6_flash",
    "gemini_3_5_flash",
)

DEFAULT_MODEL: AgentModelId = "workbench_luna"


def resolve_agent_model(model_id: Optional[str]) -> AgentModelSpec:
    """Resolve an application-level model id against the strict server allowlist.

    An absent id means "the caller did not choose", which is the documented
    default (Luna) — not a fallback from a failed model. Any value that is
    present but not in the allowlist is rejected; it is never coerced.
    """
    if model_id is None:
        return AGENT_MODELS[DEFAULT_MODEL]
    key = str(model_id).strip()
    if key in AGENT_MODELS:
        return AGENT_MODELS[key]  # type: ignore[index]
    raise ValueError(
        f"Unsupported model '{model_id}'. Supported models: {list(AGENT_MODEL_ORDER)}"
    )


def get_model_label(model_id: Optional[str]) -> str:
    """User-facing label for a model id, for error copy and badges."""
    try:
        return resolve_agent_model(model_id).label
    except ValueError:
        return "The selected model"


class AgentResponse(BaseModel):
    """Standardized Agent response payload."""
    response: str
    status: Literal["success", "error"] = "success"
    run_id: Optional[str] = None
    intent: Optional[str] = None
    model_id: AgentModelId = DEFAULT_MODEL
    provider: ProviderId = "workbench"
    steps: list[AgentStep] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    error: Optional[str] = None
