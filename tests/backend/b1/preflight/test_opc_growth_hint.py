"""Qualification tests for the narrow OPC Growth Hint ZIP-extra allowlist."""
from io import BytesIO
import json
from struct import pack, pack_into, unpack_from
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from foundation.adapters.preflight import streaming
from tests.backend.b1.preflight.test_bounded_deflate import (
    central_offset,
    deflate_package,
    failure_reason,
    member_info,
)
from tests.backend.b1.preflight.test_ooxml import run


TARGET = 'z-audit.bin'
A220 = 0xA220
A028 = 0xA028


def extra_field(header_id, payload):
    return pack('<HH', header_id, len(payload)) + payload


def growth_hint(payload_length=12, *, signature=A028, padding_initial_value=0x1234, padding_byte=0):
    assert payload_length >= 4
    payload = pack('<HH', signature, padding_initial_value)
    payload += bytes([padding_byte]) * (payload_length - 4)
    return extra_field(A220, payload)


def insert_local_extra(data, name, extra):
    """Insert metadata into the final member's LOCAL header only."""
    info = member_info(data, name)
    name_length, old_length = unpack_from('<HH', data, info.header_offset + 26)
    insertion = info.header_offset + 30 + name_length + old_length
    old_central = data.find(b'PK\x01\x02', insertion + info.compress_size)
    assert insertion + info.compress_size == old_central
    result = bytearray(data[:insertion] + extra + data[insertion:])
    pack_into('<H', result, info.header_offset + 28, old_length + len(extra))
    eocd = result.rfind(b'PK\x05\x06')
    pack_into('<I', result, eocd + 16, old_central + len(extra))
    return bytes(result)


def insert_central_extra(data, name, extra):
    """Insert metadata into one CENTRAL directory entry only."""
    offset = central_offset(data, name)
    name_length, old_length = unpack_from('<HH', data, offset + 28)
    insertion = offset + 46 + name_length + old_length
    result = bytearray(data[:insertion] + extra + data[insertion:])
    pack_into('<H', result, offset + 30, old_length + len(extra))
    eocd = result.rfind(b'PK\x05\x06')
    old_central_size = unpack_from('<I', result, eocd + 12)[0]
    pack_into('<I', result, eocd + 12, old_central_size + len(extra))
    return bytes(result)


def assert_refused(data, expected_code):
    result = run(data)
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == [expected_code]
    return result


def test_local_only_growth_hint_is_admitted():
    assert run(insert_local_extra(deflate_package(), TARGET, growth_hint())).assessment.status.value == 'COMPLETED'


def test_extra_parser_records_payload_location_and_stable_order():
    first = growth_hint(4)
    second = extra_field(0xCAFE, b'opaque')
    records = streaming._extra_fields(first + second, 'LOCAL')
    assert [(record.header_id, record.declared_length, record.location, record.occurrence) for record in records] == [
        (A220, 4, 'LOCAL', 0),
        (0xCAFE, 6, 'LOCAL', 1),
    ]
    assert records[0].payload == first[4:]
    assert records[1].payload == b'opaque'


def test_growth_hint_with_no_padding_and_uninterpreted_initial_value_is_admitted():
    data = insert_local_extra(deflate_package(), TARGET, growth_hint(4, padding_initial_value=0xFFFF))
    assert run(data).assessment.status.value == 'COMPLETED'


@pytest.mark.parametrize(
    ('field', 'reason'),
    [
        pytest.param(growth_hint(signature=0xFFFF), 'Malformed OPC Growth Hint extra field', id='bad-signature'),
        pytest.param(extra_field(A220, b'\x28\xa0\x00'), 'Malformed OPC Growth Hint extra field', id='short-payload'),
        pytest.param(growth_hint(padding_byte=1), 'Malformed OPC Growth Hint extra field', id='non-zero-padding'),
    ],
)
def test_malformed_growth_hint_is_refused(field, reason):
    result = assert_refused(insert_local_extra(deflate_package(), TARGET, field), 'CORRUPTED_DOCUMENT')
    assert failure_reason(result) == reason


def test_duplicate_local_growth_hint_is_refused():
    result = assert_refused(
        insert_local_extra(deflate_package(), TARGET, growth_hint() + growth_hint()),
        'UNSUPPORTED_FILE_FORMAT',
    )
    assert failure_reason(result) == 'Duplicate ZIP extra field is outside qualified LOCAL profile'


def test_central_only_growth_hint_is_refused():
    assert_refused(insert_central_extra(deflate_package(), TARGET, growth_hint()), 'UNSUPPORTED_FILE_FORMAT')


def test_local_and_central_growth_hint_is_refused():
    data = insert_local_extra(deflate_package(), TARGET, growth_hint())
    assert_refused(insert_central_extra(data, TARGET, growth_hint()), 'UNSUPPORTED_FILE_FORMAT')


@pytest.mark.parametrize('placement', ['both', 'local', 'central'])
def test_unknown_extra_fields_are_refused_even_when_identical(placement):
    field = extra_field(0xCAFE, b'opaque')
    data = deflate_package()
    if placement in ('both', 'local'):
        data = insert_local_extra(data, TARGET, field)
    if placement in ('both', 'central'):
        data = insert_central_extra(data, TARGET, field)
    assert_refused(data, 'UNSUPPORTED_FILE_FORMAT')


@pytest.mark.parametrize('placement', ['local', 'central'])
def test_zip64_extra_is_refused_in_each_location(placement):
    field = extra_field(0x0001, b'')
    data = insert_local_extra(deflate_package(), TARGET, field) if placement == 'local' else insert_central_extra(
        deflate_package(), TARGET, field
    )
    assert_refused(data, 'UNSUPPORTED_FILE_FORMAT')


@pytest.mark.parametrize('header_id', [0x0017, 0x9901])
def test_known_encryption_extras_are_refused(header_id):
    assert_refused(insert_local_extra(deflate_package(), TARGET, extra_field(header_id, b'')), 'ENCRYPTED_DOCUMENT')


def test_malformed_tlv_length_is_refused():
    malformed = pack('<HH', A220, 10) + b'\x28'
    assert_refused(insert_local_extra(deflate_package(), TARGET, malformed), 'CORRUPTED_DOCUMENT')


def test_growth_hint_shifts_data_start_without_entering_compressed_range():
    base = deflate_package()
    field = growth_hint(36)
    changed = insert_local_extra(base, TARGET, field)
    with ZipFile(BytesIO(base)) as archive:
        base_info = archive.getinfo(TARGET)
        base_envelope = streaming.validate_package_profile(base, archive.infolist(), archive.start_dir)[base_info.header_offset]
    with ZipFile(BytesIO(changed)) as archive:
        changed_info = archive.getinfo(TARGET)
        changed_envelope = streaming.validate_package_profile(changed, archive.infolist(), archive.start_dir)[
            changed_info.header_offset
        ]
    assert changed_envelope.data_start == base_envelope.data_start + len(field)
    assert changed_envelope.data_end == base_envelope.data_end + len(field)
    assert changed[changed_envelope.data_start:changed_envelope.data_end] == base[
        base_envelope.data_start:base_envelope.data_end
    ]


def test_growth_hint_cannot_obscure_the_physical_range():
    data = bytearray(insert_local_extra(deflate_package(), TARGET, growth_hint()))
    info = member_info(data, TARGET)
    old_length = unpack_from('<H', data, info.header_offset + 28)[0]
    pack_into('<H', data, info.header_offset + 28, old_length + 1)
    assert_refused(bytes(data), 'CORRUPTED_DOCUMENT')


@pytest.mark.parametrize('payload_length', [36, 260, 516])
def test_representative_shape_growth_hints_are_admitted(payload_length):
    data = insert_local_extra(deflate_package(), TARGET, growth_hint(payload_length, padding_initial_value=7))
    assert run(data).assessment.status.value == 'COMPLETED'


def test_configuration_records_the_exact_extra_field_policy():
    result = run(insert_local_extra(deflate_package(), TARGET, growth_hint()))
    configuration = json.loads(result.artifacts[0].data)
    strategy = configuration['parser_strategy']
    assert strategy['strategy_version'] == '1.2.0'
    assert strategy['implementation_revision'] == 'opc-growth-hint-allowlist-1'
    assert strategy['zip_extra_field_policy'] == {
        'LOCAL': {'0xA220': 'OPC Growth Hint; signature 0xA028 and zero padding required'},
        'CENTRAL': {},
        'duplicates': 'REFUSED',
        'unknown': 'REFUSED',
    }
