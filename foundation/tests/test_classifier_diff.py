"""Unit tests for eval/classifier_diff.py — the baseline-vs-candidate
Classifier comparison harness.

All tests below exercise pure `diff_elements` logic (no file I/O) except
`test_compare_on_document_stub_matches_baseline_smoke`, which is the one
end-to-end smoke test.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.classifier_diff import candidate_stub, compare_on_document, diff_elements, render_report
from perception.models import AnchorDOCX, Element, ElementType

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fixture_generic_handbook.docx"


def _el(
    index: int,
    etype: ElementType = ElementType.PARA,
    name: str = "x",
    text: str = "hello",
    style_id: str = "Normal",
    paragraph_index: int | None = None,
) -> Element:
    if paragraph_index is None:
        paragraph_index = index
    anchor = AnchorDOCX(paragraph_index=paragraph_index, style_id=style_id, text_fingerprint="abcd1234")
    return Element(index=index, type=etype, name=name, text=text, anchor=anchor, confidence=1.0)


def test_diff_elements_identical_lists_full_agreement():
    baseline = [_el(0), _el(1, etype=ElementType.HEADING, name="H"), _el(2, etype=ElementType.CELL, name="C")]
    candidate = [_el(0), _el(1, etype=ElementType.HEADING, name="H"), _el(2, etype=ElementType.CELL, name="C")]

    report = diff_elements(baseline, candidate)

    assert report.total_elements == 3
    assert report.count_match is True
    assert report.type_agreement == 1.0
    assert report.name_agreement == 1.0
    assert report.anchor_preserved == 1.0
    assert report.exact_agreement == 1.0
    assert report.divergences == []
    assert report.missing_in_candidate == []
    assert report.extra_in_candidate == []


def test_diff_elements_detects_type_and_name_divergences_at_correct_indices():
    baseline = [_el(0), _el(1), _el(2), _el(3)]
    candidate = [
        _el(0),
        _el(1, etype=ElementType.HEADING, name="different"),  # type + name divergence
        _el(2),
        _el(3, name="renamed"),  # name-only divergence
    ]

    report = diff_elements(baseline, candidate)

    assert report.count_match is True
    assert len(report.divergences) == 2
    assert {d.index for d in report.divergences} == {1, 3}

    d1 = next(d for d in report.divergences if d.index == 1)
    assert d1.baseline_type == ElementType.PARA
    assert d1.candidate_type == ElementType.HEADING
    assert d1.baseline_name == "x"
    assert d1.candidate_name == "different"
    assert d1.anchor_changed is False

    d3 = next(d for d in report.divergences if d.index == 3)
    assert d3.baseline_type == d3.candidate_type
    assert d3.candidate_name == "renamed"

    # 2 divergent / 4 common: exact_agreement halved; type only differs at
    # index 1 (3/4); name differs at 1 and 3 (2/4); anchors never changed.
    assert report.exact_agreement == 0.5
    assert report.type_agreement == 0.75
    assert report.name_agreement == 0.5
    assert report.anchor_preserved == 1.0


def test_diff_elements_handles_fewer_candidate_elements():
    baseline = [_el(0), _el(1), _el(2)]
    candidate = [_el(0), _el(1)]  # index 2 missing entirely

    report = diff_elements(baseline, candidate)

    assert report.total_elements == 3
    assert report.count_match is False
    assert report.missing_in_candidate == [2]
    assert report.extra_in_candidate == []
    # only the intersection (indices 0, 1) is diffed, and it fully agrees
    assert report.divergences == []
    assert report.exact_agreement == 1.0


def test_diff_elements_detects_anchor_change():
    baseline = [_el(0), _el(1), _el(2)]
    candidate = [
        _el(0),
        _el(1, paragraph_index=99),  # same type/name, anchor mutated
        _el(2),
    ]

    report = diff_elements(baseline, candidate)

    assert report.count_match is True
    assert report.anchor_preserved < 1.0
    assert len(report.divergences) == 1

    d = report.divergences[0]
    assert d.index == 1
    assert d.anchor_changed is True
    # the classifier must not silently relabel type/name just because the
    # anchor changed — this divergence is anchor-only
    assert d.baseline_type == d.candidate_type
    assert d.baseline_name == d.candidate_name


def test_render_report_includes_metrics_and_truncates_long_divergence_lists():
    baseline = [_el(i) for i in range(60)]
    candidate = [_el(i, name=f"different-{i}") for i in range(60)]  # all 60 diverge

    report = diff_elements(baseline, candidate)
    text = render_report(report)

    assert "exact_agreement" in text
    assert "Divergences (60)" in text
    assert "... and 10 more" in text


def test_compare_on_document_stub_matches_baseline_smoke():
    report = compare_on_document(str(FIXTURE), candidate_stub)

    assert report.count_match is True
    assert report.exact_agreement == 1.0
    assert report.divergences == []
