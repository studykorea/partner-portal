# KUA v355 Real Admin Editing Setup

This version connects the Super Admin editor to a real backend/database.

## 1. Supabase

Create/open your Supabase project, then run:

`supabase/kua_schema_v355.sql`

This creates:
- `universities`
- `admission_timelines`
- `applications`
- `partners`
- Storage bucket: `kua-university-assets`

## 2. Backend Render service environment variables

Add these to the **backend** Render service only:

```text
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_UNIVERSITY_BUCKET=kua-university-assets
ALLOWED_ORIGINS=https://partner-portal-frontend-3d0l.onrender.com
```

Start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Root directory:

```text
backend
```

## 3. Frontend Render service environment variable

Add this to the **frontend** Render service:

```text
NEXT_PUBLIC_API_URL=https://your-backend-service.onrender.com
```

## 4. Seed default universities

After the backend is live and Supabase variables are set, open this URL once in browser or Postman as POST:

```text
POST https://your-backend-service.onrender.com/api/admin/seed
```

Then `/universities` and university detail pages will load universities from Supabase.

## 5. Super Admin editing

Go to:

```text
/admin
```

Edit a university, upload logo/card/hero images, adjust application dates/statuses, and click **Save University Changes**.

The public pages will then read the saved data from Supabase.
