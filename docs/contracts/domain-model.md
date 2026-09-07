# Foundation Domain Model

## 1. Purpose

This document defines the core domain objects shared across Foundation.

The initial model is technology-neutral.

Implementation types may use Pydantic, TypeScript, C#, database schemas,
or other representations, but must preserve these domain semantics.

---

# 2. DocumentVersion

Represents one immutable version of an input or target document.

```yaml
DocumentVersion:
  document_id: string
  version_id: string
  binary_hash: string
  file_name: string
  format: DOCX | XLSX | PDF | IMAGE
  conformance: TRANSITIONAL | STRICT | UNKNOWN | NOT_APPLICABLE
  created_at: datetime

  Invariant:

ApprovedChangeSet.target_document.binary_hash
must equal
execution_document.binary_hash