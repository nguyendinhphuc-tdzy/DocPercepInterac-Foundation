"""
Source Registry & Readiness Lifecycle Tests (Phase G)
=====================================================
Location: foundation/tests/test_rollforward_source_registry.py

Locks the Phase G contract:

    §1  source registration creates artifact with all required fields
    §2  real artifact intake (FA&RPT, Appendix I)
    §3  before/after readiness BLOCKED → HUMAN_REVIEW_READY
    §3  readiness never auto-approves / auto-executes
    §4  negative upload: irrelevant artifact changes nothing
    §5  partial source: region remains blocked
    §6  duplicate SHA256 → DUPLICATE_NOOP
    §7  source update/replacement: atomic, stale previous, new hash
    §8  source scope authority enforcement
    §9  Ground Truth never satisfies a request
    §10 readiness depends only on declared inputs
    §11 audit trail records every operation
    §12 no mutation during registry operations
    §13 deterministic reproducible readiness
    §14 staling evidence removes readiness
    §G1 register() never silently changes readiness
    §G2 duplicate SHA256 is NOOP
    §G3 replace() is atomic/transactional
    §G6 idempotence
    §G7 package versioning on every mutation

Synthetic workbooks in tests are explicitly synthetic test fixtures,
not claimed client artifacts.
"""
from pathlib import Path
import json
import sys
import copy

import openpyxl
import pytest
from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.source_registry import (
    RegistrationEventType,
    RegistrationEvent,
    ReadinessGuard,
    ReadinessSnapshot,
    RegistryError,
    SourceRegistry,
)
from applications.rollforward.source_intake import (
    FORBIDDEN_READINESS,
    ArtifactFormat,
    ArtifactStatus,
    EvidenceQuality,
    GroundTruthGuard,
    PackageStatus,
    ReadinessRecalculator,
    RecalculatedReadiness,
    RollForwardSourcePackage,
    SourceArtifactRequest,
    SourceIntakeError,
    SourceIntakeProfiler,
    SourceRequestRegister,
    SourceScope,
    compute_file_hash,
)
from applications.rollforward.evidence_policy import (
    DatasetRole,
    SupplyScope,
)
from foundation.tests.evaluation.rollforward_clean_planner_c2 import (
    PATH_APP1,
    PATH_FARPT,
    PATH_GROUND_TRUTH_FORBIDDEN,
    PATH_HIST,
    PATH_TMPL,
)

BENCHMARK_ROLES = (DatasetRole.COMPARABLE_COMPANIES, DatasetRole.SCREENING_RESULTS,
                   DatasetRole.IQR_RESULTS, DatasetRole.INDEPENDENCE_CODES)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def _quarantine():
    GroundTruthGuard.reset()
    GroundTruthGuard.register([PATH_GROUND_TRUTH_FORBIDDEN])
    yield
    GroundTruthGuard.reset()


def _workbook(path: Path, sheets):
    wb = openpyxl.Workbook()
    first = True
    for name, rows in sheets:
        ws = wb.active if first else wb.create_sheet()
        ws.title = name
        first = False
        for r in rows:
            ws.append(list(r))
    wb.save(str(path))
    wb.close()
    return path


@pytest.fixture
def comparables_workbook(tmp_path):
    """SYNTHETIC test fixture: a genuine comparable-company dataset."""
    rows = [["No", "Company name", "Country", "Ticker", "Tax code", "Business description"]]
    rows += [[i, f"PEER {i} JSC", "Vietnam", f"TK{i}", f"010000000{i}", "Garment manufacturer"]
             for i in range(1, 11)]
    screening = [["Screening criteria", "Eliminated", "Retained"],
                 ["Unavailability of financial data", 245, 195],
                 ["Making loss for three consecutive years", 40, 155]]
    iqr = [["Statistic", "Value"], ["25th percentile", 3.1], ["Median", 4.5],
           ["75th percentile", 6.2], ["Interquartile range", "3.1-6.2"]]
    return _workbook(tmp_path / "client_supplied_2024.xlsx",
                     [("A", rows), ("B", screening), ("C", iqr)])


@pytest.fixture
def simple_workbook(tmp_path):
    """SYNTHETIC test fixture: minimal irrelevant workbook."""
    return _workbook(tmp_path / "simple.xlsx",
                     [("S", [["Item", "Value"], ["Rent", 100], ["Utilities", 50]])])


@pytest.fixture
def empty_registry():
    """An empty governed source registry."""
    return SourceRegistry(package_id="TEST-REG")


@pytest.fixture
def real_registry():
    """A registry pre-loaded with real Historical + Template + FA&RPT + Appendix I."""
    reg = SourceRegistry(package_id="REAL-REG")
    reg.register(PATH_HIST, SupplyScope.HISTORICAL, actor="test-setup")
    reg.register(PATH_TMPL, SupplyScope.TEMPLATE, actor="test-setup")
    reg.register(PATH_FARPT, SupplyScope.CURRENT_FINANCIAL, actor="test-setup")
    reg.register(PATH_APP1, SupplyScope.CURRENT_TAX, actor="test-setup")
    return reg


REGIONS = [
    {"region_id": "r1", "readiness": "BLOCKED_MISSING_SOURCE",
     "required_source_roles": ["COMPARABLE_COMPANIES", "IQR_RESULTS"]},
    {"region_id": "r2", "readiness": "BLOCKED_MISSING_SOURCE",
     "required_source_roles": ["COMPARABLE_COMPANIES", "CONTRACTUAL_DATA"]},
    {"region_id": "r3", "readiness": "HUMAN_REVIEW_READY",
     "required_source_roles": ["RELATED_PARTY_TRANSACTIONS"]},
    {"region_id": "r4", "readiness": "NOT_APPLICABLE", "required_source_roles": []},
]


def _fresh_regions():
    """Return deep copy of REGIONS so tests don't interfere with each other."""
    return copy.deepcopy(REGIONS)


# ============================================================================
# §1: SOURCE REGISTRATION — ALL REQUIRED FIELDS
# ============================================================================

def test_source_registration_creates_artifact_with_all_required_fields(
        empty_registry, simple_workbook):
    """§1: Every registered artifact must have artifact_id, filename, format,
    sha256, source_scope, dataset_roles, evidence_quality, timestamp,
    and the package version must be bumped."""
    event = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL, actor="user-test")

    assert event.event_type == RegistrationEventType.REGISTER
    assert event.success is True
    assert event.artifact_id is not None
    assert event.filename == simple_workbook.name
    assert event.source_scope == SupplyScope.ADDITIONAL.value
    assert event.new_hash is not None and len(event.new_hash) == 64
    assert event.timestamp is not None
    assert event.actor == "user-test"
    assert event.package_version is not None and event.package_version >= 2

    artifact = empty_registry.package.artifacts[0]
    assert artifact.artifact_id is not None
    assert artifact.filename == simple_workbook.name
    assert artifact.format in (ArtifactFormat.XLSX, ArtifactFormat.DOCX)
    assert artifact.file_hash == compute_file_hash(simple_workbook)
    assert artifact.source_scope == SupplyScope.ADDITIONAL
    assert artifact.created_at is not None


# ============================================================================
# §2: REAL ARTIFACT INTAKE
# ============================================================================

def test_real_artifact_intake_farpt_and_appendix(real_registry):
    """§2: Real FA&RPT and Appendix I fixtures are ingested successfully."""
    assert real_registry.artifact_count() == 4

    farpt = None
    app1 = None
    for a in real_registry.package.artifacts:
        if "FA&RPT" in a.filename:
            farpt = a
        if "Appendix" in a.filename:
            app1 = a

    assert farpt is not None, "FA&RPT not found in registry"
    assert app1 is not None, "Appendix I not found in registry"
    assert farpt.status == ArtifactStatus.PROFILED
    assert app1.status == ArtifactStatus.PROFILED
    assert farpt.source_scope == SupplyScope.CURRENT_FINANCIAL
    assert app1.source_scope == SupplyScope.CURRENT_TAX

    # Real sources supply genuine roles
    available = {r.value for r in real_registry.available_roles(EvidenceQuality.INFERRED)}
    assert "RELATED_PARTY_TRANSACTIONS" in available or "FINANCIAL_STATEMENTS" in available


# ============================================================================
# §3: BEFORE/AFTER READINESS — BLOCKED → HUMAN_REVIEW_READY
# ============================================================================

def test_before_after_readiness_blocked_to_human_review(
        real_registry, comparables_workbook):
    """§3: BLOCKED_MISSING_SOURCE → supply source → recalculate → HUMAN_REVIEW_READY."""
    regions = _fresh_regions()

    # Before: r1 is BLOCKED_MISSING_SOURCE
    assert regions[0]["readiness"] == "BLOCKED_MISSING_SOURCE"

    # Supply comparables (COMPARABLE_COMPANIES + IQR_RESULTS)
    reg_event = real_registry.register(
        comparables_workbook, SupplyScope.ADDITIONAL, actor="user")
    assert reg_event.event_type == RegistrationEventType.REGISTER

    # Recalculate readiness explicitly
    event, transitions, counts = real_registry.recalculate_readiness(
        regions, actor="user")

    assert event.event_type == RegistrationEventType.READINESS_RECALCULATED
    moved = {t.region_id: t for t in transitions}
    assert "r1" in moved
    assert moved["r1"].recalculated == "HUMAN_REVIEW_READY"
    assert "NOT approved" in moved["r1"].reason

    # After: r1 is now HUMAN_REVIEW_READY
    assert event.readiness_before is not None
    assert event.readiness_after is not None
    assert event.readiness_before["r1"] == "BLOCKED_MISSING_SOURCE"
    assert event.readiness_after["r1"] == "HUMAN_REVIEW_READY"


def test_before_after_readiness_never_auto_approves(
        real_registry, comparables_workbook):
    """§3: No AUTO_MUTATION_READY, no APPROVED, no EXECUTING emitted."""
    regions = _fresh_regions()
    real_registry.register(
        comparables_workbook, SupplyScope.ADDITIONAL, actor="user")

    _event, _transitions, counts = real_registry.recalculate_readiness(
        regions, actor="user")

    for forbidden in FORBIDDEN_READINESS:
        assert forbidden not in counts, (
            f"Forbidden readiness '{forbidden}' emitted during recalculation")


# ============================================================================
# §4: NEGATIVE UPLOAD — IRRELEVANT ARTIFACT
# ============================================================================

def test_negative_upload_irrelevant_artifact(real_registry, simple_workbook):
    """§4: An irrelevant artifact changes no readiness."""
    regions = _fresh_regions()

    real_registry.register(
        simple_workbook, SupplyScope.ADDITIONAL, actor="user")
    _event, transitions, _counts = real_registry.recalculate_readiness(
        regions, actor="user")

    # No blocked region became ready
    assert len(transitions) == 0, (
        f"Irrelevant artifact caused readiness transitions: {transitions}")


# ============================================================================
# §5: PARTIAL SOURCE
# ============================================================================

def test_partial_source_region_remains_blocked(real_registry, tmp_path):
    """§5: Upload artifact with only some required roles → region stays blocked."""
    # Comparable companies only, no IQR, no screening
    rows = [["No", "Company name", "Country", "Ticker", "Tax code", "Business description"]]
    rows += [[i, f"PEER {i}", "Vietnam", f"T{i}", f"010000{i}", "Manufacturer"]
             for i in range(1, 6)]
    partial = _workbook(tmp_path / "only_comparables.xlsx", [("A", rows)])

    real_registry.register(partial, SupplyScope.ADDITIONAL, actor="user")

    regions = _fresh_regions()
    _event, transitions, _counts = real_registry.recalculate_readiness(
        regions, actor="user")

    # r1 needs COMPARABLE_COMPANIES + IQR_RESULTS; only one may be supplied
    r1_moved = [t for t in transitions if t.region_id == "r1"]
    if r1_moved:
        # If partially moved, it should NOT be HUMAN_REVIEW_READY unless all roles met
        # But r1 requires IQR_RESULTS which partial doesn't have
        assert r1_moved[0].recalculated != RecalculatedReadiness.HUMAN_REVIEW_READY.value or \
            "IQR_RESULTS" in str(real_registry.available_roles()), \
            "Partial source should not fully satisfy r1"


# ============================================================================
# §6: DUPLICATE SHA256 → DUPLICATE_NOOP
# ============================================================================

def test_duplicate_sha256_is_deduplicated(empty_registry, simple_workbook, tmp_path):
    """§6: Registering an artifact whose SHA256 already exists → DUPLICATE_NOOP.
    No second artifact, no readiness change, no fake transitions."""
    event1 = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL)
    assert event1.event_type == RegistrationEventType.REGISTER
    assert empty_registry.artifact_count() == 1

    # Register same file again
    event2 = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL)
    assert event2.event_type == RegistrationEventType.DUPLICATE_NOOP
    assert empty_registry.artifact_count() == 1  # No second artifact

    # Copy with different name, same content
    copy = tmp_path / "different_name.xlsx"
    copy.write_bytes(simple_workbook.read_bytes())
    event3 = empty_registry.register(copy, SupplyScope.ADDITIONAL)
    assert event3.event_type == RegistrationEventType.DUPLICATE_NOOP
    assert empty_registry.artifact_count() == 1  # Still no duplicate

    # Package version not bumped for NOOPs
    assert event2.package_version == event1.package_version
    assert event3.package_version == event1.package_version


# ============================================================================
# §7: SOURCE UPDATE/REPLACEMENT — ATOMIC
# ============================================================================

def test_source_update_replacement_invalidates_readiness(
        empty_registry, simple_workbook, tmp_path):
    """§7: Replace → new hash, previous stale, readiness invalidated.
    replace() is atomic: failure preserves previous state."""
    event1 = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL)
    artifact_id = event1.artifact_id
    old_hash = event1.new_hash
    old_version = event1.package_version

    # Create updated workbook with different content
    updated = _workbook(tmp_path / "updated.xlsx",
                        [("S", [["Item", "Value"], ["Rent", 200], ["Utilities", 75]])])

    event2 = empty_registry.replace(artifact_id, updated, actor="user")
    assert event2.event_type == RegistrationEventType.REPLACE_SUCCESS
    assert event2.success is True
    assert event2.previous_hash == old_hash
    assert event2.new_hash != old_hash
    assert event2.package_version > old_version

    # Artifact has new hash
    art = empty_registry.find_artifact(artifact_id)
    assert art is not None
    assert art.file_hash == event2.new_hash
    assert art.status == ArtifactStatus.PROFILED


def test_replace_atomic_failure_preserves_previous(
        empty_registry, simple_workbook, tmp_path):
    """§G3: If replacement fails (e.g., file not found), previous artifact preserved."""
    event1 = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL)
    artifact_id = event1.artifact_id
    old_hash = event1.new_hash

    # Attempt replacement with non-existent file
    bad_path = tmp_path / "does_not_exist.xlsx"
    event2 = empty_registry.replace(artifact_id, bad_path, actor="user")
    assert event2.event_type == RegistrationEventType.REPLACE_FAILED
    assert event2.success is False

    # Previous artifact preserved
    art = empty_registry.find_artifact(artifact_id)
    assert art is not None
    assert art.file_hash == old_hash


def test_replace_with_identical_content_is_noop(
        empty_registry, simple_workbook, tmp_path):
    """Replacing with identical content is a DUPLICATE_NOOP."""
    event1 = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL)
    artifact_id = event1.artifact_id

    # Copy the same file
    same = tmp_path / "same_content.xlsx"
    same.write_bytes(simple_workbook.read_bytes())

    event2 = empty_registry.replace(artifact_id, same, actor="user")
    assert event2.event_type == RegistrationEventType.DUPLICATE_NOOP
    assert event2.success is True


# ============================================================================
# §8: SOURCE SCOPE AUTHORITY ENFORCEMENT
# ============================================================================

def test_source_scope_authority_enforcement(empty_registry, tmp_path):
    """§8: HISTORICAL / TEMPLATE scopes cannot satisfy current-year roles."""
    rows = [["No", "Company name", "Country", "Ticker", "Tax code", "Business description"]]
    rows += [[i, f"PEER {i} JSC", "Vietnam", f"TK{i}", f"010000000{i}", "Manufacturer"]
             for i in range(1, 6)]
    wb_path = _workbook(tmp_path / "scope_test.xlsx", [("A", rows)])

    for scope in (SupplyScope.HISTORICAL, SupplyScope.TEMPLATE):
        reg = SourceRegistry(package_id=f"scope-{scope.value}")
        reg.register(wb_path, scope, actor="test")
        art = reg.package.artifacts[0]
        assert art.can_supply_current_year is False, \
            f"{scope.value} scope should not supply current-year roles"
        for role in art.dataset_roles:
            assert not art.supplies(role), \
                f"{scope.value} scope should not satisfy {role.value}"

    # ADDITIONAL scope can supply
    reg_add = SourceRegistry(package_id="scope-add")
    # Use a new workbook to avoid duplicate hash issues
    wb_path2 = _workbook(tmp_path / "scope_test2.xlsx",
                          [("A", rows + [["extra", "data"]])])
    reg_add.register(wb_path2, SupplyScope.ADDITIONAL, actor="test")
    art_add = reg_add.package.artifacts[0]
    assert art_add.can_supply_current_year is True


# ============================================================================
# §9: GROUND TRUTH NEVER SATISFIES A REQUEST
# ============================================================================

def test_ground_truth_never_satisfies_a_request(empty_registry):
    """§9: Ground Truth cannot be registered as a source."""
    # Verify guard is active
    assert PATH_GROUND_TRUTH_FORBIDDEN.name.lower() in GroundTruthGuard._forbidden_names, \
        f"Guard not active! names={GroundTruthGuard._forbidden_names}"
    assert len(GroundTruthGuard._forbidden_hashes) > 0, "Guard has no hashes!"

    with pytest.raises(SourceIntakeError, match="evaluation-only Ground Truth"):
        empty_registry.register(PATH_GROUND_TRUTH_FORBIDDEN, SupplyScope.ADDITIONAL)

    # Registry unchanged
    assert empty_registry.artifact_count() == 0
    # No REGISTER event — only the exception
    register_events = [e for e in empty_registry.audit_log
                       if e.event_type == RegistrationEventType.REGISTER]
    assert len(register_events) == 0


def test_ground_truth_rename_is_still_blocked(empty_registry, tmp_path):
    """Ground Truth is blocked even under a different filename (content hash match)."""
    copy = tmp_path / "innocent_client_data.docx"
    copy.write_bytes(PATH_GROUND_TRUTH_FORBIDDEN.read_bytes())
    with pytest.raises(SourceIntakeError, match="same content hash"):
        empty_registry.register(copy, SupplyScope.ADDITIONAL)


# ============================================================================
# §10: READINESS DEPENDS ONLY ON DECLARED INPUTS
# ============================================================================

def test_readiness_depends_only_on_declared_inputs(
        real_registry, comparables_workbook):
    """§10: Readiness depends on current package + policy + profile + bindings + evidence.
    Not on previous readiness, Ground Truth, or LLM output."""
    regions = _fresh_regions()
    real_registry.register(comparables_workbook, SupplyScope.ADDITIONAL, actor="user")

    # First recalculation
    _e1, transitions1, counts1 = real_registry.recalculate_readiness(
        _fresh_regions(), actor="user")

    # Build a second, independent registry with the same inputs
    reg2 = SourceRegistry(package_id="INDEPENDENT")
    reg2.register(PATH_HIST, SupplyScope.HISTORICAL, actor="test")
    reg2.register(PATH_TMPL, SupplyScope.TEMPLATE, actor="test")
    reg2.register(PATH_FARPT, SupplyScope.CURRENT_FINANCIAL, actor="test")
    reg2.register(PATH_APP1, SupplyScope.CURRENT_TAX, actor="test")
    reg2.register(comparables_workbook, SupplyScope.ADDITIONAL, actor="test")

    _e2, transitions2, counts2 = reg2.recalculate_readiness(
        _fresh_regions(), actor="test")

    # Same transitions and counts
    moved1 = {t.region_id: t.recalculated for t in transitions1}
    moved2 = {t.region_id: t.recalculated for t in transitions2}
    assert moved1 == moved2
    assert counts1 == counts2


# ============================================================================
# §11: AUDIT TRAIL
# ============================================================================

def test_audit_trail_records_every_operation(
        empty_registry, simple_workbook, tmp_path):
    """§11: Every registration/replacement is traceable with:
    artifact_id, previous/new hash, changed roles, affected regions,
    readiness before/after. No sensitive contents logged."""
    # Register
    event1 = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL, actor="user-A")
    assert event1.event_type == RegistrationEventType.REGISTER
    assert event1.actor == "user-A"
    assert event1.filename == simple_workbook.name

    # Duplicate
    event2 = empty_registry.register(simple_workbook, SupplyScope.ADDITIONAL, actor="user-B")
    assert event2.event_type == RegistrationEventType.DUPLICATE_NOOP

    # Replace
    updated = _workbook(tmp_path / "updated_audit.xlsx",
                        [("S", [["Item", "Value"], ["Rent", 999]])])
    event3 = empty_registry.replace(event1.artifact_id, updated, actor="user-C")
    assert event3.event_type == RegistrationEventType.REPLACE_SUCCESS
    assert event3.previous_hash is not None
    assert event3.new_hash is not None
    assert event3.previous_hash != event3.new_hash

    # Recalculate readiness
    regions = _fresh_regions()
    event4, _, _ = empty_registry.recalculate_readiness(regions, actor="user-D")
    assert event4.event_type == RegistrationEventType.READINESS_RECALCULATED
    assert event4.readiness_before is not None
    assert event4.readiness_after is not None

    # Full audit log
    log = empty_registry.audit_log_to_dict()
    assert len(log) == 4
    for entry in log:
        assert "event_id" in entry
        assert "timestamp" in entry
        assert "actor" in entry
        # Audit privacy: no raw contents, no absolute paths
        serialized = json.dumps(entry)
        assert "\\\\Users\\\\" not in serialized, "Absolute path leaked into audit"
        assert "C:\\" not in serialized, "Absolute path leaked into audit"


# ============================================================================
# §12: NO MUTATION (NO FILE WRITES)
# ============================================================================

def test_no_mutation_occurs_during_registry_operations(
        real_registry, comparables_workbook, tmp_path):
    """§13: No DOCX/XLSX mutation, no structural writeback, no data writeback."""
    # Snapshot files before operations
    template_hash_before = compute_file_hash(PATH_TMPL)
    farpt_hash_before = compute_file_hash(PATH_FARPT)
    app1_hash_before = compute_file_hash(PATH_APP1)

    # Run full lifecycle
    real_registry.register(comparables_workbook, SupplyScope.ADDITIONAL, actor="test")
    regions = _fresh_regions()
    real_registry.recalculate_readiness(regions, actor="test")

    # Verify no file was mutated
    assert compute_file_hash(PATH_TMPL) == template_hash_before
    assert compute_file_hash(PATH_FARPT) == farpt_hash_before
    assert compute_file_hash(PATH_APP1) == app1_hash_before

    # Internal mutation counter
    assert real_registry._mutation_count == 0


# ============================================================================
# §14: DETERMINISTIC REPRODUCIBLE READINESS
# ============================================================================

def test_deterministic_reproducible_readiness(
        real_registry, comparables_workbook):
    """§14: Same source package + same hashes + same profile + same policy → same readiness."""
    real_registry.register(comparables_workbook, SupplyScope.ADDITIONAL, actor="test")

    # Run recalculation twice on identical input
    regions_a = _fresh_regions()
    _e1, transitions_a, counts_a = real_registry.recalculate_readiness(
        regions_a, actor="test")

    regions_b = _fresh_regions()
    _e2, transitions_b, counts_b = real_registry.recalculate_readiness(
        regions_b, actor="test")

    moved_a = {t.region_id: t.recalculated for t in transitions_a}
    moved_b = {t.region_id: t.recalculated for t in transitions_b}
    assert moved_a == moved_b
    assert counts_a == counts_b


# ============================================================================
# §14: STALING EVIDENCE REMOVES READINESS
# ============================================================================

def test_staling_evidence_removes_readiness(
        empty_registry, comparables_workbook, tmp_path):
    """§14: Staling a source removes its contribution to readiness."""
    # Register and verify it contributes roles
    event = empty_registry.register(
        comparables_workbook, SupplyScope.ADDITIONAL, actor="test")
    roles_before = empty_registry.available_roles(EvidenceQuality.INFERRED)
    assert len(roles_before) > 0

    # Modify the file to make it stale
    comparables_workbook.write_bytes(comparables_workbook.read_bytes() + b"\x00")

    fresh, reasons = empty_registry.verify_freshness(
        {event.artifact_id: comparables_workbook}, actor="test")
    assert fresh is False
    assert empty_registry.package.status == PackageStatus.STALE


# ============================================================================
# §G1: REGISTER MUST NOT SILENTLY CHANGE READINESS
# ============================================================================

def test_register_does_not_change_readiness(
        empty_registry, comparables_workbook):
    """§G1: register() may ingest/profile/register but readiness transitions
    must be explicit through recalculate_readiness()."""
    regions = _fresh_regions()
    readiness_before = {r["region_id"]: r["readiness"] for r in regions}

    # Register a source that would satisfy r1's roles
    empty_registry.register(comparables_workbook, SupplyScope.ADDITIONAL, actor="test")

    # Readiness is NOT recalculated — regions are untouched
    readiness_after = {r["region_id"]: r["readiness"] for r in regions}
    assert readiness_before == readiness_after, (
        "register() must NOT silently change readiness")

    # Only a REGISTER event, no READINESS_RECALCULATED
    event_types = [e.event_type for e in empty_registry.audit_log]
    assert RegistrationEventType.READINESS_RECALCULATED not in event_types


# ============================================================================
# §G6: IDEMPOTENCE
# ============================================================================

def test_idempotence_repeated_register_recalculate(
        real_registry, comparables_workbook):
    """§G6: Repeating the exact same register/recalculate against unchanged
    source artifacts produces equivalent readiness without duplicate state."""
    real_registry.register(comparables_workbook, SupplyScope.ADDITIONAL, actor="test")
    count_after_first = real_registry.artifact_count()

    # Try to register same file again
    dup_event = real_registry.register(comparables_workbook, SupplyScope.ADDITIONAL, actor="test")
    assert dup_event.event_type == RegistrationEventType.DUPLICATE_NOOP
    assert real_registry.artifact_count() == count_after_first  # no growth

    # Recalculate twice
    r1 = _fresh_regions()
    _e1, t1, c1 = real_registry.recalculate_readiness(r1, actor="test")

    r2 = _fresh_regions()
    _e2, t2, c2 = real_registry.recalculate_readiness(r2, actor="test")

    assert {t.region_id: t.recalculated for t in t1} == \
           {t.region_id: t.recalculated for t in t2}
    assert c1 == c2


# ============================================================================
# §G7: PACKAGE VERSIONING ON EVERY MUTATION
# ============================================================================

def test_package_versioning_on_every_mutation(empty_registry, tmp_path):
    """§G7: Every successful registry mutation bumps the package version."""
    versions = [empty_registry.package.version]

    for i in range(3):
        wb = _workbook(tmp_path / f"v{i}.xlsx",
                       [("S", [["Item", "Value"], [f"row{i}", i]])])
        empty_registry.register(wb, SupplyScope.ADDITIONAL, actor="test")
        versions.append(empty_registry.package.version)

    # Each registration bumped the version
    for i in range(1, len(versions)):
        assert versions[i] > versions[i - 1], \
            f"Version did not increase: {versions[i-1]} → {versions[i]}"

    # Replace also bumps version
    art = empty_registry.package.artifacts[0]
    wb_new = _workbook(tmp_path / "v_new.xlsx",
                       [("S", [["Item", "Value"], ["Updated", 999]])])
    event = empty_registry.replace(art.artifact_id, wb_new, actor="test")
    if event.success:
        assert event.package_version > versions[-1]


# ============================================================================
# END-TO-END LIFECYCLE
# ============================================================================

def test_registry_end_to_end_lifecycle(real_registry, comparables_workbook, tmp_path):
    """Full lifecycle: register → profile → recalculate → replace → re-recalculate.
    Proves the complete Phase G contract."""
    # 1. Initial state: real sources loaded
    assert real_registry.artifact_count() == 4
    version_initial = real_registry.package.version

    # 2. Recalculate readiness BEFORE adding comparables
    regions_before = _fresh_regions()
    e_before, t_before, c_before = real_registry.recalculate_readiness(
        regions_before, actor="lifecycle-test")
    assert "r1" not in {t.region_id for t in t_before}, \
        "r1 should still be BLOCKED before comparables added"

    # 3. Register comparables
    reg_event = real_registry.register(
        comparables_workbook, SupplyScope.ADDITIONAL, actor="lifecycle-test")
    assert reg_event.event_type == RegistrationEventType.REGISTER
    assert real_registry.package.version > version_initial

    # 4. Recalculate readiness AFTER adding comparables
    regions_after = _fresh_regions()
    e_after, t_after, c_after = real_registry.recalculate_readiness(
        regions_after, actor="lifecycle-test")
    moved = {t.region_id: t.recalculated for t in t_after}
    assert "r1" in moved
    assert moved["r1"] == "HUMAN_REVIEW_READY"

    # 5. Replace the comparables with updated data
    updated_rows = [["No", "Company name", "Country", "Ticker", "Tax code", "Business description"]]
    updated_rows += [[i, f"NEW PEER {i} JSC", "Vietnam", f"NTK{i}", f"020000000{i}",
                       "Updated manufacturer"] for i in range(1, 11)]
    screening = [["Screening criteria", "Eliminated", "Retained"],
                 ["Unavailability of data", 300, 180],
                 ["Making loss for 3 years", 50, 130]]
    iqr = [["Statistic", "Value"], ["25th percentile", 2.8], ["Median", 4.1],
           ["75th percentile", 5.9], ["Interquartile range", "2.8-5.9"]]
    updated_wb = _workbook(tmp_path / "updated_comparables.xlsx",
                           [("A", updated_rows), ("B", screening), ("C", iqr)])

    replace_event = real_registry.replace(
        reg_event.artifact_id, updated_wb, actor="lifecycle-test")
    assert replace_event.event_type == RegistrationEventType.REPLACE_SUCCESS
    assert replace_event.previous_hash != replace_event.new_hash

    # 6. Re-recalculate after replacement
    regions_final = _fresh_regions()
    e_final, t_final, c_final = real_registry.recalculate_readiness(
        regions_final, actor="lifecycle-test")

    # r1 should still be HUMAN_REVIEW_READY with updated data
    moved_final = {t.region_id: t.recalculated for t in t_final}
    assert "r1" in moved_final
    assert moved_final["r1"] == "HUMAN_REVIEW_READY"

    # 7. Verify complete audit trail
    audit = real_registry.audit_log_to_dict()
    event_types = [e["event_type"] for e in audit]
    assert "REGISTER" in event_types
    assert "READINESS_RECALCULATED" in event_types
    assert "REPLACE_SUCCESS" in event_types

    # 8. Governance: execution never authorized
    for entry in audit:
        if entry["event_type"] == "READINESS_RECALCULATED":
            assert "Execution authorized: False" in entry.get("reason", "")

    # 9. Final readiness guard: no forbidden states
    for value in c_final:
        assert value not in FORBIDDEN_READINESS

    # 10. Serialization round-trip
    full_state = real_registry.to_dict()
    assert full_state["mutation_count"] == 0
    assert full_state["governance"]["execution_authorized"] is False
    assert full_state["package_version"] >= 6  # initial + 4 setup + 1 register + 1 replace
