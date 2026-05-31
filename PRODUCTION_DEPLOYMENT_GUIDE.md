# Korea University Admissions Partner Portal Production Deployment Guide

This project should **not** be deployed as a static GitHub Pages website because it needs backend features: login, partner accounts, admin/super-admin dashboards, university database management, admission dates, application forms, document uploads, video/image uploads, saved universities, and secure storage.

## Recommended production architecture

| Layer | Recommended service | Purpose |
|---|---|---|
| Frontend | Vercel | Public website, university listing/detail pages, partner/admin UI |
| Database | Supabase Postgres | University data, admission dates, users, roles, applications, favorites |
| Auth | Supabase Auth | Partner login, admin/super-admin login, role-based access |
| File storage | Supabase Storage or S3-compatible storage | Student documents, PDF/JPEG uploads, university photos, brochures |
| Backend API | Render or Railway | Secure server-side APIs, upload signing, admin actions, scheduled jobs |
| Source control | GitHub | Code editing, version control, automatic deploy trigger |
| Domain/SSL | Vercel custom domain | SSL is automatically issued after DNS is connected |

## Important production rule

Do not store uploaded student documents, university images, brochures, or videos inside GitHub or inside the project folder. Files stored inside the app folder may disappear during redeployment or become publicly exposed. Use Supabase Storage or S3-compatible storage.

## Deployment flow

1. Edit code locally or in GitHub.
2. Push to GitHub.
3. Vercel automatically redeploys the frontend.
4. Render/Railway automatically redeploys the backend API.
5. Admin-uploaded data stays in Supabase Database and Storage, so redeploying code does not delete uploaded content.

## Recommended repository layout

```text
partner-portal/
  frontend/                  # Future Next.js/Vite frontend for Vercel
  backend/                   # FastAPI backend for Render/Railway
  supabase/                  # SQL schema, RLS policies, storage policies
  docs/                      # Deployment/security/backup documentation
  scripts/                   # Helper scripts
  app.py                     # Current Streamlit prototype/legacy app
  db.py                      # Current local database helper
  .env.example               # Root environment example
```

## Environment variables

Use separate frontend and backend environment variables. Never commit real secrets to GitHub.

Frontend variables may be visible in the browser, so only use public keys there, such as `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

Backend variables must stay private, such as `SUPABASE_SERVICE_ROLE_KEY`, JWT secrets, and database direct URLs.

## Production checklist

- [ ] Move university data from CSV/local files to Supabase tables.
- [ ] Move uploads from local folder to Supabase Storage.
- [ ] Enable Supabase RLS on all tables.
- [ ] Create separate roles: student, partner, admin, super_admin.
- [ ] Use private storage buckets for student documents.
- [ ] Use public or signed URLs for university images and brochures.
- [ ] Add backup schedule for database and uploaded files.
- [ ] Add custom domain in Vercel.
- [ ] Add SSL through Vercel DNS/domain settings.
- [ ] Test login, uploads, favorites, application forms, and admin dashboard before launch.

