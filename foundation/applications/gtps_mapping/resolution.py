"""Engagement-scoped identity and bounded slot allocation; no Office IO."""
from decimal import Decimal
import re
from .planner import MappingError, pointer, verify_view, verify_row_relationship, Selection


def name_key(value):
    # Typographical normalization only; never expands abbreviations/legal forms.
    return ''.join(c for c in value.casefold() if c.isalnum())


def contains_name(text, name):
    words=re.findall(r'[^\W_]+',name.casefold())
    if not words:return False
    return re.search(r'(?<!\w)'+r'[\W_]*'.join(re.escape(w) for w in words)+r'(?!\w)',text.casefold()) is not None


class PartyAliasMap:
    def __init__(self, scope, entries, views):
        if not scope:
            raise MappingError('PARTY_ALIAS_SCOPE_REQUIRED')
        self.scope = scope
        self.entries = entries
        self.names = {}
        bykey = {v.key: v for v in views}
        seen_ids = set()
        for entry in entries:
            party = entry['canonical_party_id']
            if not party or party in seen_ids:
                raise MappingError('PARTY_IDENTITY_REVIEW_REQUIRED')
            seen_ids.add(party)
            names = [entry['canonical_name'], *entry['known_aliases']]
            proof_groups = []
            for ref in entry['evidence_reference']:
                v = bykey.get(ref['document_key'])
                if v is None or v.role not in ('CURRENT_SOURCE', 'HISTORICAL_REFERENCE'):
                    raise MappingError('PARTY_ALIAS_EVIDENCE_INVALID')
                verify_view(v)
                if ref['version'] != v.version.model_dump(mode='json') or ref['digest'] != v.digest:
                    raise MappingError('PARTY_ALIAS_EVIDENCE_INVALID')
                values = []
                paths=list(ref['pointers'])
                if not paths:raise MappingError('PARTY_ALIAS_EVIDENCE_INVALID')
                if len(paths)>1:
                    if not all(p.startswith('/tables/') for p in paths):raise MappingError('PARTY_ALIAS_EVIDENCE_INVALID')
                    verify_row_relationship(v,Selection('RPT',paths[0],paths[0],{str(i):p for i,p in enumerate(paths[1:])}))
                for path, expected in ref['pointers'].items():
                    if pointer(v.data, path) != expected:
                        raise MappingError('PARTY_ALIAS_EVIDENCE_INVALID')
                    values.append(expected)
                # A reference group is an explicit reviewed alias-definition or
                # same-row name/narrative association, retained for mapping review.
                proof_groups.append(' '.join(values))
            for name in names:
                key = name_key(name)
                if not key or not any(contains_name(p,entry['canonical_name']) and contains_name(p,name) for p in proof_groups):
                    raise MappingError('PARTY_ALIAS_EVIDENCE_INVALID')
                if key in self.names and self.names[key] != party:
                    raise MappingError('PARTY_IDENTITY_REVIEW_REQUIRED')
                self.names[key] = party

    def resolve(self, name):
        if name_key(name) not in self.names:
            raise MappingError('PARTY_IDENTITY_REVIEW_REQUIRED')
        return self.names[name_key(name)]


def allocate_rows(facts, capacity, ordering):
    if ordering != 'UNDER_REVIEW_THEN_AMOUNT_DESC':
        raise MappingError('WORKFLOW_PROFILE_CONFIGURATION_REQUIRED')
    if type(capacity) is not int or capacity < len(facts):
        raise MappingError('STRUCTURAL_CAPABILITY_REQUIRED')
    if len({f['identity'] for f in facts}) != len(facts):
        raise MappingError('SOURCE_CONFLICTING')
    ordered = sorted(facts, key=lambda f: (not f['under_review'], -Decimal(f['amount'])))
    # No invented tie breaker for equally material transactions.
    if len({(f['under_review'], Decimal(f['amount'])) for f in facts}) != len(facts):
        raise MappingError('WORKFLOW_PROFILE_CONFIGURATION_REQUIRED')
    return {'status': 'ROW_GROWTH_NOT_REQUIRED_FOR_REPRESENTATIVE_CASE',
            'capacity': capacity, 'required': len(facts),
            'rows': {f['identity']: i+1 for i, f in enumerate(ordered)}}
