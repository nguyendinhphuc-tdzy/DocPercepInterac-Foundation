# ADR-002: Separate Business, Semantic, and Native Document Identities

## Status

ACCEPTED

## Date

2026-09-07

## Context

Foundation operates simultaneously at three different levels:

1. business meaning;
2. semantic document perception;
3. physical Office execution.

A single identifier cannot safely represent all three responsibilities.

Using paragraph indexes, semantic references, fuzzy matches, or physical
positions as a universal identity would make replay fragile and
difficult to audit.

## Decision

Foundation must maintain three separate identity classes.

### 1. Business Target ID

Stable across document versions.

Example:

```text
VN_LOCAL_FILE.FINANCIAL.NCP

Represents a logical business concept.

2. Semantic Reference

Represents the object within the semantic perception model.

Example:

#/texts/137

This reference may change after re-perception and must not be used as a
native mutation address.

3. Native Locator

Identifies the exact native Office object inside one immutable document
version.

Example:

{
  "document_hash": "...",
  "part_uri": "/word/document.xml",
  "locator_type": "content_control",
  "locator_payload": {
    "sdt_id": "8775518"
  }
}
Fundamental Rule
BusinessTargetID
!=
SemanticReference
!=
NativeLocator
Native Locator Scope

Native Locators are version-scoped.

They do not need to remain stable across independently edited document
versions.

Every locator must be associated with the target document binary hash.

If the binary hash no longer matches:

STALE_DOCUMENT_VERSION

The executor must refuse the ChangeSet.

The system must then:

re-perceive the new document;
rebuild native bindings;
re-map the target where required;
re-validate evidence and approval where required.
Execution Rule

The Controlled Replay Engine may execute only against a valid
NativeLocator.

A SemanticReference may provide context but must never be the sole
physical mutation address.

Fuzzy Matching

Fuzzy matching may be used during discovery or mapping.

Fuzzy matching must not be used as a silent execution fallback.

If a NativeLocator resolves to zero or multiple objects:

LOCATOR_NOT_FOUND

or:

LOCATOR_AMBIGUOUS

Execution must stop.

Consequences

Foundation requires an explicit semantic-to-native binding layer.

FoundationObject must therefore contain both:

semantic representation;
native binding.
Benefits
deterministic execution;
clean audit trail;
protection against document drift;
clearer separation of responsibilities;
easier recovery from changed documents.
Risks

Native locator capture requires format-specific integration.

Some native objects may not expose durable IDs and therefore require
version-scoped composite locators.

Validation

Golden Corpus tests must verify:

semantic object is perceived correctly;
semantic/native binding is created;
locator resolves exactly one native object;
stale document versions are blocked;
unsupported ambiguity is refused.