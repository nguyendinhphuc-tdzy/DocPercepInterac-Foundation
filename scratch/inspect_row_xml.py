import sys
from pathlib import Path
sys.path.insert(0, '.')
sys.path.insert(0, './foundation')

from docx import Document
from tests.evaluation.rollforward_profiler import PATH_TMPL

doc = Document(str(PATH_TMPL))
for idx in [10, 13, 14, 15]:
    tbl = doc.tables[idx]
    row = tbl.rows[1]
    tags = [c.tag for c in row._tr.iter()]
    special = [t for t in tags if any(k in t.lower() for k in ["bookmark", "comment", "ins", "del", "drawing", "blip"])]
    print(f"Table {idx} (row 1): special tags count = {len(special)}, special = {special}")
