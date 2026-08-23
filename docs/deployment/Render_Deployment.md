# Render Backend Deployment Guide

**Service Type**: Web Service (Python)  
**Repository Root**: `.` (Repository root)  
**Configuration**: `render.yaml` or Render Dashboard  

---

## 1. Setup Instructions

1. Log in to [Render](https://dashboard.render.com/).
2. Create a new **Web Service** pointing to your repository.
3. Configure the following build & start settings:
   - **Environment**: `Python 3`
   - **Region**: `Singapore` (Recommended for APAC latency)
   - **Build Command**: `pip install -r foundation/requirements.txt`
   - **Start Command**: `gunicorn --chdir foundation --config foundation/gunicorn.conf.py "api.app:create_app()"`
   - **Health Check Path**: `/api/health`

---

## 2. Environment Variables on Render

| Variable | Recommended Production Value | Description |
|:---|:---|:---|
| `ENVIRONMENT` | `production` | Enables fail-closed validation & strict CORS |
| `STORAGE_BACKEND` | `supabase` | Routes document binaries to Supabase Storage |
| `DATABASE_BACKEND` | `supabase` | Routes metadata to Supabase Postgres |
| `AI_PROVIDER_MODE` | `local` | Allows Gemini models + Workbench |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` | Comma-separated list of allowed frontend origins |
| `SUPABASE_URL` | `https://<ref>.supabase.co` | Supabase Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJ...` | Supabase Service Role Secret Key (Backend-only) |
| `GEMINI_API_KEY` | `AIza...` | Google Gemini API Key (Backend-only) |
| `WORKBENCH_SUBSCRIPTION_KEY` | (Optional) | KPMG Workbench Key |
| `WORKBENCH_CHARGE_CODE` | (Optional) | KPMG Workbench Charge Code |
| `WEB_CONCURRENCY` | `2` | Number of Gunicorn worker processes |
| `PYTHON_GET_THREADS` | `4` | Number of threads per worker |

---

## 3. Health & Verification

Once deployed, probe the health endpoints:
```bash
curl -i https://<your-render-service>.onrender.com/api/health
curl -i https://<your-render-service>.onrender.com/api/health/database
curl -i https://<your-render-service>.onrender.com/api/health/storage
```
Expected response: HTTP 200 with JSON status `ok`.
