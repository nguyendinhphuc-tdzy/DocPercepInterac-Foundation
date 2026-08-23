# Production Deployment Runbook

**Phase**: DEPLOY-1  
**Authoritative Deployment Steps**: Step-by-step procedure for provisioning and deploying DocPercepInterac-Foundation.

---

## 1. Pre-Deployment Checklist

- [ ] Supabase project created with regions matching user base.
- [ ] Database migration `001_initial_schema.sql` applied cleanly.
- [ ] Private buckets (`documents`, `generated`, `source-artifacts`) created in Supabase Storage.
- [ ] `GEMINI_API_KEY` available for demo AI operations.
- [ ] Vercel account linked to repository.
- [ ] Render account linked to repository.

---

## 2. Step-by-Step Deployment Procedure

### Step A: Deploy Backend to Render
1. Push all code to the target GitHub branch (e.g. `main`).
2. In Render Dashboard, create a **Web Service** from the repository or use the Blueprint sync (`render.yaml`).
3. Set environment variables on Render:
   ```env
   ENVIRONMENT=production
   STORAGE_BACKEND=supabase
   DATABASE_BACKEND=supabase
   AI_PROVIDER_MODE=local
   SUPABASE_URL=https://<your-project>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
   GEMINI_API_KEY=<your-gemini-key>
   ALLOWED_ORIGINS=https://<your-project>.vercel.app
   ```
4. Trigger manual deploy or wait for automatic build.
5. Verify health check:
   ```bash
   curl -s https://<your-render-backend>.onrender.com/api/health
   # Expected: {"ai_provider_mode":"local","database_backend":"supabase","environment":"production","status":"ok","storage_backend":"supabase","version":"1.0.0"}
   ```

### Step B: Deploy Frontend to Vercel
1. In Vercel Dashboard, import the repository with Root Directory set to `frontend`.
2. Add environment variable:
   ```env
   VITE_API_BASE_URL=https://<your-render-backend>.onrender.com
   ```
3. Deploy the project.
4. If your Vercel URL changed, update `ALLOWED_ORIGINS` in Render environment settings.

---

## 3. Post-Deployment Verification

1. Open frontend URL: `https://<your-project>.vercel.app`.
2. Upload test document `Compare LF/HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx`.
3. Verify document renders elements and tables accurately.
4. Test live edit: double-click a paragraph/cell and modify a value. Verify patched download succeeds.
5. In Agent panel, select **Gemini 3.6 Flash** and ask a document question. Verify reasoning response and citations.
6. Select **Workbench Luna** on an external non-corporate network. Verify it reports explicit `unavailable` error without silently falling back to Gemini.
7. Inspect Supabase Storage: confirm uploaded file and patched version exist in `documents` bucket.
8. Inspect Supabase Database: confirm rows were inserted in `documents`, `document_versions`, and `lineage_events`.

---

## 4. Emergency & Rollback Procedures

- **Backend Rollback**: In Render Dashboard $\rightarrow$ Deploys $\rightarrow$ select previous working commit $\rightarrow$ Rollback.
- **Frontend Rollback**: In Vercel Dashboard $\rightarrow$ Deployments $\rightarrow$ select previous deployment $\rightarrow$ Promote to Production.
- **Data Integrity**: Database tables are non-destructive and versioned. Existing versions remain immutable in Supabase Object Storage.
