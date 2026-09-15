"""Fixture-driven B1.4 acceptance; these are not SME fidelity judgments."""

from types import SimpleNamespace
import json
from hashlib import sha256

import pytest

from foundation.domain import DocumentVersion, NativeLocator, PerceptionSnapshot, SemanticObject
from foundation.services.binding import SemanticNativeBindingService


ENVELOPE = dict(schema_version="0.1.0", revision=1, task_id="task", created_at="2026-09-15T00:00:00Z")
CONTENT = dict(uri="urn:fixture:bytes", sha256="a" * 64, media_type="application/octet-stream")
VERSION = dict(document_id="doc", version_id="version", binary_hash="a" * 64)


def ref(kind, identity):
    return dict(object_type=kind, object_id=identity, revision=1)


@pytest.fixture
def inputs():
    document = DocumentVersion(**ENVELOPE, object_type="DocumentVersion", id="version", document_id="doc", binary_hash="a" * 64, byte_length=1, content_ref=CONTENT)
    semantic = SemanticObject(**ENVELOPE, object_type="SemanticObject", id="semantic", semantic_reference=dict(snapshot_ref=ref("PerceptionSnapshot", "snapshot"), semantic_id="#/texts/0"), object_kind="paragraph", value=dict(kind="TEXT", value="Exact text", review_text="Exact text"), native_binding_refs=[])
    snapshot = PerceptionSnapshot(**ENVELOPE, object_type="PerceptionSnapshot", id="snapshot", document_version_ref=VERSION, analysis_run_ref=ref("AnalysisRun", "analysis"), engine="fixture", engine_version="1.0", configuration_ref=CONTENT, semantic_object_refs=[ref("SemanticObject", "semantic")], limitations=["Fixture-only"])
    locator = NativeLocator(**ENVELOPE, object_type="NativeLocator", id="native", document_version_ref=VERSION, part_uri="/word/document.xml", locator_type="DOCX_RUN", address=dict(kind="DOCX_RUN", run_path=[dict(namespace_uri="urn:fixture:w", local_name="r", ordinal=1)]), expected_object_type="run", capture_engine="fixture/1.0", structural_fingerprint="b" * 64, fingerprint_profile_ref=CONTENT)
    return document, snapshot, semantic, locator


class Resolver:
    def __init__(self, status="EXACT_MATCH", text="Exact text", fingerprint="b" * 64):
        self.status, self.text, self.fingerprint = status, text, fingerprint
        self.calls = []

    def resolve(self, document, locator):
        self.calls.append(locator.id)
        return SimpleNamespace(status=self.status, reason="Fixture result", structural_fingerprint=self.fingerprint, text=self.text)


def bind(inputs, resolver=None, candidates=None):
    document, snapshot, semantic, locator = inputs
    return SemanticNativeBindingService(resolver or Resolver()).bind(document, snapshot, semantic, [locator] if candidates is None else candidates)


def test_exact_association_is_stable_contract_valid_and_does_not_modify_inputs(inputs):
    before = [x.model_dump_json() for x in inputs]
    result = bind(inputs)
    assert result.status.value == "RESOLVED"
    assert result == bind(inputs)
    assert result.native_locator_refs[0].object_id == "native"
    assert result.semantic_object_ref.object_id == "semantic"
    assert "association" in result.reason.lower()
    assert [x.model_dump_json() for x in inputs] == before


def test_no_candidates_never_binds(inputs):
    assert bind(inputs, candidates=[]).status.value == "UNSUPPORTED"


def test_two_exact_candidates_remain_ambiguous_in_either_order(inputs):
    locator = inputs[-1]
    other = locator.model_copy(update={"id": "native-other", "address": locator.address.model_copy(update={"run_path": [locator.address.run_path[0].model_copy(update={"ordinal": 2})]})})
    result = bind(inputs, candidates=[locator, other])
    assert result.status.value == "AMBIGUOUS"
    assert len(result.native_locator_refs) == 2
    assert result == bind(inputs, candidates=[other, locator])


@pytest.mark.parametrize("status", ["NOT_FOUND", "UNSUPPORTED", "FINGERPRINT_MISMATCH", "STALE_DOCUMENT_VERSION", "AMBIGUOUS"])
def test_native_resolution_failure_never_binds(inputs, status):
    result = bind(inputs, resolver=Resolver(status=status))
    assert result.status.value != "RESOLVED"
    assert status in result.reason


def test_resolver_claim_cannot_override_observed_fingerprint(inputs):
    assert bind(inputs, resolver=Resolver(fingerprint="c" * 64)).status.value == "UNSUPPORTED"


@pytest.mark.parametrize("text", ["exact text", "Exact text ", "different", None, ""])
def test_no_fuzzy_or_missing_text_association(inputs, text):
    assert bind(inputs, resolver=Resolver(text=text)).status.value == "UNSUPPORTED"


def test_stale_candidate_refused_before_resolution(inputs):
    locator = inputs[-1]
    stale = locator.model_copy(update={"document_version_ref": locator.document_version_ref.model_copy(update={"version_id": "old"})})
    resolver = Resolver()
    result = bind(inputs, resolver, [stale])
    assert result.status.value == "UNSUPPORTED"
    assert "STALE_DOCUMENT_VERSION" in result.reason
    assert not resolver.calls


@pytest.mark.parametrize("change", ["snapshot_version", "snapshot_membership", "semantic_snapshot", "task"])
def test_semantic_identity_must_belong_to_pinned_snapshot_and_task(inputs, change):
    document, snapshot, semantic, locator = inputs
    if change == "snapshot_version":
        snapshot = snapshot.model_copy(update={"document_version_ref": snapshot.document_version_ref.model_copy(update={"binary_hash": "c" * 64})})
    elif change == "snapshot_membership":
        snapshot = snapshot.model_copy(update={"semantic_object_refs": []})
    elif change == "semantic_snapshot":
        semantic = semantic.model_copy(update={"semantic_reference": semantic.semantic_reference.model_copy(update={"snapshot_ref": semantic.semantic_reference.snapshot_ref.model_copy(update={"revision": 2})})})
    else:
        locator = locator.model_copy(update={"task_id": "other-task"})
    assert bind((document, snapshot, semantic, locator)).status.value == "UNSUPPORTED"


def test_one_good_candidate_does_not_hide_invalid_second_candidate(inputs):
    locator = inputs[-1]
    stale = locator.model_copy(update={"id": "stale", "document_version_ref": locator.document_version_ref.model_copy(update={"version_id": "old"})})
    assert bind(inputs, candidates=[locator, stale]).status.value == "UNSUPPORTED"


def test_duplicate_ref_with_changed_content_is_refused(inputs):
    locator = inputs[-1]
    conflict = locator.model_copy(update={"structural_fingerprint": "c" * 64})
    assert bind(inputs, candidates=[locator, conflict]).status.value == "UNSUPPORTED"


def test_provider_failure_is_closed_and_reason_does_not_leak_private_error(inputs):
    class BrokenResolver:
        def resolve(self, document, locator):
            raise RuntimeError("private client document text")
    result = bind(inputs, resolver=BrokenResolver())
    assert result.status.value == "UNSUPPORTED"
    assert "private client" not in result.reason


def test_auditable_result_retains_exact_inputs_observations_and_configuration(inputs):
    service = SemanticNativeBindingService(Resolver())
    document, snapshot, semantic, locator = inputs
    result = service.bind_with_evidence(document, snapshot, semantic, [locator])
    assert result.binding == service.bind(document, snapshot, semantic, [locator])
    payload = json.loads(result.observation_artifact.data)
    assert payload["observations"][0]["exact_text_equal"] is True
    assert payload["candidates"][0] == locator.model_dump(mode="json")
    assert payload["configuration_ref"] == service.configuration_artifact.ref.model_dump(mode="json")
    assert sha256(result.observation_artifact.data).hexdigest() == result.observation_artifact.ref.sha256
    assert json.loads(service.configuration_artifact.data)["production_qualified"] is False


@pytest.mark.parametrize("observation", [None, SimpleNamespace(status="EXACT_MATCH"), SimpleNamespace(status="PASS", text="Exact text", structural_fingerprint="b" * 64), SimpleNamespace(status="EXACT_MATCH", text="Exact text", structural_fingerprint={"private": "data"})])
def test_unknown_or_malformed_resolver_output_is_refused(inputs, observation):
    class Malformed:
        def resolve(self, document, locator):
            return observation
    assert bind(inputs, resolver=Malformed()).status.value == "UNSUPPORTED"


def test_duplicate_identical_candidate_does_not_create_false_ambiguity(inputs):
    locator = inputs[-1]
    assert bind(inputs, candidates=[locator, locator]).status.value == "RESOLVED"


def test_distinct_aliases_of_same_address_do_not_silently_select(inputs):
    locator = inputs[-1]
    alias = locator.model_copy(update={"id": "alias"})
    assert bind(inputs, candidates=[locator, alias]).status.value == "AMBIGUOUS"


def test_real_docx_native_provider_substitutes_without_binding_changes(inputs):
    from foundation.adapters.native_identity import DocxNativeIdentity
    from tools.b1.build_corpus import docx_parts, package, W

    # Creating a synthetic input fixture is not governed replay.
    parts = docx_parts()
    parts["word/document.xml"] = f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>Exact text</w:t></w:r></w:p></w:body></w:document>'
    data = package(parts)
    digest = sha256(data).hexdigest()
    document, snapshot, semantic, _ = inputs
    document = DocumentVersion.model_validate({**document.model_dump(mode="json"), "binary_hash": digest, "byte_length": len(data), "content_ref": {**CONTENT, "sha256": digest}})
    snapshot = snapshot.model_copy(update={"document_version_ref": snapshot.document_version_ref.model_copy(update={"binary_hash": digest})})

    class BytesResolver:
        def resolve(self, document):
            return data

    native = DocxNativeIdentity(BytesResolver())
    discovery = native.discover(document)
    service = SemanticNativeBindingService(native)
    result = service.bind_with_evidence(document, snapshot, semantic, discovery.native_locators)
    assert result.binding.status.value == "RESOLVED"
    assert result == service.bind_with_evidence(document, snapshot, semantic, discovery.native_locators)
    assert sha256(data).hexdigest() == digest
    changed = discovery.native_locators[0].model_copy(update={"structural_fingerprint": "c" * 64})
    assert service.bind(document, snapshot, semantic, [changed]).status.value == "UNSUPPORTED"


def test_unqualified_default_docx_template_does_not_gain_binding(inputs):
    from io import BytesIO
    from docx import Document
    from foundation.adapters.native_identity import DocxNativeIdentity
    source = Document()
    source.add_paragraph("Exact text")
    stream = BytesIO()
    source.save(stream)
    data = stream.getvalue()
    digest = sha256(data).hexdigest()
    document, snapshot, semantic, _ = inputs
    document = DocumentVersion.model_validate({**document.model_dump(mode="json"), "binary_hash": digest, "byte_length": len(data), "content_ref": {**CONTENT, "sha256": digest}})
    snapshot = snapshot.model_copy(update={"document_version_ref": snapshot.document_version_ref.model_copy(update={"binary_hash": digest})})
    class BytesResolver:
        def resolve(self, document):
            return data
    native = DocxNativeIdentity(BytesResolver())
    discovery = native.discover(document)
    assert not discovery.native_locators
    assert discovery.limitations
    assert SemanticNativeBindingService(native).bind(document, snapshot, semantic, discovery.native_locators).status.value == "UNSUPPORTED"
