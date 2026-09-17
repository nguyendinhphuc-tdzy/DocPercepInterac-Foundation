"""Read-only template candidates for mapping review, never execution support.

Reuses B1's verified bytes, resource-safe preflight, external python-docx loader,
QName addresses and independent re-resolution. UNKNOWN package conformance is
retained as a limitation; only Transitional main-body objects are addressed.
"""
from hashlib import sha256
import json
import re
import docx
from lxml import etree
from foundation.adapters.native_identity import DocxNativeIdentity, Q, W, fingerprint, version_ref
from foundation.adapters.preflight.evidence import EvidenceArtifact
from foundation.applications.gtps_mapping.planner import NativeResult, verify_view
from foundation.domain import NativeLocator

REVIEW_PROPERTIES = {'b','i','u','sz','szCs','color','rFonts','rStyle','highlight','lang',
    'pStyle','jc','spacing','keepNext','keepLines','cnfStyle','tcW','vAlign',
    'top','left','bottom','right','insideH','insideV'}
REVIEW_GRAMMAR = {'tc': {'tcPr','p'}, 'tcPr': {'tcW','vAlign','tcBorders','cnfStyle'},
    'tcBorders': {'top','left','bottom','right','insideH','insideV'},
    'p': {'pPr','r'}, 'pPr': {'pStyle','jc','spacing','keepNext','keepLines','cnfStyle','rPr'},
    'r': {'rPr','t'}, 'rPr': {'b','i','u','sz','szCs','color','rFonts','rStyle','highlight','lang'}}


class ReviewNativeIdentity(DocxNativeIdentity):
    identity_conformances = {'TRANSITIONAL', 'UNKNOWN'}
    profile = EvidenceArtifact.create({
        'profile': 'b21r-formatted-text-identity-v1', 'qualification': 'PROVISIONAL_REVIEW_ONLY',
        'fingerprint': 'SHA256 inclusive C14N 1.0 subtree without comments',
        'address': 'root-inclusive QName and same-QName one-based ordinal',
        'engine': 'python-docx', 'engine_version': docx.__version__,
        'canonicalizer_version': etree.LXML_VERSION,
        'scope': 'Transitional main-body plain runs and unmerged single-paragraph table cells; allowlisted formatting',
        'conformance': 'UNKNOWN package conformance permitted for read-only identity; no mutation support',
        'refusals': 'fields, bookmarks, protection, nested/merged tables, SDTs, drawings, revisions, unknown text constructs',
        'native_dom_max_expanded_bytes': 8*1024*1024,
        'grammar': {k: sorted(v) for k,v in REVIEW_GRAMMAR.items()},
        'leaf_properties': sorted(REVIEW_PROPERTIES),
    })

    def _plain_tree(self, element):
        props = REVIEW_PROPERTIES
        grammar = REVIEW_GRAMMAR
        for n in element.iter():
            if not isinstance(n.tag,str) or not n.tag.startswith('{'+W+'}'):
                return False
            name=etree.QName(n).localname
            if name in props or name=='t':
                if len(n):return False
            elif name in grammar:
                if any(c.tag not in {Q(v) for v in grammar[name]} for c in n):return False
            else:return False
        return True

    def _supported(self, e):
        if e.tag not in {Q('r'),Q('tc')}:return False
        if any(a.tag not in {Q(n) for n in ('document','body','p','tbl','tr','tc')} for a in e.iterancestors()):return False
        if sum(a.tag==Q('tbl') for a in e.iterancestors())>1:return False
        return super()._supported(e)


def text_of(e):
    return ''.join(n.text or '' for n in e.iter(Q('t')))


def semantic_grid(table):
    d=table['data'];grid={}
    for c in d['table_cells']:
        if c.get('row_span',1)!=1 or c.get('col_span',1)!=1:return None
        key=(c['start_row_offset_idx'],c['start_col_offset_idx'])
        if key in grid:return None
        grid[key]=c['text'].strip()
    if len(grid)!=d['num_rows']*d['num_cols']:return None
    return [[grid[(r,c)] for c in range(d['num_cols'])] for r in range(d['num_rows'])]


class TemplateNativeCandidates:
    def __init__(self, document, resolver):
        self.document=document
        self.identity=ReviewNativeIdentity(resolver)
        self.preflight_summary=None

    def _capture(self, e, target):
        address=self.identity._address(e)
        key=sha256(json.dumps([self.document.task_id,target.version.model_dump(mode='json'),address,self.identity.profile.ref.sha256],sort_keys=True).encode()).hexdigest()
        return NativeLocator(schema_version='0.1.0',object_type='NativeLocator',id='native-'+key,revision=1,
            created_at=self.document.created_at,task_id=self.document.task_id,document_version_ref=target.version,
            part_uri='/word/document.xml',locator_type=address['kind'],address=address,expected_object_type=e.tag,
            capture_engine='python-docx/'+docx.__version__,structural_fingerprint=fingerprint(e),fingerprint_profile_ref=self.identity.profile.ref)

    def heading_candidates(self, target, semantic_heading, native_heading):
        """Navigation identities only. No heading replacement proposal is made."""
        from foundation.applications.gtps_mapping.template_resolution import unique_heading
        from foundation.applications.gtps_mapping.planner import MappingError
        output={'status':'REVIEW_REQUIRED','native_locators':[],'executable':False,
                'warning':'Heading identifies detailed context; deterministic narrative payload is not configured.'}
        verify_view(target)
        if target.role!='TARGET_TEMPLATE' or target.version!=version_ref(self.document):
            return {**output,'status':'STALE_DOCUMENT_VERSION'}
        try:output['semantic_pointer']=unique_heading(target,semantic_heading)
        except MappingError as exc:return {**output,'status':exc.code}
        if re.sub(r'^\d+(?:\.\d+)*\s+','',semantic_heading)!=native_heading:
            return {**output,'status':'TARGET_NOT_FOUND'}
        _,root,refusal=self.identity._load(self.document)
        if refusal:return {**output,'status':'UNSUPPORTED'}
        matches=[p for p in root.find(Q('body')).findall(Q('p')) if text_of(p)==native_heading]
        if len(matches)!=1:return {**output,'status':'TARGET_AMBIGUOUS' if matches else 'TARGET_NOT_FOUND'}
        runs=[r for r in matches[0].findall(Q('r')) if text_of(r)]
        if not runs or not all(self.identity._supported(r) for r in runs):return {**output,'status':'UNSUPPORTED'}
        locators=[self._capture(r,target) for r in runs]
        if not all(self.identity.resolve(self.document,l).status=='EXACT_MATCH' for l in locators):
            return {**output,'status':'UNSUPPORTED'}
        return {**output,'status':'RESOLVED','native_locators':[l.model_dump(mode='json') for l in locators]}

    def resolve(self, slot, target):
        verify_view(target)
        def refused(code):return NativeResult(status=code)
        if target.role!='TARGET_TEMPLATE':return refused('ROLE_NOT_PERMITTED')
        if target.version!=version_ref(self.document):return refused('STALE_NATIVE_LOCATOR')
        result,root,refusal=self.identity._load(self.document)
        assessment=result.assessment
        self.preflight_summary=dict(status=assessment.status.value,conformance=assessment.detected_conformance.value,
            protection_findings=len(assessment.protection_findings),engine=assessment.engine,engine_version=assessment.engine_version,
            configuration_ref=assessment.configuration_ref.model_dump(mode='json'),mutation_qualified=False)
        if refusal:return refused('NATIVE_STRUCTURE_UNSUPPORTED')
        match=re.fullmatch(r'/tables/(\d+)/data/table_cells/(\d+)/text',slot.pointer)
        if not match:return refused('NATIVE_STRUCTURE_UNSUPPORTED')
        table=target.data['tables'][int(match[1])]
        expected=semantic_grid(table)
        if expected is None:return refused('NATIVE_STRUCTURE_UNSUPPORTED')
        candidates=[]
        # Whole-table identity + exact cell coordinates, never global text search
        # for an empty/xxx cell or assumed Docling-index == Word-index.
        for t in root.find(Q('body')).findall(Q('tbl')):
            grid=[[text_of(c).strip() for c in row.findall(Q('tc'))] for row in t.findall(Q('tr'))]
            if grid==expected:candidates.append(t)
        if len(candidates)!=1:return refused('TARGET_AMBIGUOUS' if candidates else 'TARGET_NOT_FOUND')
        cell=table['data']['table_cells'][int(match[2])]
        e=candidates[0].findall(Q('tr'))[cell['start_row_offset_idx']].findall(Q('tc'))[cell['start_col_offset_idx']]
        if not self.identity._supported(e):return refused('NATIVE_STRUCTURE_UNSUPPORTED')
        locator=self._capture(e,target)
        # Reload and recheck the actual bytes, typed address and fingerprint.
        checked=self.identity.resolve(self.document,locator)
        if checked.status!='EXACT_MATCH':return refused(checked.status)
        return NativeResult((locator,),checked.structural_fingerprint,checked.text,False,slot.region.id,slot.pointer,'EXACT_MATCH',cell['text'])
