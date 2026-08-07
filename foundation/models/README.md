# Docling models — distributed separately, not in Git

This project uses [Docling](https://github.com/docling-project/docling) for
document layout/table/code parsing. Docling's models (layout, tableformer,
code-formula, OCR, etc.) total **~1.4GB**, well over GitHub's 100MB per-file
limit, so they are **not committed to this repository**.

## Where to get them

The pre-downloaded model bundle (`docling-models-v1.zip`, ~1.2GB) is attached
as a **GitHub Release asset** on this repo (not a git commit, so it's not
subject to the 100MB file limit or LFS quota):

https://github.com/nguyendinhphuc-tdzy/DocPercepInterac-Foundation/releases/download/models-v1/docling-models-v1.zip

(Release tag: `models-v1`. If it 404s, check the repo's Releases page for the
current tag — the link above is only valid once that release is published.)

## How to set up after cloning

1. Download the zip from the link above:
   ```bash
   curl -L -o docling-models-v1.zip https://github.com/nguyendinhphuc-tdzy/DocPercepInterac-Foundation/releases/download/models-v1/docling-models-v1.zip
   ```
2. Extract it into `foundation/models/` so this folder looks like:
   ```
   foundation/models/
     docling-project--docling-layout-heron/
     docling-project--docling-layout-heron-onnx/
     docling-project--docling-models/
     docling-project--CodeFormulaV2/
     ...
   ```
3. That's it — `foundation/perception/parser.py` auto-detects this folder
   (`LOCAL_ARTIFACTS_PATH`) and points Docling at it, so no env vars or code
   changes are needed. The app never reaches out to Hugging Face at runtime
   once the models are extracted here.

   If you'd rather keep the models somewhere else, override with:
   ```bash
   set DOCLING_ARTIFACTS_PATH=C:\path\to\models
   ```
   (PowerShell: `$env:DOCLING_ARTIFACTS_PATH="C:\path\to\models"`)

## Regenerating the bundle (only if models change)

```bash
foundation\.venv\Scripts\python.exe -m docling.cli.tools models download -o foundation/models
```
Then re-zip `foundation/models/`, and on GitHub create a new Release (e.g.
tag `models-v2`) with the zip attached as an asset. Update the link above to
match.
