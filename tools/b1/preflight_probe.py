"""Run synthetic preflight and preserve the returned evidence for qualification."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from foundation.adapters.preflight import OoxmlPreflight
from foundation.domain import DocumentVersion, DocumentPreflightAssessment, DocumentPreflightStatus
from foundation.evaluation.perception.docling_probe import LocalPinnedContent


def run_preflight(manifest_path: Path, output: Path):
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    cases=[]
    for case in manifest['cases']:
        root=manifest_path.parent.resolve(); path=(root/case['input_path']).resolve()
        if not path.is_relative_to(root): raise ValueError('Input escapes corpus root')
        data=path.read_bytes()
        document=DocumentVersion(schema_version='0.1.0',object_type='DocumentVersion',id='version-'+case['case_id'],revision=1,
            created_at='2026-09-08T00:00:00Z',task_id='qualification-b1',document_id='document-'+case['case_id'],
            binary_hash=case['input_sha256'],byte_length=len(data),content_ref={'uri':'urn:qualification:sha256:'+case['input_sha256'],
                'sha256':case['input_sha256'],'media_type':'application/octet-stream'})
        adapter=OoxmlPreflight(LocalPinnedContent(path))
        assessing=DocumentPreflightAssessment(schema_version='0.1.0',object_type='DocumentPreflightAssessment',
            id='preflight-'+case['case_id'],revision=2,created_at='2026-09-08T00:00:01Z',task_id=document.task_id,
            document_version_ref={'document_id':document.document_id,'version_id':document.id,'binary_hash':document.binary_hash},
            status='ASSESSING',detected_format=None,detected_conformance='UNKNOWN',format_observation_refs=[],
            protection_findings=[],native_structure_findings=[],capability_results=[],
            assessor={'actor_type':'SYSTEM','actor_id':'synthetic-preflight'},engine=adapter.engine,engine_version=adapter.version,
            configuration_ref=adapter.configuration.ref,assessed_at=None,error_codes=[])
        pending=assessing.model_copy(update={'status':DocumentPreflightStatus.PENDING,'revision':1,'created_at':'2026-09-08T00:00:00Z'})
        result=adapter.assess(document,assessing,'2026-09-08T00:00:02Z')
        cases.append({'case_id':case['case_id'],'input_sha256':document.binary_hash,
            'document':document.model_dump(mode='json'),
            'assessment_history':[r.model_dump(mode='json',exclude_unset=True) for r in (pending,assessing,result.assessment)],
            'artifacts':[{'ref':a.ref.model_dump(mode='json'),'canonical_utf8':a.data.decode('utf-8')} for a in result.artifacts]})
    report={'evaluation_version':'1.0.0','qualification_kind':'SYNTHETIC_ONLY','production_qualified':False,
        'audit_integration':'NOT_EVALUATED; caller-owned persistence and causal event emission deferred', 'cases':cases}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,default=ROOT/'tests/golden/cases/b1/manifest.json')
    parser.add_argument('--report',type=Path,default=ROOT/'tests/golden/reports/b1/preflight.json')
    args=parser.parse_args()
    result=run_preflight(args.manifest,args.report)
    for case in result['cases']:
        final=case['assessment_history'][-1]
        print(case['case_id'],final['status'],final['detected_format'],final['error_codes'])
