"""Explicit human review decisions."""

from __future__ import annotations

from typing import Literal

from .base import TaskOwnedRecord, Text
from .enums import ObjectType, ReviewOutcome
from .refs import Actor, ChangeProposalRef, Ref, SourceRequirementRef


class ReviewDecision(TaskOwnedRecord):
    object_type: Literal[ObjectType.REVIEW_DECISION]
    change_proposal_ref: ChangeProposalRef
    reviewer: Actor
    outcome: ReviewOutcome
    reason: Text
    reviewed_evidence_refs: list[Ref]
    requested_source_requirement_refs: list[SourceRequirementRef]
