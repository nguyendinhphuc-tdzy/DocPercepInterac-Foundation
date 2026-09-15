"""Integrated engineering evidence, never representative qualification."""
from dataclasses import replace
import json
import pytest
from foundation.evaluation.b1_integrated import B1Harness, write_run
from foundation.adapters.perception_docling import DoclingPerceptionAdapter
from foundation.adapters.native_identity import DocxNativeIdentity
from foundation.services.binding import SemanticNativeBindingService
from tests.backend.b1.native_identity.test_docx import fixture, RUN
from tests.backend.b1.perception.test_adapter import analysis


def harness(resolver):
    native = DocxNativeIdentity(resolver)
    return B1Harness(resolver, DoclingPerceptionAdapter(resolver), native, SemanticNativeBindingService(native))


def test_real_chain_deterministic_but_unqualified():
    doc, resolver = fixture(RUN)
    h = harness(resolver)
    a = h.run(doc, analysis(doc))
    assert a == h.run(doc, analysis(doc))
    assert all(a['stages'][s]['outcome'] == 'PASS' for s in ('preflight','perception','native_identity','binding','invariants','input_integrity'))
    assert a['review_status'] == 'REVIEW_REQUIRED'
    assert a['production_qualified'] is False
    assert a['decision'] == 'INSUFFICIENT_EVIDENCE'
    assert a['records']['bindings'][0]['status'] == 'RESOLVED'


def test_duplicate_text_does_not_pass_binding():
    doc, resolver = fixture(RUN+RUN)
    out = harness(resolver).run(doc, analysis(doc))
    assert out['stages']['binding']['outcome'] == 'FAIL'
    assert all(x['status']=='AMBIGUOUS' for x in out['records']['bindings'])


def test_missing_component_not_implemented_not_pass():
    doc,resolver=fixture(RUN)
    out=B1Harness(resolver).run(doc,analysis(doc))
    assert out['stages']['perception']=={'implementation':'NOT_IMPLEMENTED','outcome':'NOT_EVALUATED','error_codes':[]}
    assert out['stages']['binding']['outcome']=='NOT_EVALUATED'


def test_stale_input_refuses_before_components():
    doc,resolver=fixture(RUN);resolver.data=b'changed'
    out=harness(resolver).run(doc,analysis(doc))
    assert out['stages']['input_integrity']['outcome']=='FAIL'
    assert out['stages']['perception']['outcome']=='NOT_EVALUATED'


def test_private_error_not_in_public_summary(tmp_path):
    doc,resolver=fixture(RUN)
    class Broken:
        def perceive(self,*a): raise RuntimeError('SECRET source path')
    out=B1Harness(resolver,Broken()).run(doc,analysis(doc))
    private=tmp_path/'.foundation-private/run-001.json'
    public=tmp_path/'qualification/b1/integrated/reports/run-001.json'
    result=write_run(out,private,public,tmp_path)
    assert 'SECRET' not in public.read_text()
    assert 'Hello' not in public.read_text()
    assert doc.binary_hash not in public.read_text()
    assert result['production_qualified'] is False
    before=private.read_bytes()
    with pytest.raises(FileExistsError): write_run(out,private,public,tmp_path)
    assert private.read_bytes()==before


def test_public_path_cannot_receive_full_evidence(tmp_path):
    doc,resolver=fixture(RUN)
    out=B1Harness(resolver).run(doc,analysis(doc))
    with pytest.raises(ValueError):write_run(out,tmp_path/'full.json',tmp_path/'summary.json',tmp_path)


def test_refused_discovery_cannot_be_pass():
    doc,resolver=fixture(RUN)
    native=DocxNativeIdentity(resolver)
    class Empty:
        def discover(self,d):return replace(native.discover(d),native_locators=())
    out=B1Harness(resolver,DoclingPerceptionAdapter(resolver),Empty(),SemanticNativeBindingService(native)).run(doc,analysis(doc))
    assert out['stages']['native_identity']['outcome']=='FAIL'
    assert out['stages']['binding']['outcome']=='NOT_EVALUATED'

def test_forged_snapshot_configuration_cannot_pass():
    doc,resolver=fixture(RUN)
    real=DoclingPerceptionAdapter(resolver)
    class Forged:
        configuration=real.configuration
        value_schema=real.value_schema
        def perceive(self,*args):
            r=real.perceive(*args)
            return replace(r,snapshot=r.snapshot.model_copy(update={'configuration_ref':r.snapshot.configuration_ref.model_copy(update={'sha256':'0'*64})}))
    out=B1Harness(resolver,Forged()).run(doc,analysis(doc))
    assert out['stages']['perception']['outcome']=='FAIL'


def test_forged_native_fingerprint_cannot_pass():
    doc,resolver=fixture(RUN)
    real=DocxNativeIdentity(resolver)
    class Forged:
        def discover(self,d):
            r=real.discover(d)
            return replace(r,native_locators=(r.native_locators[0].model_copy(update={'structural_fingerprint':'0'*64}),))
        def resolve(self,*args):return real.resolve(*args)
    out=B1Harness(resolver,DoclingPerceptionAdapter(resolver),Forged()).run(doc,analysis(doc))
    assert out['stages']['native_identity']['outcome']=='FAIL'


def test_public_failure_preserves_no_raw_error_or_content(tmp_path):
    from foundation.evaluation.b1_integrated import public_summary
    doc,resolver=fixture(RUN)
    out=harness(resolver).run(doc,analysis(doc))
    out['stages']['binding']['error_codes']=['SECRET']
    public=public_summary(out)
    assert 'SECRET' not in json.dumps(public)
    assert 'records' not in public

def test_wrong_analysis_task_refused_before_adapter():
    doc,resolver=fixture(RUN)
    out=harness(resolver).run(doc,analysis(doc).model_copy(update={'task_id':'different'}))
    assert out['stages']['perception']['outcome']=='NOT_EVALUATED'
    assert out['stages']['preflight']['outcome']=='FAIL'
