"""B1.2B provisional Office adapter behind PerceptionPort; never mutation.

Uses the public Office mechanics already exercised by B1.2A/B1.2R. Those
observations are not representative fidelity approval. The application owns
persistence and audit; configuration/schema artifacts are exposed for storage.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from foundation.adapters.preflight import OoxmlPreflight, PreflightConfig
from foundation.adapters.preflight.evidence import EvidenceArtifact
from foundation.domain import (
    AnalysisRun, AnalysisStatus, DocumentPreflightAssessment, DocumentVersion,
    DocumentVersionRef, ErrorCode, PerceptionSnapshot, SemanticObject,
)
from foundation.evaluation.perception.docling_probe import CONFIGURATION, CANDIDATE, VERSION, convert_office
from foundation.ports.content import ContentAccessError, DocumentContentResolverPort, verified_bytes
from foundation.ports.perception import PerceptionResult


def _digest(value):
    # Semantic identity encoding only; never an authorization/AuditEvent digest.
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def _ref(kind, identity):
    return dict(object_type=kind, object_id=identity, revision=1)


@dataclass(frozen=True)
class _PinnedBytes:
    data: bytes

    def resolve(self, document):
        return self.data


class DoclingPerceptionAdapter:
    """Bounded Transitional DOCX/XLSX perception; PROVISIONAL, unqualified.

    No ContentRef URI fetch, corpus lookup, writes, native addressing or approval.
    Standard resource-safe preflight is mandatory even if a caller ran it earlier.
    """
    engine = CANDIDATE
    version = VERSION

    def __init__(self, resolver: DocumentContentResolverPort, preflight_config: PreflightConfig | None = None):
        self.resolver = resolver
        self.preflight = OoxmlPreflight(resolver, preflight_config)
        self.value_schema = EvidenceArtifact.create({
            '$schema':'https://json-schema.org/draft/2020-12/schema',
            'title':'B1.2B observed Docling semantic node v1', 'type':'object',
            'required':['collection','node'], 'additionalProperties':False,
            'properties':{'collection':{'type':'string'}, 'node':{'type':'object'}},
        })
        self.configuration = EvidenceArtifact.create({**CONFIGURATION,
            'adapter_version':'1.0.0', 'production_qualified':False,
            'preflight_configuration_ref':self.preflight.configuration.ref.model_dump(mode='json'),
            'structured_value_schema_ref':self.value_schema.ref.model_dump(mode='json'),
            'ordering':'body then furniture depth-first children; reject unreachable nodes',
            'identity':'task + exact version + analysis revision + configuration + semantic export digest',
        })

    def perceive(self, document: DocumentVersion, analysis_run: AnalysisRun) -> PerceptionResult:
        version_ref = DocumentVersionRef(document_id=document.document_id, version_id=document.id,
                                         binary_hash=document.binary_hash)
        if (analysis_run.task_id != document.task_id or version_ref not in analysis_run.document_version_refs
                or analysis_run.status is not AnalysisStatus.RUNNING):
            raise ContentAccessError(ErrorCode.INVALID_CONTRACT, 'Perception requires a running analysis pinned to the exact task and document version')
        data = verified_bytes(document, self.resolver)
        # The conversion consumes exactly the bytes the preflight inspected.
        preflight = OoxmlPreflight(_PinnedBytes(data), self.preflight.config)
        stamp = analysis_run.created_at
        started = DocumentPreflightAssessment(schema_version='0.1.0', object_type='DocumentPreflightAssessment',
            id='perception-preflight-'+_digest([document.task_id, version_ref.model_dump(), analysis_run.id])[:32],
            revision=2, created_at=stamp, task_id=document.task_id, document_version_ref=version_ref,
            status='ASSESSING', detected_format=None, detected_conformance='UNKNOWN', format_observation_refs=[],
            protection_findings=[], native_structure_findings=[], capability_results=[],
            assessor={'actor_type':'SYSTEM','actor_id':'b1-perception-adapter'}, engine=preflight.engine,
            engine_version=preflight.version, configuration_ref=preflight.configuration.ref, assessed_at=None, error_codes=[])
        assessment = preflight.assess(document, started, stamp).assessment
        if assessment.status.value != 'COMPLETED':
            raise ContentAccessError(assessment.error_codes[0] if assessment.error_codes else ErrorCode.PREFLIGHT_FAILED,
                                     'Perception refused by standard resource-safe preflight')
        if assessment.detected_conformance.value != 'TRANSITIONAL' or assessment.detected_format.value not in ('DOCX','XLSX'):
            raise ContentAccessError(ErrorCode.UNSUPPORTED_FILE_FORMAT, 'Perception supports only bounded Transitional DOCX/XLSX')
        try:
            raw = convert_office(data, assessment.detected_format.value)
            ordered = self._ordered_nodes(raw)
            seed = [document.task_id, version_ref.model_dump(mode='json'), analysis_run.id,
                    analysis_run.revision, self.configuration.ref.sha256, _digest(raw)]
            snapshot_id = 'perception-'+_digest(seed)
            ids = {node['self_ref']:'semantic-'+_digest([snapshot_id, node['self_ref']]) for _, node in ordered}
            objects = []
            for collection, node in ordered:
                text = node.get('text')
                value = ({'kind':'TEXT', 'review_text':text, 'value':text} if isinstance(text, str) else
                         {'kind':'STRUCTURED', 'review_text':str(node.get('label', collection)),
                          'schema_ref':self.value_schema.ref, 'value':{'collection':collection, 'node':node}})
                parent = (node.get('parent') or {}).get('$ref')
                payload = dict(schema_version='0.1.0', object_type='SemanticObject', id=ids[node['self_ref']],
                    revision=1, created_at=stamp, task_id=document.task_id,
                    semantic_reference={'snapshot_ref':_ref('PerceptionSnapshot', snapshot_id),'semantic_id':node['self_ref']},
                    object_kind=node.get('label', collection), value=value, native_binding_refs=[])
                if parent in ids: payload['parent_ref'] = _ref('SemanticObject', ids[parent])
                objects.append(SemanticObject.model_validate(payload))
            limitations = [
                'PROVISIONAL: B1.2R SME fidelity and coverage review remains pending; production_qualified=false.',
                'Presence and repeatability do not establish semantic correctness, source sufficiency or mutation authority.',
                'Semantic references are not native locators; all native binding references remain empty.',
                'Only observed Docling text and structured nodes are represented; no claim of complete Office fidelity.',
                'Remote/local fetch and chart rendering disabled; drawings, organisation charts, fields, revisions and protected content require scoped SME review.',
                'Standard preflight limits retained; Docling conversion has no process-isolated CPU/memory deadline in this provisional adapter.',
            ]
            if assessment.detected_format.value == 'XLSX':
                limitations.append('XLSX formula identity, cached-value freshness and cross-sheet business meaning require independent native enrichment; no recalculation.')
            known = {'texts','tables','groups','pictures','key_value_items','form_items',
                     'schema_name','version','name','origin','body','furniture','pages'}
            for field in sorted(set(raw) - known):
                limitations.append('Engine field '+field+' is outside the semantic projection; NOT_EVALUATED.')
            for kind in sorted({f.native_object_type for f in assessment.native_structure_findings + assessment.protection_findings}):
                limitations.append('Preflight observed '+kind+'; semantic/native fidelity is NOT_EVALUATED by this adapter.')
            snapshot = PerceptionSnapshot(schema_version='0.1.0', object_type='PerceptionSnapshot', id=snapshot_id,
                revision=1, created_at=stamp, task_id=document.task_id, document_version_ref=version_ref,
                analysis_run_ref=dict(object_type='AnalysisRun', object_id=analysis_run.id, revision=analysis_run.revision),
                engine=self.engine, engine_version=self.version, configuration_ref=self.configuration.ref,
                semantic_object_refs=[_ref('SemanticObject', obj.id) for obj in objects], limitations=limitations)
            return PerceptionResult(snapshot, tuple(objects))
        except (ImportError, ContentAccessError):
            raise
        except Exception as exc:
            raise ContentAccessError(ErrorCode.PERCEPTION_FAILED, 'Pinned perception failed; no successful snapshot produced') from exc
        finally:
            verified_bytes(document, self.resolver)

    @staticmethod
    def _ordered_nodes(raw):
        """Validate an engine graph, not an Office parser or semantic matcher."""
        collections = ('texts','tables','groups','pictures','key_value_items','form_items')
        nodes = [(kind, node) for kind in collections for node in raw.get(kind, [])]
        by_ref = {}
        roots = {raw.get(key, {}).get('self_ref') for key in ('body','furniture')} - {None}
        for kind, node in nodes:
            ref = node.get('self_ref')
            if not isinstance(ref, str) or not ref or ref in by_ref or ref in roots:
                raise ValueError('Missing or duplicate semantic reference')
            by_ref[ref] = (kind, node)
        if not by_ref: raise ValueError('Empty semantic representation')
        result, visited = [], set()
        # Iterative traversal avoids recursion amplification from engine output.
        stack = [(child['$ref'], raw[root].get('self_ref')) for root in ('furniture','body')
                 for child in reversed(raw.get(root, {}).get('children', []))]
        while stack:
            ref, parent = stack.pop()
            if ref not in by_ref or ref in visited: raise ValueError('Unresolved, repeated or cyclic semantic child')
            kind, node = by_ref[ref]
            if (node.get('parent') or {}).get('$ref') != parent: raise ValueError('Inconsistent semantic parent')
            visited.add(ref); result.append((kind, node))
            stack.extend((child['$ref'], ref) for child in reversed(node.get('children', [])))
        if visited != set(by_ref): raise ValueError('Unreachable semantic objects')
        return result
