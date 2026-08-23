# Environment Variables Reference

**Phase**: DEPLOY-1  

---

## 1. Backend (Render / Local Python Service)

| Variable | Type | Allowed Values | Default (Dev) | Required in Production | Description |
|:---|:---:|:---:|:---:|:---:|:---|
| `ENVIRONMENT` | `string` | `development`, `production`, `testing` | `development` | Yes | App runtime mode. In `production`, fail-closed invariant validation is enforced. |
| `STORAGE_BACKEND` | `string` | `local`, `supabase` | `local` | Yes (`supabase`) | Where document binaries are stored. Must be `supabase` in production. |
| `DATABASE_BACKEND` | `string` | `local`, `supabase` | `local` | Yes (`supabase`) | Where session/document/proposal metadata is stored. Must be `supabase` in production. |
| `ALLOWED_ORIGINS` | `string` | Comma-separated URLs | `http://localhost:5173,...` | Yes | Allowed frontend origins for CORS headers. Never `*` in production. |
| `PORT` | `integer` | `1024-65535` | `5000` | Yes (injected by Render) | Listening port for Gunicorn / Flask. |
| `SUPABASE_URL` | `string` | `https://*.supabase.co` | `None` | Yes | Supabase Project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | `string` | JWT Secret | `None` | Yes | Backend administrative service key for Postgres & Storage. |
| `AI_PROVIDER_MODE` | `string` | `workbench`, `local` | `workbench` | Optional (`local`) | `workbench` restricts to Luna/Sol. `local` enables Gemini 3.6 Flash / 3.5 Flash. |
| `GEMINI_API_KEY` | `string` | Secret | `None` | If Gemini models enabled | Google Gemini API key. |
| `WORKBENCH_SUBSCRIPTION_KEY` | `string` | Secret | `None` | If Workbench enabled | KPMG Workbench subscription key. |
| `WORKBENCH_CHARGE_CODE` | `string` | String | `None` | If Workbench enabled | KPMG Workbench charge code. |

---

## 2. Frontend (Vercel / Local Vite Dev Server)

| Variable | Scope | Value Example | Description |
|:---|:---:|:---|:---|
| `VITE_API_BASE_URL` | Build-time / Runtime | `https://docpercepinterac-api.onrender.com` | Base URL of the backend Flask service. |

> [!IMPORTANT]
> Do NOT set backend API keys or database connection strings in Vercel.
