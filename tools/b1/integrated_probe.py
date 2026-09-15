"""Synthetic-only integrated B1 probe; never reads a representative corpus.

Run from the repository: python -m tools.b1.integrated_probe --run-id run-001
All domain policy refs below are explicit evaluation fixture stubs. They are
not business definitions, source authority, approval or replay configuration.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re

from foundation.adapters.native_identity import DocxNativeIdentity
from foundation.adapters.perception_docling import DoclingPerceptionAdapter
from foundation.domain import AnalysisRun, DocumentVersion
from foundation.evaluation.b1_integrated import B1Harness, write_run
from foundation.services.binding import SemanticNativeBindingService
from tools.b1.build_corpus import W, docx_parts, xlsx_parts, package

CASES=('docx-positive','docx-ambiguous','xlsx-unsupported','malformed','stale')
TIMESTAMP='2026-09-15T00:00:00Z'

@dataclass(frozen=True)
class SyntheticBytes:
    data: bytes
    def resolve(self,document): return self.data


def synthetic_case(case):
    if case not in CASES: raise ValueError('Unknown synthetic case')
    parts=docx_parts()
    paragraph='<w:p><w:r><w:t>Synthetic unique text</w:t></w:r></w:p>'
    body=paragraph*2 if case=='docx-ambiguous' else paragraph
    parts['word/document.xml']=f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    data=package(xlsx_parts() if case=='xlsx-unsupported' else parts)
    if case=='malformed':data=b'PK synthetic malformed package'
    digest=sha256(data).hexdigest()
    document=DocumentVersion(schema_version='0.1.0',object_type='DocumentVersion',id='fixture-version-'+case,
        revision=1,created_at=TIMESTAMP,task_id='fixture-task-'+case,document_id='fixture-document-'+case,
        binary_hash=digest,byte_length=len(data),content_ref={'uri':'urn:foundation:synthetic:'+case,
        'sha256':digest,'media_type':'application/octet-stream'})
    analysis=AnalysisRun(schema_version='0.1.0',object_type='AnalysisRun',id='fixture-analysis-'+case,
        revision=1,created_at=TIMESTAMP,task_id=document.task_id,
        document_version_refs=[{'document_id':document.document_id,'version_id':document.id,'binary_hash':digest}],
        target_contract_definition_ref={'object_type':'TargetContractDefinition','object_id':'fixture-definition-stub','revision':1},
        target_contract_instance_ref={'object_type':'TargetContractInstance','object_id':'fixture-instance-stub','revision':1},
        rule_pack_ref={'object_type':'RulePack','object_id':'fixture-rule-pack-stub','revision':1},
        status='RUNNING',output_refs=[],error_codes=[])
    return document,analysis,SyntheticBytes(data if case!='stale' else data+b'stale synthetic bytes')


def run_suite(repo,run_id):
    """Write five new per-case immutable reports; existing runs are never reused."""
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',run_id):
        raise ValueError('Run ID must be a single opaque alphanumeric name')
    repo=Path(repo).resolve()
    private=repo/'.foundation-private/b1-integrated'/run_id
    public=repo/'qualification/b1/integrated/reports'/run_id
    # Refuse the whole suite before conversion if any output already exists.
    if private.exists() or public.exists():raise FileExistsError('Immutable suite path already exists')
    results={}
    for case in CASES:
        document,analysis,resolver=synthetic_case(case)
        native=DocxNativeIdentity(resolver)
        harness=B1Harness(resolver,DoclingPerceptionAdapter(resolver),native,SemanticNativeBindingService(native))
        report=harness.run(document,analysis)
        report['fixture_scope']='SYNTHETIC_ONLY'
        report['fixture_policy_refs']='EVALUATION_STUBS_ONLY; not business authority or qualified policy'
        results[case]=write_run(report,private/f'{case}.json',public/f'{case}.json',repo)
    return results


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True,help='New immutable run directory name; no corpus input accepted')
    args=parser.parse_args(argv)
    repo=Path(__file__).resolve().parents[2]
    results=run_suite(repo,args.run_id)
    print(json.dumps({'scope':'SYNTHETIC_ONLY','run_id':args.run_id,'cases':results},indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
