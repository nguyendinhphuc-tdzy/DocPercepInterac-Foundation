"""All paths/content below are synthetic; no private corpus is read in CI."""

import json
from pathlib import Path
import subprocess

import pytest

from tools.b1.verify_private_corpus_boundary import violations, verify
from tools.b1.representative_probe import run
from foundation.evaluation.perception import representative as rep


@pytest.mark.parametrize('name', ['.foundation-private/manifest.local.json',
    'private-corpus/document.docx', 'b1-private-corpus/book.xlsx', 'tests/private-corpus/raw.json'])
def test_reserved_tracked_paths_are_refused(tmp_path, name):
    assert violations([name], tmp_path) == 1


def test_configured_inside_path_and_synthetic_exemption(tmp_path):
    assert violations(['custom-private/a.json'], tmp_path, tmp_path / 'custom-private') == 1
    assert violations(['tests/golden/cases/b1/docx-basic.docx'], tmp_path) == 0


def init_repo(root):
    subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
    (root / '.gitignore').write_text('.foundation-private/\n')


def test_force_staged_ignored_file_is_detected_without_printing_path(tmp_path):
    init_repo(tmp_path)
    private = tmp_path / '.foundation-private'; private.mkdir()
    (private / 'SECRET.json').write_text('{}')
    subprocess.run(['git', '-C', str(tmp_path), 'add', '-f', '.foundation-private/SECRET.json'], check=True, capture_output=True)
    with pytest.raises(ValueError) as error: verify(tmp_path)
    assert 'SECRET' not in str(error.value)


def test_missing_corpus_cli_writes_only_empty_safe_summary(tmp_path, monkeypatch):
    init_repo(tmp_path); monkeypatch.delenv(rep.CORPUS_ENV, raising=False)
    private = tmp_path / '.foundation-private/full.json'
    public = tmp_path / 'qualification/b1/representative/reports/summary.json'
    out = run(tmp_path / '.foundation-private/manifest.local.json', private, public, tmp_path)
    assert not private.exists()
    assert json.loads(public.read_text()) == out
    assert out['cases'] == [] and out['corpus_status'] == 'CORPUS_NOT_PROVIDED'


def test_private_and_public_paths_cannot_be_swapped(tmp_path, monkeypatch):
    init_repo(tmp_path); monkeypatch.delenv(rep.CORPUS_ENV, raising=False)
    private = tmp_path / '.foundation-private/full.json'
    public = tmp_path / 'qualification/b1/representative/reports/summary.json'
    for args in ((public, private, public), (private, public, public), (private, private, private)):
        with pytest.raises(rep.QualificationError): run(*args, tmp_path)


def test_symlink_escape_refused(tmp_path):
    repo = tmp_path / 'repo'; repo.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir()
    try: (repo / '.foundation-private').symlink_to(outside, target_is_directory=True)
    except OSError: pytest.skip('Platform does not permit unprivileged symlinks')
    with pytest.raises(rep.QualificationError): rep.private_path(repo / '.foundation-private/full.json', repo)


def test_full_evidence_stays_private_and_cannot_be_overwritten(tmp_path, monkeypatch):
    from tests.backend.b1.representative.test_representative import manifest, result
    repo = tmp_path / 'repo'; init_repo(repo)
    corpus = tmp_path / 'corpus'; corpus.mkdir()
    monkeypatch.setenv(rep.CORPUS_ENV, str(corpus))
    m = manifest(); full = {'corpus_status': 'AVAILABLE', 'manifest': m, 'cases': [result()]}
    monkeypatch.setattr(rep, 'evaluate', lambda *args: full)
    manifest_path = repo / '.foundation-private/manifest.local.json'
    manifest_path.parent.mkdir(); manifest_path.write_text(json.dumps(m))
    private = repo / '.foundation-private/reports/run-001/full.json'
    public = repo / 'qualification/b1/representative/reports/summary.json'
    run(manifest_path, private, public, repo)
    assert 'SECRET' in private.read_text() and 'SECRET' not in public.read_text()
    before = private.read_bytes()
    with pytest.raises(FileExistsError): run(manifest_path, private, public, repo)
    assert private.read_bytes() == before


def test_input_symlink_cannot_escape_private_corpus(tmp_path, monkeypatch):
    from tests.backend.b1.representative.test_representative import manifest
    root = tmp_path / 'corpus'; root.mkdir(); outside = tmp_path / 'outside.docx'; outside.write_bytes(b'synthetic')
    m = manifest()
    try: (root / m['cases'][0]['local_path']).symlink_to(outside)
    except OSError: pytest.skip('Platform does not permit unprivileged symlinks')
    monkeypatch.setenv(rep.CORPUS_ENV, str(root))
    with pytest.raises(rep.QualificationError): rep.evaluate(m, rep.ROOT)
