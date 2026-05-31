# Exact deployment steps

## 1. GitHub
1. Create a private GitHub repository.
2. Upload this project ZIP to the repository.
3. Do not commit real `.env` files.
4. Keep `.env.example` only.

## 2. Supabase
1. Create a Supabase project.
2. Open SQL Editor.
3. Run `supabase/schema.sql`.
4. Run `supabase/rls_policies.sql`.
5. Run `supabase/storage_policies.sql`.
6. Create your first super admin user in Supabase Auth.
7. Insert a matching row in `public.profiles` with role `super_admin`.

## 3. Backend API on Render or Railway
1. Create a new web service from GitHub.
2. Root directory: `backend`.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Add backend environment variables from `backend/.env.example`.
6. Test `/health` endpoint.

## 4. Frontend on Vercel
1. Import the GitHub repository to Vercel.
2. For the future frontend, set root directory to `frontend`.
3. Add variables from `frontend/.env.example`.
4. Deploy.
5. Connect your custom domain in Vercel project settings.
6. Add the DNS records from Vercel to your domain provider.
7. Wait for SSL to become active.

## 5. Current Streamlit prototype
The current `app.py` can still be used for beta testing, but for full production scalability, migrate database and upload logic to Supabase and split frontend/backend as documented.

## 6. Backups
1. Enable Supabase database backups according to your Supabase plan.
2. Export storage bucket metadata regularly.
3. For important student documents, add a scheduled backup to S3-compatible storage.
4. Keep monthly CSV/database exports for university data and admission dates.
