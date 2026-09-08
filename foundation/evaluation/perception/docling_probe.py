"""Isolated Docling Office qualification via public declarative backend APIs.

The high-level DocumentConverter eagerly imports unrelated formats in 2.126.0.
This spike explicitly selects the public Office backend convert() interface;
there is no runtime fallback and no access to InputDocument._backend.
"""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from importlib import metadata
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter

from foundation.domain import DocumentVersion, ErrorCode
from foundation.ports.content import ContentAccessError, verified_bytes
from foundation.adapters.preflight.evidence import EvidenceArtifact

CANDIDATE = 'docling-slim'
VERSION = '2.126.0'
CONFIGURATION = {
    'probe_version':'1.0.0', 'api':'public declarative Office backend convert()',
    'candidate':CANDIDATE, 'candidate_version':VERSION,
    'enable_remote_fetch':False, 'enable_local_fetch':False, 'render_chart_images':False,
    'xlsx_parse_charts':True, 'xlsx_treat_singleton_as_text':False, 'xlsx_gap_tolerance':0,
    'supplement':'pypdfium2==5.13.0', 'native_identity_created':False,
}


def digest(value):
    # Evaluation-only canonical encoding preserves Docling's uint64 origin hash.
    # This is deliberately not the frozen authorization/AuditEvent JCS algorithm.
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')).hexdigest()


class LocalPinnedContent:
    """Explicit local input selected by evaluation caller, never ContentRef URI fetch."""
    def __init__(self, path: Path): self.path=path
    def resolve(self, document): return self.path.read_bytes()


def installed_candidate():
    actual=metadata.version(CANDIDATE)
    if actual!=VERSION:
        raise RuntimeError(f'Qualification requires {CANDIDATE}=={VERSION}; installed {actual}')
    return actual


def convert_office(data: bytes, fmt: str):
    """Use public InputDocument and backend constructors; streams own byte lifetime."""
    installed_candidate()
    from docling.datamodel.document import InputDocument
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.backend_options import MsWordBackendOptions, MsExcelBackendOptions
    from docling.backend.msword_backend import MsWordDocumentBackend
    from docling.backend.msexcel_backend import MsExcelDocumentBackend
    choices={
        'DOCX':(InputFormat.DOCX, MsWordDocumentBackend, MsWordBackendOptions(enable_remote_fetch=False, enable_local_fetch=False, render_chart_images=False)),
        'XLSX':(InputFormat.XLSX, MsExcelDocumentBackend, MsExcelBackendOptions(enable_remote_fetch=False, enable_local_fetch=False, render_chart_images=False, parse_charts=True, treat_singleton_as_text=False, gap_tolerance=0)),
    }
    if fmt not in choices: raise ValueError('Only explicitly selected DOCX/XLSX qualification inputs are allowed')
    input_format, backend_type, options=choices[fmt]
    with BytesIO(data) as registration_stream, BytesIO(data) as conversion_stream:
        in_doc=InputDocument(path_or_stream=registration_stream,format=input_format,
            backend=backend_type,backend_options=options,filename='immutable-input.'+fmt.lower())
        if not in_doc.valid: raise ValueError('Docling rejected input document')
        backend=backend_type(in_doc=in_doc,path_or_stream=conversion_stream,options=options)
        try:
            if not backend.is_valid(): raise ValueError('Docling backend rejected input')
            doc=backend.convert()
            return doc.export_to_dict()
        finally:
            backend.unload()


def semantic_observations(doc: dict) -> dict:
    """Separate semantic content/shape/order from literal reference stability."""
    collections=('texts','tables','groups','pictures','key_value_items','form_items')
    nodes=[(kind,node) for kind in collections for node in doc.get(kind,[])]
    refs=[node.get('self_ref') for _,node in nodes]
    index={ref:i for i,ref in enumerate(refs)}
    # Root IDs and all literal node refs remain visible in the references signature.
    def link(ref):
        if ref is None: return None
        value=ref.get('$ref')
        return index[value] if value in index else {'root_or_unresolved':value}
    structure=[{'kind':kind,'label':node.get('label'),'parent':link(node.get('parent')),
        'children':[link(x) for x in node.get('children',[])]} for kind,node in nodes]
    references=[{'self_ref':node.get('self_ref'),'parent':node.get('parent'), 'children':node.get('children',[])} for _,node in nodes]
    tables=[{'rows':t.get('data',{}).get('num_rows'), 'cols':t.get('data',{}).get('num_cols'),
        'cells':t.get('data',{}).get('table_cells',[])} for t in doc.get('tables',[])]
    text=[node.get('text','') for node in doc.get('texts',[])]
    content={'text':text, 'table_text':[[c.get('text','') for c in t['cells']] for t in tables]}
    # Traversal order is derived from explicit parent/child representation.
    by_ref={n.get('self_ref'): (k,n) for k,n in nodes}
    ordering=[]
    def walk(node, active):
        for child in node.get('children',[]):
            reference=child.get('$ref')
            if reference in active: raise ValueError('Cyclic semantic hierarchy')
            if reference not in by_ref: raise ValueError('Unresolved semantic child')
            kind,value=by_ref[reference]
            ordering.append({'kind':kind,'label':value.get('label'),'text':value.get('text')})
            walk(value, active | {reference})
    walk(doc.get('body',{}),set()); walk(doc.get('furniture',{}),set())
    shape={'nodes':structure, 'body_children':[link(x) for x in doc.get('body',{}).get('children',[])],
        'furniture_children':[link(x) for x in doc.get('furniture',{}).get('children',[])]}
    reference_shape={'nodes':references,'body':doc.get('body',{}),'furniture':doc.get('furniture',{})}
    return {
        'counts_by_kind':dict(sorted(Counter(node.get('label',kind) for kind,node in nodes).items())),
        'collection_counts':{kind:len(doc.get(kind,[])) for kind in collections},
        'table_count':len(tables), 'table_shapes':[[t['rows'],t['cols']] for t in tables],
        'text_content_digest':digest(content), 'text_items':text, 'hierarchy':shape,
        'semantic_reference_values':refs,
        'signatures':{'content':digest(content),'structure':digest(shape),'tables':digest(tables),
            'ordering':digest(ordering),'references':digest(reference_shape)},
        'unclassified_top_level_fields':sorted(set(doc)-set(collections)-{'schema_name','version','name','origin','body','furniture','pages'}),
    }


def probe_once(document: DocumentVersion, resolver, fmt: str) -> dict:
    data=verified_bytes(document,resolver)
    installed_candidate()  # Missing/wrong candidate is infrastructure failure, not a successful negative case.
    start=perf_counter()
    result={'candidate_package':CANDIDATE,'candidate_version':VERSION,'input_sha256':document.binary_hash,
        'format':fmt,'conversion_status':'FAIL','observations':None,'semantic_document':None,'errors':[]}
    try:
        exported=convert_office(data,fmt)
        observations=semantic_observations(exported)
        if not any(observations['collection_counts'].values()): raise ValueError('Empty semantic representation')
        result.update(conversion_status='PASS', observations=observations, semantic_document=exported)
    except (ImportError, metadata.PackageNotFoundError):
        raise  # B1 qualification must not pass when dependencies are missing.
    except Exception as exc:
        result['errors']=[{'error_code':ErrorCode.PERCEPTION_FAILED.value,'exception_type':type(exc).__name__,
            'message':'Docling conversion failed; no successful perception output was produced'}]
    finally:
        # Detect unexpected input change without ever saving a document.
        verified_bytes(document,resolver)
    result['elapsed_seconds']=perf_counter()-start
    return result


def compare_runs(runs):
    if len(runs)<3: raise ValueError('At least three same-binary runs required')
    if len({r['input_sha256'] for r in runs})!=1: raise ValueError('Runs must use the same binary')
    if any(r['conversion_status']!='PASS' for r in runs):
        return {k:'NOT_EVALUATED' for k in ('content','structure','tables','ordering','references')}
    return {k:('PASS' if len({r['observations']['signatures'][k] for r in runs})==1 else 'OBSERVED_LIMITATION')
        for k in ('content','structure','tables','ordering','references')}


def run_manifest(manifest_path: Path, output: Path) -> dict:
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['engine']!=CANDIDATE or manifest['engine_version']!=installed_candidate() or manifest['run_count']<3:
        raise ValueError('Manifest does not match the exact candidate/repeatability requirements')
    config=EvidenceArtifact.create(CONFIGURATION)
    cases=[]
    for case in manifest['cases']:
        root=manifest_path.parent.resolve(); path=(root/case['input_path']).resolve()
        if not path.is_relative_to(root): raise ValueError('Corpus input escapes manifest root')
        data=path.read_bytes(); actual=sha256(data).hexdigest()
        if actual!=case['input_sha256']: raise ContentAccessError(ErrorCode.STALE_DOCUMENT_VERSION,'Corpus hash mismatch')
        document=DocumentVersion(schema_version='0.1.0',object_type='DocumentVersion',id='version-'+case['case_id'],revision=1,
            created_at='2026-09-08T00:00:00Z',task_id='qualification-b1',document_id='document-'+case['case_id'],
            binary_hash=actual,byte_length=len(data),content_ref={'uri':'urn:qualification:sha256:'+actual,'sha256':actual,'media_type':'application/octet-stream'})
        runs=[probe_once(document,LocalPinnedContent(path),case['format']) for _ in range(manifest['run_count'])]
        repeatability=compare_runs(runs)
        behavior=all(r['conversion_status']==case['expected_conversion'] for r in runs)
        cases.append({'case_id':case['case_id'],'input_sha256':actual,'format':case['format'],
            'feature_profile':case['feature_profile'],'run_count':len(runs),'runs':runs,'repeatability':repeatability,
            'behavior_result':'PASS' if behavior else 'FAIL'})
    stable={
        'evaluation_version':'1.0.0','qualification_kind':'SYNTHETIC_ONLY',
        'qualification_status':'PROVISIONAL_CONTINUE' if all(c['behavior_result']=='PASS' for c in cases) else 'PROVISIONAL_BLOCK',
        'production_qualified':False,'engine':CANDIDATE,'engine_version':VERSION,
        'configuration_ref':config.ref.model_dump(mode='json'),'configuration':CONFIGURATION,
        'evidence_limitations':['Synthetic qualification evidence only; representative Local File corpus gate remains open.',
            'Office-only extras require supplemental pypdfium2 in candidate 2.126.0.',
            'Public declarative backends evaluated; high-level DocumentConverter is NOT_EVALUATED after its missing PDF dependency import.',
            'Content preservation observations are not evidence sufficiency or native execution identity.',
            'No production adapter, locator resolution, formula recalculation or replay qualification.'],
        'cases':[{**c,'runs':[{k:v for k,v in r.items() if k!='elapsed_seconds'} for r in c['runs']]} for c in cases],
    }
    report={**stable,'reproducible_payload_sha256':digest(stable),
        'timing_observations':{c['case_id']:[r['elapsed_seconds'] for r in c['runs']] for c in cases},
        'installed_packages':dict(sorted((d.metadata['Name'],d.version) for d in metadata.distributions()))}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return report
