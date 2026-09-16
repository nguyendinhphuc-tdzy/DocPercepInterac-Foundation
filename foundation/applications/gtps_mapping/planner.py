"""GTPS-specific deterministic mapping over pinned, already perceived evidence.

These DTOs are application read models, not new frozen contract object types.
External readers supply semantic views. Versioned, engagement-specific selectors
and target rules provide business meaning; there is no fuzzy/string-score fallback.
No file IO, AI, mutation engine, approval or Replay dependency exists here.
"""
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Protocol

from foundation.domain import DocumentVersionRef, TargetRegion, NativeLocator, ChangeProposal, MappingProposal, EvidenceRecord


def canonical_digest(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


class MappingError(ValueError):
    def __init__(self, code):
        self.code=code
        super().__init__(code)


@dataclass(frozen=True)
class View:
    key: str
    role: str
    version: DocumentVersionRef
    digest: str
    data: dict


@dataclass(frozen=True)
class Selection:
    kind: str
    label_pointer: str
    period_pointer: str
    fields: dict[str,str]
    meaning: str = ''
    meaning_pointer: str = ''
    meaning_expected: str = ''
    field_patterns: dict[str,str] = field(default_factory=dict)


@dataclass(frozen=True)
class Fact:
    document_key: str
    version: DocumentVersionRef
    observation_digest: str
    kind: str
    concept: str
    period: int
    fields: dict[str,str]
    evidence: dict[str,str]
    meaning: str
    selection: Selection


@dataclass(frozen=True)
class TargetRule:
    business_target_id: str
    kind: str
    concept: str
    historical_meaning: str
    current_sources: tuple[str,...]


@dataclass(frozen=True)
class Policy:
    workflow_profile: str
    version: str
    current_year: int
    historical_year: int
    aliases: dict[str,str]
    targets: tuple[TargetRule,...]
    target_definition_ref: dict
    target_instance_ref: dict
    rule_pack_ref: dict


@dataclass(frozen=True)
class Slot:
    region: TargetRegion
    pointer: str
    expected_content: str
    field: str
    operation: str
    protected: bool = False
    value_prefix: str = ''
    value_suffix: str = ''


@dataclass(frozen=True)
class NativeResult:
    """Adapter observation, not an execution capability or authorization."""
    locators: tuple[NativeLocator,...] = ()
    observed_fingerprint: str = ''
    observed_content: str = ''
    protected: bool = False
    record_region_id: str = ''
    semantic_pointer: str = ''


class NativeCandidates(Protocol):
    def resolve(self, slot: Slot, target: View) -> NativeResult: ...


def pointer(data,path,*,allow_empty=False):
    if not isinstance(path,str) or not path.startswith('/'):
        raise MappingError('EVIDENCE_POINTER_INVALID')
    try:
        value=data
        for part in path[1:].split('/'):
            part=part.replace('~1','/').replace('~0','~')
            if isinstance(value,list):
                if not re.fullmatch(r'0|[1-9][0-9]*',part):raise MappingError('EVIDENCE_POINTER_INVALID')
                value=value[int(part)]
            else:value=value[part]
        if not isinstance(value,str) or (not allow_empty and not value.strip()):
            raise MappingError('SOURCE_MISSING')
        return value
    except (KeyError,IndexError,TypeError,ValueError) as exc:
        if isinstance(exc,MappingError): raise
        raise MappingError('SOURCE_MISSING') from None


def number(value):
    # No locale guessing, exponent parsing, float conversion or formula execution.
    if not isinstance(value,str) or not re.fullmatch(r'-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',value.strip()):
        raise MappingError('NUMERIC_VALUE_UNSUPPORTED')
    result=format(Decimal(value.strip().replace(',','')),'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


def verify_view(view):
    if view.role not in ('CURRENT_SOURCE','HISTORICAL_REFERENCE','TARGET_TEMPLATE'):
        raise MappingError('ROLE_NOT_PERMITTED')
    if canonical_digest(view.data)!=view.digest:
        raise MappingError('STALE_SEMANTIC_EVIDENCE')


def verify_row_relationship(view,selection):
    """Retained cell coordinates, including merged labels, must share one row.

Flat named-field views are a separate adapter input. Mixed table/text selectors
may not silently reconstruct a current structured relationship across regions.
"""
    if selection.kind not in ('RPT','NCP','FINANCIAL'):return
    paths=[selection.label_pointer,*selection.fields.values()]
    pattern=r'/tables/(0|[1-9][0-9]*)/data/table_cells/(0|[1-9][0-9]*)/text'
    matches=[re.fullmatch(pattern,p) for p in paths]
    if not any(matches):return
    if not all(matches) or len({m[1] for m in matches})!=1:raise MappingError('SOURCE_RELATIONSHIP_UNVERIFIED')
    ranges=[]
    try:
        for m in matches:
            cell=view.data['tables'][int(m[1])]['data']['table_cells'][int(m[2])]
            row=cell['start_row_offset_idx'];span=cell.get('row_span',1)
            if type(row) is not int or type(span) is not int or row<0 or span<1:raise ValueError()
            ranges.append((row,row+span))
    except (KeyError,IndexError,TypeError,ValueError):raise MappingError('SOURCE_RELATIONSHIP_UNVERIFIED') from None
    if max(r[0] for r in ranges)>=min(r[1] for r in ranges):raise MappingError('SOURCE_RELATIONSHIP_UNVERIFIED')


def normalize(view, selections, policy):
    verify_view(view)
    if view.role not in ('CURRENT_SOURCE','HISTORICAL_REFERENCE'):
        raise MappingError('SOURCE_ROLE_INVALID')
    result=[]
    for s in selections:
        verify_row_relationship(view,s)
        if s.kind not in ('RPT','NCP','FINANCIAL','PERIOD','ENTITY'):
            raise MappingError('BUSINESS_TARGET_UNSUPPORTED')
        label=pointer(view.data,s.label_pointer)
        concept=policy.aliases.get(' '.join(label.casefold().split()))
        if not concept: raise MappingError('BUSINESS_MEANING_UNRESOLVED')
        years=set(re.findall(r'(?<!\d)(20\d{2})(?!\d)',pointer(view.data,s.period_pointer)))
        expected=policy.current_year if view.role=='CURRENT_SOURCE' else policy.historical_year
        if years!={str(expected)}: raise MappingError('SOURCE_PERIOD_MISMATCH')
        fields={k:pointer(view.data,p) for k,p in s.fields.items()}
        for key,pattern in s.field_patterns.items():
            if key not in fields:raise MappingError('SOURCE_MISSING')
            match=re.fullmatch(pattern,fields[key])
            if match is None or match.lastindex!=1:raise MappingError('SOURCE_PATTERN_MISMATCH')
            fields[key]=match.group(1)
        required={'party','country','relationship','amount'} if s.kind=='RPT' else ({'value','index'} if s.kind=='NCP' else {'value'})
        if view.role=='HISTORICAL_REFERENCE':required={'party','amount'} if s.kind=='RPT' else set()
        if not required<=fields.keys(): raise MappingError('SOURCE_MISSING')
        for k in ('amount','percentage') if s.kind=='RPT' else (('value',) if s.kind in ('NCP','FINANCIAL') else ()):
            if k in fields: fields[k]=number(fields[k])
        if view.role=='HISTORICAL_REFERENCE':
            if not s.meaning or not s.meaning_expected or pointer(view.data,s.meaning_pointer)!=s.meaning_expected:
                raise MappingError('HISTORICAL_CONTEXT_UNVERIFIED')
        evidence={'label':s.label_pointer,'period':s.period_pointer,**s.fields}
        if s.meaning_pointer:evidence['business_meaning']=s.meaning_pointer
        result.append(Fact(view.key,view.version,view.digest,s.kind,concept,expected,fields,evidence,s.meaning,s))
    return result


def record_ref(record):
    return {'object_type':record.object_type.value,'object_id':record.id,'revision':record.revision}


def serialized_fact(fact):
    return {'document_key':fact.document_key,'document_version':fact.version.model_dump(mode='json'),
        'observation_digest':fact.observation_digest,'kind':fact.kind,'concept':fact.concept,'period':fact.period,
        'fields':dict(fact.fields),'evidence':dict(fact.evidence),'meaning':fact.meaning}


class MappingPlanner:
    def __init__(self,task_id,created_at,policy):
        self.task_id=task_id; self.created_at=created_at; self.policy=policy

    def envelope(self,kind,key):
        return dict(schema_version='0.1.0',object_type=kind,id=key,revision=1,created_at=self.created_at,task_id=self.task_id)

    def plan(self,views,current,historical,slots,*,native: NativeCandidates | None=None):
        result={'workflow_profile':self.policy.workflow_profile,'profile_version':self.policy.version,
            'executable':False,'production_qualified':False,'replay_qualified':False,'items':[],'exceptions':[]}
        def refuse(code,fact=None):
            result['exceptions'].append({'code':code,'source_fact':serialized_fact(fact) if fact else None,'executable':False,'review_status':'REVIEW_REQUIRED'})
        # Reject forbidden-role envelopes before touching their content.
        if any(v.role not in ('CURRENT_SOURCE','HISTORICAL_REFERENCE','TARGET_TEMPLATE') for v in views):
            refuse('ROLE_NOT_PERMITTED'); return result
        bykey={v.key:v for v in views}
        targets=[v for v in views if v.role=='TARGET_TEMPLATE']
        if len(bykey)!=len(views) or len(targets)!=1 or len([v for v in views if v.role=='HISTORICAL_REFERENCE'])!=1:
            refuse('DOCUMENT_ROLE_AMBIGUOUS'); return result
        target=targets[0]
        version_roles={}
        for v in views:
            version_roles.setdefault((v.version.document_id,v.version.version_id,v.version.binary_hash),set()).add(v.role)
        if any(len(roles)>1 for roles in version_roles.values()):
            refuse('DOCUMENT_ROLE_COLLISION'); return result
        try:
            for v in views:verify_view(v)
            for facts,role in ((current,'CURRENT_SOURCE'),(historical,'HISTORICAL_REFERENCE')):
                for f in facts:
                    v=bykey.get(f.document_key)
                    if v is None or v.role!=role:raise MappingError('SOURCE_ROLE_INVALID')
                    if v.version!=f.version or v.digest!=f.observation_digest:raise MappingError('STALE_DOCUMENT_VERSION')
                    if normalize(v,[f.selection],self.policy)!=[f]:raise MappingError('SOURCE_FACT_TAMPERED')
        except MappingError as exc:
            refuse(exc.code); return result
        if not current:refuse('SOURCE_MISSING')
        for f in sorted(current,key=lambda x:(x.kind,x.concept,x.fields.get('party',''),x.document_key)):
            duplicate=[x for x in current if (x.kind,x.concept,x.fields.get('party'))==(f.kind,f.concept,f.fields.get('party'))]
            if len(duplicate)>1:refuse('SOURCE_CONFLICTING',f);continue
            candidates=[x for x in historical if (x.kind,x.concept)==(f.kind,f.concept)]
            same_party=[x for x in candidates if x.fields.get('party')==f.fields.get('party')]
            if same_party:candidates=same_party
            if len(candidates)>1:refuse('HISTORICAL_CONTEXT_AMBIGUOUS',f);continue
            history=candidates[0] if candidates else None
            changes=[]
            if history is None:
                if f.kind!='RPT':refuse('HISTORICAL_CONTEXT_MISSING',f);continue
                changes=['NEW_TRANSACTION','NARRATIVE_REVIEW_REQUIRED']
            elif f.kind=='RPT':
                for key,change in [('party','CHANGED_RELATED_PARTY'),('relationship','CHANGED_RELATIONSHIP'),('country','CHANGED_RELATIONSHIP')]:
                    if key in history.fields and f.fields.get(key)!=history.fields.get(key) and change not in changes:changes.append(change)
                if changes:changes.append('NARRATIVE_REVIEW_REQUIRED')
                elif f.fields.get('amount')!=history.fields.get('amount') or ('percentage' in history.fields and f.fields.get('percentage')!=history.fields['percentage']):
                    changes=['SAME_TRANSACTION_CHANGED_VALUE']
                else:changes=['UNCHANGED_TRANSACTION']
            else:changes=['CURRENT_PERIOD_VALUE']
            rules=[r for r in self.policy.targets if (r.kind,r.concept)==(f.kind,f.concept) and (history is None or r.historical_meaning==history.meaning)]
            if len(rules)!=1:refuse('BUSINESS_TARGET_AMBIGUOUS' if rules else 'BUSINESS_TARGET_UNRESOLVED',f);continue
            rule=rules[0]
            if f.document_key not in rule.current_sources:refuse('SOURCE_NOT_AUTHORITATIVE',f);continue
            matches=[s for s in slots if s.region.business_target_id==rule.business_target_id]
            if len(matches)!=1:refuse('TARGET_REGION_AMBIGUOUS' if matches else 'TARGET_REGION_MISSING',f);continue
            slot=matches[0]
            if slot.region.document_version_ref!=target.version:refuse('STALE_TARGET_VERSION',f);continue
            if slot.region.task_id!=self.task_id or slot.region.target_contract_instance_ref.model_dump(mode='json')!=self.policy.target_instance_ref:
                refuse('TARGET_CONTRACT_MISMATCH',f);continue
            try:existing=pointer(target.data,slot.pointer,allow_empty=True)
            except MappingError:refuse('TARGET_REGION_MISSING',f);continue
            if existing!=slot.expected_content:refuse('STALE_TARGET_CONTENT',f);continue
            if slot.protected:refuse('PROTECTED_OBJECT',f);continue
            payloads={'REPLACE_RUN_TEXT':'RUN_TEXT_REPLACEMENT','REPLACE_SDT_TEXT':'SDT_TEXT_REPLACEMENT','REPLACE_SIMPLE_TABLE_CELL_TEXT':'SIMPLE_TABLE_CELL_TEXT_REPLACEMENT'}
            if slot.operation not in payloads:refuse('OPERATION_UNSUPPORTED',f);continue
            if slot.field not in f.fields:refuse('SOURCE_MISSING',f);continue
            proposed=slot.value_prefix+f.fields[slot.field]+slot.value_suffix
            rationale=f"{self.policy.workflow_profile}@{self.policy.version}: configured {f.concept} fact; historical meaning {history.meaning if history else 'new transaction, narrative review required'}; resolves {rule.business_target_id} to pinned template region. Current evidence only supplies current values."
            identity={'policy':asdict(self.policy),'source':serialized_fact(f),'history':serialized_fact(history) if history else None,
                'target':target.version.model_dump(mode='json'),'target_observation':target.digest,'region':slot.region.model_dump(mode='json'),
                'pointer':slot.pointer,'operation':slot.operation,'field':slot.field,'existing':existing,'task_id':self.task_id,
                'prefix':slot.value_prefix,'suffix':slot.value_suffix,'created_at':self.created_at}
            key=canonical_digest(identity)[:32]
            evidence=EvidenceRecord(**self.envelope('EvidenceRecord','evidence-'+key),kind='SOURCE_EXCERPT',document_version_ref=f.version,
                content_ref={'uri':'urn:foundation:semantic:'+f.observation_digest,'sha256':f.observation_digest,'media_type':'application/json'},
                observed_value={'kind':'TEXT','review_text':proposed,'value':proposed},authority='AUTHORITATIVE',period_scope='UNKNOWN',period=None)
            mapping=MappingProposal(**self.envelope('MappingProposal','mapping-'+key),business_target_id=rule.business_target_id,
                target_region_ref=record_ref(slot.region),evidence_refs=[record_ref(evidence)],rule_evaluation_refs=[],ai_interaction_refs=[],
                proposed_value={'kind':'TEXT','review_text':proposed,'value':proposed},status='PROPOSED',rationale=rationale,error_codes=[])
            warnings=['B2_1_NOT_EXECUTABLE','SOURCE_FRESHNESS_NOT_QUALIFIED']
            if history and f.kind=='RPT' and not {'country','relationship'}<=history.fields.keys():warnings.append('HISTORICAL_RELATIONSHIP_NOT_OBSERVED')
            if 'NARRATIVE_REVIEW_REQUIRED' in changes:warnings.append('NARRATIVE_REVIEW_REQUIRED')
            if history is None:warnings.extend(['HISTORICAL_INVENTORY_NOT_QUALIFIED','ROW_GROWTH_NOT_QUALIFIED'])
            try:
                resolution=native.resolve(slot,target) if native else NativeResult()
            except Exception:
                resolution=NativeResult()
                warnings.append('NATIVE_RESOLUTION_FAILED')
            locator=None
            if len(resolution.locators)>1:warnings.append('NATIVE_LOCATOR_AMBIGUOUS')
            elif not resolution.locators:warnings.append('NATIVE_LOCATOR_UNRESOLVED')
            else:
                candidate=resolution.locators[0]
                expected={'REPLACE_RUN_TEXT':'DOCX_RUN','REPLACE_SDT_TEXT':'DOCX_CONTENT_CONTROL','REPLACE_SIMPLE_TABLE_CELL_TEXT':'DOCX_TABLE_CELL'}[slot.operation]
                if resolution.record_region_id!=slot.region.id or resolution.semantic_pointer!=slot.pointer:warnings.append('NATIVE_REGION_MISMATCH')
                elif candidate.document_version_ref!=target.version or candidate.task_id!=self.task_id:warnings.append('STALE_NATIVE_LOCATOR')
                elif candidate.structural_fingerprint!=resolution.observed_fingerprint:warnings.append('NATIVE_FINGERPRINT_MISMATCH')
                elif candidate.locator_type.value!=expected:warnings.append('NATIVE_OPERATION_UNSUPPORTED')
                elif resolution.protected:warnings.append('PROTECTED_OBJECT')
                elif resolution.observed_content!=existing:warnings.append('STALE_NATIVE_CONTENT')
                else:locator=candidate
            change=None
            if locator and history is not None:
                change_key=canonical_digest({'mapping':identity,'locator':locator.model_dump(mode='json')})[:32]
                change=ChangeProposal(**self.envelope('ChangeProposal','change-'+change_key),status='DRAFT',business_target_id=rule.business_target_id,
                    target_document_version_ref=target.version,target_contract_definition_ref=self.policy.target_definition_ref,
                    target_contract_instance_ref=self.policy.target_instance_ref,rule_pack_ref=self.policy.rule_pack_ref,mapping_proposal_ref=record_ref(mapping),
                    source_assessment_refs=[],evidence_assessment_refs=[],proposed_value=mapping.proposed_value,
                    current_value={'kind':'TEXT','review_text':existing,'value':existing},native_locator_ref=record_ref(locator),
                    operation=slot.operation,payload={'kind':payloads[slot.operation],'replacement_text':proposed},error_codes=[])
            if change is None:
                mapping=mapping.model_copy(update={'status':type(mapping.status).BLOCKED})
                for code in warnings[2:]:
                    result['exceptions'].append({'code':code,'proposal_id':'change-'+key,'executable':False,'review_status':'REVIEW_REQUIRED'})
            projection={'business_target_id':rule.business_target_id,'target_region':record_ref(slot.region),
                'semantic_region':{'document_version':target.version.model_dump(mode='json'),'observation_digest':target.digest,'pointer':slot.pointer},
                'native_target_ref':record_ref(locator) if locator else None,'existing_value':existing,'proposed_value':proposed,
                'change_type':changes,'source_evidence_ref':record_ref(evidence),
                'historical_reference_ref':serialized_fact(history) if history else None,'mapping_status':'PROPOSED' if change else 'BLOCKED',
                'review_status':'REVIEW_REQUIRED','warning':warnings,'mapping_rationale':rationale,'executable':False}
            result['items'].append({'proposal_id':change.id if change else 'intent-'+key,'workflow_profile':self.policy.workflow_profile,'business_target_id':rule.business_target_id,
                'source_fact':serialized_fact(f),'source_role':'CURRENT_SOURCE','source_evidence_ref':record_ref(evidence),
                'historical_context':serialized_fact(history) if history else None,'historical_reference_ref':projection['historical_reference_ref'],
                'target_region':record_ref(slot.region),'native_binding_status':'EXACT_CANDIDATE' if locator else 'UNRESOLVED',
                'existing_target_content':existing,'proposed_content':proposed,'change_types':changes,'mapping_rationale':rationale,
                'conflict_state':'NONE_DETECTED','review_status':'REVIEW_REQUIRED','executable':False,'warnings':warnings,
                'mapping_proposal':mapping.model_dump(mode='json'),'change_proposal':change.model_dump(mode='json') if change else None,
                'native_locator_candidate':locator.model_dump(mode='json') if locator else None,
                'evidence_record':evidence.model_dump(mode='json'),'projection':projection})
        for past in historical:
            if past.kind=='RPT' and not any((f.kind,f.concept)==(past.kind,past.concept) for f in current):
                refuse('REMOVED_TRANSACTION',past)
                result['exceptions'][-1]['warning']='Absent from supplied current selection only; confirm complete source inventory. No deletion proposal or row-shrink operation.'
        occupied={}
        for item in result['items']:
            occupied.setdefault(('semantic',item['projection']['semantic_region']['pointer']),[]).append(item)
            candidate=item['native_locator_candidate']
            if candidate:
                occupied.setdefault(('native',candidate['part_uri'],canonical_digest(candidate['address'])),[]).append(item)
        for items in occupied.values():
            if len(items)>1:
                for item in items:
                    item['change_proposal']=None
                    if 'TARGET_REGION_COLLISION' not in item['warnings']:
                        item['warnings'].append('TARGET_REGION_COLLISION')
                        result['exceptions'].append({'code':'TARGET_REGION_COLLISION','proposal_id':item['proposal_id'],'executable':False,'review_status':'REVIEW_REQUIRED'})
                    item['projection']['mapping_status']='BLOCKED'
                    item['mapping_proposal']['status']='BLOCKED'
        return result
