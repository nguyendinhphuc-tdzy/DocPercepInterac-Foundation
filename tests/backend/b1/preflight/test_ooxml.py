from dataclasses import replace
from hashlib import sha256
import json

import pytest

from foundation.domain import DocumentVersion, DocumentPreflightAssessment, ErrorCode
from foundation.ports.content import ContentAccessError
from foundation.adapters.preflight import OoxmlPreflight, PreflightConfig
from tools.b1.build_corpus import W, S, R, content_types, docx_parts, xlsx_parts, package


def document(data):
    digest = sha256(data).hexdigest()
    return DocumentVersion(schema_version='0.1.0', object_type='DocumentVersion', id='version-b1', revision=1,
        created_at='2026-09-08T00:00:00Z', task_id='task-b1', document_id='document-b1', binary_hash=digest,
        byte_length=len(data), content_ref={'uri':'urn:test:binary', 'sha256':digest, 'media_type':'application/octet-stream'})


class Resolver:
    def __init__(self, data): self.data = data
    def resolve(self, doc): return self.data


def started(doc, adapter):
    return DocumentPreflightAssessment(schema_version='0.1.0', object_type='DocumentPreflightAssessment',
        id='preflight-b1', revision=2, created_at='2026-09-08T00:00:01Z', task_id=doc.task_id,
        document_version_ref={'document_id':doc.document_id, 'version_id':doc.id, 'binary_hash':doc.binary_hash},
        status='ASSESSING', detected_format=None, detected_conformance='UNKNOWN', format_observation_refs=[],
        protection_findings=[], native_structure_findings=[], capability_results=[],
        assessor={'actor_type':'SYSTEM', 'actor_id':'preflight-service'}, engine=adapter.engine,
        engine_version=adapter.version, configuration_ref=adapter.configuration.ref, assessed_at=None, error_codes=[])


def run(data, config=None):
    doc = document(data)
    adapter = OoxmlPreflight(Resolver(data), config or PreflightConfig())
    return adapter.assess(doc, started(doc, adapter), '2026-09-08T00:00:02Z')


@pytest.mark.parametrize('builder,fmt', [(docx_parts,'DOCX'),(xlsx_parts,'XLSX')])
def test_package_detection_and_deterministic_evidence(builder, fmt):
    data = package(builder())
    first, second = run(data), run(data)
    assert first == second
    a = first.assessment
    assert a.status.value == 'COMPLETED'
    assert a.detected_format.value == fmt
    assert a.detected_conformance.value == 'TRANSITIONAL'
    assert a.revision == 3
    refs = [*a.format_observation_refs, a.configuration_ref,
            *(f.observation_ref for f in a.native_structure_findings + a.protection_findings)]
    by_digest = {x.ref.sha256:x for x in first.artifacts}
    for ref in refs:
        assert sha256(by_digest[ref.sha256].data).hexdigest() == ref.sha256
    assert all(c.status.value != 'SUPPORTED' for c in a.capability_results)
    assert all(c.document_version_ref == a.document_version_ref for c in a.capability_results)
    assert all(not f.native_locator_refs for f in a.native_structure_findings + a.protection_findings)


def test_misleading_mime_cannot_override_binary_detection():
    data = package(xlsx_parts())
    doc = document(data)
    doc = doc.model_copy(update={'content_ref':doc.content_ref.model_copy(update={'media_type':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'})})
    adapter = OoxmlPreflight(Resolver(data))
    assert adapter.assess(doc, started(doc, adapter), '2026-09-08T00:00:02Z').assessment.detected_format.value == 'XLSX'


def test_misleading_extension_cannot_override_binary_detection(tmp_path):
    path = tmp_path / 'misleading.docx'
    path.write_bytes(package(xlsx_parts()))
    assert run(path.read_bytes()).assessment.detected_format.value == 'XLSX'


@pytest.mark.parametrize('data', [b'PK\x03\x04broken', package({'[Content_Types].xml':'<broken>'}), package({'a.xml':'<x/>'})])
def test_malformed_fails_closed(data):
    a = run(data).assessment
    assert a.status.value == 'FAILED'
    assert ErrorCode.CORRUPTED_DOCUMENT in a.error_codes
    assert not a.capability_results


def test_corrupt_deflate_stream_returns_structured_failure():
    from io import BytesIO
    from struct import unpack_from
    from zipfile import ZipFile, ZIP_DEFLATED

    stream = BytesIO()
    with ZipFile(stream, 'w', compression=ZIP_DEFLATED) as archive:
        for name, content in docx_parts().items():
            archive.writestr(name, content)
    damaged = bytearray(stream.getvalue())
    name_length, extra_length = unpack_from('<HH', damaged, 26)
    data_offset = 30 + name_length + extra_length
    damaged[data_offset] |= 7  # Reserved DEFLATE block type; valid ZIP envelope.
    assessment = run(bytes(damaged)).assessment
    assert assessment.status.value == 'FAILED'
    assert assessment.error_codes == [ErrorCode.CORRUPTED_DOCUMENT]
    assert not assessment.capability_results


def test_hash_mismatch_blocks_before_inspection(monkeypatch):
    doc = document(package(docx_parts()))
    adapter = OoxmlPreflight(Resolver(b'wrong bytes'))
    monkeypatch.setattr(adapter, '_inspect', lambda *args: pytest.fail('inspection occurred before hash verification'))
    with pytest.raises(ContentAccessError) as exc:
        adapter.assess(doc, started(doc, adapter), '2026-09-08T00:00:02Z')
    assert exc.value.code is ErrorCode.STALE_DOCUMENT_VERSION


@pytest.mark.parametrize('conformance', ['STRICT','UNKNOWN','MIXED'])
def test_conformance_never_guesses_support(conformance):
    parts = docx_parts()
    if conformance == 'STRICT':
        parts = {k:v.replace(W,'http://purl.oclc.org/ooxml/wordprocessingml/main').replace(R,'http://purl.oclc.org/ooxml/officeDocument/relationships') for k,v in parts.items()}
    elif conformance == 'UNKNOWN':
        parts['word/document.xml'] = parts['word/document.xml'].replace(W,'urn:unknown:word')
    else:
        parts['word/styles.xml'] = parts['word/styles.xml'].replace(W,'http://purl.oclc.org/ooxml/wordprocessingml/main')
    a = run(package(parts)).assessment
    assert a.detected_conformance.value == ('STRICT' if conformance == 'STRICT' else 'UNKNOWN')
    assert all(c.status.value != 'SUPPORTED' for c in a.capability_results)
    if conformance == 'STRICT':
        assert ErrorCode.STRICT_OOXML_MUTATION_UNQUALIFIED in a.error_codes
        assert all(c.status.value == 'UNSUPPORTED' for c in a.capability_results)


@pytest.mark.parametrize('namespace', ['urn:unqualified:attribute', 'http://purl.oclc.org/ooxml/wordprocessingml/main'])
def test_mixed_or_unknown_attribute_namespace_remains_unknown(namespace):
    parts = docx_parts()
    parts['word/document.xml'] = parts['word/document.xml'].replace(
        '<w:body>', f'<w:body xmlns:other="{namespace}" other:flag="1">')
    assessment = run(package(parts)).assessment
    assert assessment.detected_conformance.value == 'UNKNOWN'
    assert all(c.status.value != 'SUPPORTED' for c in assessment.capability_results)


def test_docx_native_edges_are_observed():
    a = run(package(docx_parts(True))).assessment
    kinds = {f.native_object_type for f in a.native_structure_findings}
    assert {'content_control','bookmark','field','table','revision','relationship'} <= kinds
    assert 'content_control_lock' in {f.native_object_type for f in a.protection_findings}


@pytest.mark.parametrize('enforcement,protected', [('1',True),('true',True),('0',False),('false',False)])
def test_document_protection_is_scope_specific(enforcement, protected):
    parts=docx_parts()
    parts['word/settings.xml']=f'<w:settings xmlns:w="{W}"><w:documentProtection w:enforcement="{enforcement}" w:edit="readOnly"/></w:settings>'
    a=run(package(parts)).assessment
    assert bool(a.protection_findings) == protected
    if protected:
        assert {c.native_structure.value:c.status.value for c in a.capability_results} == {
            'DOCX_RUN':'PROTECTED', 'DOCX_TABLE_CELL':'PROTECTED', 'DOCX_CONTENT_CONTROL':'UNSUPPORTED'}


def test_xlsx_structures_and_protection():
    parts=xlsx_parts()
    parts['xl/workbook.xml']=parts['xl/workbook.xml'].replace('<sheets>', '<workbookProtection lockStructure="1"/><sheets>')
    parts['xl/worksheets/sheet1.xml']=parts['xl/worksheets/sheet1.xml'].replace('<tableParts', '<sheetProtection sheet="1"/><tableParts')
    a=run(package(parts)).assessment
    assert {'formula','defined_name','table','merged_cells'} <= {f.native_object_type for f in a.native_structure_findings}
    assert {'workbook_protection','worksheet_protection'} <= {f.native_object_type for f in a.protection_findings}
    assert a.capability_results == []  # Frozen operations are DOCX-only.
    assert ErrorCode.EXECUTION_UNSUPPORTED in a.error_codes


def test_unknown_construct_is_not_dropped():
    parts=docx_parts()
    parts['word/document.xml']=parts['word/document.xml'].replace('<w:body>','<w:body><w:futureObject/>')
    a=run(package(parts)).assessment
    assert 'unknown_structure' in {f.native_object_type for f in a.native_structure_findings}
    assert ErrorCode.UNSUPPORTED_NATIVE_OBJECT in a.error_codes
    assert all(c.status.value != 'SUPPORTED' for c in a.capability_results)


def test_dtd_and_external_entities_are_refused():
    parts=docx_parts()
    parts['word/document.xml']='<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///secret">]>' + parts['word/document.xml']
    assert ErrorCode.CORRUPTED_DOCUMENT in run(package(parts)).assessment.error_codes


def test_configured_limits_are_enforced():
    a=run(package(docx_parts()), replace(PreflightConfig(), max_package_bytes=10)).assessment
    assert ErrorCode.DOCUMENT_TOO_LARGE in a.error_codes


def test_missing_relationship_target_is_corruption():
    parts=docx_parts(); del parts['word/styles.xml']
    assert ErrorCode.CORRUPTED_DOCUMENT in run(package(parts)).assessment.error_codes


def test_request_must_bind_task_version_and_assessor():
    data=package(docx_parts()); doc=document(data); adapter=OoxmlPreflight(Resolver(data))
    with pytest.raises(ContentAccessError) as exc:
        adapter.assess(doc, started(doc,adapter).model_copy(update={'task_id':'foreign'}), '2026-09-08T00:00:02Z')
    assert exc.value.code is ErrorCode.INVALID_CONTRACT
