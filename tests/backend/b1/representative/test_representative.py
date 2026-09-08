"""Synthetic engineering tests, never representative qualification evidence."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from foundation.evaluation.perception import representative as rep
from tools.b1.build_corpus import docx_parts, xlsx_parts, package


def manifest(fmt='DOCX'):
    return {'evaluation_version': '1.0.0', 'required_profiles': ['NARRATIVE'],
            'coverage_review': {'status': 'PENDING', 'reviewer_id': '', 'rationale': ''},
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
    return {'status': 'COMPLETED', 'reviewer_id': 'private-reviewer', 'reviewed_at': '2026-09-08T00:00:00Z',
            'input_sha256': case['input_sha256'], 'observation_digest': case['observation_digest'],
            'dimensions': {d: 'PASS' for d in rep.REVIEW_DIMENSIONS}, 'notes': 'SECRET review',
            'losses': [] if classification is None else [{'classification': classification,
                'critical_semantic_loss': critical, 'recoverable_by_native_identity': False,
                'description': 'SECRET loss detail'}]}


def test_schema_and_example():
    rep.validate_manifest(manifest())
    rep.validate_manifest(json.loads((rep.SPEC / 'corpus.example.json').read_text()))


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
    m = manifest(); m['coverage_review'] = {'status': 'COMPLETED', 'reviewer_id': 'private', 'rationale': 'approved scope'}
    cases = []
    for i in range(count):
        c = result(); c['case_id'] = f'LF-DOCX-{i+1:03}'
        c['input_sha256'] = sha256(f'synthetic-input-{i}'.encode()).hexdigest()
        c['review'] = review(c); cases.append(c)
    return {'corpus_status': 'AVAILABLE', 'manifest': m, 'cases': cases}


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
