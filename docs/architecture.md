# Production architecture

## Frontend
Recommended: Next.js on Vercel.

Frontend responsibilities:
- Public homepage
- Universities listing/detail pages
- Partner login UI
- Admin/super-admin dashboard UI
- Application form UI
- Favorites/saved universities UI

## Backend API
Recommended: FastAPI on Render or Railway.

Backend responsibilities:
- Secure file upload processing
- Signed URL generation
- Admin/super-admin actions that need service-role access
- Webhooks and future scheduled tasks
- Optional PDF generation or document validation

## Supabase
Supabase responsibilities:
- Postgres database
- Auth
- Storage
- Row Level Security
- Application data
- University data
- Admission dates
- Favorites

## Why not GitHub Pages
GitHub Pages is only for static websites. This project needs server-side features, authentication, database reads/writes, file uploads, access control, and secure storage. Therefore GitHub Pages is not enough.
