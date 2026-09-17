"""Explicit template business selectors and existing-row allocation."""
from .planner import MappingError, pointer
from .resolution import allocate_rows, PartyAliasMap


def unique_heading(view, text):
    matches=[i for i,t in enumerate(view.data.get('texts',[])) if t['text']==text]
    if len(matches)!=1:raise MappingError('TARGET_AMBIGUOUS' if matches else 'TARGET_NOT_FOUND')
    return '/texts/'+str(matches[0])+'/text'


def transaction_slots(target, current, historical, policy, config, views):
    """Target Template guidance is data evidence for an explicit configuration.

    No section-number heuristic, Golden-derived ordering or row insertion.
    """
    if not config or config.get('ordering')!='UNDER_REVIEW_THEN_AMOUNT_DESC':
        raise MappingError('WORKFLOW_PROFILE_CONFIGURATION_REQUIRED')
    for ref in config['ordering_evidence']:
        if pointer(target.data,ref['pointer'])!=ref['expected']:
            raise MappingError('WORKFLOW_PROFILE_CONFIGURATION_REQUIRED')
    if not config['ordering_evidence']:
        raise MappingError('WORKFLOW_PROFILE_CONFIGURATION_REQUIRED')
    unique_heading(target,config['heading'])
    candidates=[]
    for i,t in enumerate(target.data['tables']):
        cells=t['data']['table_cells']
        header=[c['text'] for c in cells if c['start_row_offset_idx']==0]
        if header==config['header']:candidates.append((i,t))
    if len(candidates)!=1:raise MappingError('TARGET_AMBIGUOUS' if candidates else 'TARGET_NOT_FOUND')
    ti,t=candidates[0];d=t['data']
    if any(c.get('row_span',1)!=1 or c.get('col_span',1)!=1 for c in d['table_cells']):
        raise MappingError('STRUCTURAL_CAPABILITY_REQUIRED')
    coords={(c['start_row_offset_idx'],c['start_col_offset_idx']):(i,c) for i,c in enumerate(d['table_cells'])}
    if len(coords)!=len(d['table_cells']) or len(coords)!=d['num_rows']*d['num_cols']:
        raise MappingError('STRUCTURAL_CAPABILITY_REQUIRED')
    aliases=PartyAliasMap(policy.engagement_scope,policy.party_alias_entries,views)
    facts=[];byid={};rules={}
    for f in current:
        if f.kind!='RPT':continue
        identity=f.concept+':'+aliases.resolve(f.fields['party'])
        matching=[r for r in policy.targets if r.kind=='RPT' and r.concept==f.concept]
        if len(matching)!=1:raise MappingError('BUSINESS_TARGET_AMBIGUOUS')
        rule=matching[0]
        contexts=[h for h in historical if h.kind=='RPT' and h.concept==f.concept and h.meaning==rule.historical_meaning]
        if not contexts:raise MappingError('HISTORICAL_CONTEXT_MISSING')
        facts.append(dict(identity=identity,amount=f.fields['amount'],under_review=rule.historical_meaning=='TRANSACTION_UNDER_REVIEW'))
        byid[identity]=f;rules[identity]=rule
    allocation=allocate_rows(facts,d['num_rows']-1,config['ordering'])
    slots=[]
    for identity,row in allocation['rows'].items():
        for field,column in config['columns'].items():
            index,cell=coords[(row,column)]
            slots.append(dict(region_id='rpt-row-'+str(row)+'-'+field,business_target_id=rules[identity].business_target_id,
                pointer=f'/tables/{ti}/data/table_cells/{index}/text',expected_content=cell['text'],field=field,
                operation='REPLACE_SIMPLE_TABLE_CELL_TEXT',occurrence_group='rpt-fields-'+identity,
                party_id=aliases.resolve(byid[identity].fields['party'])))
    return slots,allocation
