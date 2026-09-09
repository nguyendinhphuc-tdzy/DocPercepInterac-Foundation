"""Synthetic qualification evidence for the Foundation-bounded DEFLATE path."""
from dataclasses import replace
from io import BytesIO
import json
import random
from struct import pack_into, unpack_from
from zlib import crc32
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

import pytest

from foundation.adapters.preflight import OoxmlPreflight, PreflightConfig
from foundation.adapters.preflight import ooxml, streaming
from tests.backend.b1.preflight.test_ooxml import run
from tests.backend.b1.preflight.test_resource_safe import package_with_compression
from tools.b1.build_corpus import W, docx_parts


def central_offset(data, name):
    offset = 0
    while True:
        offset = data.find(b'PK\x01\x02', offset)
        if offset < 0:
            raise AssertionError('central directory entry not found')
        length = unpack_from('<H', data, offset + 28)[0]
        if data[offset + 46:offset + 46 + length] == name.encode():
            return offset
        offset += 46 + length


def member_info(data, name):
    with ZipFile(BytesIO(data)) as archive:
        return archive.getinfo(name)


def set_declared(data, name, *, expanded=None, crc=None):
    result = bytearray(data)
    info = member_info(result, name)
    central = central_offset(result, name)
    if crc is not None:
        pack_into('<I', result, info.header_offset + 14, crc)
        pack_into('<I', result, central + 16, crc)
    if expanded is not None:
        pack_into('<I', result, info.header_offset + 22, expanded)
        pack_into('<I', result, central + 24, expanded)
    return bytes(result)


def replace_last_compressed_stream(data, name, replacement):
    """Replace the final member's physical DEFLATE bytes and move central data."""
    info = member_info(data, name)
    name_length, extra_length = unpack_from('<HH', data, info.header_offset + 26)
    start = info.header_offset + 30 + name_length + extra_length
    old_end = start + info.compress_size
    old_central = data.find(b'PK\x01\x02', old_end)
    assert old_end == old_central
    result = bytearray(data[:start] + replacement + data[old_end:])
    delta = len(replacement) - info.compress_size
    central = central_offset(result, name)
    pack_into('<I', result, info.header_offset + 18, len(replacement))
    pack_into('<I', result, central + 20, len(replacement))
    eocd = result.rfind(b'PK\x05\x06')
    pack_into('<I', result, eocd + 16, old_central + delta)
    return bytes(result)


def insert_hidden_physical_suffix(data, name, suffix):
    """Insert bytes outside the declared stream while preserving ZIP readability."""
    info = member_info(data, name)
    name_length, extra_length = unpack_from('<HH', data, info.header_offset + 26)
    end = info.header_offset + 30 + name_length + extra_length + info.compress_size
    old_central = data.find(b'PK\x01\x02', end)
    assert end == old_central
    result = bytearray(data[:end] + suffix + data[end:])
    eocd = result.rfind(b'PK\x05\x06')
    pack_into('<I', result, eocd + 16, old_central + len(suffix))
    return bytes(result)


def failure_reason(result):
    return json.loads(result.artifacts[-1].data)['reason']


def deflate_package(extra_name='z-audit.bin', extra=b'audit'):
    return package_with_compression({**docx_parts(), extra_name: extra}, ZIP_DEFLATED)


def test_qualification_counterexample_refuses_actual_size_mismatch():
    payload = b'A' * (1024 * 1024)
    data = deflate_package(extra=payload)
    exposed = 128
    attacked = set_declared(data, 'z-audit.bin', expanded=exposed, crc=crc32(payload[:exposed]))
    with ZipFile(BytesIO(attacked)) as archive:
        assert archive.read('z-audit.bin') == payload[:exposed]
    result = run(attacked)
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['CORRUPTED_DOCUMENT']
    assert failure_reason(result) == 'Actual DEFLATE size disagrees with ZIP metadata'


@pytest.mark.parametrize('payload', [
    pytest.param(b'normal DEFLATE content' * 100, id='normal'),
    pytest.param(b'A' * (1024 * 1024), id='high-ratio'),
    pytest.param(random.Random(7).randbytes(256 * 1024), id='random'),
    pytest.param(b'B' * (2 * 1024 * 1024), id='dominant'),
])
def test_normal_high_ratio_random_and_dominant_members(payload):
    assert run(deflate_package(extra=payload)).assessment.status.value == 'COMPLETED'


def test_many_member_aggregate_and_exact_default_part_boundary():
    parts = {**docx_parts(), **{f'audit-{index}.bin': bytes([65 + index]) * 50000 for index in range(4)}}
    result = run(package_with_compression(parts, ZIP_DEFLATED), replace(PreflightConfig(), max_uncompressed_bytes=210000))
    assert result.assessment.status.value == 'COMPLETED'
    exact = run(deflate_package(extra=b'X' * (16 * 1024 * 1024)))
    assert exact.assessment.status.value == 'COMPLETED'


def test_actual_byte_above_default_part_limit_refuses_immediately():
    payload = b'X' * (16 * 1024 * 1024 + 1)
    data = deflate_package(extra=payload)
    attacked = set_declared(data, 'z-audit.bin', expanded=16 * 1024 * 1024, crc=crc32(payload[:-1]))
    result = run(attacked)
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['DOCUMENT_TOO_LARGE']
    assert failure_reason(result) == 'Configured expanded package limits exceeded'


def test_actual_aggregate_over_limit_refuses():
    parts = {**docx_parts(), 'y-audit.bin': b'Y' * 600, 'z-audit.bin': b'Z' * 600}
    data = package_with_compression(parts, ZIP_DEFLATED)
    attacked = set_declared(data, 'z-audit.bin', expanded=400, crc=crc32(b'Z' * 400))
    result = run(attacked, replace(PreflightConfig(), max_uncompressed_bytes=2200))
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['DOCUMENT_TOO_LARGE']


def test_valid_zero_length_deflate_member():
    assert run(deflate_package(extra=b'')).assessment.status.value == 'COMPLETED'


def test_truncated_invalid_crc_size_and_trailing_streams_fail_closed():
    payload = b'Q' * (1024 * 1024)
    data = deflate_package(extra=payload)
    info = member_info(data, 'z-audit.bin')
    name_length, extra_length = unpack_from('<HH', data, info.header_offset + 26)
    start = info.header_offset + 30 + name_length + extra_length
    compressed = data[start:start + info.compress_size]
    cases = [
        (replace_last_compressed_stream(data, 'z-audit.bin', compressed[:-1]), 'Incomplete DEFLATE stream'),
        (replace_last_compressed_stream(data, 'z-audit.bin', b'\x07'), 'Invalid DEFLATE stream'),
        (set_declared(data, 'z-audit.bin', crc=0x12345678), 'Actual DEFLATE CRC disagrees with ZIP metadata'),
        (set_declared(data, 'z-audit.bin', expanded=len(payload) + 1), 'Actual DEFLATE size disagrees with ZIP metadata'),
        (replace_last_compressed_stream(data, 'z-audit.bin', compressed + b'JUNK'), 'DEFLATE stream has trailing compressed data'),
    ]
    for attacked, reason in cases:
        result = run(attacked)
        assert result.assessment.status.value == 'FAILED'
        assert [code.value for code in result.assessment.error_codes] == ['CORRUPTED_DOCUMENT']
        assert failure_reason(result) == reason


def test_hidden_physical_suffix_is_rejected_before_decompression(monkeypatch):
    data = insert_hidden_physical_suffix(deflate_package(), 'z-audit.bin', b'HIDDEN')

    def forbidden(*args, **kwargs):
        pytest.fail('hidden physical suffix reached DEFLATE decompression')

    monkeypatch.setattr(streaming, 'decompressobj', forbidden)
    result = run(data)
    assert result.assessment.status.value == 'FAILED'
    assert failure_reason(result) == 'ZIP local/central metadata or physical member layout is inconsistent'


def test_no_progress_terminates_as_corruption(monkeypatch):
    class Stalled:
        eof = False
        unconsumed_tail = b''
        unused_data = b''

        def decompress(self, data, max_length):
            return b''

    monkeypatch.setattr(streaming, 'decompressobj', lambda *_: Stalled())
    result = run(deflate_package())
    assert result.assessment.status.value == 'FAILED'
    assert failure_reason(result) == 'Incomplete DEFLATE stream'


def test_every_zlib_call_and_output_is_bounded(monkeypatch):
    original = streaming.decompressobj
    calls = []

    class Traced:
        def __init__(self):
            self.inner = original(-15)

        def decompress(self, data, max_length):
            output = self.inner.decompress(data, max_length)
            calls.append((len(data), max_length, len(output), len(self.inner.unconsumed_tail)))
            return output

        def __getattr__(self, name):
            return getattr(self.inner, name)

    monkeypatch.setattr(streaming, 'decompressobj', lambda *_: Traced())
    result = run(deflate_package(extra=b'A' * (1024 * 1024)))
    assert result.assessment.status.value == 'COMPLETED'
    assert calls
    assert max(item[0] for item in calls) <= streaming.DEFLATE_INPUT_CHUNK_BYTES
    assert {item[1] for item in calls} == {streaming.DEFLATE_OUTPUT_CHUNK_BYTES}
    assert max(item[2] for item in calls) <= streaming.DEFLATE_OUTPUT_CHUNK_BYTES
    assert any(item[3] for item in calls)


def test_decompressed_xml_streams_into_existing_limits_without_dom(monkeypatch):
    monkeypatch.setattr(ooxml, 'scan_capacity', ooxml.scan_capacity)
    parts = docx_parts()
    parts['word/document.xml'] = parts['word/document.xml'].replace('<w:body>', '<w:body>' + '<w:p/>' * 101)
    result = run(package_with_compression(parts, ZIP_DEFLATED), replace(PreflightConfig(), max_xml_elements=100))
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['DOCUMENT_TOO_LARGE']


@pytest.mark.parametrize('insertion', [
    pytest.param('<w:p>' * 2000 + '</w:p>' * 2000, id='deep'),
    pytest.param('<w:p><w:r><w:t>' + 'T' * (512 * 1024) + '</w:t></w:r></w:p>', id='large-token'),
    pytest.param('<w:p w:rsidR="' + 'A' * (512 * 1024) + '"/>', id='large-attribute'),
])
def test_deep_xml_large_token_and_large_attribute_stream(insertion):
    parts = docx_parts()
    parts['word/document.xml'] = parts['word/document.xml'].replace('<w:body>', '<w:body>' + insertion)
    assert run(package_with_compression(parts, ZIP_DEFLATED)).assessment.status.value == 'COMPLETED'


def test_unqualified_flag_refuses_before_decompression(monkeypatch):
    data = bytearray(deflate_package())
    info = member_info(data, '[Content_Types].xml')
    central = central_offset(data, '[Content_Types].xml')
    flags = info.flag_bits | 0x10
    pack_into('<H', data, info.header_offset + 6, flags)
    pack_into('<H', data, central + 8, flags)

    def forbidden(*args, **kwargs):
        pytest.fail('unqualified ZIP profile reached DEFLATE')

    monkeypatch.setattr(streaming, 'decompressobj', forbidden)
    result = run(bytes(data))
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['UNSUPPORTED_FILE_FORMAT']


def test_data_descriptor_refuses_before_decompression(monkeypatch):
    class NonSeekable:
        def __init__(self):
            self.buffer = BytesIO()

        def write(self, data):
            return self.buffer.write(data)

        def tell(self):
            return self.buffer.tell()

        def flush(self):
            pass

    stream = NonSeekable()
    with ZipFile(stream, 'w', compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(docx_parts().items()):
            archive.writestr(name, content)

    def forbidden(*args, **kwargs):
        pytest.fail('data descriptor reached DEFLATE decompression')

    monkeypatch.setattr(streaming, 'decompressobj', forbidden)
    result = run(stream.buffer.getvalue())
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['UNSUPPORTED_FILE_FORMAT']
    assert failure_reason(result) == 'ZIP data descriptors are outside qualified preflight profile'


def test_zip64_refuses_before_decompression(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('ZIP64 reached DEFLATE decompression')

    monkeypatch.setattr(streaming, 'decompressobj', forbidden)
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        for name, content in sorted(docx_parts().items()):
            info = ZipInfo(name)
            info.compress_type = ZIP_DEFLATED
            if name == '[Content_Types].xml':
                with archive.open(info, 'w', force_zip64=True) as member:
                    member.write(content.encode())
            else:
                archive.writestr(info, content)
    result = run(stream.getvalue())
    assert result.assessment.status.value == 'FAILED'
    assert [code.value for code in result.assessment.error_codes] == ['UNSUPPORTED_FILE_FORMAT']


def test_configuration_records_complete_deflate_policy():
    configuration = json.loads(run(deflate_package()).artifacts[0].data)
    strategy = configuration['parser_strategy']
    assert strategy['strategy_version'] == '1.2.0'
    assert strategy['qualified_zip_compression_methods'] == [
        {'code': ZIP_STORED, 'name': 'STORED'},
        {'code': ZIP_DEFLATED, 'name': 'DEFLATE'},
    ]
    assert strategy['deflate_compressed_input_chunk_bytes'] == 32 * 1024
    assert strategy['deflate_expanded_output_chunk_bytes'] == 64 * 1024
    assert strategy['deflate_window_bits'] == -15
    assert strategy['deflate_flush'] == 'NEVER'
    assert strategy['deflate_actual_size'] == 'REQUIRED'
    assert strategy['deflate_actual_crc32'] == 'REQUIRED'
    assert strategy['deflate_eof'] == 'REQUIRED'
    assert strategy['deflate_trailing_data'] == 'REFUSED'
    assert strategy['python_version']
    assert strategy['zlib_compile_version']
    assert strategy['zlib_runtime_version']
