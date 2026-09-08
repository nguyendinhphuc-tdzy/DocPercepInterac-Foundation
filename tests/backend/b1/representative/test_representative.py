"""Synthetic engineering tests, never representative qualification evidence."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from foundation.evaluation.perception import representative as rep
from tools.b1.build_corpus import docx_parts, xlsx_parts, package


def manifest(fmt='DOCX'):
    return {'evaluation_version': '1.1.0', 'required_profiles': ['NARRATIVE'],
            'coverage_review': {'status': 'PENDING', 'reviewer_id': '', 'rationale': '', 'scope_digest': '0' * 64},
            'cases': [{'case_id': f'LF-{fmt}-001', 'local_path': 'client-secret.' + fmt.lower(),
                       'format': fmt, 'document_role': 'TARGET', 'privacy_classification': 'CONFIDENTIAL',
                       'expected_feature_profile': ['NARRATIVE'], 'review_status': 'APPROVED_FOR_EVALUATION'}]}


def result():
    return {'case_id': 'LF-DOCX-001', 'format': 'DOCX', 'document_role': 'TARGET',
            'expected_feature_profile': ['NARRATIVE'], 'evaluation_status': 'EVALUATED',
            'input_unchanged': True, 'input_sha256': 'a' * 64, 'observation_digest': 'b' * 64,
            'conversion_success': True, 'review': None, 'repeatability': {k: 'PASS' for k in rep.REPEATABILITY},
            'feature_checks': [], 'private_detail': 'SECRET text and filename', 'limitations': []}


def review(case, classification=None, critical=False):
    return {'evaluation_version': '1.1.0', 'status': 'COMPLETED', 'reviewer_id': 'private-reviewer', 'reviewed_at': '2026-09-08T00:00:00Z',
            'input_sha256': case['input_sha256'], 'observation_digest': case['observation_digest'],
            'dimensions': {d: ('NOT_APPLICABLE' if d == 'TABLE_FIDELITY' and 'TABLES' not in case['expected_feature_profile'] else 'PASS') for d in rep.REVIEW_DIMENSIONS},
            'feature_evidence': {p: {'status': 'PASS', 'evidence_basis': 'HUMAN'} for p in case['expected_feature_profile']},
            'notes': 'SECRET review',
            'losses': [] if classification is None else [{'classification': classification,
                'critical_semantic_loss': critical, 'recoverable_by_native_identity': False,
                'description': 'SECRET loss detail'}]}


def test_schema_and_example():
    rep.validate_manifest(manifest())
    rep.validate_manifest(json.loads((rep.SPEC / 'corpus.example.json').read_text()))
    template = json.loads((rep.SPEC / 'review.example.json').read_text())
    assert rep.Draft202012Validator(rep.SCHEMA['$defs']['Review']).is_valid(template)
    assert template['evaluation_version'] == '1.1.0'


@pytest.mark.parametrize('field,value', [('case_id', 'ClientCo'), ('case_id', 'LF-DOCX-000'),
    ('document_role', 'ClientCo'), ('format', 'PDF'), ('review_status', 'ACCEPTED'),
    ('expected_feature_profile', ['ClientCo']), ('privacy_classification', 'PUBLIC')])
def test_manifest_rejects_unsafe_values(field, value):
    m = manifest(); m['cases'][0][field] = value
    with pytest.raises(rep.QualificationError): rep.validate_manifest(m)


def test_unknown_field_duplicate_case_and_format_disagreement():
    for change in ('extra', 'duplicate', 'format'):
        m = manifest()
        if change == 'extra': m['cases'][0]['client_name'] = 'SECRET'
        elif change == 'duplicate': m['cases'] *= 2
        else: m['cases'][0]['case_id'] = 'LF-XLSX-001'
        with pytest.raises(rep.QualificationError): rep.validate_manifest(m)


def test_absent_environment_has_no_fake_results(tmp_path, monkeypatch):
    monkeypatch.delenv(rep.CORPUS_ENV, raising=False)
    out = rep.evaluate(None, tmp_path)
    assert out['corpus_status'] == 'CORPUS_NOT_PROVIDED'
    assert rep.sanitize(out)['cases'] == []
    assert rep.sanitize(out)['decision'] == 'INSUFFICIENT_EVIDENCE'


def test_missing_or_inside_repo_corpus_rejected(tmp_path, monkeypatch):
    for path in (tmp_path / 'absent', rep.ROOT):
        monkeypatch.setenv(rep.CORPUS_ENV, str(path))
        with pytest.raises(rep.QualificationError): rep.corpus_root(rep.ROOT)


def test_path_escape_and_unapproved_case_refused(tmp_path, monkeypatch):
    monkeypatch.setenv(rep.CORPUS_ENV, str(tmp_path))
    m = manifest(); m['cases'][0]['local_path'] = '../escape.docx'
    with pytest.raises(rep.QualificationError): rep.evaluate(m, rep.ROOT)
    m = manifest(); m['cases'][0]['review_status'] = 'PENDING'
    out = rep.evaluate(m, rep.ROOT)
    assert out['cases'][0]['evaluation_status'] == 'NOT_EVALUATED'
    assert rep.decide(out) == 'INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('fmt,builder', [('DOCX', docx_parts), ('XLSX', xlsx_parts)])
def test_actual_probe_reused_read_only_private_evidence(tmp_path, monkeypatch, fmt, builder):
    from importlib import metadata
    import os
    try: rep.probe.installed_candidate()
    except metadata.PackageNotFoundError:
        if os.environ.get('FOUNDATION_B1_REQUIRE_DOCLING') == '1': pytest.fail('B1 candidate required')
        pytest.skip('Docling optional outside B1')
    m = manifest(fmt); data = package(builder()); path = tmp_path / m['cases'][0]['local_path']
    path.write_bytes(data); monkeypatch.setenv(rep.CORPUS_ENV, str(tmp_path))
    full = rep.evaluate(m, rep.ROOT)
    case = full['cases'][0]
    assert path.read_bytes() == data
    assert case['input_sha256'] == case['post_input_sha256'] == sha256(data).hexdigest()
    assert case['preflight']['assessment']['detected_format'] == fmt
    assert len(case['runs']) == 3 and case['conversion_success']
    assert all(x == 'PASS' for x in case['repeatability'].values())
    assert all(v == 'REVIEW_REQUIRED' for v in rep.sanitize(full)['cases'][0]['review_dimensions'].values())
    public = json.dumps(rep.sanitize(full))
    for secret in (path.name, str(tmp_path), sha256(data).hexdigest(), '14.18%', '0.0608', 'Synthetic Local File'):
        assert secret not in public
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


def test_sanitizer_allowlist_never_copies_private_values():
    c = result(); c['review'] = review(c, 'NATIVE_REQUIRED')
    full = {'corpus_status': 'AVAILABLE', 'cases': [c], 'manifest': manifest(), 'secret': 'SECRET'}
    public = rep.sanitize(full)
    text = json.dumps(public)
    for secret in ('SECRET', 'private-reviewer', 'a' * 64, 'b' * 64, 'client-secret'):
        assert secret not in text
    c['case_id'] = 'SECRET'
    with pytest.raises(rep.QualificationError): rep.sanitize(full)


def completed_full(count=1):
    m = manifest(); m['coverage_review'].update(status='COMPLETED', reviewer_id='private', rationale='approved scope')
    cases = []
    for i in range(count):
        c = result(); c['case_id'] = f'LF-DOCX-{i+1:03}'
        c['input_sha256'] = sha256(f'synthetic-input-{i}'.encode()).hexdigest()
        c['review'] = review(c); cases.append(c)
    m['cases'] = [{**deepcopy(m['cases'][0]), 'case_id': c['case_id']} for c in cases]
    m['coverage_review']['scope_digest'] = rep.coverage_scope_digest(m)
    return {'corpus_status': 'AVAILABLE', 'manifest': m, 'cases': cases}


def with_profiles(profiles):
    full = completed_full()
    full['manifest']['required_profiles'] = list(profiles)
    full['manifest']['cases'][0]['expected_feature_profile'] = list(profiles)
    c = full['cases'][0]; c['expected_feature_profile'] = list(profiles); c['review'] = review(c)
    full['manifest']['coverage_review']['scope_digest'] = rep.coverage_scope_digest(full['manifest'])
    return full


def test_decision_requires_complete_bound_review_and_coverage():
    assert rep.decide(completed_full()) == 'PROVISIONAL_CONTINUE_TO_B1_2B'
    for defect in ('missing', 'stale', 'dimension', 'coverage', 'profile', 'mutation', 'conversion', 'repeatability'):
        full = completed_full(); c = full['cases'][0]
        if defect == 'missing': c['review'] = None
        elif defect == 'stale': c['review']['input_sha256'] = 'c' * 64
        elif defect == 'dimension': c['review']['dimensions']['CONTENT_FIDELITY'] = 'REVIEW_REQUIRED'
        elif defect == 'coverage': full['manifest']['coverage_review']['status'] = 'PENDING'
        elif defect == 'profile': full['manifest']['required_profiles'] = ['CHARTS']
        elif defect == 'mutation': c['input_unchanged'] = False
        elif defect == 'conversion': c['conversion_success'] = False
        else: c['repeatability']['references'] = 'OBSERVED_LIMITATION'
        assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE', defect


def test_native_only_loss_does_not_reject_and_repeated_critical_loss_does():
    full = completed_full(); c = full['cases'][0]; c['review'] = review(c, 'NATIVE_REQUIRED')
    assert rep.decide(full) == 'PROVISIONAL_COORDINATE_B1_2B_AND_B1_3'
    full = completed_full(2)
    for c in full['cases']: c['review'] = review(c, 'SEMANTIC_REQUIRED', True)
    assert rep.decide(full) == 'RECONSIDER_DOCLING_BASELINE'
    full['cases'] = full['cases'][:1]
    full['manifest']['cases'] = full['manifest']['cases'][:1]
    full['manifest']['coverage_review']['scope_digest'] = rep.coverage_scope_digest(full['manifest'])
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


def test_invalid_review_cannot_create_authority():
    c = result(); c['review'] = review(c, 'NATIVE_REQUIRED', True)
    assert not rep.review_valid(c)
    c['review'] = review(c); c['review']['dimensions']['TABLE_FIDELITY'] = 'CONFIDENT'
    assert not rep.review_valid(c)


def test_repeated_same_input_is_not_multiple_critical_cases():
    full = completed_full(2)
    for c in full['cases']:
        c['input_sha256'] = 'a' * 64
        c['review'] = review(c, 'SEMANTIC_REQUIRED', True)
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


def test_conversion_failures_and_logging_do_not_leak(tmp_path, monkeypatch, capsys):
    import logging
    m = manifest(); (tmp_path / m['cases'][0]['local_path']).write_bytes(package(docx_parts()))
    monkeypatch.setenv(rep.CORPUS_ENV, str(tmp_path))
    def failure(*args):
        print('SECRET PRINT'); logging.error('SECRET LOG'); raise ValueError('SECRET EXCEPTION')
    monkeypatch.setattr(rep.probe, 'probe_once', failure)
    full = rep.evaluate(m, rep.ROOT)
    assert full['cases'][0]['evaluation_status'] == 'FAILED'
    captured = capsys.readouterr()
    assert 'SECRET' not in captured.out + captured.err
    assert 'SECRET' not in json.dumps(rep.sanitize(full))
    assert 'SECRET EXCEPTION' in full['cases'][0]['private_error']


def test_native_engine_diagnostics_are_suppressed(tmp_path, monkeypatch, capfd):
    import os
    m = manifest(); (tmp_path / m['cases'][0]['local_path']).write_bytes(package(docx_parts()))
    monkeypatch.setenv(rep.CORPUS_ENV, str(tmp_path))
    def native_output(*args):
        os.write(1, b'SECRET NATIVE STDOUT'); os.write(2, b'SECRET NATIVE STDERR')
        raise ValueError('private failure')
    monkeypatch.setattr(rep.probe, 'probe_once', native_output)
    rep.evaluate(m, rep.ROOT)
    captured = capfd.readouterr()
    assert 'SECRET' not in captured.out + captured.err


def test_changed_input_is_detected_even_if_engine_reports_success(tmp_path, monkeypatch):
    m = manifest(); path = tmp_path / m['cases'][0]['local_path']; path.write_bytes(package(docx_parts()))
    monkeypatch.setenv(rep.CORPUS_ENV, str(tmp_path))
    def mutate(*args):
        path.write_bytes(b'synthetic external change')
        raise ValueError('conversion failed')
    monkeypatch.setattr(rep.probe, 'probe_once', mutate)
    full = rep.evaluate(m, rep.ROOT)
    assert not full['cases'][0]['input_unchanged']
    assert full['cases'][0]['evaluation_status'] == 'FAILED'
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


def test_missing_input_is_not_evaluated(tmp_path, monkeypatch):
    monkeypatch.setenv(rep.CORPUS_ENV, str(tmp_path))
    full = rep.evaluate(manifest(), rep.ROOT)
    assert full['cases'][0]['evaluation_status'] == 'NOT_EVALUATED'
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('defect', ['missing_map', 'missing_feature', 'not_evaluated', 'stale_review'])
def test_declared_charts_does_not_prove_evaluated_profile(defect):
    full = with_profiles(['CHARTS']); c = full['cases'][0]
    c['feature_checks'] = [{'feature': 'CHARTS', 'native_presence': 'NOT_EVALUATED', 'semantic_presence': 'NOT_EVALUATED'}]
    if defect == 'missing_map': del c['review']['feature_evidence']
    elif defect == 'missing_feature': c['review']['feature_evidence'] = {}
    elif defect == 'stale_review': c['review']['observation_digest'] = 'c' * 64
    else: c['review']['feature_evidence']['CHARTS']['status'] = 'NOT_EVALUATED'
    assert 'CHARTS' not in rep.evaluated_profiles(full['cases'])
    assert 'CHARTS' in rep.sanitize(full)['unevaluated_profiles']
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


def test_human_only_chart_review_can_supply_evidence():
    full = with_profiles(['CHARTS']); c = full['cases'][0]
    c['feature_checks'] = [{'feature': 'CHARTS', 'native_presence': 'NOT_EVALUATED', 'semantic_presence': 'NOT_EVALUATED'}]
    assert rep.evaluated_profiles(full['cases']) == {'CHARTS'}
    assert 'CHARTS' not in rep.sanitize(full)['unevaluated_profiles']
    assert rep.decide(full) == 'PROVISIONAL_CONTINUE_TO_B1_2B'


@pytest.mark.parametrize('status', ['PARTIAL', 'FAIL', 'UNSUPPORTED'])
def test_feature_quality_is_distinct_from_evaluated_coverage(status):
    full = with_profiles(['TABLES']); c = full['cases'][0]
    c['review']['feature_evidence']['TABLES']['status'] = status
    assert rep.review_valid(c)
    assert rep.evaluated_profiles(full['cases']) == {'TABLES'}
    assert 'TABLES' not in rep.sanitize(full)['unevaluated_profiles']
    assert rep.sanitize(full)['cases'][0]['feature_evidence']['TABLES']['status'] == status
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


def test_table_applicability_is_truthful():
    full = with_profiles(['NARRATIVE']); c = full['cases'][0]
    assert c['review']['dimensions']['TABLE_FIDELITY'] == 'NOT_APPLICABLE'
    assert rep.review_valid(c)
    assert rep.sanitize(full)['cases'][0]['review_dimensions']['TABLE_FIDELITY'] == 'NOT_APPLICABLE'
    assert rep.decide(full) == 'PROVISIONAL_CONTINUE_TO_B1_2B'
    c['review']['dimensions']['TABLE_FIDELITY'] = 'PASS'
    assert not rep.review_valid(c)
    c = with_profiles(['TABLES'])['cases'][0]
    c['review']['dimensions']['TABLE_FIDELITY'] = 'NOT_APPLICABLE'
    assert not rep.review_valid(c)


@pytest.mark.parametrize('dimension', [d for d in rep.REVIEW_DIMENSIONS if d != 'TABLE_FIDELITY'])
def test_other_dimensions_cannot_be_not_applicable(dimension):
    c = completed_full()['cases'][0]
    c['review']['dimensions'][dimension] = 'NOT_APPLICABLE'
    assert not rep.review_valid(c)


def test_scope_digest_canonical_order_and_private_field_exclusion():
    m = completed_full(2)['manifest']
    m['required_profiles'] = ['NARRATIVE', 'TABLES']
    m['cases'][0]['expected_feature_profile'] = ['NARRATIVE', 'TABLES']
    original = deepcopy(m)
    expected = rep.coverage_scope_digest(m)
    assert rep.coverage_scope_digest(m) == expected and m == original
    m['required_profiles'].reverse(); m['cases'][0]['expected_feature_profile'].reverse(); m['cases'].reverse()
    m['cases'][0]['local_path'] = 'SECRET OTHER FILENAME'
    m['coverage_review']['reviewer_id'] = 'SECRET REVIEWER'
    m['coverage_review']['rationale'] = 'SECRET NOTE'
    assert rep.coverage_scope_digest(m) == expected
    assert len(expected) == 64 and all(c in '0123456789abcdef' for c in expected)


@pytest.mark.parametrize('field', ['required_profiles', 'case_set', 'case_id', 'format', 'document_role', 'expected_feature_profile', 'evaluation_version'])
def test_scope_edits_invalidate_coverage_without_overwriting_digest(field):
    full = completed_full(); m = full['manifest']; before = m['coverage_review']['scope_digest']
    if field == 'required_profiles': m[field].append('TABLES')
    elif field == 'case_set':
        c = deepcopy(m['cases'][0]); c['case_id'] = 'LF-DOCX-002'; m['cases'].append(c)
    elif field == 'case_id': m['cases'][0][field] = 'LF-DOCX-002'
    elif field == 'format': m['cases'][0][field] = 'XLSX'; m['cases'][0]['case_id'] = 'LF-XLSX-001'
    elif field == 'document_role': m['cases'][0][field] = 'SOURCE'
    elif field == 'expected_feature_profile': m['cases'][0][field].append('TABLES')
    else: m[field] = '1.0.0'
    assert rep.coverage_scope_digest(m) != before
    assert not rep.coverage_review_valid(m)
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'
    assert m['coverage_review']['scope_digest'] == before


def test_result_scope_cannot_substitute_for_reviewed_case_set():
    full = completed_full(); full['cases'][0]['case_id'] = 'LF-DOCX-002'
    assert rep.decide(full) == 'INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('field,value', [('status', 'CONFIDENT'), ('evidence_basis', 'AI'), ('notes', 'SECRET')])
def test_feature_evidence_uses_closed_schema(field, value):
    c = completed_full()['cases'][0]
    c['review']['feature_evidence']['NARRATIVE'][field] = value
    assert not rep.review_valid(c)


def test_feature_review_matches_declared_scope_exactly():
    c = completed_full()['cases'][0]
    c['review']['feature_evidence']['CHARTS'] = {'status': 'PASS', 'evidence_basis': 'HUMAN'}
    assert not rep.review_valid(c)


def test_scope_digest_and_feature_evidence_do_not_leak_private_fields():
    full = completed_full(); c = full['cases'][0]
    c['review']['notes'] = 'SECRET NOTES'; c['private_detail'] = '/SECRET/PATH/client.docx'
    public = rep.sanitize(full)
    assert public['evaluation_version'] == '1.1.0'
    assert public['cases'][0]['feature_evidence'] == {'NARRATIVE': {'status': 'PASS', 'evidence_basis': 'HUMAN'}}
    encoded = json.dumps(public)
    for private in ['SECRET', 'client.docx', 'private-reviewer', c['input_sha256'], c['observation_digest'], full['manifest']['coverage_review']['scope_digest']]:
        assert private not in encoded


@pytest.mark.parametrize('basis', ['AUTOMATED', 'BOTH'])
def test_automated_evidence_basis_requires_an_observation(basis):
    full = with_profiles(['CHARTS']); c = full['cases'][0]
    c['review']['feature_evidence']['CHARTS']['evidence_basis'] = basis
    c['feature_checks'] = [{'feature': 'CHARTS', 'native_presence': 'NOT_EVALUATED', 'semantic_presence': 'NOT_EVALUATED'}]
    assert not rep.review_valid(c)
    assert 'CHARTS' in rep.sanitize(full)['unevaluated_profiles']
    c['feature_checks'][0]['native_presence'] = 'NOT_OBSERVED'
    assert rep.review_valid(c)
    assert rep.evaluated_profiles(full['cases']) == {'CHARTS'}


@pytest.mark.parametrize('digest', ['', 'A' * 64, 'a' * 63])
def test_coverage_scope_schema_rejects_invalid_digest(digest):
    m = manifest(); m['coverage_review']['scope_digest'] = digest
    with pytest.raises(rep.QualificationError): rep.validate_manifest(m)


def test_old_evaluation_schema_requires_explicit_migration():
    m = manifest(); m['evaluation_version'] = '1.0.0'
    with pytest.raises(rep.QualificationError): rep.validate_manifest(m)
    c = completed_full()['cases'][0]; c['review']['evaluation_version'] = '1.0.0'
    assert not rep.review_valid(c)


def test_failed_quality_remains_covered_for_critical_loss_decision():
    full = completed_full(2)
    for c in full['cases']:
        c['review'] = review(c, 'SEMANTIC_REQUIRED', True)
        c['review']['feature_evidence']['NARRATIVE']['status'] = 'FAIL'
        c['review']['dimensions']['CONTENT_FIDELITY'] = 'FAIL'
    assert rep.evaluated_profiles(full['cases']) == {'NARRATIVE'}
    assert rep.decide(full) == 'RECONSIDER_DOCLING_BASELINE'
