"""Bounded AI assistance interface with no authorization methods."""

from typing import Protocol

from foundation.domain import AIInteractionRecord, MappingProposal


class AIInterpretationPort(Protocol):
    def propose_mapping(self, interaction: AIInteractionRecord) -> MappingProposal: ...
