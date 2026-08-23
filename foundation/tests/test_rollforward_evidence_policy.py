"""
Canonical Dataset Role & Evidence Policy Tests (Phase F.1)
===========================================================
Location: foundation/tests/test_rollforward_evidence_policy.py

Locks the canonical policy:

    the TAXPAYER_PROFILE dispute has one evidence-backed answer
    HISTORICAL cannot satisfy a current-year role
    TEMPLATE cannot satisfy a current-year role
    current financial / current tax / additional evidence behaves as declared
    a role with missing required fields is not satisfied
    benchmarking and narrative roles behave per policy
    duplicate and conflicting evidence resolve deterministically
    role determination is not duplicated anywhere else

The governing principle under test:

    A document may contain information about a role without being an
    authorized current-year source for that role.
"""
from pathlib import Path
import json
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from foundation.applications.rollforward.evidence_policy import (
    BASELINE_SCOPES,
    CURRENT_YEAR_SCOPES,
    FORBIDDEN_SCOPES,
    ROLE_POLICIES,
    CorpusBuilder,
    DatasetRole,
    EvidenceAuthority,
    EvidenceCorpus,
    EvidencePolicyEngine,
    EvidenceStatus,
    RoleSupport,
    SchemaShape,
    SupplyScope,
    policy_compatibility_matrix,
)
from foundation.tests.evaluation.rollforward_clean_planner_c2 import (
    PATH_APP1,
    PATH_FARPT,
    PATH_GROUND_TRUTH_FORBIDDEN,
    PATH_HIST,
    PATH_TMPL,
)

BENCHMARK_ROLES = (DatasetRole.BENCHMARKING_DATA, DatasetRole.COMPARABLE_COMPANIES,
                   DatasetRole.IQR_RESULTS, DatasetRole.SCREENING_RESULTS,
                   DatasetRole.INDEPENDENCE_CODES)


@pytest.fixture(scope="module")
def appendix_corpus():
    return CorpusBuilder.from_workbook(PATH_APP1, SupplyScope.CURRENT_TAX)


@pytest.fixture(scope="module")
def farpt_corpus():
    return CorpusBuilder.from_workbook(PATH_FARPT, SupplyScope.CURRENT_FINANCIAL)


@pytest.fixture(scope="module")
def historical_corpus():
    return CorpusBuilder.from_document(PATH_HIST, SupplyScope.HISTORICAL)


@pytest.fixture(scope="module")
def template_corpus():
    return CorpusBuilder.from_document(PATH_TMPL, SupplyScope.TEMPLATE)


# ============================================================================
# THE TAXPAYER_PROFILE DISPUTE
# ============================================================================

def test_taxpayer_profile_dispute_has_one_canonical_answer(appendix_corpus):
    """Phase E said available, Phase F said unavailable. Both were wrong.

    Four of five mandatory fields are genuinely present with current-year
    values; `principal_activity` is absent from both workbooks. The canonical
    answer is therefore PARTIALLY_SUPPORTED -- neither of the two prior
    verdicts.
    """
    v = EvidencePolicyEngine.evaluate(DatasetRole.TAXPAYER_PROFILE, appendix_corpus)

    assert v.support == RoleSupport.PARTIALLY_SUPPORTED
    assert v.authority == EvidenceAuthority.CURRENT_YEAR_AUTHORITY
    assert v.can_satisfy_current_year is False

    assert set(v.satisfied_fields) == {
        "legal_name", "tax_code", "fiscal_year", "registered_address"}
    assert v.missing_fields == ["principal_activity"]


def test_the_four_present_taxpayer_fields_carry_real_values(appendix_corpus):
    v = EvidencePolicyEngine.evaluate(DatasetRole.TAXPAYER_PROFILE, appendix_corpus)
    by_name = {f.field_name: f for f in v.fields}

    assert by_name["tax_code"].has_value
    assert by_name["tax_code"].sample.strip() == "0201824857"
    assert "Hestra" in by_name["legal_name"].sample
    assert "2024" in by_name["fiscal_year"].sample
    assert by_name["registered_address"].has_value
    # The field Phase F missed entirely: the workbook says "Address:" / "Địa chỉ:".
    assert by_name["registered_address"].located


def test_principal_activity_is_absent_from_every_current_source(
        appendix_corpus, farpt_corpus):
    """The one field that genuinely is not there, in either workbook."""
    for corpus in (appendix_corpus, farpt_corpus):
        v = EvidencePolicyEngine.evaluate(DatasetRole.TAXPAYER_PROFILE, corpus)
        by_name = {f.field_name: f for f in v.fields}
        assert by_name["principal_activity"].located is False


def test_a_label_without_a_value_does_not_satisfy_a_key_value_field():
    """Phase E would have credited the role on bare labels. The policy will not."""
    labels_only = CorpusBuilder.from_rows(
        "labels.xlsx", SupplyScope.CURRENT_TAX,
        [["Company name", "Tax code", "Fiscal year", "Address", "Principal activity"]])
    v = EvidencePolicyEngine.evaluate(DatasetRole.TAXPAYER_PROFILE, labels_only)
    assert v.support in (RoleSupport.UNKNOWN, RoleSupport.PARTIALLY_SUPPORTED)
    assert v.can_satisfy_current_year is False


def test_a_complete_taxpayer_block_is_verified():
    """With all five fields carrying values, the same policy says VERIFIED."""
    complete = CorpusBuilder.from_rows(
        "complete.xlsx", SupplyScope.CURRENT_TAX,
        [["Company name:", "ACME Vietnam LLC"],
         ["Tax code", "0101234567"],
         ["Fiscal year", "2024"],
         ["Address:", "1 Industrial Park, Hanoi"],
         ["Principal activity", "Manufacture of gloves"]])
    v = EvidencePolicyEngine.evaluate(DatasetRole.TAXPAYER_PROFILE, complete)
    assert v.support == RoleSupport.VERIFIED
    assert v.can_satisfy_current_year is True
    assert v.missing_fields == []


# ============================================================================
# SCOPE AUTHORITY — content is not authority
# ============================================================================

def test_historical_cannot_satisfy_any_current_year_role(historical_corpus):
    verdicts = EvidencePolicyEngine.evaluate_all(historical_corpus)
    for role, v in verdicts.items():
        assert v.can_satisfy_current_year is False, f"{role.value} satisfied from HISTORICAL"
        if v.support != RoleSupport.UNKNOWN:
            assert v.authority == EvidenceAuthority.HISTORICAL_EVIDENCE_ONLY


def test_template_cannot_satisfy_any_current_year_role(template_corpus):
    verdicts = EvidencePolicyEngine.evaluate_all(template_corpus)
    for role, v in verdicts.items():
        assert v.can_satisfy_current_year is False, f"{role.value} satisfied from TEMPLATE"
        if v.support != RoleSupport.UNKNOWN:
            assert v.authority == EvidenceAuthority.STRUCTURAL_EVIDENCE_ONLY


def test_historical_content_is_preserved_as_evidence_not_erased(historical_corpus):
    """The prior-year file still counts as HISTORICAL_EVIDENCE; it is not blanked."""
    verdicts = EvidencePolicyEngine.evaluate_all(historical_corpus)
    historical = [r for r, v in verdicts.items()
                  if v.support == RoleSupport.HISTORICAL_EVIDENCE]
    assert historical, "the FY2023 Local File must retain historical evidence value"
    for role in historical:
        assert "may not satisfy a current-year requirement" in verdicts[role].rationale


def test_the_same_content_flips_only_on_scope():
    """Identical bytes, different scope: content constant, authority decides."""
    rows = [["Company name:", "ACME Vietnam LLC"], ["Tax code", "0101234567"],
            ["Fiscal year", "2024"], ["Address:", "1 Industrial Park"],
            ["Principal activity", "Manufacture of gloves"]]
    current = EvidencePolicyEngine.evaluate(
        DatasetRole.TAXPAYER_PROFILE,
        CorpusBuilder.from_rows("x.xlsx", SupplyScope.CURRENT_TAX, rows))
    historical = EvidencePolicyEngine.evaluate(
        DatasetRole.TAXPAYER_PROFILE,
        CorpusBuilder.from_rows("x.xlsx", SupplyScope.HISTORICAL, rows))

    assert current.satisfied_fields == historical.satisfied_fields   # same content
    assert current.can_satisfy_current_year is True
    assert historical.can_satisfy_current_year is False              # different authority
    assert historical.support == RoleSupport.HISTORICAL_EVIDENCE


def test_evaluation_only_scope_is_never_authorized():
    rows = [["Company name:", "ACME"], ["Tax code", "1"], ["Fiscal year", "2024"],
            ["Address:", "x"], ["Principal activity", "y"]]
    v = EvidencePolicyEngine.evaluate(
        DatasetRole.TAXPAYER_PROFILE,
        CorpusBuilder.from_rows("gt.docx", SupplyScope.EVALUATION_ONLY, rows))
    assert v.authority == EvidenceAuthority.NOT_AUTHORIZED
    assert v.support == RoleSupport.NOT_APPLICABLE
    assert v.can_satisfy_current_year is False


def test_no_role_grants_a_generic_scope_exception():
    """Every role's scope sets come from the shared constants, not ad-hoc lists."""
    for role, policy in ROLE_POLICIES.items():
        if role == DatasetRole.UNKNOWN:
            continue
        assert policy.allowed_supply_scopes == frozenset(CURRENT_YEAR_SCOPES), role.value
        assert BASELINE_SCOPES <= policy.disallowed_supply_scopes, role.value
        assert FORBIDDEN_SCOPES <= policy.disallowed_supply_scopes, role.value
        assert policy.allowed_supply_scopes.isdisjoint(policy.disallowed_supply_scopes)


# ============================================================================
# CURRENT-YEAR EVIDENCE
# ============================================================================

def test_current_financial_evidence_supplies_its_declared_roles(farpt_corpus):
    roles = set(EvidencePolicyEngine.current_year_roles(farpt_corpus))
    assert DatasetRole.FINANCIAL_STATEMENTS in roles
    assert DatasetRole.FINANCIAL_ANALYSIS in roles
    assert DatasetRole.RELATED_PARTY_TRANSACTIONS in roles


def test_current_tax_evidence_supplies_its_declared_roles(appendix_corpus):
    roles = set(EvidencePolicyEngine.current_year_roles(appendix_corpus))
    assert DatasetRole.RELATED_PARTY_TRANSACTIONS in roles
    assert DatasetRole.APPENDIX_DISCLOSURE in roles


def test_additional_uploaded_artifact_can_supply_a_role():
    rows = [["No", "Company name", "Country", "Ticker", "Business description"]]
    rows += [[i, f"PEER {i} JSC", "Vietnam", f"TK{i}", "Comparable garment manufacturer"]
             for i in range(1, 6)]
    corpus = CorpusBuilder.from_rows("upload.xlsx", SupplyScope.ADDITIONAL, rows)
    v = EvidencePolicyEngine.evaluate(DatasetRole.COMPARABLE_COMPANIES, corpus)
    assert v.support == RoleSupport.VERIFIED
    assert v.can_satisfy_current_year is True


def test_no_benchmarking_role_is_satisfied_by_the_real_current_sources(
        farpt_corpus, appendix_corpus):
    for corpus in (farpt_corpus, appendix_corpus):
        roles = set(EvidencePolicyEngine.current_year_roles(corpus))
        for role in BENCHMARK_ROLES:
            assert role not in roles, (
                f"{role.value} satisfied by {corpus.artifact_name}; the Phase E audit proved "
                f"no benchmarking data exists in these workbooks")


# ============================================================================
# INSUFFICIENT FIELDS & DISCRIMINATION
# ============================================================================

def test_missing_required_fields_prevents_satisfaction():
    partial = CorpusBuilder.from_rows(
        "partial.xlsx", SupplyScope.CURRENT_FINANCIAL,
        [["Net sales", 100], ["Net sales", 120], ["Net sales", 140]])
    v = EvidencePolicyEngine.evaluate(DatasetRole.FINANCIAL_STATEMENTS, partial)
    assert v.can_satisfy_current_year is False
    assert set(v.missing_fields) >= {"cost_of_sales", "result"}


def test_a_related_party_register_is_not_a_comparable_company_set():
    """Both carry Name / Country / Tax code. The discriminator separates them."""
    register = CorpusBuilder.from_rows(
        "rp.xlsx", SupplyScope.CURRENT_TAX,
        [["No.", "Name of related party", "Country", "Tax code",
          "Type of relationship", "Amount (VND)"],
         [1, "Parent Co", "Japan", "1234", "Parent", 1000],
         [2, "Sister Co", "Vietnam", "5678", "Common control", 2000],
         [3, "Affiliate", "Thailand", "9012", "Common control", 3000]])

    comparables = EvidencePolicyEngine.evaluate(DatasetRole.COMPARABLE_COMPANIES, register)
    assert comparables.can_satisfy_current_year is False
    assert comparables.support == RoleSupport.INSUFFICIENT_FIELDS
    assert "discriminating evidence" in comparables.rationale

    rpt = EvidencePolicyEngine.evaluate(DatasetRole.RELATED_PARTY_TRANSACTIONS, register)
    assert rpt.can_satisfy_current_year is True


def test_discriminator_requirement_is_declared_not_implicit():
    for role in (DatasetRole.COMPARABLE_COMPANIES, DatasetRole.SCREENING_RESULTS,
                 DatasetRole.FAR, DatasetRole.CONTRACTUAL_DATA):
        assert ROLE_POLICIES[role].discriminator_patterns, (
            f"{role.value} shares generic fields with other roles and needs a discriminator")


def test_prose_cannot_verify_a_tabular_role():
    prose = EvidenceCorpus(artifact_name="notes.docx", scope=SupplyScope.ADDITIONAL)
    for line in ("We reviewed the comparable companies with their ticker symbols.",
                 "Business description and tax code were checked for each entity.",
                 "The country of each comparable was confirmed."):
        prose.add("notes.docx!p", [line])
    prose.has_narrative_text = True

    v = EvidencePolicyEngine.evaluate(DatasetRole.COMPARABLE_COMPANIES, prose)
    assert v.evidence_status != EvidenceStatus.VERIFIED
    assert v.can_satisfy_current_year is False


def test_narrative_role_accepts_prose_but_still_needs_its_discriminator():
    supported = EvidenceCorpus(artifact_name="mi.docx", scope=SupplyScope.ADDITIONAL)
    for line in ("Functions performed by the entity during the year.",
                 "Assets used in the manufacturing operation.",
                 "Risks assumed by the entity include market risk."):
        supported.add("mi.docx!p", [line])
    v = EvidencePolicyEngine.evaluate(DatasetRole.FAR, supported)
    assert v.can_satisfy_current_year is True

    without = EvidenceCorpus(artifact_name="other.docx", scope=SupplyScope.ADDITIONAL)
    for line in ("The company owns assets used in production.",
                 "Various risks assumed are described elsewhere."):
        without.add("other.docx!p", [line])
    v2 = EvidencePolicyEngine.evaluate(DatasetRole.FAR, without)
    assert v2.can_satisfy_current_year is False


# ============================================================================
# CONFLICTING / DUPLICATE EVIDENCE
# ============================================================================

def test_duplicate_evidence_does_not_change_the_verdict():
    rows = [["Company name:", "ACME"], ["Tax code", "1"], ["Fiscal year", "2024"],
            ["Address:", "x"], ["Principal activity", "y"]]
    once = EvidencePolicyEngine.evaluate(
        DatasetRole.TAXPAYER_PROFILE,
        CorpusBuilder.from_rows("a.xlsx", SupplyScope.CURRENT_TAX, rows))
    twice = EvidencePolicyEngine.evaluate(
        DatasetRole.TAXPAYER_PROFILE,
        CorpusBuilder.from_rows("a.xlsx", SupplyScope.CURRENT_TAX, rows + rows))
    assert once.support == twice.support
    assert once.satisfied_fields == twice.satisfied_fields


def test_a_valued_field_wins_over_a_bare_label_elsewhere():
    """Conflicting evidence resolves toward the stronger observation."""
    corpus = CorpusBuilder.from_rows(
        "mixed.xlsx", SupplyScope.CURRENT_TAX,
        [["Tax code"],                       # bare label first
         ["Company name:", "ACME"],
         ["Tax code", "0101234567"],         # valued later
         ["Fiscal year", "2024"], ["Address:", "x"], ["Principal activity", "y"]])
    v = EvidencePolicyEngine.evaluate(DatasetRole.TAXPAYER_PROFILE, corpus)
    by_name = {f.field_name: f for f in v.fields}
    assert by_name["tax_code"].has_value is True
    assert by_name["tax_code"].sample.strip() == "0101234567"
    assert v.support == RoleSupport.VERIFIED


# ============================================================================
# DETERMINISM & SINGLE DEFINITION
# ============================================================================

def test_repeated_profiling_is_deterministic(appendix_corpus):
    a = EvidencePolicyEngine.evaluate_all(appendix_corpus)
    b = EvidencePolicyEngine.evaluate_all(appendix_corpus)
    assert json.dumps({r.value: v.to_dict() for r, v in a.items()}, sort_keys=True) == \
        json.dumps({r.value: v.to_dict() for r, v in b.items()}, sort_keys=True)


def test_rebuilding_the_corpus_gives_the_same_verdicts():
    a = CorpusBuilder.from_workbook(PATH_FARPT, SupplyScope.CURRENT_FINANCIAL)
    b = CorpusBuilder.from_workbook(PATH_FARPT, SupplyScope.CURRENT_FINANCIAL)
    assert EvidencePolicyEngine.current_year_roles(a) == \
        EvidencePolicyEngine.current_year_roles(b)


def test_every_role_has_exactly_one_policy():
    assert set(ROLE_POLICIES) == set(DatasetRole)
    for role, policy in ROLE_POLICIES.items():
        assert policy.role == role
        assert policy.definition
        assert policy.required_fields
        assert policy.required_schema in SchemaShape
        assert policy.evidence_status_rules


def test_source_intake_delegates_and_defines_no_roles_of_its_own():
    """§6: no duplicated role logic. Intake must consume the policy, not restate it."""
    src = (REPO_ROOT / "foundation/applications/rollforward/source_intake.py").read_text(
        encoding="utf-8")
    assert "_ROLE_SIGNALS" not in src, "intake must not carry its own role signal table"
    assert "_C2_TO_F" not in src, "intake must not carry its own role mapping"
    assert "class DatasetRole" not in src, "intake must not redefine the role vocabulary"
    assert "EvidencePolicyEngine" in src

    from foundation.applications.rollforward import source_intake
    # The repo is importable under two roots (`applications.*` and
    # `foundation.applications.*`), so compare the vocabularies by value rather
    # than by object identity.
    assert list(source_intake.DatasetRole.__members__) == list(DatasetRole.__members__)
    assert list(source_intake.SourceScope.__members__) == list(SupplyScope.__members__)
    assert list(source_intake.EvidenceQuality.__members__) == list(EvidenceStatus.__members__)
    assert source_intake.DatasetRole.__module__.endswith("evidence_policy")


def test_compatibility_matrix_covers_every_role_and_scope():
    m = policy_compatibility_matrix()
    assert set(m["matrix"]) == {r.value for r in DatasetRole}
    for role, row in m["matrix"].items():
        assert set(row) == {s.value for s in SupplyScope}
        if role == DatasetRole.UNKNOWN.value:
            continue
        assert row[SupplyScope.HISTORICAL.value] == \
            EvidenceAuthority.HISTORICAL_EVIDENCE_ONLY.value
        assert row[SupplyScope.TEMPLATE.value] == \
            EvidenceAuthority.STRUCTURAL_EVIDENCE_ONLY.value
        assert row[SupplyScope.EVALUATION_ONLY.value] == \
            EvidenceAuthority.NOT_AUTHORIZED.value
        for scope in CURRENT_YEAR_SCOPES:
            assert row[scope.value] == EvidenceAuthority.CURRENT_YEAR_AUTHORITY.value


def test_ground_truth_is_not_read_by_the_policy_layer():
    src = (REPO_ROOT / "foundation/applications/rollforward/evidence_policy.py").read_text(
        encoding="utf-8")
    assert PATH_GROUND_TRUTH_FORBIDDEN.name not in src
    assert "HMV-26" not in src
