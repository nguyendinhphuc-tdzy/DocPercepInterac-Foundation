"""Synthetic CLI evidence tests; no representative/human qualification claims."""
import json
import pytest
from tools.b1.integrated_probe import run_suite, CASES


def test_synthetic_suite_and_immutable_public_private_boundary(tmp_path):
    results=run_suite(tmp_path, 'run-001')
    assert set(results)==set(CASES)
    assert all(x['outcome']=='PASS' for x in results['docx-positive']['stages'].values())
    assert results['docx-ambiguous']['stages']['binding']['outcome']=='FAIL'
    assert results['xlsx-unsupported']['stages']['native_identity']['outcome']=='FAIL'
    assert results['malformed']['stages']['preflight']['outcome']=='FAIL'
    assert results['stale']['stages']['input_integrity']['outcome']=='FAIL'
    for case in CASES:
        private=tmp_path/'.foundation-private/b1-integrated/run-001'/f'{case}.json'
        public=tmp_path/'qualification/b1/integrated/reports/run-001'/f'{case}.json'
        report=json.loads(private.read_text()); summary=json.loads(public.read_text())
        assert report['fixture_scope']=='SYNTHETIC_ONLY'
        assert report['records']['analysis_run']['rule_pack_ref']['object_id'].startswith('fixture-')
        assert summary['production_qualified'] is False
        assert summary['review_status']=='REVIEW_REQUIRED'
        assert 'Synthetic unique' not in public.read_text()
        assert 'records' not in summary
    with pytest.raises(FileExistsError):run_suite(tmp_path,'run-001')

@pytest.mark.parametrize('run_id',['../bad','/absolute','a/b','a\\b','', '.', '..'])
def test_run_id_must_be_single_opaque_name(tmp_path,run_id):
    with pytest.raises(ValueError):run_suite(tmp_path,run_id)
