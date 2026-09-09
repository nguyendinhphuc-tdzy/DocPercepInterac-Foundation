"""Internal sequential ZIP/XML mechanics. No DOM, content collection or I/O writes."""
from dataclasses import dataclass
from struct import unpack_from
from xml.parsers import expat
from zipfile import ZIP_STORED

from foundation.domain import ErrorCode

CHUNK_BYTES = 64 * 1024
PARSER_STRATEGY = {
    'strategy_version': '1.1.1',
    'capacity': 'sequential streaming pre-pass; aggregate start-element gate',
    'CONTROL_XML': 'content types and .rels; shared events plus direct-child records',
    'BULK_XML': 'all other .xml; shared events without tree or text retention',
    'dom': 'NONE', 'chunk_bytes': CHUNK_BYTES,
    'external_entities': 'REFUSED', 'dtd': 'REFUSED',
    'qualified_zip_compression_methods': [{'code': ZIP_STORED, 'name': 'STORED'}],
    'zip_data_descriptors': 'REFUSED',
    'physical_member_layout': 'local/central fields equal; members contiguous before central directory',
    'expat_version': expat.EXPAT_VERSION,
}


class InspectionFailure(Exception):
    def __init__(self, code, reason):
        self.code, self.reason = code, reason
        super().__init__(reason)


def validate_package_profile(data, infos, central_directory_offset):
    """Admit only the bounded ZIP layout qualified for B1.1.

    ZipExtFile intentionally trusts central-directory sizes and truncates its
    consumer view to the declared expanded size. Physical layout therefore has
    to be checked before member reads; this is header validation, not a second
    decompressor.
    """
    if any(info.compress_type != ZIP_STORED for info in infos):
        raise InspectionFailure(
            ErrorCode.UNSUPPORTED_FILE_FORMAT,
            'ZIP compression method is outside qualified preflight profile',
        )
    if any(info.flag_bits & 0x08 for info in infos):
        raise InspectionFailure(
            ErrorCode.UNSUPPORTED_FILE_FORMAT,
            'ZIP data descriptors are outside qualified preflight profile',
        )

    ordered = sorted(infos, key=lambda info: info.header_offset)
    if ordered and ordered[0].header_offset != 0:
        raise InspectionFailure(
            ErrorCode.CORRUPTED_DOCUMENT,
            'ZIP local/central metadata or physical member layout is inconsistent',
        )
    for index, info in enumerate(ordered):
        offset = info.header_offset
        if offset < 0 or offset + 30 > len(data):
            raise InspectionFailure(
                ErrorCode.CORRUPTED_DOCUMENT,
                'ZIP local/central metadata or physical member layout is inconsistent',
            )
        signature, _, flags, method, _, _, crc, compressed, expanded, name_length, extra_length = unpack_from(
            '<IHHHHHIIIHH', data, offset
        )
        name_start = offset + 30
        extra_start = name_start + name_length
        data_start = extra_start + extra_length
        expected_name = info.filename.encode('utf-8' if info.flag_bits & 0x800 else 'cp437')
        next_offset = ordered[index + 1].header_offset if index + 1 < len(ordered) else central_directory_offset
        if (
            signature != 0x04034B50
            or flags != info.flag_bits
            or method != info.compress_type
            or crc != info.CRC
            or compressed != info.compress_size
            or expanded != info.file_size
            or compressed != expanded
            or data[name_start:name_start + name_length] != expected_name
            or data[extra_start:data_start] != info.extra
            or data_start + compressed != next_offset
        ):
            raise InspectionFailure(
                ErrorCode.CORRUPTED_DOCUMENT,
                'ZIP local/central metadata or physical member layout is inconsistent',
            )


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


def member_chunks(archive, info, budget):
    consumed = 0
    with archive.open(info, 'r') as stream:
        while consumed < info.file_size:
            block = stream.read(min(CHUNK_BYTES, info.file_size - consumed))
            if not block:
                break
            consumed += len(block)
            budget.expanded_bytes += len(block)
            if consumed > budget.config.max_part_bytes or budget.expanded_bytes > budget.config.max_uncompressed_bytes:
                raise InspectionFailure(ErrorCode.DOCUMENT_TOO_LARGE, 'Configured expanded package limits exceeded')
            yield block
        # Force ZipExtFile through its terminal CRC check, including when the
        # declared expanded size is zero. Physical suffixes are handled by
        # validate_package_profile(), not by this terminal read.
        stream.read(1)
    if consumed != info.file_size:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Expanded member size disagrees with ZIP metadata')


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


def scan_capacity(archive, infos, config):
    """Phase C: drain every member for CRC parity, stop immediately on XML excess."""
    budget = ReadBudget(config)
    for name, info in sorted(infos.items()):
        chunks = member_chunks(archive, info, budget)
        try:
            if name.endswith(('.xml', '.rels')):
                walk_xml(chunks, budget)
            else:
                for _ in chunks:
                    pass
        finally:
            chunks.close()
    return budget.elements


def inspect_parts(archive, infos, config, observer_factory):
    """Phase D: retain reductions only; release each parser/member before yielding."""
    budget = ReadBudget(config)
    for name, info in sorted(infos.items()):
        if not name.endswith(('.xml', '.rels')):
            continue
        observer = observer_factory(name, part_strategy(name))
        chunks = member_chunks(archive, info, budget)
        try:
            walk_xml(chunks, budget, observer.start)
        finally:
            chunks.close()
        yield name, observer
