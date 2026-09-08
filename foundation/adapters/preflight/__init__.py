"""B1.1 deterministic package inspection; no mutation or native locators."""

from .ooxml import OoxmlPreflight, PreflightConfig
from .evidence import EvidenceArtifact, PreflightResult

__all__ = ['OoxmlPreflight', 'PreflightConfig', 'EvidenceArtifact', 'PreflightResult']
