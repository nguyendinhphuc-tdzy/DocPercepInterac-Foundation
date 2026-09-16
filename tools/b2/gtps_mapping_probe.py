"""Private evaluation bridge from retained Run-003 semantics to B2.1 planning.

Usage: python -m tools.b2.gtps_mapping_probe --report <private Run-003 full.json>
  --config <private version-bound selectors.json> --output <new private plan.json>
No perception rerun, native locator fabrication, source mutation or human review.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from foundation.domain import DocumentVersionRef, TargetRegion
from foundation.applications.gtps_mapping import View, Selection, Policy, TargetRule, Slot, MappingPlanner, normalize, canonical_digest, MappingError
from tools.b1.verify_private_corpus_boundary import verify


def private_path(value, *, output=False):
    path=Path(value).absolute()
    if path.resolve()!=path or '.foundation-private' not in path.parts:
        raise ValueError('PRIVATE_PATH_REQUIRED')
    if output and path.exists():raise ValueError('IMMUTABLE_OUTPUT_EXISTS')
    return path


def evaluate(report,config):
    """Config selects only non-Golden roles. Unselected case content is never read."""
    if report.get('evaluation_version')!='1.2.0':raise ValueError('RUN003_VERSION_REQUIRED')
    views=[]; selections={}; boundaries={}
    allowed={'CURRENT_SOURCE':'SOURCE','HISTORICAL_REFERENCE':'REFERENCE','TARGET_TEMPLATE':'TARGET'}
    for key,definition in config['documents'].items():
        role=definition['role']
        if role not in allowed:raise ValueError('ROLE_NOT_PERMITTED')
        matches=[c for c in report['cases'] if c['case_id']==definition['case_id']]
        if len(matches)!=1:raise ValueError('CASE_AMBIGUOUS')
        case=matches[0]
        # Verify role before accessing semantic content; never reinterpret Golden.
        if case.get('business_role')!=role or case['document_role']!=allowed[role]:raise ValueError('ROLE_NOT_PERMITTED')
        if case['input_sha256']!=definition['input_sha256'] or case['observation_digest']!=definition['observation_digest']:
            raise ValueError('STALE_DOCUMENT_VERSION')
        if len(case['runs'])!=3 or not all(r['candidate_package']=='docling-slim' and r['candidate_version']=='2.126.0' and r['conversion_status']=='PASS' for r in case['runs']):
            raise ValueError('PERCEPTION_BASELINE_MISMATCH')
        if not case['input_unchanged']:raise ValueError('INPUT_INTEGRITY_FAILED')
        raw=case['document']
        version=DocumentVersionRef(document_id=raw['document_id'],version_id=raw['id'],binary_hash=case['input_sha256'])
        data=case['runs'][0]['semantic_document']
        if not all(r['semantic_document']==data for r in case['runs']):raise ValueError('OBSERVATION_DIFFERENCE')
        views.append(View(key,role,version,canonical_digest(data),data))
        selections[key]=[Selection(**s) for s in definition.get('selections',[])]
        boundaries[key]={'case_id':case['case_id'],'observation_digest':case['observation_digest'],'input_sha256':case['input_sha256']}
    p=config['policy']
    policy=Policy(**{**p,'targets':tuple(TargetRule(**r) for r in p['targets'])})
    created_at=config['created_at']
    task_id=config['task_id']
    planner=MappingPlanner(task_id,created_at,policy)
    current=[];historical=[];normalization_errors=[]
    for view in views:
        for selection in selections[view.key]:
            try:
                facts=normalize(view,[selection],policy)
                (current if view.role=='CURRENT_SOURCE' else historical).extend(facts)
            except MappingError as exc:
                normalization_errors.append({'code':exc.code,'document_key':view.key,'selection':selection.label_pointer})
    targets=[v for v in views if v.role=='TARGET_TEMPLATE']
    if len(targets)!=1:raise ValueError('TARGET_ROLE_AMBIGUOUS')
    slots=[];regions=[]
    for s in config['slots']:
        region=TargetRegion(**planner.envelope('TargetRegion',s['region_id']),
            region_definition_ref={'object_type':'TargetRegionDefinition','object_id':s['region_id']+'-definition','revision':1},
            target_contract_instance_ref=policy.target_instance_ref,business_target_id=s['business_target_id'],
            document_version_ref=targets[0].version,semantic_object_refs=[],native_binding_refs=[],verification_status='UNVERIFIED',
            source_requirement_refs=[],preflight_assessment_refs=[],capability_result_refs=[])
        regions.append(region.model_dump(mode='json'))
        slots.append(Slot(region,s['pointer'],s['expected_content'],s['field'],s['operation'],
            s.get('protected',False),s.get('value_prefix',''),s.get('value_suffix','')))
    if normalization_errors:
        result={'workflow_profile':policy.workflow_profile,'profile_version':policy.version,'items':[],
            'exceptions':[{'code':'NORMALIZATION_INCOMPLETE','executable':False,'review_status':'REVIEW_REQUIRED'}],
            'executable':False,'production_qualified':False,'replay_qualified':False}
    else:
        result=planner.plan(views,current,historical,slots)
    result.update(evidence_kind='PRIVATE_B2_1_MAPPING_EVALUATION',run003_bindings=boundaries,
        normalization_errors=normalization_errors,target_region_records=regions,configuration_digest=canonical_digest(config),
        limitations=['Engagement selectors and template-region hypotheses require mapping evidence review.',
            'No native provider configured: no concrete ChangeProposal, approval, replay or output document.',
            'Source/target contract and policy references are evaluation configuration, not registered production definitions.',
            'No formula-cache freshness or business source-sufficiency qualification.'])
    return result


def sanitized_counts(result):
    # Construct counts only; never print exception strings, facts, selectors or paths.
    return {'mapping_intents':len(result['items']),
        'contract_change_proposals':sum(i['change_proposal'] is not None for i in result['items']),
        'exceptions':len(result['exceptions']),'normalization_refusals':len(result['normalization_errors']),
        'executable':False,'production_qualified':False,'replay_qualified':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('report','config','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    verify(Path(__file__).resolve().parents[2])
    report_path=private_path(args.report);config_path=private_path(args.config);output=private_path(args.output,output=True)
    data=report_path.read_bytes();config=json.loads(config_path.read_text(encoding='utf-8'))
    if sha256(data).hexdigest()!=config['report_sha256']:raise ValueError('REPORT_BINDING_MISMATCH')
    result=evaluate(json.loads(data),config)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(sanitized_counts(result)))


if __name__=='__main__':
    try:main()
    except Exception:
        print('B2_1_EVALUATION_REFUSED: inspect private configuration; no evidence details published.')
        raise SystemExit(1)
