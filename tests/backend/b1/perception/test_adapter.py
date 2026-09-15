"""Provisional adapter acceptance; passing these is not SME fidelity approval."""
from copy import deepcopy
from hashlib import sha256

import pytest

from foundation.adapters import perception_docling as module
from foundation.domain import AnalysisRun, ErrorCode, PerceptionSnapshot, SemanticObject
from foundation.ports.content import ContentAccessError
from tests.backend.b1.preflight.test_ooxml import document, Resolver
from tests.backend.b1.perception.test_probe import candidate
from tools.b1.build_corpus import docx_parts, xlsx_parts, package


def analysis(doc):
    return AnalysisRun(schema_version='0.1.0', object_type='AnalysisRun', id='analysis-b1',
        revision=2, created_at='2026-09-09T00:00:00Z', task_id=doc.task_id,
        document_version_refs=[dict(document_id=doc.document_id, version_id=doc.id, binary_hash=doc.binary_hash)],
        target_contract_definition_ref=dict(object_type='TargetContractDefinition', object_id='definition-fixture', revision=1),
        target_contract_instance_ref=dict(object_type='TargetContractInstance', object_id='instance-fixture', revision=1),
        rule_pack_ref=dict(object_type='RulePack', object_id='rules-fixture', revision=1),
        status='RUNNING', output_refs=[], error_codes=[])


@pytest.mark.parametrize('builder', [docx_parts, xlsx_parts])
def test_real_adapter_exact_deterministic_contract_output(candidate, builder):
    data = package(builder()); doc = document(data)
    adapter = module.DoclingPerceptionAdapter(Resolver(data))
    result = adapter.perceive(doc, analysis(doc))
    assert result == adapter.perceive(doc, analysis(doc))
    assert result.snapshot.engine_version == '2.126.0'
    assert result.snapshot.document_version_ref.binary_hash == sha256(data).hexdigest()
    assert result.snapshot.configuration_ref == adapter.configuration.ref
    assert sha256(adapter.configuration.data).hexdigest() == adapter.configuration.ref.sha256
    assert result.snapshot.limitations and result.semantic_objects
    assert 'PROVISIONAL' in ' '.join(result.snapshot.limitations)
    assert PerceptionSnapshot.model_validate(result.snapshot.model_dump()) == result.snapshot
    refs = {r.object_id for r in result.snapshot.semantic_object_refs}
    assert refs == {o.id for o in result.semantic_objects}
    for obj in result.semantic_objects:
        assert SemanticObject.model_validate(obj.model_dump()) == obj
        assert obj.semantic_reference.snapshot_ref.object_id == result.snapshot.id
        assert not obj.native_binding_refs
        assert obj.parent_ref is None or obj.parent_ref.object_id in refs
    assert adapter.resolver.data == data


@pytest.mark.parametrize('changed', ['task', 'version', 'state'])
def test_analysis_binding_refused_before_engine(monkeypatch, changed):
    data = package(docx_parts()); doc = document(data); run = analysis(doc)
    if changed == 'task': run = run.model_copy(update={'task_id':'other'})
    if changed == 'version': run = run.model_copy(update={'document_version_refs':[]})
    if changed == 'state': run = run.model_copy(update={'status':module.AnalysisStatus.COMPLETED})
    monkeypatch.setattr(module, 'convert_office', lambda *args: pytest.fail('engine ran'))
    with pytest.raises(ContentAccessError): module.DoclingPerceptionAdapter(Resolver(data)).perceive(doc, run)


@pytest.mark.parametrize('data', [b'PKbroken', b'not Office'])
def test_preflight_refusal_precedes_engine(monkeypatch, data):
    monkeypatch.setattr(module, 'convert_office', lambda *args: pytest.fail('engine ran'))
    doc = document(data)
    with pytest.raises(ContentAccessError): module.DoclingPerceptionAdapter(Resolver(data)).perceive(doc, analysis(doc))


def test_stale_bytes_refused_before_engine(monkeypatch):
    data = package(docx_parts()); doc = document(data)
    monkeypatch.setattr(module, 'convert_office', lambda *args: pytest.fail('engine ran'))
    with pytest.raises(ContentAccessError) as exc:
        module.DoclingPerceptionAdapter(Resolver(b'changed')).perceive(doc, analysis(doc))
    assert exc.value.code == ErrorCode.STALE_DOCUMENT_VERSION


@pytest.mark.parametrize('problem', ['duplicate', 'unresolved', 'cycle', 'empty'])
def test_malformed_semantic_references_fail_closed(monkeypatch, problem):
    raw = {'body':{'self_ref':'#/body','children':[{'$ref':'#/texts/0'}]},
           'texts':[{'self_ref':'#/texts/0', 'label':'text','text':'safe', 'parent':{'$ref':'#/body'}, 'children':[]}]}
    if problem == 'duplicate': raw['texts'].append(deepcopy(raw['texts'][0]))
    if problem == 'unresolved': raw['texts'][0]['parent'] = {'$ref':'#/missing'}
    if problem == 'cycle': raw['texts'][0]['children'] = [{'$ref':'#/texts/0'}]
    if problem == 'empty': raw = {}
    monkeypatch.setattr(module, 'convert_office', lambda *args: raw)
    data = package(docx_parts()); doc = document(data)
    with pytest.raises(ContentAccessError) as exc:
        module.DoclingPerceptionAdapter(Resolver(data)).perceive(doc, analysis(doc))
    assert exc.value.code == ErrorCode.PERCEPTION_FAILED


def test_resolver_change_during_conversion_refuses_output(monkeypatch):
    data = package(docx_parts()); resolver = Resolver(data); doc = document(data)
    def change(*args):
        resolver.data = b'changed'
        return {}
    monkeypatch.setattr(module, 'convert_office', change)
    with pytest.raises(ContentAccessError) as exc:
        module.DoclingPerceptionAdapter(resolver).perceive(doc, analysis(doc))
    assert exc.value.code == ErrorCode.STALE_DOCUMENT_VERSION


def test_configuration_pins_standard_preflight_and_engine():
    import json
    adapter = module.DoclingPerceptionAdapter(Resolver(b''))
    config = json.loads(adapter.configuration.data)
    assert config['candidate_version'] == '2.126.0'
    assert config['enable_remote_fetch'] is False and config['enable_local_fetch'] is False
    assert config['production_qualified'] is False
    assert config['preflight_configuration_ref']['sha256'] == adapter.preflight.configuration.ref.sha256


def test_resource_limit_refusal_precedes_engine(monkeypatch):
    data = package(docx_parts()); doc = document(data)
    monkeypatch.setattr(module, 'convert_office', lambda *args: pytest.fail('engine ran'))
    adapter = module.DoclingPerceptionAdapter(Resolver(data), module.PreflightConfig(max_package_bytes=1))
    with pytest.raises(ContentAccessError) as exc: adapter.perceive(doc, analysis(doc))
    assert exc.value.code == ErrorCode.DOCUMENT_TOO_LARGE


def test_strict_conformance_is_not_silently_converted(monkeypatch):
    parts = {name:text.replace('http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                              'http://purl.oclc.org/ooxml/wordprocessingml/main')
             for name, text in docx_parts().items()}
    data = package(parts); doc = document(data)
    monkeypatch.setattr(module, 'convert_office', lambda *args: pytest.fail('engine ran'))
    with pytest.raises(ContentAccessError): module.DoclingPerceptionAdapter(Resolver(data)).perceive(doc, analysis(doc))


def test_node_order_follows_hierarchy_not_collection_order(monkeypatch):
    raw = {'body':{'self_ref':'#/body','children':[{'$ref':'#/texts/1'}, {'$ref':'#/texts/0'}]},
           'texts':[{'self_ref':f'#/texts/{i}', 'label':'text', 'text':str(i),
                     'parent':{'$ref':'#/body'}, 'children':[]} for i in range(2)]}
    monkeypatch.setattr(module, 'convert_office', lambda *args: raw)
    data = package(docx_parts()); doc = document(data)
    adapter = module.DoclingPerceptionAdapter(Resolver(data))
    result = adapter.perceive(doc, analysis(doc))
    assert [obj.value.value for obj in result.semantic_objects] == ['1','0']
    version2 = doc.model_copy(update={'id':'version-b2'})
    rerun = adapter.perceive(version2, analysis(version2))
    assert rerun.snapshot.id != result.snapshot.id
    assert set(obj.id for obj in result.semantic_objects).isdisjoint(obj.id for obj in rerun.semantic_objects)


def test_real_structured_values_validate_and_protection_is_not_authority(candidate):
    import json
    from jsonschema import Draft202012Validator
    data = package(docx_parts(True)); doc = document(data)
    adapter = module.DoclingPerceptionAdapter(Resolver(data))
    result = adapter.perceive(doc, analysis(doc))
    structured = [obj for obj in result.semantic_objects if obj.value.kind.value == 'STRUCTURED']
    assert structured
    validator = Draft202012Validator(json.loads(adapter.value_schema.data))
    for obj in structured:
        assert validator.is_valid(obj.value.value)
    assert any('content_control_lock' in limitation for limitation in result.snapshot.limitations)
    assert all(not obj.native_binding_refs for obj in result.semantic_objects)


def test_unclassified_engine_fields_are_explicit_limitations(monkeypatch):
    raw = {'body':{'self_ref':'#/body','children':[{'$ref':'#/texts/0'}]},
           'texts':[{'self_ref':'#/texts/0','label':'text','text':'safe','parent':{'$ref':'#/body'}}],
           'new_collection':[{'text':'unqualified'}]}
    monkeypatch.setattr(module, 'convert_office', lambda *args: raw)
    data = package(docx_parts()); doc = document(data)
    result = module.DoclingPerceptionAdapter(Resolver(data)).perceive(doc, analysis(doc))
    assert any('new_collection' in limitation and 'NOT_EVALUATED' in limitation for limitation in result.snapshot.limitations)
