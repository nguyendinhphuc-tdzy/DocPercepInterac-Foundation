"""B1.5 engineering harness; non-contract evidence, no replay or qualification promotion.

PASS measures the named mechanical check only. Existing evaluation vocabulary
is retained: PASS/FAIL/NOT_EVALUATED and REVIEW_REQUIRED. NOT_IMPLEMENTED is
component availability, never a domain status. No human judgment is accepted or
invented here; B1.2R remains a separate immutable representative evidence lane.
"""
from hashlib import sha256
import json
from pathlib import Path
from typing import Protocol

from foundation.adapters.preflight import OoxmlPreflight
from foundation.domain import DocumentPreflightAssessment, DocumentVersionRef, Ref
from foundation.governance.invariants import InvariantContext, InvariantEngine
from foundation.ports.content import verified_bytes, ContentAccessError
from foundation.ports.perception import PerceptionPort

STAGES=('input_integrity','preflight','perception','native_identity','binding','invariants')


def ref(record):
    return Ref(object_type=record.object_type,object_id=record.id,revision=record.revision)


def version(document):
    return DocumentVersionRef(document_id=document.document_id,version_id=document.id,binary_hash=document.binary_hash)


class NativeDiscovery(Protocol):
    def discover(self, document): ...
    def resolve(self, document, locator): ...


class Binding(Protocol):
    def bind(self, document, snapshot, semantic_object, candidates): ...


class B1Harness:
    def __init__(self,resolver,perception:PerceptionPort|None=None,native:NativeDiscovery|None=None,binding:Binding|None=None):
        self.resolver,self.perception,self.native,self.binding=resolver,perception,native,binding

    def run(self,document,analysis_run):
        components={'perception':self.perception,'native_identity':self.native,'binding':self.binding}
        out={'evaluation_version':'b1-integrated-1.0.0','implementation_status':'PROVISIONAL',
             'production_qualified':False,'production_authorized':False,
             'review_status':'REVIEW_REQUIRED','decision':'INSUFFICIENT_EVIDENCE',
             'stages':{s:{'implementation':'NOT_IMPLEMENTED' if s in components and components[s] is None else 'IMPLEMENTED',
                          'outcome':'NOT_EVALUATED','error_codes':[]} for s in STAGES},
             'records':{'document':document.model_dump(mode='json'),'analysis_run':analysis_run.model_dump(mode='json'),
                        'semantic_objects':[],'native_locators':[],'bindings':[]},
             'artifacts':[], 'limitations':[], 'invariant_results':[]}
        def stage(name,outcome,codes=()):
            out['stages'][name].update(outcome=outcome,error_codes=list(codes))
        def artifacts(values):
            for a in values:
                if sha256(a.data).hexdigest()!=a.ref.sha256:raise ValueError('Artifact digest mismatch')
                out['artifacts'].append({'ref':a.ref.model_dump(mode='json'),'content':a.data.decode('utf-8')})
        current='input_integrity'
        try:
            verified_bytes(document,self.resolver)
            stage(current,'PASS')
            current='preflight'
            if analysis_run.task_id!=document.task_id or analysis_run.status.value!='RUNNING' or version(document) not in analysis_run.document_version_refs:
                raise ValueError('Analysis context invalid')
            adapter=OoxmlPreflight(self.resolver)
            started=DocumentPreflightAssessment(schema_version='0.1.0',object_type='DocumentPreflightAssessment',
                id='integrated-preflight-'+sha256((document.id+document.binary_hash+analysis_run.id).encode()).hexdigest(),
                revision=2,created_at=analysis_run.created_at,task_id=document.task_id,document_version_ref=version(document),
                status='ASSESSING',detected_format=None,detected_conformance='UNKNOWN',format_observation_refs=[],
                protection_findings=[],native_structure_findings=[],capability_results=[],
                assessor={'actor_type':'SYSTEM','actor_id':'b1-integrated-evaluator'},engine=adapter.engine,engine_version=adapter.version,
                configuration_ref=adapter.configuration.ref,assessed_at=None,error_codes=[])
            preflight=adapter.assess(document,started,analysis_run.created_at)
            out['records']['preflight']=preflight.assessment.model_dump(mode='json');artifacts(preflight.artifacts)
            if preflight.assessment.status.value!='COMPLETED':
                stage(current,'FAIL',[e.value for e in preflight.assessment.error_codes]);return out
            stage(current,'PASS')
            perceived=discovered=None
            if self.perception is not None:
                current='perception'
                perceived=self.perception.perceive(document,analysis_run)
                snapshot=perceived.snapshot;objects=perceived.semantic_objects
                if (snapshot.document_version_ref!=version(document) or snapshot.task_id!=document.task_id or
                    snapshot.analysis_run_ref!=ref(analysis_run) or not objects or
                    snapshot.semantic_object_refs!=[ref(o) for o in objects] or
                    len({o.id for o in objects})!=len(objects) or
                    any(o.task_id!=document.task_id or o.semantic_reference.snapshot_ref!=ref(snapshot) for o in objects)):
                    raise ValueError('Perception provenance invalid')
                by_ref={ref(o).model_dump_json():o for o in objects}
                if len({o.semantic_reference.semantic_id for o in objects})!=len(objects):raise ValueError('Duplicate semantic identity')
                for obj in objects:
                    seen=set();cursor=obj
                    if obj.native_binding_refs:raise ValueError('Unresolved upstream native links')
                    while cursor.parent_ref is not None:
                        key=cursor.parent_ref.model_dump_json()
                        if key not in by_ref or key in seen:raise ValueError('Invalid semantic parent graph')
                        seen.add(key);cursor=by_ref[key]
                evidence=[getattr(self.perception,k) for k in ('configuration','value_schema') if hasattr(self.perception,k)]
                if snapshot.configuration_ref not in [a.ref for a in evidence]:raise ValueError('Configuration evidence missing')
                from jsonschema import Draft202012Validator
                for obj in objects:
                    if obj.value.kind.value=='STRUCTURED':
                        schema=next((a for a in evidence if a.ref==obj.value.schema_ref),None)
                        if schema is None:raise ValueError('Structured schema evidence missing')
                        Draft202012Validator(json.loads(schema.data)).validate(obj.value.value)
                out['records']['snapshot']=snapshot.model_dump(mode='json')
                out['records']['semantic_objects']=[o.model_dump(mode='json') for o in objects]
                out['limitations'].extend(snapshot.limitations)
                artifacts([getattr(self.perception,k) for k in ('configuration','value_schema') if hasattr(self.perception,k)])
                stage(current,'PASS')
            if self.native is not None:
                current='native_identity';discovered=self.native.discover(document)
                locators=discovered.native_locators
                out['records']['native_preflight']=discovered.preflight_assessment.model_dump(mode='json')
                out['records']['native_locators']=[x.model_dump(mode='json') for x in locators]
                out['limitations'].extend(discovered.limitations);artifacts(discovered.artifacts)
                if (not locators or discovered.preflight_assessment.status.value!='COMPLETED' or
                    discovered.preflight_assessment.document_version_ref!=version(document) or
                    any(x.document_version_ref!=version(document) or x.task_id!=document.task_id for x in locators)):
                    stage(current,'FAIL',['NATIVE_BINDING_MISSING']);return out
                resolutions=[]
                for locator in locators:
                    observation=self.native.resolve(document,locator)
                    resolutions.append({'locator_ref':ref(locator).model_dump(mode='json'),'status':observation.status,
                                        'fingerprint':observation.structural_fingerprint})
                    if observation.status!='EXACT_MATCH' or observation.structural_fingerprint!=locator.structural_fingerprint:
                        stage(current,'FAIL',['LOCATOR_FINGERPRINT_MISMATCH'])
                out['native_resolution_observations']=resolutions
                if out['stages'][current]['outcome']=='FAIL':return out
                stage(current,'PASS')
            if perceived is not None and discovered is not None and self.binding is not None:
                current='binding'
                bindings=[]
                for obj in perceived.semantic_objects:
                    if hasattr(self.binding,'bind_with_evidence'):
                        result=self.binding.bind_with_evidence(document,perceived.snapshot,obj,discovered.native_locators)
                        bindings.append(result.binding)
                        artifacts((result.observation_artifact,result.configuration_artifact))
                    else:bindings.append(self.binding.bind(document,perceived.snapshot,obj,discovered.native_locators))
                known={ref(x).model_dump_json() for x in discovered.native_locators}
                if any(b.task_id!=document.task_id or b.semantic_object_ref!=ref(obj) or
                       any(r.model_dump_json() not in known for r in b.native_locator_refs)
                       for obj,b in zip(perceived.semantic_objects,bindings)):
                    raise ValueError('Binding provenance invalid')
                out['records']['bindings']=[b.model_dump(mode='json') for b in bindings]
                if any(b.status.value!='RESOLVED' or len(b.native_locator_refs)!=1 for b in bindings):
                    stage(current,'FAIL',['NATIVE_BINDING_MISSING'])
                else:stage(current,'PASS')
                current='invariants'
                records=(document,analysis_run,perceived.snapshot,*perceived.semantic_objects,*discovered.native_locators,*bindings)
                context=InvariantContext(records=records)
                # Only applicable B1 invariants; do not claim vacuous replay/approval checks.
                results=[InvariantEngine().evaluate(key,context) for key in ('FND-INV-DOC-001','FND-INV-ID-001','FND-INV-ID-002')]
                out['invariant_results']=[r.model_dump(mode='json') for r in results]
                stage(current,'PASS' if all(r.passed for r in results) else 'FAIL',[r.error_code.value for r in results if r.error_code])
        except Exception as error:
            code=error.code.value if isinstance(error,ContentAccessError) else 'INVALID_CONTRACT'
            stage(current,'FAIL',[code])
            # Raw adapter diagnostics are not copied to either report.
        finally:
            try:verified_bytes(document,self.resolver)
            except Exception:stage('input_integrity','FAIL',['STALE_DOCUMENT_VERSION'])
        return out


def public_summary(report):
    if set(report['stages'])!=set(STAGES):raise ValueError('Invalid stage set')
    stages={}
    for key in STAGES:
        s=report['stages'][key]
        if s['implementation'] not in ('IMPLEMENTED','NOT_IMPLEMENTED') or s['outcome'] not in ('PASS','FAIL','NOT_EVALUATED'):
            raise ValueError('Invalid evaluation status')
        stages[key]={k:s[k] for k in ('implementation','outcome')}
    return {'evaluation_version':'b1-integrated-1.0.0','implementation_status':'PROVISIONAL',
            'stages':stages,'review_status':'REVIEW_REQUIRED','decision':'INSUFFICIENT_EVIDENCE',
            'production_qualified':False,'production_authorized':False}


def write_run(report,private_report,public_report,repo):
    """Exclusive new run files; content never crosses into the public projection."""
    repo=Path(repo).resolve();boundary=repo/'.foundation-private'
    private=Path(private_report).absolute();public=Path(public_report).absolute()
    allowed=repo/'qualification/b1/integrated/reports'
    if (boundary.resolve()!=boundary or private.resolve()!=private or public.resolve()!=public or
        not private.is_relative_to(boundary) or not public.is_relative_to(allowed) or
        private.suffix!='.json' or public.suffix!='.json'):
        raise ValueError('EVIDENCE_OUTPUT_BOUNDARY')
    summary=public_summary(report)
    if private.exists() or public.exists():raise FileExistsError('Immutable run path already exists')
    private.parent.mkdir(parents=True,exist_ok=True);public.parent.mkdir(parents=True,exist_ok=True)
    with private.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2,allow_nan=False)
    with public.open('x',encoding='utf-8') as stream:json.dump(summary,stream,indent=2,allow_nan=False)
    return summary
