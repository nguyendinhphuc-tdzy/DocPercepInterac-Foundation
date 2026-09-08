"""Operational artifact retention checks; no domain/schema authority."""

import json

import pytest

from tools.b1.verify_ci_artifacts import EXPECTED_FILES, verify_artifacts


def populate(root):
    for name in EXPECTED_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'evidence': True}), encoding='utf-8')


def test_complete_artifacts_are_accepted(tmp_path):
    populate(tmp_path)
    assert verify_artifacts(tmp_path) == list(EXPECTED_FILES)


@pytest.mark.parametrize('name', EXPECTED_FILES)
@pytest.mark.parametrize('defect', ['missing', 'empty', 'malformed'])
def test_each_artifact_must_exist_be_nonempty_and_parse(tmp_path, name, defect):
    populate(tmp_path)
    path = tmp_path / name
    if defect == 'missing':
        path.unlink()
    else:
        path.write_text('' if defect == 'empty' else '{broken', encoding='utf-8')
    with pytest.raises(ValueError, match=name.replace('.', r'\.')):
        verify_artifacts(tmp_path)


def test_semantic_keys_verification_detects_missing_keys(tmp_path):
    populate(tmp_path)
    with pytest.raises(ValueError, match="missing expected semantic key"):
        verify_artifacts(tmp_path, require_semantic_keys=True)


def test_semantic_keys_accepted_when_present(tmp_path):
    for name in EXPECTED_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == "b1-ci-reports/preflight.json":
            payload = {"evaluation_version": "1.0.0", "cases": []}
        elif name == "b1-ci-reports/docling-qualification.json":
            payload = {
                "qualification_status": "PROVISIONAL_CONTINUE",
                "engine": "docling-slim",
                "engine_version": "2.126.0",
                "cases": [],
                "reproducible_payload_sha256": "abc",
            }
        else:
            payload = {"fixtures_evaluated": 8}
        path.write_text(json.dumps(payload), encoding="utf-8")
    assert verify_artifacts(tmp_path, require_semantic_keys=True) == list(EXPECTED_FILES)
