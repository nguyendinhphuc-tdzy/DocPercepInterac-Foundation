from hashlib import sha256
import pytest
from foundation.domain import DocumentVersion, NativeLocator
from foundation.adapters.native_identity import DocxNativeIdentity
from tools.b1.build_corpus import docx_parts, xlsx_parts, package, W

class Resolver:
    def __init__(self, data): self.data = data
    def resolve(self, document): return self.data

def fixture(body=None):
    parts = docx_parts()
    if body is not None:
        parts['word/document.xml'] = f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    data = package(parts)
    digest = sha256(data).hexdigest()
    doc = DocumentVersion(schema_version='0.1.0', object_type='DocumentVersion', id='v1', revision=1,
        created_at='2026-09-15T00:00:00Z', task_id='t1', document_id='d1', binary_hash=digest,
        byte_length=len(data), content_ref={'uri':'urn:test:doc', 'sha256':digest,'media_type':'application/octet-stream'})
    return doc, Resolver(data)

RUN = '<w:p><w:r><w:t>Hello</w:t></w:r></w:p>'
SDT = '<w:sdt><w:sdtPr><w:id w:val="7"/></w:sdtPr><w:sdtContent>'+RUN+'</w:sdtContent></w:sdt>'
TABLE = '<w:tbl><w:tr><w:tc>'+RUN+'</w:tc></w:tr></w:tbl>'

@pytest.mark.parametrize('body,kind', [(RUN,'DOCX_RUN'),(SDT,'DOCX_CONTENT_CONTROL'),(TABLE,'DOCX_TABLE_CELL')])
def test_exact_deterministic_no_mutation(body, kind):
    doc,resolver=fixture(body); adapter=DocxNativeIdentity(resolver)
    before=resolver.data; first=adapter.discover(doc)
    assert first == adapter.discover(doc)
    candidates=[x for x in first.native_locators if x.locator_type.value==kind]
    assert len(candidates)==1
    locator=NativeLocator.model_validate(candidates[0].model_dump(mode='json'))
    result=adapter.resolve(doc,locator)
    assert result.status=='EXACT_MATCH' and result.text=='Hello'
    assert result.structural_fingerprint==locator.structural_fingerprint
    assert resolver.data==before
    assert all(x.status.value!='SUPPORTED' for x in first.preflight_assessment.capability_results)

@pytest.mark.parametrize('field,value,status', [('structural_fingerprint','0'*64,'FINGERPRINT_MISMATCH'),('expected_object_type','wrong','UNSUPPORTED'),('part_uri','/word/header1.xml','UNSUPPORTED')])
def test_refusals(field,value,status):
    doc,resolver=fixture(RUN); a=DocxNativeIdentity(resolver); loc=a.discover(doc).native_locators[0]
    assert a.resolve(doc,loc.model_copy(update={field:value})).status==status

def test_stale_and_not_found():
    doc,resolver=fixture(RUN); a=DocxNativeIdentity(resolver); loc=a.discover(doc).native_locators[0]
    changed=loc.address.model_copy(update={'run_path':[*loc.address.run_path[:-1],loc.address.run_path[-1].model_copy(update={'ordinal':99})]})
    assert a.resolve(doc,loc.model_copy(update={'address':changed})).status=='NOT_FOUND'
    assert a.resolve(doc.model_copy(update={'id':'v2'}),loc).status=='STALE_DOCUMENT_VERSION'
    resolver.data+=b'changed'
    assert a.resolve(doc,loc).status=='STALE_DOCUMENT_VERSION'

def test_duplicate_sdt_refused():
    doc,resolver=fixture(SDT+SDT); a=DocxNativeIdentity(resolver)
    discovered=a.discover(doc)
    assert not any(x.locator_type.value=='DOCX_CONTENT_CONTROL' for x in discovered.native_locators)
    assert any('AMBIGUOUS' in x for x in discovered.limitations)

@pytest.mark.parametrize('body', ['<w:tbl><w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>'+RUN+'</w:tc></w:tr></w:tbl>', '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r></w:p>', '<w:ins>'+RUN+'</w:ins>'])
def test_complex_structures_refused(body):
    doc,resolver=fixture(body); result=DocxNativeIdentity(resolver).discover(doc)
    assert not result.native_locators
    assert result.limitations

@pytest.mark.parametrize('body', [
    '<w:tbl><w:tr><w:tc><w:p><w:hyperlink><w:r><w:t>Hello</w:t></w:r></w:hyperlink></w:p></w:tc></w:tr></w:tbl>',
    '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:t>Hello</w:t></w:r></w:p>',
    SDT+SDT,
    '<w:p><w:pPr><w:rPr><w:del/></w:rPr></w:pPr><w:r><w:t>Hello</w:t></w:r></w:p>',
])
def test_unsupported_context_cannot_leak_child_identity(body):
    doc,resolver=fixture(body)
    assert not DocxNativeIdentity(resolver).discover(doc).native_locators

def test_existing_unsupported_exact_address_is_not_missing():
    from foundation.adapters.native_identity import path_of, PROFILE, version_ref
    doc,resolver=fixture('<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r></w:p>')
    a=DocxNativeIdentity(resolver); _,root,_=a._load(doc)
    e=next(root.iter('{'+W+'}r'))
    import docx
    loc=NativeLocator(schema_version='0.1.0',object_type='NativeLocator',id='unsupported',revision=1,
        created_at=doc.created_at,task_id=doc.task_id,document_version_ref=version_ref(doc),part_uri='/word/document.xml',
        locator_type='DOCX_RUN',address={'kind':'DOCX_RUN','run_path':path_of(e)},expected_object_type=e.tag,
        capture_engine='python-docx/'+docx.__version__,structural_fingerprint='0'*64,fingerprint_profile_ref=PROFILE.ref)
    assert a.resolve(doc,loc).status=='UNSUPPORTED'

def test_duplicate_sdt_exact_resolution_is_ambiguous():
    from foundation.adapters.native_identity import version_ref
    doc,resolver=fixture(SDT); a=DocxNativeIdentity(resolver)
    loc=next(x for x in a.discover(doc).native_locators if x.locator_type.value=='DOCX_CONTENT_CONTROL')
    duplicate,other=fixture(SDT+SDT)
    loc=loc.model_copy(update={'document_version_ref':version_ref(duplicate)})
    assert DocxNativeIdentity(other).resolve(duplicate,loc).status=='AMBIGUOUS'

def test_table_conjunctive_coordinates_are_checked():
    doc,resolver=fixture(TABLE); a=DocxNativeIdentity(resolver)
    loc=next(x for x in a.discover(doc).native_locators if x.locator_type.value=='DOCX_TABLE_CELL')
    wrong=loc.model_copy(update={'address':loc.address.model_copy(update={'row_ordinal':2})})
    assert a.resolve(doc,wrong).status=='NOT_FOUND'

def test_xlsx_explicitly_refused():
    data=package(xlsx_parts()); doc,_=fixture()
    digest=sha256(data).hexdigest()
    doc=doc.model_copy(update={'binary_hash':digest,'byte_length':len(data),
        'content_ref':doc.content_ref.model_copy(update={'sha256':digest})})
    result=DocxNativeIdentity(Resolver(data)).discover(doc)
    assert not result.native_locators
    assert any('XLSX' in x for x in result.limitations)

def test_preflight_refusal_never_invokes_external_reader(monkeypatch):
    from foundation.adapters.preflight import PreflightConfig
    import docx
    doc,resolver=fixture(RUN)
    def forbidden(*args,**kwargs): raise AssertionError('reader invoked after failed preflight')
    monkeypatch.setattr(docx,'Document',forbidden)
    result=DocxNativeIdentity(resolver,PreflightConfig(max_package_bytes=1)).discover(doc)
    assert result.preflight_assessment.status.value=='FAILED'
    assert not result.native_locators

def test_fingerprint_profile_bytes_and_unknown_profile_refusal():
    doc,resolver=fixture(RUN); a=DocxNativeIdentity(resolver); result=a.discover(doc)
    loc=result.native_locators[0]
    artifact=next(x for x in result.artifacts if x.ref==loc.fingerprint_profile_ref)
    assert sha256(artifact.data).hexdigest()==artifact.ref.sha256
    wrong=loc.model_copy(update={'fingerprint_profile_ref':loc.fingerprint_profile_ref.model_copy(update={'sha256':'0'*64})})
    assert a.resolve(doc,wrong).status=='UNSUPPORTED'
