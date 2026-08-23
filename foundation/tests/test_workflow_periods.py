"""
Fiscal-period logic (Phase PROD-UX-1 hardening, P0-3).

The roll-forward relationship is defined once, explicitly, and generally:

    historical_period + expected_gap == current_period

and the gating invariant is the timeless one: the historical period strictly
precedes the current one. No year is ever special-cased — these tests run the
same rules across periods decades apart to prove it.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

import pytest

from applications.rollforward.source_intake import ArtifactFormat
from applications.rollforward.evidence_policy import DatasetRole
from applications.rollforward.workflow_intake import (
    EXPECTED_ROLL_FORWARD_GAP_YEARS,
    SLOT_SPECS,
    DocumentSignals,
    FiscalPeriod,
    PeriodRelationship,
    RollForwardPeriods,
    SlotId,
    SlotRoleValidator,
    SlotValidationStatus,
)

warnings.filterwarnings("ignore")

MODULE_SOURCE = (Path(__file__).resolve().parents[1]
                 / "applications" / "rollforward" / "workflow_intake.py").read_text(
    encoding="utf-8")


def _local_file_signals(year: int | None, placeholders: int = 0) -> DocumentSignals:
    """A Local File-shaped DOCX stating `year`, with no perception involved."""
    return DocumentSignals(
        artifact_format=ArtifactFormat.DOCX,
        fiscal_year=year,
        fiscal_year_hits=12 if year else 0,
        placeholder_hits=placeholders,
        observed_roles=(DatasetRole.FAR, DatasetRole.BUSINESS_NARRATIVE,
                        DatasetRole.RELATED_PARTY_TRANSACTIONS),
        satisfying_roles=(),
        is_local_file_shaped=True,
        is_blank_template_shaped=placeholders >= 10 and year is None,
        record_count=40,
    )


def _source_signals(year: int | None) -> DocumentSignals:
    return DocumentSignals(
        artifact_format=ArtifactFormat.XLSX,
        fiscal_year=year,
        fiscal_year_hits=8 if year else 0,
        placeholder_hits=0,
        observed_roles=(DatasetRole.RELATED_PARTY_TRANSACTIONS,),
        satisfying_roles=(DatasetRole.RELATED_PARTY_TRANSACTIONS,),
        is_local_file_shaped=False,
        is_blank_template_shaped=False,
        record_count=120,
    )


def _validate_historical(candidate_year: int | None, current_year: int | None):
    return SlotRoleValidator.validate(
        SLOT_SPECS[SlotId.HISTORICAL_LOCAL_FILE],
        _local_file_signals(candidate_year),
        RollForwardPeriods(current=FiscalPeriod.of(current_year)),
    )


# ---------------------------------------------------------------------------
# THE RELATIONSHIP
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("historical,current", [
    (1999, 2000), (2018, 2019), (2023, 2024), (2030, 2031), (2098, 2099),
])
def test_consecutive_periods_hold_across_any_era(historical, current):
    periods = RollForwardPeriods(FiscalPeriod(historical), FiscalPeriod(current))
    assert periods.relationship is PeriodRelationship.CONSECUTIVE
    assert periods.satisfies_invariant
    assert periods.gap_years == EXPECTED_ROLL_FORWARD_GAP_YEARS


@pytest.mark.parametrize("historical,current,relationship", [
    (2015, 2024, PeriodRelationship.WIDE_GAP),
    (2024, 2024, PeriodRelationship.SAME_PERIOD),
    (2025, 2024, PeriodRelationship.INVERTED),
    (2001, 1999, PeriodRelationship.INVERTED),
])
def test_relationship_classification(historical, current, relationship):
    periods = RollForwardPeriods(FiscalPeriod(historical), FiscalPeriod(current))
    assert periods.relationship is relationship


def test_relationship_is_unknown_until_both_sides_state_a_period():
    assert RollForwardPeriods(FiscalPeriod(2024), None).relationship \
        is PeriodRelationship.UNKNOWN
    assert RollForwardPeriods(None, FiscalPeriod(2024)).relationship \
        is PeriodRelationship.UNKNOWN
    assert RollForwardPeriods().satisfies_invariant is False


def test_the_invariant_is_that_historical_precedes_current():
    assert RollForwardPeriods(FiscalPeriod(2015), FiscalPeriod(2024)).satisfies_invariant
    assert not RollForwardPeriods(FiscalPeriod(2024), FiscalPeriod(2024)).satisfies_invariant
    assert not RollForwardPeriods(FiscalPeriod(2025), FiscalPeriod(2024)).satisfies_invariant


def test_expected_gap_is_configurable_not_assumed():
    """A workflow that rolls two periods forward states so; it is not hardcoded."""
    periods = RollForwardPeriods(FiscalPeriod(2020), FiscalPeriod(2022), expected_gap_years=2)
    assert periods.relationship is PeriodRelationship.CONSECUTIVE
    assert RollForwardPeriods(FiscalPeriod(2020), FiscalPeriod(2022)).relationship \
        is PeriodRelationship.WIDE_GAP


def test_descriptions_name_the_actual_periods():
    text = RollForwardPeriods(FiscalPeriod(2031), FiscalPeriod(2032)).describe()
    assert "FY2031" in text and "FY2032" in text


# ---------------------------------------------------------------------------
# THE VALIDATOR USES IT — same rules, any era
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("historical,current", [(2019, 2020), (2023, 2024), (2040, 2041)])
def test_preceding_local_file_is_confirmed_in_any_era(historical, current):
    verdict = _validate_historical(historical, current)
    assert verdict.status is SlotValidationStatus.ROLE_CONFIRMED
    assert f"FY{historical}" in verdict.reasons[0]


@pytest.mark.parametrize("year", [2019, 2024, 2035])
def test_same_period_local_file_is_a_mismatch_in_any_era(year):
    verdict = _validate_historical(year, year)
    assert verdict.status is SlotValidationStatus.ROLE_MISMATCH
    assert verdict.detected_label == f"FY{year} Final Local File"


@pytest.mark.parametrize("historical,current", [(2025, 2024), (2041, 2040)])
def test_a_later_local_file_in_the_historical_slot_is_a_mismatch(historical, current):
    assert _validate_historical(historical, current).status is SlotValidationStatus.ROLE_MISMATCH


def test_a_wider_gap_is_escalated_to_a_human_not_silently_accepted():
    verdict = _validate_historical(2015, 2024)
    assert verdict.status is SlotValidationStatus.HUMAN_REVIEW
    assert "9 periods" in verdict.reasons[0]


def test_without_current_year_evidence_the_period_is_provisionally_accepted():
    verdict = _validate_historical(2024, None)
    assert verdict.status is SlotValidationStatus.ROLE_CONFIRMED
    assert "re-checked" in verdict.reasons[0]


def test_a_source_older_than_the_historical_file_is_a_mismatch():
    verdict = SlotRoleValidator.validate(
        SLOT_SPECS[SlotId.CURRENT_YEAR_SOURCES],
        _source_signals(2018),
        RollForwardPeriods(historical=FiscalPeriod(2019), current=FiscalPeriod(2020)),
    )
    assert verdict.status is SlotValidationStatus.ROLE_MISMATCH
    assert "FY2018" in verdict.reasons[0] and "FY2019" in verdict.reasons[0]


def test_a_source_after_the_historical_file_is_confirmed():
    verdict = SlotRoleValidator.validate(
        SLOT_SPECS[SlotId.CURRENT_YEAR_SOURCES],
        _source_signals(2020),
        RollForwardPeriods(historical=FiscalPeriod(2019), current=FiscalPeriod(2020)),
    )
    assert verdict.status is SlotValidationStatus.ROLE_CONFIRMED


# ---------------------------------------------------------------------------
# NO YEAR IS BAKED IN
# ---------------------------------------------------------------------------

def test_no_fiscal_year_is_hardcoded_in_the_intake_module():
    """Guards against a rule like "FY2023 means historical" creeping back in."""
    literals = re.findall(r"\b(?:19|20)\d{2}\b", MODULE_SOURCE)
    assert literals == [], f"hardcoded year literal(s) in workflow_intake.py: {set(literals)}"


def test_period_detection_accepts_any_four_digit_year():
    from applications.rollforward.workflow_intake import _PERIOD_PATTERN

    for year in ("1998", "2007", "2024", "2099"):
        assert _PERIOD_PATTERN.findall(f"for the year ended 31 December {year}") == [year]
