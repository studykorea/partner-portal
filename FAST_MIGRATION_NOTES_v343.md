# v343 Fast Next.js/FastAPI Migration

This version restores the main Partner Portal contents and layout from the Streamlit version while keeping the fast Next.js frontend structure.

## Restored frontend pages
- Home page with original hero text, buttons, lock notice, and featured universities
- Universities information page
- Partner login page
- Partner sign-up / access request page
- Partner dashboard
- Admin dashboard
- Eligibility check page
- Tuition & scholarship calculator page
- Saved universities page
- Application status / visa timeline page
- Contact page

## Deployment on Render
Frontend Node Web Service:
- Root Directory: empty
- Build Command: npm install && npm run build
- Start Command: npm run start
- Environment variable: NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-URL.onrender.com

Backend Python Web Service:
- Root Directory: backend
- Build Command: pip install -r requirements.txt
- Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

## Important
The legacy Streamlit app is kept in legacy_streamlit/app.py only as a backup/reference. Deploy the frontend as Node, not Streamlit.
