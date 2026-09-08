"""Bounded OOXML package inspection, not semantic parsing or native addressing."""

from collections import Counter
from dataclasses import asdict, dataclass
from io import BytesIO
import posixpath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile
from zlib import error as DecompressionError

from foundation.domain import (
    CapabilityResult, DocumentPreflightAssessment, DocumentVersion, DocumentVersionRef,
    ErrorCode, PreflightFinding,
)
from foundation.ports.content import ContentAccessError, DocumentContentResolverPort, verified_bytes
from .evidence import EvidenceArtifact, PreflightResult

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
WS = 'http://purl.oclc.org/ooxml/wordprocessingml/main'
SS = 'http://purl.oclc.org/ooxml/spreadsheetml/main'
RS = 'http://purl.oclc.org/ooxml/officeDocument/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
MAIN_TYPES = {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml': ('DOCX', 'document'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml': ('XLSX', 'workbook'),
}
OPERATIONS = [('REPLACE_RUN_TEXT','DOCX_RUN','run'), ('REPLACE_SDT_TEXT','DOCX_CONTENT_CONTROL','content_control'), ('REPLACE_SIMPLE_TABLE_CELL_TEXT','DOCX_TABLE_CELL','table_cell')]
# Inspection coverage, not an OOXML validity or support allowlist. Everything
# outside it is retained as unknown, including new constructs in known namespaces.
WORD_KNOWN = set('document body p pPr pStyle r rPr t b i u sz color tbl tblPr tblGrid gridCol tr trPr tc tcPr tcW gridSpan vMerge sectPr pgSz pgMar sdt sdtPr sdtContent id tag alias lock bookmarkStart bookmarkEnd fldSimple fldChar instrText hyperlink ins del delText moveFrom moveTo settings documentProtection trackRevisions styles style name basedOn next qFormat outlineLvl hdr ftr headerReference footerReference drawing pict txbxContent tab br spacing numPr ilvl numId jc keepNext keepLines w type'.split())
SHEET_KNOWN = set('workbook workbookPr bookViews workbookView workbookProtection sheets sheet definedNames definedName calcPr worksheet dimension sheetViews sheetView selection sheetFormatPr cols col sheetData row c f v is t sheetProtection mergeCells mergeCell tableParts tablePart table autoFilter tableColumns tableColumn tableStyleInfo drawing legacyDrawing pageMargins sheetPr pageSetUpPr conditionalFormatting cfRule extLst'.split())
WORD_FINDINGS = {'r':'run','p':'paragraph','tbl':'table','tc':'table_cell','sdt':'content_control','bookmarkStart':'bookmark','fldSimple':'field','fldChar':'field','instrText':'field','ins':'revision','del':'revision','moveFrom':'revision','moveTo':'revision','drawing':'drawing','pict':'drawing','txbxContent':'text_box','hyperlink':'hyperlink','hdr':'header','ftr':'footer'}
SHEET_FINDINGS = {'c':'cell','f':'formula','definedName':'defined_name','table':'table','mergeCell':'merged_cells','drawing':'drawing','sheet':'worksheet'}


@dataclass(frozen=True)
class PreflightConfig:
    """Versioned technical limits; no business freshness or production thresholds."""

    profile_version: str = '1.0.0'
    max_package_bytes: int = 32 * 1024 * 1024
    max_uncompressed_bytes: int = 128 * 1024 * 1024
    max_part_bytes: int = 16 * 1024 * 1024
    max_parts: int = 4096
    max_xml_elements: int = 500000

    def __post_init__(self):
        if self.profile_version != '1.0.0' or any(type(v) is not int or v <= 0 for k,v in asdict(self).items() if k != 'profile_version'):
            raise ValueError('Unknown profile or invalid positive technical limits')


class InspectionFailure(Exception):
    def __init__(self, code, reason): self.code, self.reason = code, reason


class NoDTD(ET.TreeBuilder):
    def doctype(self, *args):
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'DTD declarations are outside the inspection profile')


def qname(tag):
    return tuple(tag[1:].split('}',1)) if tag.startswith('{') else ('',tag)


def part_target(source: str, target: str) -> str:
    uri = urlsplit(target)
    if uri.scheme or uri.netloc or uri.query or uri.fragment or '\\' in target:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Invalid internal relationship target')
    decoded = unquote(uri.path)
    if not decoded or '\\' in decoded:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Empty or invalid relationship target')
    path = posixpath.normpath(decoded.lstrip('/') if decoded.startswith('/') else posixpath.join(posixpath.dirname(source),decoded))
    if path.startswith('../') or path in ('.','..'):
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Relationship escapes package root')
    return path


class OoxmlPreflight:
    engine = 'foundation-ooxml-preflight'
    version = '1.0.0'

    def __init__(self, resolver: DocumentContentResolverPort, config: PreflightConfig | None = None):
        self.resolver, self.config = resolver, config or PreflightConfig()
        self.configuration = EvidenceArtifact.create({'engine':self.engine, 'engine_version':self.version,
            'config':asdict(self.config), 'candidate_engine':'OpenXmlSdk', 'candidate_version':'3.5.1',
            'qualification':'UNQUALIFIED', 'coverage':'all XML element names and relationships; no execution locators'})

    def assess(self, document: DocumentVersion, started: DocumentPreflightAssessment, completed_at: str) -> PreflightResult:
        ref = DocumentVersionRef(document_id=document.document_id, version_id=document.id, binary_hash=document.binary_hash)
        if (started.status.value != 'ASSESSING' or started.task_id != document.task_id or started.document_version_ref != ref
            or started.engine != self.engine or started.engine_version != self.version
            or started.configuration_ref != self.configuration.ref or started.assessor.actor_type.value != 'SYSTEM'
            or completed_at < started.created_at):
            raise ContentAccessError(ErrorCode.INVALID_CONTRACT, 'Preflight request must pin task, version, assessor, configuration and legal assessment state/time')
        data = verified_bytes(document,self.resolver)  # Mandatory before any ZIP/XML inspection.
        artifacts = [self.configuration]
        def evidence(kind, **facts):
            artifact = EvidenceArtifact.create({'document_version_ref':ref.model_dump(mode='json'),
                'input_sha256':document.binary_hash, 'observation_type':kind, 'assessor':self.engine,
                'assessor_version':self.version, 'configuration_ref':self.configuration.ref.model_dump(mode='json'), **facts})
            artifacts.append(artifact)
            return artifact.ref
        try:
            fmt, conf, findings, protection, capabilities, codes, format_ref = self._inspect(data, ref, evidence)
            status='COMPLETED'
        except InspectionFailure as exc:
            fmt, conf, findings, protection, capabilities, codes = None, 'UNKNOWN', [], [], [], [exc.code]
            format_ref=evidence('inspection_failure', error_code=exc.code.value, reason=exc.reason)
            status='FAILED'
        payload = started.model_dump(mode='json', exclude_unset=True)
        payload.update(revision=started.revision+1, created_at=completed_at, assessed_at=completed_at,
            status=status, detected_format=fmt, detected_conformance=conf, native_structure_findings=findings,
            protection_findings=protection, capability_results=capabilities, error_codes=codes,
            format_observation_refs=[format_ref])
        return PreflightResult(DocumentPreflightAssessment.model_validate(payload), tuple(artifacts))

    def _inspect(self, data, ref, evidence):
        cfg=self.config
        if len(data)>cfg.max_package_bytes:
            raise InspectionFailure(ErrorCode.DOCUMENT_TOO_LARGE, 'Configured package byte limit exceeded')
        if not data.startswith(b'PK'):
            raise InspectionFailure(ErrorCode.UNSUPPORTED_FILE_FORMAT, 'Binary is outside the ZIP Office intake profile')
        try:
            with ZipFile(BytesIO(data)) as archive:
                infos=archive.infolist(); names=[i.filename for i in infos]
                if len(infos)>cfg.max_parts or sum(i.file_size for i in infos)>cfg.max_uncompressed_bytes or any(i.file_size>cfg.max_part_bytes for i in infos):
                    raise InspectionFailure(ErrorCode.DOCUMENT_TOO_LARGE, 'Configured expanded package limits exceeded')
                if len(names)!=len(set(names)) or any(n.startswith('/') or '\\' in n or posixpath.normpath(n)!=n or '..' in n.split('/') for n in names):
                    raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Duplicate or noncanonical package part')
                if any(i.flag_bits & 1 for i in infos):
                    raise InspectionFailure(ErrorCode.ENCRYPTED_DOCUMENT, 'Encrypted ZIP member')
                parts={i.filename:archive.read(i) for i in infos}
        except (BadZipFile, DecompressionError, RuntimeError, NotImplementedError, EOFError, OSError) as exc:
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Unreadable ZIP structure or CRC') from exc
        try:
            xml={}
            for name, blob in sorted(parts.items()):
                if name.endswith(('.xml','.rels')):
                    xml[name]=ET.fromstring(blob,parser=ET.XMLParser(target=NoDTD()))
            if sum(sum(1 for _ in root.iter()) for root in xml.values())>cfg.max_xml_elements:
                raise InspectionFailure(ErrorCode.DOCUMENT_TOO_LARGE, 'Configured XML element limit exceeded')
            types=xml['[Content_Types].xml']; root_rels=xml['_rels/.rels']
            if types.tag != f'{{{CT}}}Types' or root_rels.tag != f'{{{P}}}Relationships':
                raise ValueError('Unexpected OPC roots')
            overrides={}
            for item in types:
                if item.tag==f'{{{CT}}}Override':
                    name=item.attrib['PartName'].lstrip('/')
                    if name in overrides or name not in parts: raise ValueError('Invalid override')
                    overrides[name]=item.attrib['ContentType']
            mains=[x for x in root_rels if x.get('Type') in (R+'/officeDocument',RS+'/officeDocument')]
            if len(mains)!=1 or mains[0].get('TargetMode','Internal')!='Internal': raise ValueError('Missing/ambiguous main part')
            main=part_target('',mains[0].attrib['Target'])
            main_type=overrides.get(main)
            if main_type not in MAIN_TYPES:
                raise InspectionFailure(ErrorCode.UNSUPPORTED_FILE_FORMAT, 'Main content type is outside DOCX/XLSX profile')
            fmt,root_name=MAIN_TYPES[main_type]
            if qname(xml[main].tag)[1]!=root_name: raise ValueError('Main XML root disagrees with content type')
            rel_observations=[]; classes=set()
            for name,root in xml.items():
                if name.endswith('.rels'):
                    if root.tag!=f'{{{P}}}Relationships': raise ValueError('Invalid relationship part root')
                    source='' if name=='_rels/.rels' else posixpath.join(posixpath.dirname(posixpath.dirname(name)),posixpath.basename(name)[:-5])
                    if source and source not in parts: raise ValueError('Missing relationship source')
                    ids=set()
                    for rel in root:
                        if rel.tag!=f'{{{P}}}Relationship' or not {'Id','Type','Target'} <= rel.attrib.keys() or rel.attrib['Id'] in ids: raise ValueError('Malformed relationship')
                        ids.add(rel.attrib['Id']); kind=rel.attrib['Type']; mode=rel.get('TargetMode','Internal')
                        if mode not in ('Internal','External'): raise ValueError('Invalid relationship mode')
                        if mode=='Internal' and part_target(source,rel.attrib['Target']) not in parts: raise ValueError('Missing relationship target')
                        if kind.startswith(R+'/'): classes.add('TRANSITIONAL')
                        elif kind.startswith(RS+'/'): classes.add('STRICT')
                        rel_observations.append({'part':name,'type':kind,'external':mode=='External'})
                for node in root.iter():
                    # Used attribute namespaces are evidence too. Unqualified
                    # attributes and xml:space do not establish OOXML conformance.
                    namespaces={qname(node.tag)[0]}
                    namespaces.update(qname(attr)[0] for attr in node.attrib if qname(attr)[0])
                    for ns in namespaces:
                        if ns in (W,S,R) or ns.startswith('http://schemas.openxmlformats.org/drawingml/'):
                            classes.add('TRANSITIONAL')
                        elif ns in (WS,SS,RS) or ns.startswith('http://purl.oclc.org/ooxml/drawingml/'):
                            classes.add('STRICT')
                        elif ns not in (P,CT,'http://www.w3.org/XML/1998/namespace') and not ns.startswith(('http://schemas.microsoft.com/office/', 'http://schemas.openxmlformats.org/markup-compatibility/', 'http://schemas.openxmlformats.org/officeDocument/2006/math', 'urn:schemas-microsoft-com:')):
                            classes.add('UNKNOWN')
            main_ns=qname(xml[main].tag)[0]
            expected_ns=(W,WS) if fmt=='DOCX' else (S,SS)
            conf=next(iter(classes)) if len(classes)==1 and main_ns in expected_ns else 'UNKNOWN'
        except (ET.ParseError, KeyError, ValueError) as exc:
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Malformed or inconsistent OPC/XML package') from exc
        findings=[]; protections=[]; codes=set(); observed=set(); global_protected=False
        def finding(kind,name,facts,protected=False):
            obs=evidence(kind, part=name, **facts)
            f=PreflightFinding(finding_id='finding-'+obs.sha256, native_object_type=kind, part_uri='/'+name,
                native_locator_refs=[], observation_ref=obs, description=f'{kind} observed in package part; inspection is not native execution identity')
            (protections if protected else findings).append(f)
            observed.add(kind)
        for name,root in sorted(xml.items()):
            counts=Counter(node.tag for node in root.iter())
            finding('xml_inventory',name,{'element_counts':dict(sorted(counts.items()))})
            for tag,count in sorted(counts.items()):
                ns,local=qname(tag)
                mapping=WORD_FINDINGS if ns in (W,WS) else SHEET_FINDINGS if ns in (S,SS) else {}
                if local in mapping: finding(mapping[local],name,{'qname':tag,'count':count})
                known=(local in WORD_KNOWN if ns in (W,WS) else local in SHEET_KNOWN if ns in (S,SS) else ns in (P,CT))
                if not known:
                    finding('unknown_structure',name,{'qname':tag,'count':count})
                    codes.add(ErrorCode.UNSUPPORTED_NATIVE_OBJECT)
            for node in root.iter():
                ns,local=qname(node.tag); attrs={qname(k)[1]:v for k,v in node.attrib.items()}
                # Never export passwords, formula/text contents or hyperlink targets.
                if ns in (W,WS) and local=='documentProtection':
                    enforcement=attrs.get('enforcement','false')
                    if enforcement in ('1','true','on'):
                        global_protected=True; finding('document_protection',name,{'enforcement':True},True)
                    elif enforcement not in ('0','false','off'):
                        finding('unknown_structure',name,{'reason':'unrecognized protection enforcement'}); codes.add(ErrorCode.UNSUPPORTED_NATIVE_OBJECT)
                if ns in (W,WS) and local=='lock' and attrs.get('val') in ('sdtLocked','contentLocked','sdtContentLocked'):
                    finding('content_control_lock',name,{'lock':attrs['val']},True)
                if ns in (S,SS) and local in ('workbookProtection','sheetProtection'):
                    keys=('lockStructure','lockWindows','lockRevision') if local=='workbookProtection' else ('sheet',)
                    active={k:attrs[k] for k in keys if attrs.get(k) in ('1','true','on')}
                    if active: finding('workbook_protection' if local=='workbookProtection' else 'worksheet_protection',name,{'flags':active},True)
        for name in sorted({r['part'] for r in rel_observations}):
            finding('relationship',name,{'relationships':[r for r in rel_observations if r['part']==name]})
        for name in sorted(parts.keys()-xml.keys()):
            finding('uninspected_binary_part',name,{'byte_length':len(parts[name])})
            codes.add(ErrorCode.UNSUPPORTED_NATIVE_OBJECT)
        capabilities=[]
        if conf=='STRICT': codes.add(ErrorCode.STRICT_OOXML_MUTATION_UNQUALIFIED)
        if conf=='UNKNOWN': codes.add(ErrorCode.CAPABILITY_UNKNOWN)
        if fmt=='DOCX':
            for operation,structure,kind in OPERATIONS:
                status='UNSUPPORTED' if conf=='STRICT' or kind not in observed else 'PROTECTED' if global_protected else 'UNKNOWN'
                code={'UNKNOWN':ErrorCode.CAPABILITY_UNKNOWN,'UNSUPPORTED':ErrorCode.EXECUTION_UNSUPPORTED,'PROTECTED':ErrorCode.PROTECTED_OBJECT}[status]
                codes.add(code)
                reason='Strict mutation is unqualified' if conf=='STRICT' else 'Structure absent' if kind not in observed else 'Enforced document-wide protection' if global_protected else 'Replay qualification and exact native locator remain open'
                capabilities.append(CapabilityResult(capability_result_id=operation.lower(), operation=operation,
                    native_structure=structure, document_version_ref=ref, native_locator_refs=[], engine='OpenXmlSdk',
                    engine_version='3.5.1', conformance=conf, qualification_evidence_refs=[],status=status,reason=reason))
        else:
            codes.add(ErrorCode.EXECUTION_UNSUPPORTED)  # No XLSX MutationOperation in v0.1.
        format_ref=evidence('format_and_coverage', main_part=main, main_content_type=main_type,
            detected_format=fmt, conformance=conf, namespace_classes=sorted(classes), package_parts=sorted(parts),
            inspected_xml_parts=sorted(xml), mutation_qualification=False, native_locators_created=False,
            schema_validation_performed=False, candidate_policy='OpenXmlSdk 3.5.1 is provisional; frozen DOCX operations only')
        return fmt,conf,findings,protections,capabilities,sorted(codes,key=lambda c:c.value),format_ref
