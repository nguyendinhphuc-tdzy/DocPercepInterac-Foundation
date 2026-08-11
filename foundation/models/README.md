# Docling models — removed (2026-08-11)

This project used to run [Docling](https://github.com/docling-project/docling)
for document layout/table/code parsing. **Docling has been removed** (see
`../STATUS.md` and `Foundation_Build_Plan_v4.md` mục 0 điểm 4) — the Geometry
Layer is now `python-docx` (DOCX) + `pdfplumber`/`pdf2image` (PDF), both
deterministic, no model weights, no GPU/CPU inference.

The old model bundle (`docling-project--*`, `RapidOcr`, ~1.4GB) has been
deleted from this folder — it was never git-tracked (see `.gitignore`), so
this is not a history rewrite, just local disk cleanup. The zip that used to
back a GitHub Release (`docling-models-v1.zip`, tag `models-v1`) has also
been deleted locally; the Release asset on GitHub itself still exists if
anyone needs to reference the old Docling setup, but nothing in this repo
depends on it anymore.

If Docling is ever reintroduced, re-download via:
```bash
foundation\.venv\Scripts\python.exe -m docling.cli.tools models download -o foundation/models
```
