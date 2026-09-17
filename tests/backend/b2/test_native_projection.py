from dataclasses import replace
from foundation.adapters.gtps_native_candidates import ReviewNativeIdentity, TemplateNativeCandidates
from foundation.adapters.native_identity import DocxNativeIdentity, Q
from tests.backend.b1.native_identity.test_docx import fixture, RUN, TABLE
from tests.backend.b2.test_gtps_mapping import setup, view


def test_formatted_cell_has_read_only_identity():
    body=TABLE.replace('<w:tc>', '<w:tc><w:tcPr><w:vAlign w:val="center"/></w:tcPr>')
    d,r=fixture(body)
    assert not DocxNativeIdentity(r).discover(d).native_locators
    a=ReviewNativeIdentity(r)
    loc=next(x for x in a.discover(d).native_locators if x.locator_type.value=='DOCX_TABLE_CELL')
    assert a.resolve(d,loc).status=='EXACT_MATCH'
    assert a.resolve(d,loc).text=='Hello'
    assert not any(c.status.value=='SUPPORTED' for c in a.discover(d).preflight_assessment.capability_results)


def test_field_result_and_nested_cells_still_refused():
    for body in [TABLE.replace('<w:t>Hello</w:t>','<w:fldChar w:fldCharType="begin"/><w:t>Hello</w:t>'),
                 TABLE.replace(RUN,TABLE)]:
        d,r=fixture(body)
        assert not ReviewNativeIdentity(r).discover(d).native_locators


def test_equal_tables_never_choose_first(setup):
    d,r=fixture(TABLE+TABLE)
    _,_,_,t,_,_,slot=setup
    from foundation.adapters.native_identity import version_ref
    t=view('template','TARGET_TEMPLATE',{'tables':[{'data':{'num_rows':1,'num_cols':1,'table_cells':[
        {'text':'Hello','start_row_offset_idx':0,'start_col_offset_idx':0,'row_span':1,'col_span':1}]}}]})
    t=replace(t,version=version_ref(d))
    slot=replace(slot,pointer='/tables/0/data/table_cells/0/text',expected_content='Hello')
    provider=TemplateNativeCandidates(d,r)
    assert provider.resolve(slot,t).status=='TARGET_AMBIGUOUS'


def test_exact_native_cell_content_preserves_whitespace_and_binary(setup):
    from foundation.adapters.native_identity import version_ref
    d,r=fixture(TABLE.replace('Hello','Hello '));before=r.data
    _,_,_,t,_,_,slot=setup
    t=view('template','TARGET_TEMPLATE',{'tables':[{'data':{'num_rows':1,'num_cols':1,'table_cells':[
        {'text':'Hello','start_row_offset_idx':0,'start_col_offset_idx':0,'row_span':1,'col_span':1}]}}]})
    t=replace(t,version=version_ref(d));slot=replace(slot,pointer='/tables/0/data/table_cells/0/text',expected_content='Hello')
    p=TemplateNativeCandidates(d,r);result=p.resolve(slot,t)
    assert result.status=='EXACT_MATCH' and result.observed_content=='Hello ' and result.semantic_content=='Hello'
    assert r.data==before
    assert p.resolve(slot,replace(t,version=t.version.model_copy(update={'version_id':'stale'}))).status=='STALE_NATIVE_LOCATOR'


def test_governed_native_adapters_cannot_use_legacy_mutation():
    import ast
    from pathlib import Path
    root=Path(__file__).resolve().parents[3]
    for name in ['native_identity.py','gtps_native_candidates.py']:
        tree=ast.parse((root/'foundation/adapters'/name).read_text())
        for n in ast.walk(tree):
            if isinstance(n,(ast.Import,ast.ImportFrom)):
                names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or '']
                assert all(not any(x in name for x in ('writeback','action_executor','rollforward','replay')) for name in names)
            if isinstance(n,ast.Attribute):assert n.attr not in ('save','apply_single_patch','execute','replay')
