-- ============================================================================
-- DocPercepInterac-Foundation — Workflow Intake Schema Migration
-- Migration: 002_workflow_intake.sql
-- Version: 1.1.0 (Phase PROD-UX-1 hardening)
-- ============================================================================
-- Canonical persistence for structured workflow intake (Local File Roll-Forward).
--
-- Render's filesystem is ephemeral, so intake state cannot live on local disk in
-- production: a redeploy or restart would silently lose which document holds
-- which workflow role. These tables are that state's home.
--
-- Document BYTES are never stored here. `document_id` references public.documents,
-- whose bytes live in Supabase Storage.
--
-- Safety: Non-destructive, additive only. Safe to re-run on an existing database.
-- ============================================================================

-- 1. WORKFLOW SESSIONS — one structured intake per workspace session
CREATE TABLE IF NOT EXISTS public.workflow_sessions (
    workflow_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES public.sessions(session_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    workflow_type TEXT NOT NULL,
    target_fiscal_year INTEGER,
    -- Optimistic concurrency. Intake is read-modify-write (a new file changes the
    -- verdicts of the other slots too), so a write carries the version it was
    -- based on and only lands if the stored row is still that version. Without
    -- it, two overlapping uploads each save their own stale slot set and the
    -- slower one deletes the faster one's assignment.
    state_version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Existing deployments of 002 without the column.
ALTER TABLE public.workflow_sessions
    ADD COLUMN IF NOT EXISTS state_version INTEGER NOT NULL DEFAULT 0;

-- One workflow per (session, user): re-entering the workflow re-attaches to the
-- existing intake instead of starting a second, competing one.
CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_sessions_session_user
    ON public.workflow_sessions(session_id, user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_sessions_user_id
    ON public.workflow_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_sessions_type
    ON public.workflow_sessions(workflow_type);

-- 2. WORKFLOW SLOT ASSIGNMENTS — which document plays which role, and its verdict
CREATE TABLE IF NOT EXISTS public.workflow_slot_assignments (
    workflow_id TEXT NOT NULL REFERENCES public.workflow_sessions(workflow_id) ON DELETE CASCADE,
    slot_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'anonymous',
    filename TEXT NOT NULL DEFAULT '',
    file_format TEXT NOT NULL DEFAULT '',
    file_hash TEXT NOT NULL DEFAULT '',
    file_size BIGINT NOT NULL DEFAULT 0,
    perception_status TEXT NOT NULL DEFAULT 'ready',
    element_count INTEGER,
    artifact_id TEXT,
    validation_status TEXT NOT NULL DEFAULT 'PENDING',
    readiness_status TEXT NOT NULL DEFAULT 'EMPTY',
    detected_label TEXT NOT NULL DEFAULT '',
    expected_label TEXT NOT NULL DEFAULT '',
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- The deterministic content profile the verdict was derived from, so a
    -- reloaded workflow never re-opens the file to answer a readiness question.
    signals JSONB NOT NULL DEFAULT '{}'::jsonb,
    human_review_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workflow_id, slot_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_assignments_workflow
    ON public.workflow_slot_assignments(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_assignments_session
    ON public.workflow_slot_assignments(session_id);
CREATE INDEX IF NOT EXISTS idx_workflow_assignments_user
    ON public.workflow_slot_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_assignments_document
    ON public.workflow_slot_assignments(document_id);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE public.workflow_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_slot_assignments ENABLE ROW LEVEL SECURITY;

-- Backend service-role bypass, matching 001_initial_schema.sql. The application
-- additionally scopes every query by user_id, so isolation does not depend on
-- RLS alone.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'workflow_sessions' AND policyname = 'service_role_all_workflow_sessions'
    ) THEN
        CREATE POLICY service_role_all_workflow_sessions ON public.workflow_sessions
            TO service_role USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'workflow_slot_assignments'
          AND policyname = 'service_role_all_workflow_assignments'
    ) THEN
        CREATE POLICY service_role_all_workflow_assignments ON public.workflow_slot_assignments
            TO service_role USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT table_name FROM information_schema.tables
--  WHERE table_schema = 'public'
--    AND table_name IN ('workflow_sessions', 'workflow_slot_assignments');
