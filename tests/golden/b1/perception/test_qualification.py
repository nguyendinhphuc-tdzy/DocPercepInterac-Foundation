from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path

import pytest

from foundation.evaluation.perception.docling_probe import run_manifest, digest, installed_candidate
from tools.b1.build_corpus import build
from tools.b1.preflight_probe import run_preflight

CORPUS=Path('tests/golden/cases/b1')


def test_corpus_is_byte_reproducible(tmp_path):
    manifest=build(tmp_path)
    assert manifest==json.loads((CORPUS/'manifest.json').read_text())
    for case in manifest['cases']:
        assert (tmp_path/case['input_path']).read_bytes()==(CORPUS/case['input_path']).read_bytes()
        assert sha256((CORPUS/case['input_path']).read_bytes()).hexdigest()==case['input_sha256']


def test_preflight_report_reproducible_and_frozen_schema_conforming(tmp_path):
    import yaml
    from tools.contracts.validate_contract_fixtures import MachineContract
    machine=MachineContract(yaml.safe_load(Path('docs/contracts/foundation.openapi.yaml').read_text(encoding='utf-8')))
    a=run_preflight(CORPUS/'manifest.json',tmp_path/'first.json')
    b=run_preflight(CORPUS/'manifest.json',tmp_path/'second.json')
    assert a==b
    for case in a['cases']:
        for assessment in case['assessment_history']:
            assert list(machine.validator('DocumentPreflightAssessment').iter_errors(assessment))==[]
        final=case['assessment_history'][-1]
        assert all(c['status']!='SUPPORTED' for c in final['capability_results'])
        for artifact in case['artifacts']:
            assert sha256(artifact['canonical_utf8'].encode()).hexdigest()==artifact['ref']['sha256']


def test_real_docling_corpus_three_runs_and_repeat_report(tmp_path):
    try: installed_candidate()
    except metadata.PackageNotFoundError:
        if os.environ.get('FOUNDATION_B1_REQUIRE_DOCLING')=='1': pytest.fail('Required B1 Docling missing')
        pytest.skip('Docling is intentionally optional in B0')
    a=run_manifest(CORPUS/'manifest.json',tmp_path/'first.json')
    b=run_manifest(CORPUS/'manifest.json',tmp_path/'second.json')
    assert a['reproducible_payload_sha256']==b['reproducible_payload_sha256']
    assert len(a['cases'])==4
    for case in a['cases']:
        assert case['run_count']==3
        assert case['behavior_result']=='PASS'
        if case['case_id']=='malformed':
            assert all(r['conversion_status']=='FAIL' and r['semantic_document'] is None for r in case['runs'])
            continue
        assert all(v=='PASS' for v in case['repeatability'].values())
        first=case['runs'][0]
        obs=first['observations']
        assert obs['table_shapes']==([[3,2],[1,2]] if case['format']=='XLSX' else [[2,2]])
        if case['case_id']=='docx-native-edge':
            assert {'CONTROL_SENTINEL','BOOKMARK_SENTINEL','FIELD_SENTINEL','LINK_SENTINEL','REVISION_SENTINEL','HEADER_SENTINEL'} <= set(obs['text_items'])
        elif case['case_id']=='xlsx-basic':
            cells=first['semantic_document']['tables'][0]['data']['table_cells']
            assert '0.0608' in [c['text'] for c in cells]
            assert '6.08/100' not in json.dumps(first['semantic_document'])
        else:
            assert '14.18%' in obs['text_items']
    stable={k:v for k,v in a.items() if k not in ('timing_observations','installed_packages','reproducible_payload_sha256')}
    assert digest(stable)==a['reproducible_payload_sha256']
