"""Synthetic proof for the B1 representative-only preflight profile."""
from dataclasses import asdict, replace
from hashlib import sha256
from io import BytesIO
import json
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from foundation.adapters.preflight import OoxmlPreflight, PreflightConfig
from foundation.evaluation.perception import representative as rep
from tests.backend.b1.preflight.test_ooxml import Resolver, run
from tests.backend.b1.preflight.test_resource_safe import package_with_compression
from tests.backend.b1.representative.test_representative import manifest, result, review
from tools.b1.build_corpus import docx_parts


EXPECTED_PROFILE = {
    'profile_version': '1.2.0',
    'max_package_bytes': 3004377,
    'max_uncompressed_bytes': 22302224,
    'max_part_bytes': 17856208,
    'max_parts': 132,
    'max_xml_elements': 796703,
}
EXPECTED_DEFAULT = {
    'profile_version': '1.2.0',
    'max_package_bytes': 33554432,
    'max_uncompressed_bytes': 134217728,
    'max_part_bytes': 16777216,
    'max_parts': 4096,
    'max_xml_elements': 500000,
}


def digest_for(adapter, profile_id=rep.REPRESENTATIVE_PREFLIGHT_PROFILE_ID):
    payload = rep.stable_observation_payload(input_hash='a' * 64, adapter=adapter,
        preflight_status='COMPLETED', feature_checks=[],
        runs=[{'conversion_status': 'PASS', 'elapsed_seconds': 12.5}],
        input_unchanged=True, profile_id=profile_id)
    return rep.probe.digest(payload)


def assert_capacity_refusal(data):
    assessment = run(data, rep.REPRESENTATIVE_PREFLIGHT_CONFIG).assessment
    assert assessment.status.value == 'FAILED'
    assert [code.value for code in assessment.error_codes] == ['DOCUMENT_TOO_LARGE']


def test_profile_identity_and_exact_values_are_harness_owned():
    assert rep.REPRESENTATIVE_PREFLIGHT_PROFILE_ID == 'b1-representative-core-v1'
    assert asdict(rep.REPRESENTATIVE_PREFLIGHT_CONFIG) == EXPECTED_PROFILE


def test_general_defaults_and_constructor_remain_unchanged():
    assert asdict(PreflightConfig()) == EXPECTED_DEFAULT
    adapter = OoxmlPreflight(Resolver(package_with_compression(docx_parts(), ZIP_DEFLATED)))
    assert asdict(adapter.config) == EXPECTED_DEFAULT


def test_representative_constructor_explicitly_supplies_profile(monkeypatch):
    captured = {}
    sentinel = object()

    def construct(resolver, config=None):
        captured.update(resolver=resolver, config=config)
        return sentinel

    monkeypatch.setattr(rep, 'OoxmlPreflight', construct)
    resolver = object()
    assert rep.representative_preflight(resolver) is sentinel
    assert captured == {'resolver': resolver, 'config': rep.REPRESENTATIVE_PREFLIGHT_CONFIG}


def test_private_evidence_binds_profile_and_configuration_without_public_exposure(tmp_path, monkeypatch):
    case = manifest()['cases'][0]
    path = tmp_path / case['local_path']
    path.write_bytes(package_with_compression(docx_parts(), ZIP_DEFLATED))
    fake_run = {'conversion_status': 'PASS', 'semantic_document': {'texts': [], 'tables': [], 'groups': []},
                'observations': {'collection_counts': {}}, 'elapsed_seconds': 1.0}
    monkeypatch.setattr(rep.probe, 'probe_once', lambda *_: fake_run)
    monkeypatch.setattr(rep.probe, 'compare_runs', lambda _: {key: 'PASS' for key in rep.REPEATABILITY if key != 'conversion'})
    evaluated = rep.evaluate_case(case, path)
    assert evaluated['representative_preflight_profile_id'] == rep.REPRESENTATIVE_PREFLIGHT_PROFILE_ID
    assert evaluated['preflight_configuration_ref'] == evaluated['preflight']['assessment']['configuration_ref']
    assert evaluated['observation_digest']
    public = json.dumps(rep.sanitize({'corpus_status': 'AVAILABLE', 'cases': [evaluated], 'manifest': manifest()}))
    assert rep.REPRESENTATIVE_PREFLIGHT_PROFILE_ID not in public
    assert evaluated['preflight_configuration_ref']['sha256'] not in public


def test_profile_identity_and_config_each_change_observation_and_invalidate_review():
    data = package_with_compression(docx_parts(), ZIP_DEFLATED)
    resolver = Resolver(data)
    accepted = rep.representative_preflight(resolver)
    changed_config = OoxmlPreflight(resolver, replace(rep.REPRESENTATIVE_PREFLIGHT_CONFIG, max_xml_elements=796702))
    original_digest = digest_for(accepted)
    assert digest_for(accepted, 'b1-representative-core-v2') != original_digest
    assert accepted.configuration.ref != changed_config.configuration.ref
    changed_digest = digest_for(changed_config)
    assert changed_digest != original_digest

    case = result()
    case['observation_digest'] = original_digest
    case['review'] = review(case)
    assert rep.review_valid(case)
    case['observation_digest'] = changed_digest
    assert not rep.review_valid(case)


def combined_default_blocker():
    parts = docx_parts()
    xml = parts['word/document.xml']
    prefix, suffix = xml.split('</w:body>')
    elements = '<w:p/>' * 500001
    fixed = prefix + elements + '<!---->' + '</w:body>' + suffix
    padding = PreflightConfig().max_part_bytes + 1 - len(fixed.encode())
    assert padding >= 0
    parts['word/document.xml'] = prefix + elements + '<!--' + ('X' * padding) + '-->' + '</w:body>' + suffix
    assert len(parts['word/document.xml'].encode()) == PreflightConfig().max_part_bytes + 1
    return package_with_compression(parts, ZIP_DEFLATED)


def test_default_capacity_refuses_while_representative_profile_admits_same_shape():
    data = combined_default_blocker()
    assert len(data) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_package_bytes
    default = run(data, PreflightConfig()).assessment
    qualified = run(data, rep.REPRESENTATIVE_PREFLIGHT_CONFIG).assessment
    assert default.status.value == 'FAILED'
    assert [code.value for code in default.error_codes] == ['DOCUMENT_TOO_LARGE']
    assert qualified.status.value == 'COMPLETED'


def test_qualification_package_limit_plus_one_refuses():
    data = package_with_compression(docx_parts(), ZIP_DEFLATED)
    data += b'X' * (rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_package_bytes + 1 - len(data))
    assert len(data) == rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_package_bytes + 1
    assert_capacity_refusal(data)


def test_qualification_aggregate_limit_plus_one_refuses():
    parts = docx_parts()
    base = sum(len(value.encode() if isinstance(value, str) else value) for value in parts.values())
    remaining = rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_uncompressed_bytes + 1 - base
    parts['a.bin'] = b'A' * (remaining // 2)
    parts['b.bin'] = b'B' * (remaining - remaining // 2)
    data = package_with_compression(parts, ZIP_DEFLATED)
    with ZipFile(BytesIO(data)) as archive:
        infos = archive.infolist()
        assert sum(info.file_size for info in infos) == rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_uncompressed_bytes + 1
        assert max(info.file_size for info in infos) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_part_bytes
    assert len(data) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_package_bytes
    assert_capacity_refusal(data)


def test_qualification_part_limit_plus_one_refuses():
    parts = {**docx_parts(), 'large.bin': b'A' * (rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_part_bytes + 1)}
    data = package_with_compression(parts, ZIP_DEFLATED)
    with ZipFile(BytesIO(data)) as archive:
        infos = archive.infolist()
        assert max(info.file_size for info in infos) == rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_part_bytes + 1
        assert sum(info.file_size for info in infos) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_uncompressed_bytes
    assert len(data) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_package_bytes
    assert_capacity_refusal(data)


def test_qualification_part_count_limit_plus_one_refuses():
    parts = docx_parts()
    for index in range(rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_parts + 1 - len(parts)):
        parts[f'bounded-{index:03}.bin'] = b''
    assert len(parts) == rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_parts + 1
    data = package_with_compression(parts, ZIP_DEFLATED)
    with ZipFile(BytesIO(data)) as archive:
        assert len(archive.infolist()) == rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_parts + 1
    assert len(data) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_package_bytes
    assert_capacity_refusal(data)


def test_qualification_xml_element_limit_plus_one_refuses():
    parts = docx_parts()
    base_count = sum(len(list(ET.fromstring(value).iter())) for name, value in parts.items()
                     if name.endswith(('.xml', '.rels')))
    addition = rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_xml_elements + 1 - base_count
    parts['word/document.xml'] = parts['word/document.xml'].replace('<w:body>', '<w:body>' + '<w:p/>' * addition)
    assert sum(len(list(ET.fromstring(value).iter())) for name, value in parts.items()
               if name.endswith(('.xml', '.rels'))) == rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_xml_elements + 1
    data = package_with_compression(parts, ZIP_DEFLATED)
    with ZipFile(BytesIO(data)) as archive:
        assert max(info.file_size for info in archive.infolist()) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_part_bytes
    assert len(data) <= rep.REPRESENTATIVE_PREFLIGHT_CONFIG.max_package_bytes
    assert_capacity_refusal(data)
