"""Internal sequential ZIP/XML mechanics. No DOM, content collection or I/O writes."""
from dataclasses import dataclass
from xml.parsers import expat

from foundation.domain import ErrorCode

CHUNK_BYTES = 64 * 1024
PARSER_STRATEGY = {
    'strategy_version': '1.0.0',
    'capacity': 'sequential streaming pre-pass; aggregate start-element gate',
    'CONTROL_XML': 'content types and .rels; shared events plus direct-child records',
    'BULK_XML': 'all other .xml; shared events without tree or text retention',
    'dom': 'NONE', 'chunk_bytes': CHUNK_BYTES,
    'external_entities': 'REFUSED', 'dtd': 'REFUSED',
    'expat_version': expat.EXPAT_VERSION,
}


class InspectionFailure(Exception):
    def __init__(self, code, reason):
        self.code, self.reason = code, reason
        super().__init__(reason)


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
        while True:
            # Read at most one byte beyond the declared part envelope before refusal.
            block = stream.read(min(CHUNK_BYTES, info.file_size - consumed + 1))
            if not block:
                break
            consumed += len(block)
            budget.expanded_bytes += len(block)
            if consumed > info.file_size:
                raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Expanded member size disagrees with ZIP metadata')
            if consumed > budget.config.max_part_bytes or budget.expanded_bytes > budget.config.max_uncompressed_bytes:
                raise InspectionFailure(ErrorCode.DOCUMENT_TOO_LARGE, 'Configured expanded package limits exceeded')
            yield block
    if consumed != info.file_size:
        raise InspectionFailure(ErrorCode.CORRUPTED_DOCUMENT, 'Expanded member size disagrees with ZIP metadata')


def walk_xml(chunks, budget, observe=None):
    """Shared QName/attribute event interpretation; values are never collected."""
    parser = expat.ParserCreate(namespace_separator='}')
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    depth = 0

    def expanded(name):
        return '{' + name if '}' in name else name

    def start(name, attrs):
        nonlocal depth
        budget.element()  # Mandatory before observation state is added.
        depth += 1
        if observe is not None:
            observe(expanded(name), {expanded(k):v for k,v in attrs.items()}, depth)

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
