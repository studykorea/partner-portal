# Fast Migration Notes v342

This package starts the migration from the old Streamlit deployment to a faster production structure.

## What changed

1. Removed old backup ZIP files from the deploy root.
2. Moved the huge Streamlit app to `legacy_streamlit/app.py` so it is kept temporarily but no longer controls the main production app.
3. Rebuilt the public website in Next.js:
   - `/` homepage
   - `/universities`
   - `/login`
   - `/partner-dashboard`
   - `/admin`
4. Added optimized WebP images under `public/assets`.
5. Updated FastAPI backend endpoints:
   - `/health`
   - `/api/universities`
   - `/api/admission-criteria`
   - `/api/uploads/student-document`
6. Updated `render.yaml` for separate frontend and backend Render services.

## Recommended Render deployment

Create two services from the same GitHub repo.

### Frontend service

- Runtime: Node
- Root directory: leave empty / repository root
- Build command: `npm ci && npm run build`
- Start command: `npm run start`
- Environment variable:
  - `NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-RENDER-URL`

### Backend service

- Runtime: Python
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `ALLOWED_ORIGINS=https://YOUR-FRONTEND-RENDER-URL`
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `DATABASE_URL`

## Important

Do not deploy the root as Streamlit anymore. The old Streamlit app is only kept under `legacy_streamlit` as a temporary backup.

For real production, connect login, file uploads, and dashboards to Supabase Auth, Supabase Postgres, and Supabase Storage.
