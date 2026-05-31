# Frontend Deployment Target

Recommended target: Vercel.

This folder is prepared for the future production frontend. The current Streamlit prototype remains in the repository root. For production scalability, migrate public pages, partner login pages, admin dashboard, and university pages into this frontend folder.

Vercel settings:
- Framework: Next.js
- Root directory: frontend
- Build command: npm run build
- Output: .next
- Environment variables: use frontend/.env.example
