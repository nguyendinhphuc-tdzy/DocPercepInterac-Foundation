"""Foundation Agent Package.

Provides governed agent orchestrator, context builder, models, and action executor.
"""
from applications.agent.models import (
    AGENT_MODEL_ORDER,
    AGENT_MODELS,
    DEFAULT_MODEL,
    AgentContext,
    AgentIntent,
    AgentModelId,
    AgentModelSpec,
    AgentResponse,
    AgentStep,
    Citation,
    ProposedAction,
    ProviderId,
    get_model_label,
    resolve_agent_model,
)
from applications.agent.context_builder import ContextBuilder
from applications.agent.orchestrator import AgentOrchestrator
from applications.agent.proposal_store import ProposalStore
from applications.agent.action_executor import ActionExecutor
from applications.agent.providers import ModelProvider, get_provider

__all__ = [
    "AGENT_MODELS",
    "AGENT_MODEL_ORDER",
    "DEFAULT_MODEL",
    "AgentModelId",
    "AgentModelSpec",
    "ProviderId",
    "ModelProvider",
    "get_provider",
    "get_model_label",
    "resolve_agent_model",
    "AgentContext",
    "AgentIntent",
    "AgentResponse",
    "AgentStep",
    "Citation",
    "ProposedAction",
    "ContextBuilder",
    "AgentOrchestrator",
    "ProposalStore",
    "ActionExecutor",
]
