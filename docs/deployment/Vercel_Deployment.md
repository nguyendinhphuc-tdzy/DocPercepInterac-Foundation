# Vercel Frontend Deployment Guide

**Framework**: Vite + React + TailwindCSS  
**Root Directory**: `frontend`  
**Configuration**: `frontend/vercel.json`  

---

## 1. Setup Instructions

1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New Project** and import the repository.
3. In Project Settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

---

## 2. Environment Variables on Vercel

| Variable | Value | Description |
|:---|:---|:---|
| `VITE_API_BASE_URL` | `https://<your-render-backend>.onrender.com` | Base URL of the Render Flask backend |

> [!CAUTION]
> Never set `GEMINI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, or `DATABASE_URL` in Vercel environment variables. Frontend only needs `VITE_API_BASE_URL`.

---

## 3. Post-Deployment Verification

1. Open the Vercel deployment URL in a browser.
2. Upload a test `.docx` / `.xlsx` document and verify elements render.
3. Open Developer Tools Network tab and confirm all requests go to `https://<your-render-backend>.onrender.com/api/...` with zero 404 or CORS errors.
