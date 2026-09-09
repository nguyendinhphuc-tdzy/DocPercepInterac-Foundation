"""Internal sequential ZIP/XML mechanics. No DOM, content collection or I/O writes."""
from binascii import crc32
from dataclasses import dataclass
from struct import unpack_from
import sys
from xml.parsers import expat
from zipfile import ZIP_DEFLATED, ZIP_STORED
from zlib import ZLIB_RUNTIME_VERSION, ZLIB_VERSION, decompressobj, error as ZlibError

from foundation.domain import ErrorCode

CHUNK_BYTES = 64 * 1024
DEFLATE_INPUT_CHUNK_BYTES = 32 * 1024
DEFLATE_OUTPUT_CHUNK_BYTES = 64 * 1024
DEFLATE_WINDOW_BITS = -15
UTF8_NAME_FLAG = 0x0800
DATA_DESCRIPTOR_FLAG = 0x0008
STORED_ALLOWED_FLAGS = UTF8_NAME_FLAG
DEFLATE_ALLOWED_FLAGS = UTF8_NAME_FLAG | 0x0006
ZIP64_EXTRA_FIELD_ID = 0x0001
OPC_GROWTH_HINT_EXTRA_FIELD_ID = 0xA220
OPC_GROWTH_HINT_SIGNATURE = 0xA028
ENCRYPTION_EXTRA_FIELD_IDS = frozenset((0x0014, 0x0015, 0x0016, 0x0017, 0x9901))
PARSER_STRATEGY = {
    'strategy_version': '1.2.0',
    'implementation_revision': 'opc-growth-hint-allowlist-1',
    'capacity': 'sequential streaming pre-pass; aggregate start-element gate',
    'CONTROL_XML': 'content types and .rels; shared events plus direct-child records',
    'BULK_XML': 'all other .xml; shared events without tree or text retention',
    'dom': 'NONE', 'chunk_bytes': CHUNK_BYTES,
    'external_entities': 'REFUSED', 'dtd': 'REFUSED',
    'qualified_zip_compression_methods': [
        {'code': ZIP_STORED, 'name': 'STORED'},
        {'code': ZIP_DEFLATED, 'name': 'DEFLATE'},
    ],
    'zip_data_descriptors': 'REFUSED',
    'zip64': 'REFUSED',
    'zip_allowed_general_purpose_flags': {
        'STORED': STORED_ALLOWED_FLAGS,
        'DEFLATE': DEFLATE_ALLOWED_FLAGS,
    },
    'physical_member_layout': 'local/central core fields agree; members contiguous before central directory',
    'zip_extra_field_policy': {
        'LOCAL': {'0xA220': 'OPC Growth Hint; signature 0xA028 and zero padding required'},
        'CENTRAL': {},
        'duplicates': 'REFUSED',
        'unknown': 'REFUSED',
    },
    'deflate_compressed_input_chunk_bytes': DEFLATE_INPUT_CHUNK_BYTES,
    'deflate_expanded_output_chunk_bytes': DEFLATE_OUTPUT_CHUNK_BYTES,
    'deflate_window_bits': DEFLATE_WINDOW_BITS,
    'deflate_flush': 'NEVER',
    'deflate_actual_size': 'REQUIRED',
    'deflate_actual_crc32': 'REQUIRED',
    'deflate_eof': 'REQUIRED',
    'deflate_trailing_data': 'REFUSED',
    'python_version': sys.version.split()[0],
    'zlib_compile_version': ZLIB_VERSION,
    'zlib_runtime_version': ZLIB_RUNTIME_VERSION,
    'expat_version': expat.EXPAT_VERSION,
}


class InspectionFailure(Exception):
    def __init__(self, code, reason):
        self.code, self.reason = code, reason
        super().__init__(reason)


@dataclass(frozen=True)
class MemberEnvelope:
    data_start: int
    data_end: int


@dataclass(frozen=True)
class ExtraFieldRecord:
    header_id: int
    declared_length: int
    payload: bytes
    location: str
    occurrence: int


def _extra_fields(extra, location):
    """Parse a complete ZIP extra-field sequence without interpreting payloads."""
    offset = 0
    occurrence = 0
    records = []
    seen = set()
    while offset < len(extra):
        if offset + 4 > len(extra):
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Malformed ZIP extra field')
        kind, length = unpack_from('<HH', extra, offset)
        offset += 4
        end = offset + length
        if end > len(extra):
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Malformed ZIP extra field')
        if kind in seen:
            raise InspectionFailure(
                ErrorCode.UNSUPPORTED_FILE_FORMAT,
                f'Duplicate ZIP extra field is outside qualified {location} profile',
            )
        seen.add(kind)
        records.append(ExtraFieldRecord(kind, length, extra[offset:end], location, occurrence))
        occurrence += 1
        offset = end
    return tuple(records)


def _validate_extra_fields(extra, location):
    records = _extra_fields(extra, location)
    for record in records:
        if record.header_id == ZIP64_EXTRA_FIELD_ID:
            raise InspectionFailure(ErrorCode.UNSUPPORTED_FILE_FORMAT, 'ZIP64 is outside qualified preflight profile')
        if record.header_id in ENCRYPTION_EXTRA_FIELD_IDS:
            raise InspectionFailure(ErrorCode.ENCRYPTED_DOCUMENT, 'ZIP encryption extra field is outside qualified preflight profile')
        if record.header_id != OPC_GROWTH_HINT_EXTRA_FIELD_ID or location != 'LOCAL':
            raise InspectionFailure(
                ErrorCode.UNSUPPORTED_FILE_FORMAT,
                f'ZIP extra field is outside qualified {location} profile',
            )
        if record.declared_length < 4:
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Malformed OPC Growth Hint extra field')
        signature, _padding_initial_value = unpack_from('<HH', record.payload)
        if signature != OPC_GROWTH_HINT_SIGNATURE or any(record.payload[4:]):
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Malformed OPC Growth Hint extra field')
    return records


def validate_package_profile(data, infos, central_directory_offset):
    """Validate the exact physical envelope before any member expansion.

    STORED retains ZipExtFile integrity finalization. DEFLATE uses the returned
    physical range with Foundation-bounded raw zlib; ZipExtFile is not its size,
    CRC or EOF authority.
    """
    eocd_offset = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    if eocd_offset >= 20 and data[eocd_offset - 20:eocd_offset - 16] == b'PK\x06\x07':
        raise InspectionFailure(ErrorCode.UNSUPPORTED_FILE_FORMAT, 'ZIP64 is outside qualified preflight profile')
    if any(info.compress_type not in (ZIP_STORED, ZIP_DEFLATED) for info in infos):
        raise InspectionFailure(
            ErrorCode.UNSUPPORTED_FILE_FORMAT,
            'ZIP compression method is outside qualified preflight profile',
        )
    if any(info.flag_bits & DATA_DESCRIPTOR_FLAG for info in infos):
        raise InspectionFailure(
            ErrorCode.UNSUPPORTED_FILE_FORMAT,
            'ZIP data descriptors are outside qualified preflight profile',
        )
    for info in infos:
        allowed = STORED_ALLOWED_FLAGS if info.compress_type == ZIP_STORED else DEFLATE_ALLOWED_FLAGS
        if info.flag_bits & ~allowed:
            raise InspectionFailure(
                ErrorCode.UNSUPPORTED_FILE_FORMAT,
                'ZIP general-purpose flags are outside qualified preflight profile',
            )
        _validate_extra_fields(info.extra, 'CENTRAL')

    ordered = sorted(infos, key=lambda info: info.header_offset)
    if ordered and ordered[0].header_offset != 0:
        raise InspectionFailure(
            ErrorCode.CORRUPTED_DOCUMENT,
            'ZIP local/central metadata or physical member layout is inconsistent',
        )
    envelopes = {}
    for index, info in enumerate(ordered):
        offset = info.header_offset
        if offset < 0 or offset + 30 > len(data):
            raise InspectionFailure(
                ErrorCode.CORRUPTED_DOCUMENT,
                'ZIP local/central metadata or physical member layout is inconsistent',
            )
        signature, version_needed, flags, method, _, _, crc, compressed, expanded, name_length, extra_length = unpack_from(
            '<IHHHHHIIIHH', data, offset
        )
        name_start = offset + 30
        extra_start = name_start + name_length
        data_start = extra_start + extra_length
        local_extra = data[extra_start:data_start]
        _validate_extra_fields(local_extra, 'LOCAL')
        if (
            version_needed >= 45
            or info.extract_version >= 45
            or compressed == 0xFFFFFFFF
            or expanded == 0xFFFFFFFF
        ):
            raise InspectionFailure(ErrorCode.UNSUPPORTED_FILE_FORMAT, 'ZIP64 is outside qualified preflight profile')
        expected_name = info.filename.encode('utf-8' if info.flag_bits & 0x800 else 'cp437')
        next_offset = ordered[index + 1].header_offset if index + 1 < len(ordered) else central_directory_offset
        if (
            signature != 0x04034B50
            or flags != info.flag_bits
            or method != info.compress_type
            or crc != info.CRC
            or compressed != info.compress_size
            or expanded != info.file_size
            or (method == ZIP_STORED and compressed != expanded)
            or data[name_start:name_start + name_length] != expected_name
            or data_start + compressed != next_offset
        ):
            raise InspectionFailure(
                ErrorCode.CORRUPTED_DOCUMENT,
                'ZIP local/central metadata or physical member layout is inconsistent',
            )
        envelopes[info.header_offset] = MemberEnvelope(data_start, data_start + compressed)
    return envelopes


def part_strategy(name):
    return 'CONTROL_XML' if name == '[Content_Types].xml' or name.endswith('.rels') else 'BULK_XML'


@dataclass
class ReadBudget:
    config: object
    expanded_bytes: int = 0
    elements: int = 0

    def element(self):
        self.elements += 1
        if self.elements > self.config.max_xml_elements:
            raise InspectionFailure(ErrorCode.DOCUMENT_TOO_LARGE, 'Configured XML element limit exceeded')

    def output(self, count, part_total):
        self.expanded_bytes += count
        if part_total > self.config.max_part_bytes or self.expanded_bytes > self.config.max_uncompressed_bytes:
            raise InspectionFailure(ErrorCode.DOCUMENT_TOO_LARGE, 'Configured expanded package limits exceeded')


def _stored_chunks(archive, info, budget):
    consumed = 0
    with archive.open(info, 'r') as stream:
        while consumed < info.file_size:
            block = stream.read(min(CHUNK_BYTES, info.file_size - consumed))
            if not block:
                break
            consumed += len(block)
            budget.output(len(block), consumed)
            yield block
        # Force ZipExtFile through its terminal CRC check, including when the
        # declared expanded size is zero. Physical suffixes are handled by
        # validate_package_profile(), not by this terminal read.
        stream.read(1)
    if consumed != info.file_size:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Expanded member size disagrees with ZIP metadata')


def _deflate_chunks(data, info, envelope, budget):
    compressed = memoryview(data)[envelope.data_start:envelope.data_end]
    decompressor = decompressobj(DEFLATE_WINDOW_BITS)
    supplied = 0
    pending = b''
    actual_size = 0
    actual_crc = 0

    while not decompressor.eof:
        if not pending and supplied < len(compressed):
            end = min(supplied + DEFLATE_INPUT_CHUNK_BYTES, len(compressed))
            pending = compressed[supplied:end]
            supplied = end
        input_size = len(pending)
        try:
            output = decompressor.decompress(pending, max_length=DEFLATE_OUTPUT_CHUNK_BYTES)
        except ZlibError as exc:
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Invalid DEFLATE stream') from exc
        pending = decompressor.unconsumed_tail
        if output:
            actual_size += len(output)
            actual_crc = crc32(output, actual_crc)
            budget.output(len(output), actual_size)
            yield output
        if decompressor.eof:
            break
        if input_size and len(pending) == input_size and not output:
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Incomplete DEFLATE stream')
        if not pending and supplied == len(compressed) and not output:
            raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Incomplete DEFLATE stream')

    if supplied != len(compressed) or pending or decompressor.unused_data:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'DEFLATE stream has trailing compressed data')
    if actual_size != info.file_size:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Actual DEFLATE size disagrees with ZIP metadata')
    if actual_crc & 0xFFFFFFFF != info.CRC:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Actual DEFLATE CRC disagrees with ZIP metadata')


def member_chunks(data, archive, info, envelope, budget):
    if info.compress_type == ZIP_STORED:
        yield from _stored_chunks(archive, info, budget)
    else:
        yield from _deflate_chunks(data, info, envelope, budget)


def walk_xml(chunks, budget, observe=None):
    """Shared QName/attribute event interpretation; values are never collected."""
    parser = expat.ParserCreate(namespace_separator='}')
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    depth = 0
    observer_error = None

    def expanded(name):
        return '{' + name if '}' in name else name

    def start(name, attrs):
        nonlocal depth, observer_error
        budget.element()  # Mandatory before observation state is added.
        depth += 1
        if observe is not None:
            try:
                observe(expanded(name), {expanded(k):v for k,v in attrs.items()}, depth)
            except (ValueError, LookupError) as exc:
                observer_error = exc
                raise

    def end(name):
        nonlocal depth
        depth -= 1

    def refuse(*args):
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'DTD declarations are outside the inspection profile')

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = refuse
    parser.ExternalEntityRefHandler = refuse
    # No character-data handler, TreeBuilder or unsafe reparse-deferral override.
    try:
        for block in chunks:
            parser.Parse(block, False)
        parser.Parse(b'', True)
    except expat.ExpatError as exc:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Malformed or inconsistent OPC/XML package') from exc
    except (ValueError, LookupError) as exc:
        if exc is observer_error:
            raise
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Malformed or unsupported XML encoding') from exc


def scan_capacity(data, archive, infos, envelopes, config):
    """Phase C: drain every member for CRC parity, stop immediately on XML excess."""
    budget = ReadBudget(config)
    for name, info in sorted(infos.items()):
        chunks = member_chunks(data, archive, info, envelopes[info.header_offset], budget)
        try:
            if name.endswith(('.xml', '.rels')):
                walk_xml(chunks, budget)
            else:
                for _ in chunks:
                    pass
        finally:
            chunks.close()
    return budget.elements


def inspect_parts(data, archive, infos, envelopes, config, observer_factory):
    """Phase D: retain reductions only; release each parser/member before yielding."""
    budget = ReadBudget(config)
    for name, info in sorted(infos.items()):
        if not name.endswith(('.xml', '.rels')):
            continue
        observer = observer_factory(name, part_strategy(name))
        chunks = member_chunks(data, archive, info, envelopes[info.header_offset], budget)
        try:
            walk_xml(chunks, budget, observer.start)
        finally:
            chunks.close()
        yield name, observer
