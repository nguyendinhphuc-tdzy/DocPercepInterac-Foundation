from dataclasses import replace
import pytest
from foundation.applications.gtps_mapping.resolution import PartyAliasMap, allocate_rows
from foundation.applications.gtps_mapping.planner import MappingError, View, canonical_digest
from tests.backend.b2.test_gtps_mapping import setup, run, view


def test_aliases_require_bound_business_evidence(setup):
    _, c, _, _, _, _, _ = setup
    c = view('current', 'CURRENT_SOURCE', {'definition': 'Party A (PA)'})
    entry = dict(canonical_party_id='party-a', canonical_name='Party A', known_aliases=['PA'],
        evidence_reference=[dict(document_key=c.key, version=c.version.model_dump(mode='json'),
            digest=c.digest, pointers={'/definition': 'Party A (PA)'})])
    aliases = PartyAliasMap('engagement-1', [entry], [c])
    assert aliases.resolve('PA') == aliases.resolve('Party A')
    with pytest.raises(MappingError, match='PARTY_IDENTITY_REVIEW_REQUIRED'):
        aliases.resolve('Party AB')
    entry['evidence_reference'][0]['digest'] = '0'*64
    with pytest.raises(MappingError, match='PARTY_ALIAS_EVIDENCE_INVALID'):
        PartyAliasMap('engagement-1', [entry], [c])


def test_alias_substring_is_not_identity_evidence(setup):
    _,c,_,_,_,_,_=setup
    c=view('current','CURRENT_SOURCE',{'definition':'Party A'})
    entry=dict(canonical_party_id='a',canonical_name='Party A',known_aliases=['PA'],evidence_reference=[
        dict(document_key=c.key,version=c.version.model_dump(mode='json'),digest=c.digest,pointers={'/definition':'Party A'})])
    with pytest.raises(MappingError,match='PARTY_ALIAS_EVIDENCE_INVALID'):PartyAliasMap('engagement',[entry],[c])


def test_rows_require_configuration_and_never_insert():
    facts = [{'identity': 'a', 'amount': '100', 'under_review': False},
             {'identity': 'b', 'amount': '50', 'under_review': True}]
    with pytest.raises(MappingError, match='WORKFLOW_PROFILE_CONFIGURATION_REQUIRED'):
        allocate_rows(facts, 7, None)
    result = allocate_rows(facts, 7, 'UNDER_REVIEW_THEN_AMOUNT_DESC')
    assert result['rows'] == {'b': 1, 'a': 2}
    assert result['status'] == 'ROW_GROWTH_NOT_REQUIRED_FOR_REPRESENTATIVE_CASE'
    with pytest.raises(MappingError, match='STRUCTURAL_CAPABILITY_REQUIRED'):
        allocate_rows(facts, 1, 'UNDER_REVIEW_THEN_AMOUNT_DESC')


def test_explicit_multiple_occurrences(setup):
    p,c,h,t,cs,hs,slot = setup
    from foundation.applications.gtps_mapping.planner import normalize
    t = view(t.key,t.role,{'slot':'XX','second':'XX'})
    first = replace(slot, occurrence_group='approved-occurrences')
    second = replace(first,pointer='/second',region=slot.region.model_copy(update={'id':'region-2'}))
    result=p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs],p.policy),[first,second])
    assert len(result['items']) == 2
    assert len({i['projection']['target_region_id'] for i in result['items']}) == 2


def test_same_category_multiple_parties_removal_is_not_collapsed(setup):
    from foundation.applications.gtps_mapping.planner import normalize
    p,c,h,t,cs,hs,slot=setup
    h=view(h.key,h.role,{**h.data,'second_party':'Party B','second_amount':'90'})
    second=replace(hs,fields={**hs.fields,'party':'/second_party','amount':'/second_amount'})
    result=p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs,second],p.policy),[slot])
    assert result['items'][0]['historical_context']['fields']['party']=='Party A'
    removed=[e for e in result['exceptions'] if e['code']=='REMOVED_TRANSACTION']
    assert len(removed)==1 and removed[0]['source_fact']['fields']['party']=='Party B'


def test_alias_spelling_change_is_not_changed_counterparty(setup):
    from foundation.applications.gtps_mapping.planner import normalize, MappingPlanner
    p,c,h,t,cs,hs,slot=setup
    h=view(h.key,h.role,{**h.data,'party':'PA','alias_definition':'Party A (PA)'})
    entry=dict(canonical_party_id='a',canonical_name='Party A',known_aliases=['PA'],evidence_reference=[
        dict(document_key=h.key,version=h.version.model_dump(mode='json'),digest=h.digest,pointers={'/alias_definition':'Party A (PA)'})])
    policy=replace(p.policy,engagement_scope='engagement-a',party_alias_entries=(entry,))
    result=MappingPlanner('test',p.created_at,policy).plan([c,h,t],normalize(c,[cs],policy),normalize(h,[hs],policy),[slot])
    assert result['items'][0]['change_types']==['SAME_TRANSACTION_CHANGED_VALUE']
    c=view(c.key,c.role,{**c.data,'party':'Unknown Party'})
    result=MappingPlanner('test',p.created_at,policy).plan([c,h,t],normalize(c,[cs],policy),normalize(h,[hs],policy),[slot])
    assert not result['items']
    assert any(e['code']=='PARTY_IDENTITY_REVIEW_REQUIRED' for e in result['exceptions'])


def test_new_transaction_context_does_not_fabricate_prior_value(setup):
    from foundation.applications.gtps_mapping.planner import normalize
    p,c,h,t,cs,hs,slot=setup
    hs=replace(hs,fields={},context_only=True,context_concept='PROCESSING_SERVICES')
    result=p.plan([c,h,t],normalize(c,[cs],p.policy),normalize(h,[hs],p.policy),[slot])
    item=result['items'][0]
    assert item['change_types']==['NEW_TRANSACTION','NARRATIVE_REVIEW_REQUIRED']
    assert item['historical_context']['fields']=={}
    assert not any(e['code']=='REMOVED_TRANSACTION' for e in result['exceptions'])


def test_missing_or_ambiguous_detailed_heading_refuses(setup):
    from foundation.applications.gtps_mapping.template_resolution import unique_heading
    t=view('template','TARGET_TEMPLATE',{'texts':[{'text':'Provision of services'},{'text':'Provision of services'}]})
    with pytest.raises(MappingError,match='TARGET_AMBIGUOUS'):unique_heading(t,'Provision of services')
    with pytest.raises(MappingError,match='TARGET_NOT_FOUND'):unique_heading(t,'Different services')


def test_financial_context_only_can_produce_concrete_draft(setup,scenarios):
    from foundation.applications.gtps_mapping.planner import normalize, MappingPlanner, TargetRule
    from tests.backend.b2.test_gtps_mapping import native_provider
    p,c,h,t,cs,hs,slot=setup
    policy=replace(p.policy,aliases={'net sales':'NET_SALES'},targets=(
        TargetRule('FINANCIAL.NET_SALES','FINANCIAL','NET_SALES','FINANCIAL_CONTEXT',('current',)),))
    c=view(c.key,c.role,{'period':'FY2024','label':'Net sales','value':'125'})
    h=view(h.key,h.role,{'period':'FY2023','context':'Audited operating results'})
    cs=replace(cs,kind='FINANCIAL',fields={'value':'/value'})
    hs=replace(hs,kind='FINANCIAL',label_pointer='/context',fields={},meaning='FINANCIAL_CONTEXT',
        meaning_expected='Audited operating results',context_only=True,context_concept='NET_SALES')
    slot=replace(slot,field='value',region=slot.region.model_copy(update={'business_target_id':'FINANCIAL.NET_SALES'}))
    result=MappingPlanner('test',p.created_at,policy).plan([c,h,t],normalize(c,[cs],policy),normalize(h,[hs],policy),[slot],native=native_provider(setup,scenarios))
    assert result['items'][0]['change_proposal']['status']=='DRAFT'
    assert result['items'][0]['historical_context']['fields']=={}
    assert result['items'][0]['proposed_content']=='125'


def container_fixture(setup):
    from foundation.applications.gtps_mapping.planner import normalize
    p,c,h,t,cs,hs,slot=setup
    c=view(c.key,c.role,{**c.data,'definition':'Party A (PA)'})
    entry=dict(canonical_party_id='a',canonical_name='Party A',known_aliases=['PA'],evidence_reference=[
        dict(document_key=c.key,version=c.version.model_dump(mode='json'),digest=c.digest,pointers={'/definition':'Party A (PA)'})])
    policy=replace(p.policy,party_alias_entries=(entry,),engagement_scope='engagement')
    headers=['Transaction','Party','Relationship','Amount']
    cells=[{'text':value,'start_row_offset_idx':i//4,'start_col_offset_idx':i%4,'row_span':1,'col_span':1}
        for i,value in enumerate(headers+['Generic transaction','xxx','xxx','xxx'])]
    t=view('template','TARGET_TEMPLATE',{'texts':[{'text':'Related party transactions'}],
        'ordering':'Sort transactions by materiality','tables':[{'data':{'num_rows':2,'num_cols':4,'table_cells':cells}}]})
    config=dict(heading='Related party transactions',header=headers,ordering='UNDER_REVIEW_THEN_AMOUNT_DESC',
        ordering_evidence=[dict(pointer='/ordering',expected='Sort transactions by materiality')],
        columns=dict(label=0,party=1,relationship=2,amount=3))
    return t,normalize(c,[cs],policy),normalize(h,[hs],policy),policy,config,[c,h,t]


def test_generic_template_rows_are_slots_not_transaction_labels(setup):
    from foundation.applications.gtps_mapping.template_resolution import transaction_slots
    args=container_fixture(setup)
    slots,allocation=transaction_slots(*args)
    assert len(slots)==4 and allocation['required']==1
    assert slots[0]['expected_content']=='Generic transaction'
    assert all(s['party_id']=='a' for s in slots)


@pytest.mark.parametrize('change,code',[
    ('ordering','WORKFLOW_PROFILE_CONFIGURATION_REQUIRED'),('duplicate','TARGET_AMBIGUOUS'),
    ('missing','TARGET_NOT_FOUND'),('merged','STRUCTURAL_CAPABILITY_REQUIRED')])
def test_container_negative_paths(setup,change,code):
    import copy
    from foundation.applications.gtps_mapping.template_resolution import transaction_slots
    args=list(container_fixture(setup));data=copy.deepcopy(args[0].data)
    if change=='ordering':args[4]['ordering']=None
    if change=='duplicate':data['tables']*=2
    if change=='missing':data['tables']=[]
    if change=='merged':data['tables'][0]['data']['table_cells'][4]['col_span']=2
    args[0]=view('template','TARGET_TEMPLATE',data);args[5][-1]=args[0]
    with pytest.raises(MappingError,match=code):transaction_slots(*args)


def test_explicit_native_refusal_cannot_be_overridden_by_candidate(setup,scenarios):
    from tests.backend.b2.test_gtps_mapping import native_provider
    result=run(setup,native_provider(setup,scenarios,status='NATIVE_STRUCTURE_UNSUPPORTED'))
    assert result['items'][0]['change_proposal'] is None
    assert result['items'][0]['native_binding_status']=='UNRESOLVED'
