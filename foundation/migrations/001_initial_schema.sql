-- ============================================================================
-- DocPercepInterac-Foundation — Supabase Postgres Initial Schema Migration
-- Migration: 001_initial_schema.sql
-- Version: 1.0.0 (Phase DEPLOY-1)
-- ============================================================================
-- Safety: Non-destructive, additive only. Safe to re-run on existing database.
-- ============================================================================

-- 1. SESSIONS
CREATE TABLE IF NOT EXISTS public.sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    status TEXT NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON public.sessions(created_at DESC);

-- 2. DOCUMENTS
CREATE TABLE IF NOT EXISTS public.documents (
    doc_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES public.sessions(session_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    original_filename TEXT NOT NULL,
    format TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ready',
    element_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_session_id ON public.documents(session_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);

-- 3. DOCUMENT VERSIONS (Immutable historical lineage & patched states)
CREATE TABLE IF NOT EXISTS public.document_versions (
    version_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES public.documents(doc_id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    version_number INTEGER NOT NULL DEFAULT 1,
    sha256 TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    is_patched BOOLEAN NOT NULL DEFAULT FALSE,
    element_count INTEGER NOT NULL DEFAULT 0,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_versions_doc_id ON public.document_versions(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_versions_session_id ON public.document_versions(session_id);
CREATE INDEX IF NOT EXISTS idx_document_versions_sha256 ON public.document_versions(sha256);

-- 4. GOVERNED AGENT PROPOSALS (Strict locking, lifecycle tracking, TTL, replay prevention)
CREATE TABLE IF NOT EXISTS public.proposals (
    action_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES public.sessions(session_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    doc_id TEXT NOT NULL,
    element_id TEXT NOT NULL,
    target_anchor JSONB,
    current_value TEXT,
    proposed_value TEXT NOT NULL,
    rationale TEXT,
    doc_hash TEXT,
    status TEXT NOT NULL DEFAULT 'proposed', -- proposed, executing, applied, rejected, stale, expired
    ttl_seconds INTEGER NOT NULL DEFAULT 86400,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proposals_session_id ON public.proposals(session_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON public.proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_created_at ON public.proposals(created_at DESC);

-- 5. SOURCE PACKAGES (Phase G Roll-Forward Versioned Source Packages)
CREATE TABLE IF NOT EXISTS public.source_packages (
    package_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 1,
    parent_version INTEGER,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    status TEXT NOT NULL DEFAULT 'DRAFT', -- DRAFT, FROZEN, STALE
    package_hash TEXT NOT NULL,
    artifact_count INTEGER NOT NULL DEFAULT 0,
    history JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_source_packages_user_id ON public.source_packages(user_id);
CREATE INDEX IF NOT EXISTS idx_source_packages_hash ON public.source_packages(package_hash);

-- 6. SOURCE ARTIFACTS (Phase G Ingested Source Files & Role Verdicts)
CREATE TABLE IF NOT EXISTS public.source_artifacts (
    artifact_id TEXT PRIMARY KEY,
    package_id TEXT REFERENCES public.source_packages(package_id) ON DELETE SET NULL,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    format TEXT NOT NULL,
    source_scope TEXT NOT NULL,
    dataset_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    satisfying_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    role_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    storage_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'REGISTERED', -- REGISTERED, PROFILED, STALE_INPUT, REJECTED, QUARANTINED
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_source_artifacts_package_id ON public.source_artifacts(package_id);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_hash ON public.source_artifacts(file_hash);

-- 7. LINEAGE EVENTS (Cryptographic patch audit trail)
CREATE TABLE IF NOT EXISTS public.lineage_events (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    target_anchor TEXT NOT NULL,
    target_value_hash TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_anchor TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_lineage_events_session_id ON public.lineage_events(session_id);
CREATE INDEX IF NOT EXISTS idx_lineage_events_timestamp ON public.lineage_events(timestamp DESC);

-- 8. PILOT EVENTS (Telemetry, fail-open observability)
CREATE TABLE IF NOT EXISTS public.pilot_events (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    event_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_id TEXT,
    provider TEXT,
    status TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_pilot_events_session_id ON public.pilot_events(session_id);
CREATE INDEX IF NOT EXISTS idx_pilot_events_event_type ON public.pilot_events(event_type);
CREATE INDEX IF NOT EXISTS idx_pilot_events_timestamp ON public.pilot_events(timestamp DESC);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lineage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pilot_events ENABLE ROW LEVEL SECURITY;

-- Backend Service Role Bypass (Server uses SUPABASE_SERVICE_ROLE_KEY to administer)
-- If authenticated JWT user tokens are enabled in the future, these policies scope access:
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'sessions' AND policyname = 'service_role_all_sessions'
    ) THEN
        CREATE POLICY service_role_all_sessions ON public.sessions TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'documents' AND policyname = 'service_role_all_documents'
    ) THEN
        CREATE POLICY service_role_all_documents ON public.documents TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'document_versions' AND policyname = 'service_role_all_doc_versions'
    ) THEN
        CREATE POLICY service_role_all_doc_versions ON public.document_versions TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'proposals' AND policyname = 'service_role_all_proposals'
    ) THEN
        CREATE POLICY service_role_all_proposals ON public.proposals TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'source_packages' AND policyname = 'service_role_all_packages'
    ) THEN
        CREATE POLICY service_role_all_packages ON public.source_packages TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'source_artifacts' AND policyname = 'service_role_all_artifacts'
    ) THEN
        CREATE POLICY service_role_all_artifacts ON public.source_artifacts TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'lineage_events' AND policyname = 'service_role_all_lineage'
    ) THEN
        CREATE POLICY service_role_all_lineage ON public.lineage_events TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tabUATION = 'pilot_events' AND policyname = 'service_role_all_pilot_events'
    ) THEN
        CREATE POLICY service_role_all_pilot_events ON public.pilot_events TO service_role USING (true) WITH CHECK (true);
    END IF;
END $$;
