"""Synthetic business fixtures only; private representative evidence stays local."""
from dataclasses import replace
import pytest
from foundation.domain import DocumentVersionRef, TargetRegion, NativeLocator, ChangeProposal
from foundation.applications.gtps_mapping import (
    View, Selection, Policy, TargetRule, Slot, NativeResult, MappingPlanner,
    normalize, canonical_digest, MappingError,
)

NOW = '2026-09-17T00:00:00Z'  # Synthetic test clock, not a review timestamp.
def ref(kind, key): return {'object_type':kind,'object_id':key,'revision':1}
def version(key): return DocumentVersionRef(document_id=key,version_id=key+'-v1',binary_hash='a'*64)
def view(key,role,data): return View(key,role,version(key),canonical_digest(data),data)

@pytest.fixture
def setup():
    current=view('current','CURRENT_SOURCE',{'period':'FY2024','label':'Provision of processing services','party':'Party A','country':'AA','relationship':'parent','amount':'125.00'})
    history=view('history','HISTORICAL_REFERENCE',{'period':'FY2023','label':'Provision of processing services','party':'Party A','country':'AA','relationship':'parent','amount':'100','context':'Transaction under Review'})
    target=view('template','TARGET_TEMPLATE',{'slot':'XX'})
    selection=Selection('RPT','/label','/period',{'party':'/party','country':'/country','relationship':'/relationship','amount':'/amount'})
    historic=replace(selection,meaning='TRANSACTION_UNDER_REVIEW',meaning_pointer='/context',meaning_expected='Transaction under Review')
    region=TargetRegion(schema_version='0.1.0',object_type='TargetRegion',id='region',revision=1,created_at=NOW,task_id='test',
        region_definition_ref=ref('TargetRegionDefinition','region-definition'),target_contract_instance_ref=ref('TargetContractInstance','instance'),
        business_target_id='RPT.TRANSACTION_UNDER_REVIEW.PROCESSING_SERVICES',document_version_ref=target.version,
        semantic_object_refs=[],native_binding_refs=[],verification_status='UNVERIFIED',source_requirement_refs=[],preflight_assessment_refs=[],capability_result_refs=[])
    slot=Slot(region,'/slot','XX','amount','REPLACE_SIMPLE_TABLE_CELL_TEXT')
    rule=TargetRule(region.business_target_id,'RPT','PROCESSING_SERVICES','TRANSACTION_UNDER_REVIEW',('current',))
    policy=Policy('GTPS_LOCAL_FILE','0.2',2024,2023,{'provision of processing services':'PROCESSING_SERVICES'},(rule,),ref('TargetContractDefinition','definition'),ref('TargetContractInstance','instance'),ref('RulePack','rules'))
    planner=MappingPlanner('test',NOW,policy)
    return planner,current,history,target,selection,historic,slot

def run(s, native=None):
    p,c,h,t,cs,hs,slot=s
    return p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs],p.policy),[slot],native=native)

def test_business_meaning_precedes_region_and_native_binding(setup):
    result=run(setup)
    item=result['items'][0]
    assert item['business_target_id']=='RPT.TRANSACTION_UNDER_REVIEW.PROCESSING_SERVICES'
    assert item['change_types']==['SAME_TRANSACTION_CHANGED_VALUE']
    assert item['proposed_content']=='125'
    assert item['change_proposal'] is None
    assert 'NATIVE_LOCATOR_UNRESOLVED' in item['warnings']
    assert item['projection']['target_region']['object_id']=='region'
    assert item['projection']['source_evidence_ref']
    assert item['projection']['historical_reference_ref']
    assert item['executable'] is False

@pytest.mark.parametrize('field,value,expected',[
    ('party','Party B','CHANGED_RELATED_PARTY'),
    ('relationship','affiliate','CHANGED_RELATIONSHIP'),
])
def test_relationship_changes_require_narrative_review(setup,field,value,expected):
    s=list(setup); data={**s[1].data,field:value}; s[1]=view('current','CURRENT_SOURCE',data)
    item=run(s)['items'][0]
    assert expected in item['change_types']
    assert 'NARRATIVE_REVIEW_REQUIRED' in item['change_types']

def test_new_and_removed_transactions_are_explicit_and_nonexecutable(setup):
    p,c,h,t,cs,hs,slot=setup
    result=p.plan([c,h,t],normalize(c,[cs],p.policy),[],[slot])
    assert result['items'][0]['change_types']==['NEW_TRANSACTION','NARRATIVE_REVIEW_REQUIRED']
    result=p.plan([c,h,t],[],normalize(h,[hs],p.policy),[slot])
    assert 'REMOVED_TRANSACTION' in {e['code'] for e in result['exceptions']}
    assert 'SOURCE_MISSING' in {e['code'] for e in result['exceptions']}
    assert result['items']==[]

def test_ambiguous_history_does_not_choose_by_value(setup):
    p,c,h,t,cs,hs,slot=setup; past=normalize(h,[hs],p.policy)
    result=p.plan([c,h,t],normalize(c,[cs],p.policy),past+past,[slot])
    assert result['exceptions'][0]['code']=='HISTORICAL_CONTEXT_AMBIGUOUS'
    assert not result['items']

def test_ambiguous_template_does_not_pick_first(setup):
    p,c,h,t,cs,hs,slot=setup
    result=p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs],p.policy),[slot,slot])
    assert result['exceptions'][0]['code']=='TARGET_REGION_AMBIGUOUS'

@pytest.mark.parametrize('role',['GOLDEN_EVALUATION_ONLY','SUPPORTING_CURRENT_EVIDENCE'])
def test_unconfigured_role_never_enters_runtime_reasoning(setup,role):
    p,c,h,t,cs,hs,slot=setup
    forbidden=replace(c,key='forbidden',role=role,data={'do not inspect':'private'})
    result=p.plan([c,h,t,forbidden],[],[],[slot])
    assert result['items']==[]
    assert result['exceptions'][0]['code']=='ROLE_NOT_PERMITTED'

@pytest.mark.parametrize('change,code',[
 ('missing','SOURCE_MISSING'),('period','SOURCE_PERIOD_MISMATCH'),('stale','STALE_SEMANTIC_EVIDENCE'),
])
def test_normalization_refuses_missing_stale_or_wrong_period(setup,change,code):
    p,c,h,t,cs,hs,slot=setup
    data=dict(c.data)
    if change=='missing':del data['amount']
    if change=='period':data['period']='FY2022'
    changed=replace(c,data=data) if change=='stale' else view(c.key,c.role,data)
    if change=='stale': changed=replace(c,digest='b'*64)
    with pytest.raises(MappingError,match=code):normalize(changed,[cs],p.policy)

def test_conflicting_current_facts_never_newest_wins(setup):
    p,c,h,t,cs,hs,slot=setup
    facts=normalize(c,[cs],p.policy)
    other=replace(facts[0],fields={**facts[0].fields,'amount':'777'})
    result=p.plan([c,h,t],facts+[other],normalize(h,[hs],p.policy),[slot])
    assert not result['items']
    assert result['exceptions']

@pytest.mark.parametrize('raw',['NaN','Infinity','1e4','1,23','',True])
def test_numeric_normalization_is_bounded(setup,raw):
    p,c,h,t,cs,hs,slot=setup
    c=view(c.key,c.role,{**c.data,'amount':raw})
    with pytest.raises(MappingError):normalize(c,[cs],p.policy)

@pytest.mark.parametrize('label,concept',[
 ('Purchase of raw materials and tools','RAW_MATERIAL_PURCHASE'),
 ('Sales of raw materials','RAW_MATERIAL_SALE'),
 ('Interest expense','INTEREST_EXPENSE'),('Other expenses','OTHER_EXPENSES'),
])
def test_multiple_rpt_categories_use_configured_business_targets(setup,label,concept):
    p,c,h,t,cs,hs,slot=setup
    policy=replace(p.policy,aliases={label.casefold():concept},targets=(replace(p.policy.targets[0],concept=concept,business_target_id='RPT.OTHER.'+concept),))
    c=view(c.key,c.role,{**c.data,'label':label});h=view(h.key,h.role,{**h.data,'label':label})
    slot=replace(slot,region=slot.region.model_copy(update={'business_target_id':'RPT.OTHER.'+concept}))
    result=MappingPlanner('test',NOW,policy).plan([c,h,t],normalize(c,[cs],policy),normalize(h,[hs],policy),[slot])
    assert result['items'][0]['business_target_id']=='RPT.OTHER.'+concept

@pytest.mark.parametrize('kind,label,fields,target_id',[
 ('NCP','Net Cost Plus',{'value':'0.061','index':'F/(A-F)'},'PROFITABILITY.CURRENT_NCP'),
 ('FINANCIAL','Net sales',{'value':'125','index':'A'},'FINANCIAL.NET_SALES'),
 ('PERIOD','Reporting period',{'value':'FY2024'},'REPORTING.PERIOD'),
])
def test_scalar_business_targets(setup,kind,label,fields,target_id):
    p,c,h,t,cs,hs,slot=setup
    policy=replace(p.policy,aliases={label.casefold():kind},targets=(TargetRule(target_id,kind,kind,'CONTEXT',('current',)),))
    c=view(c.key,c.role,{'period':'FY2024','label':label,**fields})
    h=view(h.key,h.role,{'period':'FY2023','label':label,**fields,'context':'context'})
    cs=Selection(kind,'/label','/period',{k:'/'+k for k in fields});hs=replace(cs,meaning='CONTEXT',meaning_pointer='/context',meaning_expected='context')
    slot=replace(slot,field='value',region=slot.region.model_copy(update={'business_target_id':target_id}))
    item=MappingPlanner('test',NOW,policy).plan([c,h,t],normalize(c,[cs],policy),normalize(h,[hs],policy),[slot])['items'][0]
    assert item['business_target_id']==target_id
    assert item['source_fact']['fields']['value']==fields['value']
    assert not item['executable']


def native_provider(setup, scenarios, **overrides):
    original=next(r for scenario in scenarios.values() for r in scenario['records'] if isinstance(r,NativeLocator) )
    data=original.model_dump(mode='json')
    path=[{'namespace_uri':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','local_name':'tbl','ordinal':1}]
    data.update(task_id='test',document_version_ref=setup[3].version.model_dump(mode='json'),locator_type='DOCX_TABLE_CELL',
        address={'kind':'DOCX_TABLE_CELL','table_path':path,'row_ordinal':1,'cell_ordinal':1,'cell_path':path})
    locator=NativeLocator.model_validate(data)
    result=NativeResult((locator,),locator.structural_fingerprint,'XX',False,
        record_region_id='region',semantic_pointer='/slot')
    result=replace(result,**overrides)
    class Provider:
        def resolve(self,slot,target):return result
    return Provider()


def test_exact_candidate_produces_frozen_draft_only(setup,scenarios):
    result=run(setup,native_provider(setup,scenarios))
    proposal=ChangeProposal.model_validate(result['items'][0]['change_proposal'])
    assert proposal.status.value=='DRAFT'
    assert proposal.payload.replacement_text=='125'
    assert proposal.target_document_version_ref==setup[3].version
    assert result['items'][0]['native_binding_status']=='EXACT_CANDIDATE'
    assert not result['items'][0]['executable']
    assert 'approved_change_set' not in result


@pytest.mark.parametrize('overrides,code',[
    ({'observed_fingerprint':'b'*64},'NATIVE_FINGERPRINT_MISMATCH'),
    ({'observed_content':'different'},'STALE_NATIVE_CONTENT'),
    ({'protected':True},'PROTECTED_OBJECT'),
    ({'record_region_id':'wrong'},'NATIVE_REGION_MISMATCH'),
    ({'semantic_pointer':'/wrong'},'NATIVE_REGION_MISMATCH'),
])
def test_invalid_native_candidate_never_materializes_change(setup,scenarios,overrides,code):
    item=run(setup,native_provider(setup,scenarios,**overrides))['items'][0]
    assert item['change_proposal'] is None
    assert code in item['warnings']


@pytest.mark.parametrize('change,code',[
    ('missing','TARGET_REGION_MISSING'),('protected','PROTECTED_OBJECT'),
    ('content','STALE_TARGET_CONTENT'),('version','STALE_TARGET_VERSION'),
    ('operation','OPERATION_UNSUPPORTED'),('authority','SOURCE_NOT_AUTHORITATIVE'),
])
def test_target_and_authority_refusals(setup,change,code):
    p,c,h,t,cs,hs,slot=setup
    if change=='protected':slot=replace(slot,protected=True)
    if change=='content':slot=replace(slot,expected_content='different')
    if change=='version':slot=replace(slot,region=slot.region.model_copy(update={'document_version_ref':version('stale')}))
    if change=='operation':slot=replace(slot,operation='INSERT_ROW')
    if change=='authority':p=MappingPlanner('test',NOW,replace(p.policy,targets=(replace(p.policy.targets[0],current_sources=('other',)),)))
    result=p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs],p.policy),[] if change=='missing' else [slot])
    assert code in {e['code'] for e in result['exceptions']}
    assert result['items']==[]


def test_reproducibility_and_input_immutability(setup):
    import copy
    snapshot=copy.deepcopy([v.data for v in setup[1:4]])
    assert run(setup)==run(setup)
    assert snapshot==[v.data for v in setup[1:4]]


def test_target_rule_ambiguity(setup):
    p,c,h,t,cs,hs,slot=setup
    p=MappingPlanner('test',NOW,replace(p.policy,targets=p.policy.targets*2))
    assert p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs],p.policy),[slot])['exceptions'][0]['code']=='BUSINESS_TARGET_AMBIGUOUS'


def test_historical_meaning_requires_exact_context_evidence(setup):
    p,c,h,t,cs,hs,slot=setup
    with pytest.raises(MappingError,match='HISTORICAL_CONTEXT_UNVERIFIED'):
        normalize(h,[replace(hs,meaning_expected='invented')],p.policy)


def test_empty_template_slot_is_valid_while_empty_source_is_not(setup):
    p,c,h,t,cs,hs,slot=setup
    t=view(t.key,t.role,{'slot':''});slot=replace(slot,expected_content='')
    item=p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs],p.policy),[slot])['items'][0]
    assert item['existing_target_content']==''
    assert item['proposed_content']=='125'


def test_explicit_date_capture_preserves_source_lineage(setup):
    p,c,h,t,cs,hs,slot=setup
    policy=replace(p.policy,aliases={'reporting period':'PERIOD'})
    c=view('current','CURRENT_SOURCE',{'period':'FY2024','label':'Reporting period','value':'Fiscal year end: 31 December 2024'})
    selection=Selection('PERIOD','/label','/period',{'value':'/value'},field_patterns={'value':r'Fiscal year end: (.+)'})
    fact=normalize(c,[selection],policy)[0]
    assert fact.fields['value']=='31 December 2024'
    assert fact.evidence['value']=='/value'


def test_true_conflicting_evidence_from_two_observed_rows_is_refused(setup):
    p,c,h,t,cs,hs,slot=setup
    c=view('current','CURRENT_SOURCE',{**c.data,'second_amount':'222'})
    second=replace(cs,fields={**cs.fields,'amount':'/second_amount'})
    result=p.plan([c,h,t],normalize(c,[cs,second],p.policy),normalize(h,[hs],p.policy),[slot])
    assert all(e['code']=='SOURCE_CONFLICTING' for e in result['exceptions'])
    assert not result['items']


def test_changed_source_version_does_not_reuse_normalized_fact(setup):
    p,c,h,t,cs,hs,slot=setup
    facts=normalize(c,[cs],p.policy)
    changed=replace(c,version=version('new-current'))
    result=p.plan([changed,h,t],facts,normalize(h,[hs],p.policy),[slot])
    assert result['exceptions'][0]['code']=='STALE_DOCUMENT_VERSION'


def test_duplicate_native_candidates_refuse(setup,scenarios):
    first=native_provider(setup,scenarios).resolve(setup[-1],setup[3])
    provider=native_provider(setup,scenarios,locators=first.locators*2)
    item=run(setup,provider)['items'][0]
    assert 'NATIVE_LOCATOR_AMBIGUOUS' in item['warnings']
    assert item['change_proposal'] is None


def test_changed_locator_changes_proposal_identity(setup,scenarios):
    first=native_provider(setup,scenarios)
    candidate=first.resolve(setup[-1],setup[3]).locators[0]
    second=native_provider(setup,scenarios,locators=(candidate.model_copy(update={'id':'different-locator'}),))
    assert run(setup,first)['items'][0]['proposal_id']!=run(setup,second)['items'][0]['proposal_id']


def test_native_provider_failure_is_structured_and_private(setup):
    class Broken:
        def resolve(self,slot,target):raise RuntimeError('private diagnostic')
    result=run(setup,Broken())
    assert 'NATIVE_RESOLUTION_FAILED' in result['items'][0]['warnings']
    assert 'private diagnostic' not in str(result)


def test_different_region_ids_cannot_hide_same_semantic_target(setup):
    p,c,h,t,cs,hs,slot=setup
    policy=replace(p.policy,aliases={**p.policy.aliases,'second category':'SECOND'},targets=p.policy.targets+(replace(p.policy.targets[0],concept='SECOND',business_target_id='RPT.OTHER.SECOND'),))
    c=view(c.key,c.role,{**c.data,'label2':'second category'})
    h=view(h.key,h.role,{**h.data,'label2':'second category'})
    other_slot=replace(slot,region=slot.region.model_copy(update={'id':'different-region','business_target_id':'RPT.OTHER.SECOND'}))
    result=MappingPlanner('test',NOW,policy).plan([c,h,t],normalize(c,[cs,replace(cs,label_pointer='/label2')],policy),
        normalize(h,[hs,replace(hs,label_pointer='/label2')],policy),[slot,other_slot])
    assert len(result['items'])==2
    assert all('TARGET_REGION_COLLISION' in x['warnings'] and x['change_proposal'] is None for x in result['items'])


def test_source_and_history_cannot_share_one_version(setup):
    p,c,h,t,cs,hs,slot=setup
    h=replace(h,version=c.version)
    result=p.plan([c,h,t],[],[],[slot])
    assert result['exceptions'][0]['code']=='DOCUMENT_ROLE_COLLISION'


def test_table_coordinates_prevent_cross_row_fact_assembly(setup):
    p,c,h,t,cs,hs,slot=setup
    values=['Provision of processing services','Party A','AA','parent','125','999']
    data={'period':'FY2024','tables':[{'data':{'table_cells':[
        {'text':value,'start_row_offset_idx':1 if i<5 else 2,'row_span':1} for i,value in enumerate(values)]}}]}
    c=view(c.key,c.role,data)
    ptr=lambda i:f'/tables/0/data/table_cells/{i}/text'
    cs=Selection('RPT',ptr(0),'/period',{'party':ptr(1),'country':ptr(2),'relationship':ptr(3),'amount':ptr(4)})
    assert normalize(c,[cs],p.policy)[0].fields['amount']=='125'
    with pytest.raises(MappingError,match='SOURCE_RELATIONSHIP_UNVERIFIED'):
        normalize(c,[replace(cs,fields={**cs.fields,'amount':ptr(5)})],p.policy)


def probe_fixture(setup):
    from dataclasses import asdict
    p,c,h,t,cs,hs,slot=setup
    report={'evaluation_version':'1.2.0','cases':[]}
    config={'task_id':'test','created_at':NOW,'policy':asdict(p.policy),'documents':{},'slots':[
        {'region_id':slot.region.id,'business_target_id':slot.region.business_target_id,'pointer':slot.pointer,
         'expected_content':slot.expected_content,'field':slot.field,'operation':slot.operation}]}
    for v,s in [(c,[cs]),(h,[hs]),(t,[])]:
        report['cases'].append({'case_id':v.key,'business_role':v.role,'document_role':{'CURRENT_SOURCE':'SOURCE','HISTORICAL_REFERENCE':'REFERENCE','TARGET_TEMPLATE':'TARGET'}[v.role],
            'input_sha256':v.version.binary_hash,'observation_digest':'b'*64,'input_unchanged':True,
            'document':{'id':v.version.version_id,'document_id':v.version.document_id},
            'runs':[{'candidate_package':'docling-slim','candidate_version':'2.126.0','conversion_status':'PASS','semantic_document':v.data} for _ in range(3)]})
        config['documents'][v.key]={'case_id':v.key,'role':v.role,'input_sha256':v.version.binary_hash,'observation_digest':'b'*64,'selections':[asdict(x) for x in s]}
    return report,config


def test_golden_content_never_reaches_mapping_context(setup):
    from tools.b2.gtps_mapping_probe import evaluate
    report,config=probe_fixture(setup)
    expected=evaluate(report,config)
    report['cases'].append({'case_id':'golden','business_role':'GOLDEN_EVALUATION_ONLY','document_role':'REFERENCE','runs':object()})
    assert evaluate(report,config)==expected
    config['documents']['current']['case_id']='golden'
    with pytest.raises(ValueError,match='ROLE_NOT_PERMITTED'):evaluate(report,config)


def test_partial_normalization_does_not_invent_removed_transactions(setup):
    from tools.b2.gtps_mapping_probe import evaluate
    report,config=probe_fixture(setup)
    config['documents']['current']['selections'][0]['fields']['amount']='/absent'
    result=evaluate(report,config)
    assert result['items']==[]
    assert result['exceptions'][0]['code']=='NORMALIZATION_INCOMPLETE'
    assert result['normalization_errors'][0]['code']=='SOURCE_MISSING'


def test_private_output_is_immutable_and_public_paths_refused(tmp_path):
    from tools.b2.gtps_mapping_probe import private_path
    with pytest.raises(ValueError,match='PRIVATE_PATH_REQUIRED'):private_path(tmp_path/'public.json',output=True)
    p=tmp_path/'.foundation-private'/'plan.json';p.parent.mkdir();p.write_text('unchanged')
    with pytest.raises(ValueError,match='IMMUTABLE_OUTPUT_EXISTS'):private_path(p,output=True)
    assert p.read_text()=='unchanged'


def test_no_legacy_or_replay_dependency_in_mapping_lane():
    import ast
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]/'foundation/applications/gtps_mapping'
    for file in root.glob('*.py'):
        tree=ast.parse(file.read_text(encoding='utf-8'))
        for n in ast.walk(tree):
            if isinstance(n,(ast.Import,ast.ImportFrom)):
                names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
                assert all(not any(x in name for x in ('writeback','action_executor','rollforward','replay','docx','openpyxl')) for name in names)
            if isinstance(n,ast.Attribute):assert n.attr not in ('apply_single_patch','save','execute','replay')
