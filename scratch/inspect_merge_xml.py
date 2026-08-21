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
    for r_i, row in enumerate(tbl.rows):
        for c_i, cell in enumerate(row.cells):
            tcPr = cell._tc.get_or_add_tcPr()
            vm = tcPr.find(qn('w:vMerge'))
            gs = tcPr.find(qn('w:gridSpan'))
            if vm is not None:
                print(f"Table {idx} R{r_i}C{c_i}: vMerge={vm.get(qn('w:val'))}")
            if gs is not None:
                print(f"Table {idx} R{r_i}C{c_i}: gridSpan={gs.get(qn('w:val'))}")
