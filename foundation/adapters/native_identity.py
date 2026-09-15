"""Provisional, read-only exact DOCX identities. Never grants mutation capability.

python-docx owns package loading and XML objects; this adapter only selects a
small allowlisted structure profile and produces the frozen native addresses.
"""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import docx
from lxml import etree

from foundation.domain import DocumentPreflightAssessment, DocumentVersionRef, NativeLocator
from foundation.ports.content import ContentAccessError, verified_bytes
from foundation.adapters.preflight import OoxmlPreflight, PreflightConfig
from foundation.adapters.preflight.evidence import EvidenceArtifact

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
Q = lambda name: '{'+W+'}'+name
PROFILE = EvidenceArtifact.create({
    'profile':'b1-docx-native-subtree-v1', 'qualification':'PROVISIONAL',
    'fingerprint':'SHA256 of lxml inclusive C14N 1.0 subtree without comments; tail excluded',
    'address':'root-inclusive expanded QName path; one-based same-QName sibling ordinal',
    'scope':'Transitional main body text-only runs, unlocked plain SDTs, unmerged simple table cells',
    'engine':'python-docx', 'engine_version':docx.__version__,
    'canonicalizer':'lxml', 'canonicalizer_version':etree.LXML_VERSION,
    'native_dom_max_expanded_bytes':8*1024*1024,
    'properties':'allowlisted simple paragraph/run/cell properties only; unknown descendants refused',
})

@dataclass(frozen=True)
class NativeResolution:
    status: str
    reason: str
    structural_fingerprint: str | None = None
    text: str | None = None

@dataclass(frozen=True)
class NativeDiscoveryResult:
    preflight_assessment: DocumentPreflightAssessment
    native_locators: tuple
    limitations: tuple[str, ...]
    artifacts: tuple = ()

def version_ref(document):
    return DocumentVersionRef(document_id=document.document_id,version_id=document.id,binary_hash=document.binary_hash)

def path_of(element):
    path=[]
    while element is not None:
        parent=element.getparent()
        ordinal=1 if parent is None else [x for x in parent if x.tag==element.tag].index(element)+1
        q=etree.QName(element)
        path.append({'namespace_uri':q.namespace,'local_name':q.localname,'ordinal':ordinal})
        element=parent
    return list(reversed(path))

def fingerprint(element):
    return sha256(etree.tostring(element,method='c14n',with_comments=False)).hexdigest()

class DocxNativeIdentity:
    """Separate discovery/resolution interface; no serializer, save or write path.

    The tighter DOM envelope is additional to unchanged resource-safe preflight.
    All returned identities remain unqualified for mutation.
    """
    def __init__(self,resolver,config=None):
        self.resolver=resolver
        self.preflight=OoxmlPreflight(resolver,config or PreflightConfig())

    def _load(self,document):
        # Materialize ONCE: preflight and external reader must inspect identical bytes.
        data=verified_bytes(document,self.resolver)
        class Pinned:
            def resolve(self,_document): return data
        preflight=OoxmlPreflight(Pinned(), self.preflight.config)
        started=DocumentPreflightAssessment(schema_version='0.1.0',object_type='DocumentPreflightAssessment',
            id='native-preflight-'+sha256((document.task_id+document.id+document.binary_hash+preflight.configuration.ref.sha256).encode()).hexdigest(),
            revision=1,created_at=document.created_at,task_id=document.task_id,document_version_ref=version_ref(document),
            status='ASSESSING',detected_format=None,detected_conformance='UNKNOWN',format_observation_refs=[],
            protection_findings=[],native_structure_findings=[],capability_results=[],assessor={'actor_type':'SYSTEM','actor_id':'native-identity'},
            engine=preflight.engine,engine_version=preflight.version,configuration_ref=preflight.configuration.ref,assessed_at=None,error_codes=[])
        result=preflight.assess(document,started,document.created_at)
        a=result.assessment
        if a.status.value!='COMPLETED': return result,None,'UNSUPPORTED: preflight refused input'
        if a.detected_format.value!='DOCX': return result,None,'UNSUPPORTED: XLSX/native non-DOCX identity is outside this bounded profile'
        if a.detected_conformance.value!='TRANSITIONAL': return result,None,'UNSUPPORTED: only Transitional DOCX identity profile'
        if a.protection_findings: return result,None,'UNSUPPORTED: protection observations require a separately qualified identity profile'
        # python-docx materializes a DOM; bound it more tightly than streaming preflight.
        from zipfile import ZipFile
        with ZipFile(BytesIO(data)) as archive:
            if sum(x.file_size for x in archive.infolist()) > 8*1024*1024:
                return result,None,'UNSUPPORTED: native reader expanded DOM budget exceeded (8 MiB)'
        try:
            loaded=docx.Document(BytesIO(data))
        except Exception:
            return result,None,'UNSUPPORTED: external DOCX reader could not load the validated package'
        if str(loaded.part.partname)!='/word/document.xml':
            return result,None,'UNSUPPORTED: main part outside bounded /word/document.xml profile'
        return result,loaded.element,None

    def _plain_tree(self, element):
        # Bounded grammar, including properties: unknown constructs never inherit
        # text-only status just because a descendant has a w:t element.
        grammar = {
            'p': {'pPr', 'r'}, 'pPr': {'pStyle', 'jc', 'spacing', 'keepNext', 'keepLines'},
            'r': {'rPr', 't'}, 'rPr': {'b', 'i', 'u', 'sz', 'color'},
            'tc': {'tcPr', 'p'}, 'tcPr': {'tcW'},
            'sdtContent': {'p'},
        }
        leaves = {'pStyle', 'jc', 'spacing', 'keepNext', 'keepLines', 'b', 'i', 'u', 'sz', 'color', 't', 'tcW'}
        for node in element.iter():
            if not isinstance(node.tag, str) or not node.tag.startswith('{'+W+'}'): return False
            name = etree.QName(node).localname
            if name in leaves:
                if len(node): return False
            elif name in grammar:
                if any(child.tag not in {Q(n) for n in grammar[name]} for child in node): return False
            else: return False
            if name == 'r' and not node.findall(Q('t')): return False
        return True

    def _duplicate_sdt(self, element):
        props = element.find(Q('sdtPr'))
        ids = [] if props is None else props.findall(Q('id'))
        if len(ids) != 1 or not ids[0].get(Q('val')): return True
        root = element.getroottree().getroot()
        value = ids[0].get(Q('val'))
        return sum(x.get(Q('val')) == value for x in root.iter(Q('id'))) != 1

    def _supported(self,e):
        allowed_ancestors = {Q(n) for n in ('document','body','p','tbl','tr','tc','sdt','sdtContent')}
        if any(x.tag not in allowed_ancestors for x in e.iterancestors()): return False
        name = etree.QName(e).localname
        if name == 'r':
            if e.getparent().tag != Q('p') or not self._plain_tree(e.getparent()): return False
        elif name == 'sdt':
            if self._duplicate_sdt(e): return False
            props=e.find(Q('sdtPr')); content=e.find(Q('sdtContent'))
            if content is None or len(e) != 2: return False
            if any(x.tag not in {Q('id'),Q('tag'),Q('alias'),Q('text')} or len(x) for x in props): return False
            if not self._plain_tree(content): return False
        elif name == 'tc':
            row=e.getparent(); table=row.getparent()
            if row.tag != Q('tr') or table is None or table.tag != Q('tbl'): return False
            if any(x.tag in {Q('gridSpan'),Q('vMerge'),Q('hMerge'),Q('tbl')} for x in table.iter() if x is not table): return False
            if len(e.findall(Q('p'))) != 1 or not self._plain_tree(e): return False
        else: return False
        for ancestor in e.iterancestors():
            if ancestor.tag in {Q('sdt'),Q('tc')} and not self._supported(ancestor): return False
        return True

    def _address(self,e):
        if e.tag==Q('r'): return {'kind':'DOCX_RUN','run_path':path_of(e)}
        if e.tag==Q('sdt'): return {'kind':'DOCX_CONTENT_CONTROL','sdt_id':e.find(Q('sdtPr')).find(Q('id')).get(Q('val')),'element_path':path_of(e)}
        row=e.getparent(); table=row.getparent()
        return {'kind':'DOCX_TABLE_CELL','table_path':path_of(table),'row_ordinal':list(table.findall(Q('tr'))).index(row)+1,
            'cell_ordinal':list(row.findall(Q('tc'))).index(e)+1,'cell_path':path_of(e)}

    def discover(self,document):
        result,root,refusal=self._load(document)
        limitations=['PROVISIONAL: native identity is not qualified operation support or semantic fidelity.',
            'UNSUPPORTED: XLSX, headers/footers, bookmarks, nested/merged tables, fields, drawings, revisions, complex SDTs.']
        if refusal: return NativeDiscoveryResult(result.assessment,(),tuple(limitations+[refusal]),result.artifacts+(PROFILE,))
        locators=[]
        for e in root.iter():
            if e.tag not in {Q('r'),Q('tc'),Q('sdt')}: continue
            if e.tag==Q('sdt') and self._duplicate_sdt(e):
                limitations.append('AMBIGUOUS: duplicate or missing SDT identity'); continue
            if not self._supported(e):
                limitations.append('UNSUPPORTED: native structure outside text-only main-body profile'); continue
            address=self._address(e)
            if e.tag==Q('sdt') and (not address['sdt_id'] or sum(x.get(Q('val'))==address['sdt_id'] for x in root.iter(Q('id')))>1):
                limitations.append('AMBIGUOUS: duplicate or missing SDT identity'); continue
            digest=sha256(json.dumps([document.task_id,version_ref(document).model_dump(),address,PROFILE.ref.sha256],sort_keys=True).encode()).hexdigest()
            locators.append(NativeLocator(schema_version='0.1.0',object_type='NativeLocator',id='native-'+digest,revision=1,
                created_at=document.created_at,task_id=document.task_id,document_version_ref=version_ref(document),part_uri='/word/document.xml',
                locator_type=address['kind'],address=address,expected_object_type=e.tag,capture_engine='python-docx/'+docx.__version__,
                structural_fingerprint=fingerprint(e),fingerprint_profile_ref=PROFILE.ref))
        return NativeDiscoveryResult(result.assessment,tuple(locators),tuple(dict.fromkeys(limitations)),result.artifacts+(PROFILE,))

    def resolve(self,document,locator):
        if locator.document_version_ref!=version_ref(document) or locator.task_id!=document.task_id:
            return NativeResolution('STALE_DOCUMENT_VERSION','Locator task/version does not equal requested exact binary')
        if locator.fingerprint_profile_ref!=PROFILE.ref or locator.capture_engine!='python-docx/'+docx.__version__:
            return NativeResolution('UNSUPPORTED','Unknown fingerprint/capture engine profile')
        if locator.part_uri!='/word/document.xml' or locator.locator_type.value not in {'DOCX_RUN','DOCX_CONTENT_CONTROL','DOCX_TABLE_CELL'}:
            return NativeResolution('UNSUPPORTED','Native address outside provisional reader profile')
        try: _,root,refusal=self._load(document)
        except ContentAccessError as exc: return NativeResolution(exc.code.value,str(exc))
        if refusal: return NativeResolution('UNSUPPORTED',refusal)
        # Walk exact root-inclusive QName/ordinal paths, before support/fingerprint.
        address=locator.address
        segments=getattr(address,'run_path',getattr(address,'element_path',getattr(address,'cell_path',None)))
        nodes=[root]
        for index,segment in enumerate(segments):
            tag='{'+segment.namespace_uri+'}'+segment.local_name
            if index==0:
                nodes=[root] if root.tag==tag and segment.ordinal==1 else []
            else:
                nodes=[children[segment.ordinal-1] for node in nodes
                    if len(children:=[x for x in node if x.tag==tag])>=segment.ordinal]
        if not nodes: return NativeResolution('NOT_FOUND','Exact path does not exist')
        if len(nodes)!=1: return NativeResolution('AMBIGUOUS','More than one exact path match')
        e=nodes[0]
        if e.tag==Q('sdt') and self._duplicate_sdt(e):
            return NativeResolution('AMBIGUOUS','SDT identity is missing or duplicated')
        if e.tag!=locator.expected_object_type or not self._supported(e):
            return NativeResolution('UNSUPPORTED','Exact addressed structure is outside supported identity profile')
        if self._address(e)!=address.model_dump(mode='json'):
            return NativeResolution('NOT_FOUND','Conjunctive typed address constraints disagree')
        observed=fingerprint(e)
        if observed!=locator.structural_fingerprint: return NativeResolution('FINGERPRINT_MISMATCH','Exact object structural fingerprint differs',observed)
        return NativeResolution('EXACT_MATCH','One exact version-bound native object; mutation authority is absent',observed,''.join(x.text or '' for x in e.iter(Q('t'))))
