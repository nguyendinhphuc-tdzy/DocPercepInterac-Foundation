"""Synthetic-only safety and accepted-v1 semantic equivalence requirements."""
from dataclasses import asdict, replace
from io import BytesIO
import json
from struct import pack_into, unpack_from
import warnings
from xml.etree import ElementTree as ET
from zlib import crc32
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZIP_LZMA, ZIP_STORED, ZipFile

import pytest

from foundation.adapters.preflight import OoxmlPreflight, PreflightConfig
from foundation.adapters.preflight import ooxml
from tests.backend.b1.preflight import accepted_v1 as old
from tests.backend.b1.preflight.test_ooxml import document, started, Resolver, run
from tools.b1.build_corpus import docx_parts, xlsx_parts, package, relationships, W, S, R, large_xlsx_parts as large_parts




def accepted_result(adapter_type, data):
    doc=document(data); adapter=adapter_type(Resolver(data))
    return adapter.assess(doc,started(doc,adapter),'2026-09-08T00:00:02Z')


def semantics(result):
    """Normalize only provenance; resolve every digest ref into compared contents."""
    artifacts={a.ref.sha256:json.loads(a.data) for a in result.artifacts}
    def observation(ref):
        value=dict(artifacts[ref.sha256])
        value.pop('assessor_version',None); value.pop('configuration_ref',None)
        return value
    a=result.assessment
    def finding(f):
        return {**f.model_dump(mode='json',exclude={'finding_id','observation_ref'}),
            'observation':observation(f.observation_ref)}
    value=a.model_dump(mode='json',exclude={'engine_version','configuration_ref','native_structure_findings','protection_findings','format_observation_refs'})
    value['native_structure_findings']=[finding(f) for f in a.native_structure_findings]
    value['protection_findings']=[finding(f) for f in a.protection_findings]
    value['format_observations']=[observation(ref) for ref in a.format_observation_refs]
    # Compare all nonconfiguration artifacts, including multiplicity and order.
    value['artifacts']=[observation(x.ref) for x in result.artifacts if x.ref!=a.configuration_ref]
    return value


def package_with_compression(parts, compression):
    stream = BytesIO()
    with ZipFile(stream, 'w', compression=compression) as archive:
        for name, content in sorted(parts.items()):
            archive.writestr(name, content.encode() if isinstance(content, str) else content)
    return stream.getvalue()


def understate_stored_member(data, name, exposed):
    """Keep a physical suffix while making both ZIP headers describe only a prefix."""
    result = bytearray(data)
    with ZipFile(BytesIO(result)) as archive:
        info = archive.getinfo(name)
    prefix_crc = crc32(exposed)
    pack_into('<III', result, info.header_offset + 14, prefix_crc, len(exposed), len(exposed))
    offset = 0
    while True:
        offset = result.find(b'PK\x01\x02', offset)
        if offset < 0:
            raise AssertionError('central directory entry not found')
        name_length = unpack_from('<H', result, offset + 28)[0]
        if result[offset + 46:offset + 46 + name_length] == name.encode():
            pack_into('<III', result, offset + 16, prefix_crc, len(exposed), len(exposed))
            return bytes(result)
        offset += 46 + name_length


def forge_member_crc(data, name, forged_crc):
    """Make local and central CRC metadata agree on the same wrong value."""
    result = bytearray(data)
    with ZipFile(BytesIO(result)) as archive:
        info = archive.getinfo(name)
    pack_into('<I', result, info.header_offset + 14, forged_crc)
    offset = 0
    while True:
        offset = result.find(b'PK\x01\x02', offset)
        if offset < 0:
            raise AssertionError('central directory entry not found')
        name_length = unpack_from('<H', result, offset + 28)[0]
        if result[offset + 46:offset + 46 + name_length] == name.encode():
            pack_into('<I', result, offset + 16, forged_crc)
            return bytes(result)
        offset += 46 + name_length


def parity_parts(case):
    p=docx_parts(True) if case!='xlsx' else xlsx_parts()
    if case=='strict': p={k:v.replace(W,old.WS).replace(R,old.RS) for k,v in p.items()}
    if case=='mixed': p['word/styles.xml']=p['word/styles.xml'].replace(W,old.WS)
    if case=='unknown': p['word/document.xml']=p['word/document.xml'].replace('<w:body>','<w:body xmlns:x="urn:synthetic:unknown"><x:future/><x:future/><w:future/>')
    if case=='attribute': p['word/document.xml']=p['word/document.xml'].replace('<w:body>','<w:body xmlns:x="urn:synthetic:attribute" x:flag="1">')
    if case=='protection': p['word/settings.xml']=f'<w:settings xmlns:w="{W}"><w:documentProtection w:enforcement="true"/><w:documentProtection w:enforcement="on"/><w:documentProtection w:enforcement="unexpected"/></w:settings>'
    if case=='binary': p['synthetic.bin']=b'not parsed but CRC checked'
    if case=='xlsx':
        p['xl/workbook.xml']=p['xl/workbook.xml'].replace('<sheets>','<workbookProtection lockStructure="true"/><sheets>')
        p['xl/worksheets/sheet1.xml']=p['xl/worksheets/sheet1.xml'].replace('<sheetData>','<sheetProtection sheet="1"/><sheetData>')
    return p


@pytest.mark.parametrize('case',['basic','strict','mixed','unknown','attribute','protection','binary','xlsx'])
def test_old_new_semantic_equivalence(case):
    data=package(parity_parts(case))
    before=accepted_result(old.OoxmlPreflight,data); after=accepted_result(OoxmlPreflight,data)
    assert before.assessment.status.value==after.assessment.status.value=='COMPLETED'
    assert semantics(before)==semantics(after)
    assert after==accepted_result(OoxmlPreflight,data)


def test_versioned_mechanics_preserve_all_numeric_defaults():
    new=asdict(PreflightConfig()); previous=asdict(old.PreflightConfig())
    assert OoxmlPreflight.version=='1.1.2' and new.pop('profile_version')=='1.1.1'
    previous.pop('profile_version'); assert new==previous


@pytest.mark.parametrize('encoding', ['UTF-7', 'Shift-JIS', 'unknown-audit-encoding'])
def test_xml_encoding_failures_are_structured(encoding):
    p = docx_parts()
    p['word/document.xml'] = f'<?xml version="1.0" encoding="{encoding}"?>' + p['word/document.xml']
    result = run(package(p))
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['CORRUPTED_DOCUMENT']
    failure = json.loads(result.artifacts[-1].data)
    assert failure['reason'] == 'Malformed or unsupported XML encoding'


def test_inspection_pass_also_structures_xml_encoding_failure(monkeypatch):
    p = docx_parts()
    p['word/document.xml'] = '<?xml version="1.0" encoding="UTF-7"?>' + p['word/document.xml']
    monkeypatch.setattr(ooxml, 'scan_capacity', lambda *args: 0)
    result = run(package(p))
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['CORRUPTED_DOCUMENT']
    assert json.loads(result.artifacts[-1].data)['reason'] == 'Malformed or unsupported XML encoding'


def test_observer_programmer_error_is_not_normalized_as_input_failure(monkeypatch):
    monkeypatch.setattr(ooxml, 'scan_capacity', lambda *args: 0)

    def programmer_error(*args, **kwargs):
        raise ValueError('synthetic observer defect')

    monkeypatch.setattr(ooxml.PartObservation, 'start', programmer_error)
    with pytest.raises(ValueError, match='synthetic observer defect'):
        run(package(docx_parts()))


def test_qualified_stored_compression_is_accepted():
    result = run(package_with_compression(docx_parts(), ZIP_STORED))
    assert result.assessment.status.value == 'COMPLETED'


def test_valid_zero_length_member_reaches_terminal_integrity_read(monkeypatch):
    data = package_with_compression({**docx_parts(), 'zero.bin': b''}, ZIP_STORED)
    reads = []
    original = ZipFile.open

    class TrackedStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def read(self, size=-1):
            reads.append(size)
            return self.stream.read(size)

    def tracked_open(self, member, *args, **kwargs):
        stream = original(self, member, *args, **kwargs)
        name = member.filename if hasattr(member, 'filename') else member
        return TrackedStream(stream) if name == 'zero.bin' else stream

    monkeypatch.setattr(ZipFile, 'open', tracked_open)
    result = run(data)
    assert result.assessment.status.value == 'COMPLETED'
    assert reads == [1]


def test_forged_crc_zero_length_member_fails_closed():
    data = package_with_compression({**docx_parts(), 'zero.bin': b''}, ZIP_STORED)
    result = run(forge_member_crc(data, 'zero.bin', 0x12345678))
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['CORRUPTED_DOCUMENT']
    failure = json.loads(result.artifacts[-1].data)
    assert failure['reason'] == 'Unreadable ZIP structure or CRC'


@pytest.mark.parametrize('compression', [ZIP_DEFLATED, ZIP_BZIP2, ZIP_LZMA])
def test_unqualified_compression_is_refused_before_member_decompression(monkeypatch, compression):
    data = package_with_compression(docx_parts(), compression)

    def forbidden(*args, **kwargs):
        pytest.fail('unqualified compression reached member decompression')

    monkeypatch.setattr(ZipFile, 'open', forbidden)
    result = run(data)
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['UNSUPPORTED_FILE_FORMAT']
    assert json.loads(result.artifacts[-1].data)['reason'] == 'ZIP compression method is outside qualified preflight profile'


def test_understated_stored_member_with_hidden_suffix_is_refused():
    p = docx_parts()
    p['z-audit.xml'] = '<x/><hidden-malformed'
    data = package_with_compression(p, ZIP_STORED)
    data = understate_stored_member(data, 'z-audit.xml', b'<x/>')
    result = run(data)
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['CORRUPTED_DOCUMENT']
    assert json.loads(result.artifacts[-1].data)['reason'] == 'ZIP local/central metadata or physical member layout is inconsistent'


@pytest.mark.parametrize('delta',[-1,0,1])
def test_exact_aggregate_capacity_boundary(delta):
    p=xlsx_parts(); count=sum(sum(1 for _ in ET.fromstring(v).iter()) for v in p.values())
    result=run(package(p),replace(PreflightConfig(),max_xml_elements=count+delta))
    assert result.assessment.status.value==('FAILED' if delta<0 else 'COMPLETED')
    if delta<0: assert [e.value for e in result.assessment.error_codes]==['DOCUMENT_TOO_LARGE']


@pytest.mark.parametrize('rows',[(3000,), (300,)*10])
def test_early_refusal_never_constructs_a_dom_or_inspects_parts(monkeypatch,rows):
    data=package(large_parts(rows))
    def forbidden(*args,**kwargs): pytest.fail('DOM or structural inspection reached after capacity failure')
    monkeypatch.setattr(ET,'fromstring',forbidden)
    monkeypatch.setattr(ooxml,'inspect_parts',forbidden,raising=False)
    result=run(data,replace(PreflightConfig(),max_xml_elements=1000))
    assert [e.value for e in result.assessment.error_codes]==['DOCUMENT_TOO_LARGE']
    assert not result.assessment.capability_results


def test_dominant_bulk_part_and_controls_complete_without_dom(monkeypatch):
    # More than 300,000 elements, within the unchanged default capacity.
    data=package(large_parts((10000,5),cells=10,formulas=True))
    def forbidden(*args,**kwargs): pytest.fail('Preflight constructed a DOM')
    monkeypatch.setattr(ET,'fromstring',forbidden)
    result=run(data)
    assert result.assessment.status.value=='COMPLETED'
    obs=[json.loads(a.data) for a in result.artifacts]
    assert sum(o.get('count',0) for o in obs if o.get('observation_type')=='cell')==100050
    assert sum(o.get('count',0) for o in obs if o.get('observation_type')=='formula')==100050
    assert all(not f.native_locator_refs for f in result.assessment.native_structure_findings)


@pytest.mark.parametrize('defect',['duplicate','noncanonical','encrypted','binary_crc','xml_crc','bad_mode','duplicate_rel_id','missing_source','bad_main_root','duplicate_main','missing_main','bad_types','external_entity'])
def test_package_and_control_failures_remain_closed(defect):
    p=docx_parts(); expected='CORRUPTED_DOCUMENT'
    if defect=='noncanonical': p['../escape.bin']=b'x'
    elif defect in ('encrypted','binary_crc'): p['synthetic.bin']=b'unique synthetic marker'
    elif defect=='bad_mode': p['_rels/.rels']=p['_rels/.rels'].replace('Target="word/document.xml"','Target="word/document.xml" TargetMode="Invalid"')
    elif defect=='duplicate_rel_id': p['word/_rels/document.xml.rels']=relationships([('same',R+'/styles','styles.xml',False)]*2)
    elif defect=='missing_source': p['word/_rels/missing.xml.rels']=relationships([])
    elif defect=='bad_main_root': p['word/document.xml']=f'<w:wrong xmlns:w="{W}"/>'
    elif defect=='duplicate_main': p['_rels/.rels']=relationships([('one',R+'/officeDocument','word/document.xml',False),('two',R+'/officeDocument','word/document.xml',False)])
    elif defect=='missing_main': p['_rels/.rels']=relationships([])
    elif defect=='bad_types': p['[Content_Types].xml']='<wrong/>'
    elif defect=='external_entity': p['word/document.xml']='<!DOCTYPE x [<!ENTITY x SYSTEM "file:///never-read">]><x>&x;</x>'
    data=package(p)
    if defect=='duplicate':
        stream=BytesIO(data)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with ZipFile(stream,'a') as z: z.writestr('word/styles.xml',p['word/styles.xml'])
        data=stream.getvalue()
    if defect=='encrypted':
        data=bytearray(data); at=0
        while True:
            at=data.find(b'PK\x01\x02',at)
            if at<0: break
            pack_into('<H',data,at+8,1); at+=4
        data=bytes(data); expected='ENCRYPTED_DOCUMENT'
    if defect in ('binary_crc','xml_crc'):
        marker=b'unique synthetic marker' if defect=='binary_crc' else b'Synthetic Local File'
        data=bytearray(data); at=data.index(marker); data[at]^=1; data=bytes(data)
    result=run(data)
    assert result.assessment.status.value=='FAILED'
    assert [e.value for e in result.assessment.error_codes]==[expected]


def test_many_parts_and_dominant_part_equivalence():
    for rows in ((5000,), (500,)*10):
        data=package(large_parts(rows))
        assert semantics(accepted_result(old.OoxmlPreflight,data))==semantics(accepted_result(OoxmlPreflight,data))


@pytest.mark.parametrize('delta',[-1,0,1])
def test_part_byte_boundary(delta):
    p=docx_parts(); maximum=max(len(v.encode()) for v in p.values())
    result=run(package(p),replace(PreflightConfig(),max_part_bytes=maximum+delta))
    assert result.assessment.status.value==('FAILED' if delta<0 else 'COMPLETED')


def test_capacity_stops_before_later_defect_and_closes_current_member(monkeypatch):
    p=large_parts((10000,)); p['zz-later.xml']='<malformed'
    data=package(p)  # Instrument inspection reads, not fixture-construction writes.
    opened=[]; streams=[]; original=ZipFile.open
    def tracked(self, member, *args, **kwargs):
        name=member.filename if hasattr(member,'filename') else member
        opened.append(name)
        stream=original(self,member,*args,**kwargs); streams.append(stream)
        return stream
    monkeypatch.setattr(ZipFile,'open',tracked)
    result=run(data,replace(PreflightConfig(),max_xml_elements=100))
    assert [e.value for e in result.assessment.error_codes]==['DOCUMENT_TOO_LARGE']
    assert 'zz-later.xml' not in opened
    assert all(s.closed for s in streams)
    assert opened.count('xl/worksheets/sheet1.xml')==1  # No inspection pass.


def test_control_capacity_fails_before_control_records_are_retained(monkeypatch):
    p=docx_parts()
    p['_rels/.rels']=relationships([('main',R+'/officeDocument','word/document.xml',False)]+
        [(f'link{i}',R+'/hyperlink','https://example.invalid',True) for i in range(500)])
    def forbidden(*args,**kwargs): pytest.fail('Reducer allocated before capacity admission')
    monkeypatch.setattr(ooxml,'PartObservation',forbidden)
    result=run(package(p),replace(PreflightConfig(),max_xml_elements=100))
    assert result.assessment.status.value=='FAILED'
    assert [e.value for e in result.assessment.error_codes]==['DOCUMENT_TOO_LARGE']


def test_unknown_namespace_counts_and_private_values_are_not_lost_or_retained():
    p=docx_parts()
    p['word/document.xml']=p['word/document.xml'].replace('<w:body>',
        '<w:body xmlns:x="urn:synthetic:future"><x:future x:flag="SECRET_ATTRIBUTE">SECRET_TEXT</x:future><x:future/>')
    p['word/settings.xml']=f'<w:settings xmlns:w="{W}"><w:documentProtection w:enforcement="1" w:password="SECRET_PASSWORD"/></w:settings>'
    result=run(package(p)); payloads=[json.loads(a.data) for a in result.artifacts]
    unknown=[o for o in payloads if o.get('observation_type')=='unknown_structure' and o.get('qname')=='{urn:synthetic:future}future']
    assert len(unknown)==1 and unknown[0]['count']==2
    assert 'SECRET_' not in json.dumps(payloads)


def test_repeated_findings_have_unique_deterministic_occurrence_ids():
    p = docx_parts()
    p['word/settings.xml'] = f'<w:settings xmlns:w="{W}"><w:documentProtection w:enforcement="true"/><w:documentProtection w:enforcement="true"/></w:settings>'
    first, second = run(package(p)), run(package(p))
    first_findings = first.assessment.native_structure_findings + first.assessment.protection_findings
    second_findings = second.assessment.native_structure_findings + second.assessment.protection_findings
    ids = [finding.finding_id for finding in first_findings]
    assert len(ids) == len(set(ids))
    assert ids == [finding.finding_id for finding in second_findings]
    repeated = [finding for finding in first.assessment.protection_findings if finding.native_object_type == 'document_protection']
    assert len(repeated) == 2
    assert repeated[0].observation_ref == repeated[1].observation_ref
    assert repeated[0].finding_id != repeated[1].finding_id


def test_constant_numeric_profile_and_explicit_parser_provenance():
    result=run(package(docx_parts()))
    configuration=json.loads(result.artifacts[0].data)
    assert configuration['config']==asdict(PreflightConfig())
    strategy=configuration['parser_strategy']
    assert strategy['strategy_version'] == '1.1.1'
    assert strategy['dom']=='NONE' and 'CONTROL_XML' in strategy and 'BULK_XML' in strategy
    assert strategy['dtd']==strategy['external_entities']=='REFUSED'
    assert strategy['qualified_zip_compression_methods'] == [{'code': ZIP_STORED, 'name': 'STORED'}]
