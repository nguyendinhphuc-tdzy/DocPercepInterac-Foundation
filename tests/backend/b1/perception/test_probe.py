"""Optional in B0; B1 sets FOUNDATION_B1_REQUIRE_DOCLING=1 to prohibit skips."""

from copy import deepcopy
from hashlib import sha256
from importlib import metadata
import os
from pathlib import Path

import pytest

from foundation.domain import ErrorCode
from foundation.ports.content import ContentAccessError
from foundation.evaluation.perception import docling_probe as probe
from tests.backend.b1.preflight.test_ooxml import document, Resolver
from tools.b1.build_corpus import docx_parts, package


@pytest.fixture
def candidate():
    try:
        probe.installed_candidate()
    except metadata.PackageNotFoundError:
        if os.environ.get('FOUNDATION_B1_REQUIRE_DOCLING')=='1':
            pytest.fail('B1 CI requires installed Docling; skipping is forbidden')
        pytest.skip('Docling intentionally absent in B0 environment')


def test_hash_gate_precedes_docling_import_and_conversion(monkeypatch):
    doc=document(package(docx_parts()))
    monkeypatch.setattr(probe,'installed_candidate',lambda:pytest.fail('candidate inspected before hash gate'))
    with pytest.raises(ContentAccessError) as exc:
        probe.probe_once(doc,Resolver(b'changed'),'DOCX')
    assert exc.value.code is ErrorCode.STALE_DOCUMENT_VERSION


def test_exact_version_cannot_be_substituted(monkeypatch):
    monkeypatch.setattr(probe.metadata,'version',lambda name:'2.125.0')
    with pytest.raises(RuntimeError): probe.installed_candidate()


def test_conversion_failure_retains_hash_without_fake_output(candidate, monkeypatch):
    data=package(docx_parts()); doc=document(data)
    def fail(*args): raise ValueError('synthetic failure')
    monkeypatch.setattr(probe,'convert_office',fail)
    result=probe.probe_once(doc,Resolver(data),'DOCX')
    assert result['input_sha256']==sha256(data).hexdigest()
    assert result['conversion_status']=='FAIL'
    assert result['semantic_document'] is None and result['observations'] is None
    assert result['errors'][0]['error_code']=='PERCEPTION_FAILED'


def test_reference_drift_is_measured_separately_from_content(candidate):
    raw=probe.convert_office(package(docx_parts()),'DOCX')
    changed=deepcopy(raw)
    def rename(value):
        if isinstance(value,dict):
            for key,val in value.items():
                if key in ('self_ref','$ref') and isinstance(val,str) and val.startswith('#/texts/'):
                    value[key]=val+'-rerun'
                else: rename(val)
        elif isinstance(value,list):
            for v in value: rename(v)
    rename(changed)
    old,new=probe.semantic_observations(raw),probe.semantic_observations(changed)
    assert old['signatures']['references']!=new['signatures']['references']
    for kind in ('content','structure','tables','ordering'):
        assert old['signatures'][kind]==new['signatures'][kind]


def test_no_legacy_parser_ai_native_locator_or_mutation_imports():
    import ast
    modules=[Path(probe.__file__), *Path('foundation/adapters/preflight').glob('*.py')]
    forbidden=('foundation.perception','foundation.output','foundation.applications','foundation.api','openai')
    for path in modules:
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or '').startswith(forbidden)
                assert all(a.name not in ('NativeLocator','NativeBinding','ApprovedChangeSet') for a in node.names)
            if isinstance(node,ast.Import):
                assert all(not a.name.startswith(forbidden) for a in node.names)


def test_empty_document_is_not_success(candidate,monkeypatch):
    data=package(docx_parts())
    monkeypatch.setattr(probe,'convert_office',lambda *args:{})
    result=probe.probe_once(document(data),Resolver(data),'DOCX')
    assert result['conversion_status']=='FAIL'


def test_missing_dependency_cannot_count_as_expected_conversion_failure(monkeypatch):
    data=package(docx_parts())
    monkeypatch.setattr(probe,'installed_candidate',lambda:probe.VERSION)
    def missing(*args): raise ImportError('synthetic missing dependency')
    monkeypatch.setattr(probe,'convert_office',missing)
    with pytest.raises(ImportError): probe.probe_once(document(data),Resolver(data),'DOCX')
