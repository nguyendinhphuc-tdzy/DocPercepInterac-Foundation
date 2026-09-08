"""Private B1.2R evaluation. No production mapping, native addressing or mutation.

Public summaries are constructed from closed vocabularies, never by removing a
few known secrets from a raw export. Review input is local SME evidence, not an
authenticated approval service and never document mutation authority.
"""

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
import logging
import os
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker

from foundation.adapters.preflight import OoxmlPreflight
from foundation.domain import DocumentPreflightAssessment, DocumentVersion
from . import docling_probe as probe

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / 'qualification/b1/representative'
CORPUS_ENV = 'FOUNDATION_B1_PRIVATE_CORPUS_DIR'
SCHEMA = json.loads((SPEC / 'corpus.schema.json').read_text(encoding='utf-8'))
FEATURES = tuple(SCHEMA['$defs']['Feature']['enum'])
REVIEW_DIMENSIONS = tuple(SCHEMA['$defs']['ReviewDimension']['enum'])
REPEATABILITY = ('conversion', 'content', 'structure', 'tables', 'ordering', 'references')
EVALUATION_STATUSES = ('EVALUATED', 'FAILED', 'NOT_EVALUATED')
FEATURE_STATUSES = ('OBSERVED', 'NOT_OBSERVED', 'NOT_EVALUATED')


class QualificationError(ValueError):
    """Messages are deliberately fixed safe codes, not input/path diagnostics."""


@contextmanager
def quiet_native_output():
    """Discard low-level engine stdout/stderr too; serial qualification CLI only."""
    saved = []
    try:
        with open(os.devnull, 'wb') as sink:
            for fd in (1, 2):
                saved.append((fd, os.dup(fd)))
                os.dup2(sink.fileno(), fd)
            yield
    finally:
        for fd, original in reversed(saved):
            os.dup2(original, fd)
            os.close(original)


def validate_manifest(value):
    validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
    if not validator.is_valid(value):
        raise QualificationError('INVALID_PRIVATE_MANIFEST')
    ids = [c['case_id'] for c in value['cases']]
    if len(ids) != len(set(ids)) or any(c['case_id'].split('-')[1] != c['format'] for c in value['cases']):
        raise QualificationError('INVALID_CASE_IDENTITY')


def corpus_root(repo=ROOT):
    configured = os.environ.get(CORPUS_ENV)
    if not configured:
        return None
    root = Path(configured).resolve()
    repo = Path(repo).resolve()
    if not root.is_dir():
        raise QualificationError('CORPUS_UNAVAILABLE')
    if root.is_relative_to(repo) or repo.is_relative_to(root):
        raise QualificationError('PRIVATE_CORPUS_MUST_BE_OUTSIDE_REPOSITORY')
    return root


def private_path(path, repo=ROOT):
    """Confine metadata/output to the actual ignored directory, including links."""
    repo = Path(repo).resolve()
    boundary = repo / '.foundation-private'
    if boundary.resolve() != boundary:
        raise QualificationError('PRIVATE_OUTPUT_BOUNDARY')
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(boundary) or resolved == boundary:
        raise QualificationError('PRIVATE_OUTPUT_BOUNDARY')
    return resolved


def review_valid(case):
    review = case.get('review')
    if not Draft202012Validator(SCHEMA['$defs']['Review'], format_checker=FormatChecker()).is_valid(review):
        return False
    if (review['status'] != 'COMPLETED' or not review['reviewer_id'].strip()
            or review['input_sha256'] != case.get('input_sha256')
            or review['observation_digest'] != case.get('observation_digest')):
        return False
    if any(v in ('NOT_EVALUATED', 'REVIEW_REQUIRED') for v in review['dimensions'].values()):
        return False
    return not any(loss['critical_semantic_loss'] and (
        loss['classification'] != 'SEMANTIC_REQUIRED' or loss['recoverable_by_native_identity'])
        for loss in review['losses'])


def decide(full):
    """Conservative, unweighted qualification recommendation, never authority."""
    cases = full['cases']
    if full['corpus_status'] != 'AVAILABLE' or not cases:
        return 'INSUFFICIENT_EVIDENCE'
    coverage = full['manifest']['coverage_review']
    if coverage['status'] != 'COMPLETED' or not coverage['reviewer_id'].strip() or not coverage['rationale'].strip():
        return 'INSUFFICIENT_EVIDENCE'
    covered = {p for c in cases if c['evaluation_status'] == 'EVALUATED' for p in c['expected_feature_profile']}
    if not set(full['manifest']['required_profiles']) <= covered:
        return 'INSUFFICIENT_EVIDENCE'
    if any(not review_valid(c) or not c['input_unchanged'] or c['evaluation_status'] != 'EVALUATED' for c in cases):
        return 'INSUFFICIENT_EVIDENCE'
    critical_cases = sum(any(l['critical_semantic_loss'] for l in c['review']['losses']) for c in cases)
    # "Repeated representative cases" requires more than one distinct input.
    critical_hashes = {c['input_sha256'] for c in cases if any(l['critical_semantic_loss'] for l in c['review']['losses'])}
    if critical_cases >= 2 and len(critical_hashes) >= 2:
        return 'RECONSIDER_DOCLING_BASELINE'
    if critical_cases or any(not c['conversion_success'] or any(v != 'PASS' for v in c['repeatability'].values()) for c in cases):
        return 'INSUFFICIENT_EVIDENCE'
    losses = [loss for c in cases for loss in c['review']['losses']]
    if any(l['classification'] in ('UNKNOWN', 'SEMANTIC_REQUIRED') for l in losses):
        return 'INSUFFICIENT_EVIDENCE'
    if any(c['review']['dimensions'][d] != 'PASS' for c in cases for d in
           ('CONTENT_FIDELITY', 'STRUCTURE_FIDELITY', 'TABLE_FIDELITY', 'BUSINESS_RELEVANT_STRUCTURE', 'SEMANTIC_LOSS', 'FAILURE_TRANSPARENCY')):
        return 'INSUFFICIENT_EVIDENCE'
    if any(l['classification'] == 'NATIVE_REQUIRED' for l in losses):
        return 'PROVISIONAL_COORDINATE_B1_2B_AND_B1_3'
    if any(c['review']['dimensions']['NATIVE_IDENTITY_LOSS'] != 'PASS' for c in cases):
        return 'INSUFFICIENT_EVIDENCE'
    return 'PROVISIONAL_CONTINUE_TO_B1_2B'


# Presence observations reuse B1.1 findings and Docling collections. They do not
# establish semantic equivalence, exact addresses, business relevance or absence
# of an unobserved native structure. Unimplemented feature checks stay explicit.
NATIVE_FEATURES = {'NARRATIVE': 'paragraph', 'TABLES': 'table', 'HEADERS': 'header',
    'FOOTERS': 'footer', 'HYPERLINKS': 'hyperlink', 'FIELDS': 'field', 'BOOKMARKS': 'bookmark',
    'CONTENT_CONTROLS': 'content_control', 'DRAWINGS': 'drawing', 'CELLS': 'cell',
    'FORMULAS': 'formula', 'DEFINED_NAMES': 'defined_name', 'MERGED_RANGES': 'merged_cells'}


def feature_observations(profiles, assessment, runs):
    kinds = {f.native_object_type for f in assessment.native_structure_findings}
    successful = [r for r in runs if r['conversion_status'] == 'PASS']
    doc = successful[0]['semantic_document'] if successful else {}
    counts = successful[0]['observations']['collection_counts'] if successful else {}
    semantic = {'NARRATIVE': bool(doc.get('texts')), 'TABLES': bool(doc.get('tables')),
        'HEADINGS': any(t.get('label') == 'section_header' for t in doc.get('texts', [])),
        'IMAGES': bool(counts.get('pictures')), 'HYPERLINKS': any(t.get('hyperlink') for t in doc.get('texts', [])),
        'MULTIPLE_SHEETS': sum(g.get('label') == 'sheet' for g in doc.get('groups', [])) > 1}
    checks = []
    for feature in profiles:
        native = ('OBSERVED' if NATIVE_FEATURES[feature] in kinds else 'NOT_OBSERVED') if feature in NATIVE_FEATURES else 'NOT_EVALUATED'
        if feature == 'PROTECTION':
            native = 'OBSERVED' if assessment.protection_findings else 'NOT_OBSERVED'
        checks.append({'feature': feature, 'native_presence': native,
            'semantic_presence': ('OBSERVED' if semantic[feature] else 'NOT_OBSERVED') if successful and feature in semantic else 'NOT_EVALUATED',
            'fidelity': 'REVIEW_REQUIRED'})
    return checks


def evaluate_case(case, path):
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    initial = path.read_bytes()
    input_hash = sha256(initial).hexdigest()
    document = DocumentVersion(schema_version='0.1.0', object_type='DocumentVersion',
        id='version-' + case['case_id'], revision=1, created_at=now, task_id='qualification-b1-representative',
        document_id='document-' + case['case_id'], binary_hash=input_hash, byte_length=len(initial),
        content_ref={'uri': 'urn:private:sha256:' + input_hash, 'sha256': input_hash, 'media_type': 'application/octet-stream'})
    resolver = probe.LocalPinnedContent(path)
    adapter = OoxmlPreflight(resolver)
    started = DocumentPreflightAssessment(schema_version='0.1.0', object_type='DocumentPreflightAssessment',
        id='preflight-' + case['case_id'], revision=2, created_at=now, task_id=document.task_id,
        document_version_ref={'document_id': document.document_id, 'version_id': document.id, 'binary_hash': input_hash},
        status='ASSESSING', detected_format=None, detected_conformance='UNKNOWN', format_observation_refs=[],
        protection_findings=[], native_structure_findings=[], capability_results=[],
        assessor={'actor_type': 'SYSTEM', 'actor_id': 'representative-evaluator'}, engine=adapter.engine,
        engine_version=adapter.version, configuration_ref=adapter.configuration.ref, assessed_at=None, error_codes=[])
    value = {**case, 'input_sha256': input_hash, 'local_path': str(path), 'document': document.model_dump(mode='json'),
        'evaluation_status': 'FAILED', 'runs': [], 'preflight': None, 'feature_checks': [],
        'input_unchanged': False, 'conversion_success': False,
        'repeatability': {k: 'NOT_EVALUATED' for k in REPEATABILITY}, 'limitations': ['REVIEW_REQUIRED']}
    capture = StringIO()
    old_disable = logging.root.manager.disable
    try:
        # Serial CLI only. Suppress third-party Python logs and capture prints;
        # neither engine diagnostics nor document contents go to public stdout.
        logging.disable(logging.CRITICAL)
        with redirect_stdout(capture), redirect_stderr(capture), quiet_native_output():
            assessment = adapter.assess(document, started, now)
            value['preflight'] = {'assessment': assessment.assessment.model_dump(mode='json', exclude_unset=True),
                'artifacts': [{'ref': a.ref.model_dump(mode='json'), 'canonical_utf8': a.data.decode()} for a in assessment.artifacts]}
            if (assessment.assessment.status.value != 'COMPLETED'
                    or assessment.assessment.detected_format.value != case['format']):
                raise QualificationError('PREFLIGHT_REFUSED_OR_FORMAT_MISMATCH')
            value['runs'] = [probe.probe_once(document, resolver, case['format']) for _ in range(3)]
            value['repeatability'] = {'conversion': 'PASS' if len({r['conversion_status'] for r in value['runs']}) == 1 else 'OBSERVED_LIMITATION',
                                     **probe.compare_runs(value['runs'])}
            value['conversion_success'] = all(r['conversion_status'] == 'PASS' for r in value['runs'])
            value['feature_checks'] = feature_observations(case['expected_feature_profile'], assessment.assessment, value['runs'])
            value['evaluation_status'] = 'EVALUATED'
    except Exception as exc:
        value['private_error'] = str(exc)
    finally:
        logging.disable(old_disable)
        value['private_console'] = capture.getvalue()
        try:
            value['post_input_sha256'] = sha256(path.read_bytes()).hexdigest()
            value['input_unchanged'] = value['post_input_sha256'] == input_hash
        except OSError:
            value['post_input_sha256'] = None
        if not value['input_unchanged']:
            value['evaluation_status'] = 'FAILED'
    stable = {'input_sha256': input_hash, 'configuration': probe.CONFIGURATION,
        'preflight_engine': adapter.engine, 'preflight_version': adapter.version,
        'preflight_configuration': adapter.configuration.ref.model_dump(mode='json'),
        'preflight_status': value['preflight']['assessment']['status'] if value['preflight'] else None,
        'feature_checks': value['feature_checks'],
        'runs': [{k: v for k, v in r.items() if k != 'elapsed_seconds'} for r in value['runs']],
        'input_unchanged': value['input_unchanged']}
    value['observation_digest'] = probe.digest(stable)
    return value


def evaluate(manifest, repo=ROOT):
    root = corpus_root(repo)
    if root is None:
        return {'corpus_status': 'CORPUS_NOT_PROVIDED', 'cases': [], 'manifest': None}
    validate_manifest(manifest)
    paths = []
    for case in manifest['cases']:
        path = (root / case['local_path']).resolve()
        if not path.is_relative_to(root) or path.is_relative_to(Path(repo).resolve()) or path == root:
            raise QualificationError('PRIVATE_INPUT_BOUNDARY')
        paths.append(path)
    results = []
    for case, path in zip(manifest['cases'], paths):
        if case['review_status'] != 'APPROVED_FOR_EVALUATION' or not path.is_file():
            results.append({**case, 'evaluation_status': 'NOT_EVALUATED', 'input_unchanged': False,
                'conversion_success': False, 'repeatability': {k: 'NOT_EVALUATED' for k in REPEATABILITY},
                'feature_checks': [], 'limitations': ['REVIEW_REQUIRED']})
        else:
            results.append(evaluate_case(case, path))
    return {'corpus_status': 'AVAILABLE', 'cases': results, 'manifest': manifest}


def sanitize(full):
    """Build a safe public projection; no free text, path or document hash fields."""
    if full['corpus_status'] not in ('AVAILABLE', 'CORPUS_NOT_PROVIDED'):
        raise QualificationError('INVALID_PUBLIC_STATUS')
    cases = []
    for case in full['cases']:
        if (not re.fullmatch(r'LF-(DOCX|XLSX)-(?!000)[0-9]{3}', case['case_id'])
                or case['format'] not in ('DOCX', 'XLSX') or case['case_id'].split('-')[1] != case['format']
                or case['document_role'] not in ('TARGET', 'SOURCE', 'REFERENCE')
                or case['evaluation_status'] not in EVALUATION_STATUSES
                or any(p not in FEATURES for p in case['expected_feature_profile'])
                or set(case['repeatability']) != set(REPEATABILITY)
                or any(v not in ('PASS', 'OBSERVED_LIMITATION', 'NOT_EVALUATED') for v in case['repeatability'].values())):
            raise QualificationError('UNSAFE_PUBLIC_PROJECTION')
        checks = []
        for check in case['feature_checks']:
            if (check['feature'] not in FEATURES or any(check[k] not in FEATURE_STATUSES for k in ('native_presence', 'semantic_presence'))):
                raise QualificationError('UNSAFE_FEATURE_PROJECTION')
            checks.append({k: check[k] for k in ('feature', 'native_presence', 'semantic_presence')})
        valid = review_valid(case)
        cases.append({'case_id': case['case_id'], 'format': case['format'],
            'document_role_category': case['document_role'], 'feature_profile': list(case['expected_feature_profile']),
            'evaluation_status': case['evaluation_status'], 'repeatability': dict(case['repeatability']),
            'input_integrity': 'PASS' if case['input_unchanged'] is True else 'NOT_CONFIRMED',
            'review_status': 'COMPLETED' if valid else 'REVIEW_REQUIRED',
            'review_dimensions': {d: case['review']['dimensions'][d] if valid else 'REVIEW_REQUIRED' for d in REVIEW_DIMENSIONS},
            'loss_classifications': sorted({l['classification'] for l in case['review']['losses']}) if valid else ['UNKNOWN'],
            'critical_semantic_loss': any(l['critical_semantic_loss'] for l in case['review']['losses']) if valid else None,
            'automated_feature_presence': checks})
    return {'evaluation_version': '1.0.0', 'evidence_kind': 'REPRESENTATIVE_QUALIFICATION',
        'corpus_status': full['corpus_status'], 'decision': decide(full),
        'docling_qualification_status': 'PROVISIONAL_CONTINUE', 'engine': probe.CANDIDATE,
        'engine_version': probe.VERSION, 'production_qualified': False,
        'cases': cases, 'unevaluated_profiles': sorted(set(FEATURES) - {p for c in cases for p in c['feature_profile'] if c['evaluation_status'] == 'EVALUATED'})}
