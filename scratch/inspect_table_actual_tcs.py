import sys
from pathlib import Path
sys.path.insert(0, '.')
sys.path.insert(0, './foundation')

from docx import Document
from docx.oxml.ns import qn
from tests.evaluation.rollforward_profiler import PATH_TMPL

doc = Document(str(PATH_TMPL))
for idx in [10, 13, 14, 15]:
    tbl = doc.tables[idx]
    print(f"=== TABLE {idx} (cols={len(tbl.columns)}, rows={len(tbl.rows)}) ===")
    for r_i, r in enumerate(tbl.rows):
        tcs = r._tr.findall(qn('w:tc'))
        spans = []
        for tc in tcs:
            tcPr = tc.get_or_add_tcPr()
            gs = tcPr.find(qn('w:gridSpan'))
            spans.append(int(gs.get(qn('w:val'))) if gs is not None else 1)
        print(f"  Row {r_i}: {len(tcs)} actual tcs, spans={spans}, sum={sum(spans)}")
