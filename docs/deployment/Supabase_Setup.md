# Supabase Setup Guide: Postgres & Storage

**Phase**: DEPLOY-1  
**Target**: Supabase Project (Postgres Database + Object Storage)  

---

## 1. Create Supabase Project

1. Log in to [Supabase](https://supabase.com/).
2. Create a new project (e.g. `docpercepinterac-production`) in your preferred region.
3. Note your **Project URL** (`https://<project-ref>.supabase.co`) and **service_role secret key** under **Project Settings $\rightarrow$ API**.

---

## 2. Run Database Migrations

1. Navigate to **SQL Editor** in the Supabase Dashboard.
2. Open [`foundation/migrations/001_initial_schema.sql`](../../foundation/migrations/001_initial_schema.sql).
3. Paste the contents into the SQL Editor and click **Run**.
4. Verify the following tables were created:
   - `public.sessions`
   - `public.documents`
   - `public.document_versions`
   - `public.proposals`
   - `public.source_packages`
   - `public.source_artifacts`
   - `public.lineage_events`
   - `public.pilot_events`

---

## 3. Create Storage Buckets

1. Navigate to **Storage** in the Supabase Dashboard.
2. Create the following **Private** buckets:
   - `documents` (Private: unchecked Public Bucket)
   - `generated` (Private: unchecked Public Bucket)
   - `source-artifacts` (Private: unchecked Public Bucket)

---

## 4. Security & Access Control

- All buckets are private. Only backend calls using `SUPABASE_SERVICE_ROLE_KEY` or signed URLs can access document binaries.
- Client browsers communicate exclusively with the Render backend, never directly with Supabase Storage buckets.
