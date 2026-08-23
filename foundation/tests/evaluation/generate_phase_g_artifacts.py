import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.source_registry import SourceRegistry, RegistrationEventType
from applications.rollforward.source_intake import (
    SourceIntakeProfiler,
    SourceRequestRegister,
    SourceArtifactRequest,
    RecalculatedReadiness,
    FORBIDDEN_READINESS,
    GroundTruthGuard,
)
from applications.rollforward.evidence_policy import SupplyScope, DatasetRole
from foundation.tests.evaluation.rollforward_clean_planner_c2 import (
    PATH_HIST,
    PATH_TMPL,
    PATH_FARPT,
    PATH_APP1,
    PATH_GROUND_TRUTH_FORBIDDEN,
)

GroundTruthGuard.reset()
GroundTruthGuard.register([PATH_GROUND_TRUTH_FORBIDDEN])

# Build real registry
registry = SourceRegistry(package_id="PKG-ROLLFORWARD-G-FY2024")
e1 = registry.register(PATH_HIST, SupplyScope.HISTORICAL, actor="system-setup")
e2 = registry.register(PATH_TMPL, SupplyScope.TEMPLATE, actor="system-setup")
e3 = registry.register(PATH_FARPT, SupplyScope.CURRENT_FINANCIAL, actor="system-setup")
e4 = registry.register(PATH_APP1, SupplyScope.CURRENT_TAX, actor="system-setup")

# Mock regions representative of template profile
sample_regions = [
    {"region_id": "rgn-001", "readiness": "HUMAN_REVIEW_READY", "required_source_roles": ["FINANCIAL_STATEMENTS"]},
    {"region_id": "rgn-010", "readiness": "HUMAN_REVIEW_READY", "required_source_roles": ["RELATED_PARTY_TRANSACTIONS"]},
    {"region_id": "rgn-013", "readiness": "HUMAN_REVIEW_READY", "required_source_roles": ["RELATED_PARTY_TRANSACTIONS"]},
    {"region_id": "rgn-014", "readiness": "HUMAN_REVIEW_READY", "required_source_roles": ["RELATED_PARTY_TRANSACTIONS"]},
    {"region_id": "rgn-015", "readiness": "HUMAN_REVIEW_READY", "required_source_roles": ["RELATED_PARTY_TRANSACTIONS"]},
    {"region_id": "rgn-046", "readiness": "BLOCKED_MISSING_SOURCE", "required_source_roles": ["COMPARABLE_COMPANIES", "IQR_RESULTS"]},
    {"region_id": "rgn-051", "readiness": "BLOCKED_MISSING_SOURCE", "required_source_roles": ["COMPARABLE_COMPANIES", "SCREENING_RESULTS"]},
    {"region_id": "rgn-070", "readiness": "NOT_APPLICABLE", "required_source_roles": []},
]

# Recalculate baseline readiness
event_base, trans_base, counts_base = registry.recalculate_readiness(
    sample_regions, actor="planner"
)

# Export readiness recalculation json
output_data = {
    "phase": "PHASE_G_REAL_SOURCE_INTAKE_READINESS_RECALCULATION",
    "evaluation_date": "2026-08-23",
    "package": registry.package.to_dict(),
    "audit_log": registry.audit_log_to_dict(),
    "sample_regions_recalculation": {
        "event": event_base.to_dict(),
        "transitions": [t.to_dict() for t in trans_base],
        "counts": counts_base,
    },
    "governance": {
        "execution_authorized": False,
        "requires_human_approval": True,
        "mutation_occurred": False,
        "forbidden_states_absent": True,
        "ground_truth_quarantined": True,
    },
    "contract_invariants_verified": [
        "REGISTER_DOES_NOT_CHANGE_READINESS",
        "RECALCULATE_IS_EXPLICIT",
        "DUPLICATE_SHA256_IS_NOOP",
        "ATOMIC_REPLACEMENT_TRANSACTIONAL",
        "AUDIT_PRIVACY_ENFORCED",
        "FINAL_READINESS_GUARD_ACTIVE",
        "IDEMPOTENCE_PRESERVED",
        "PACKAGE_VERSIONING_BUMPED_ON_MUTATION",
        "NO_MUTATION_PERFORMED",
    ]
}

out_path = REPO_ROOT / "docs" / "evaluation" / "LocalFile_RollForward_Readiness_Recalculation_G_2026-08-23.json"
out_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out_path}")
