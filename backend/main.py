import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "Korea University Admissions Partner Portal API"
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]

app = FastAPI(title=APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": APP_NAME}

@app.get("/api/config")
def api_config():
    return {
        "storage": "Supabase Storage or S3-compatible storage",
        "database": "Supabase Postgres",
        "auth": "Supabase Auth",
    }

@app.post("/api/uploads/student-document")
async def upload_student_document(file: UploadFile = File(...)):
    """
    Production note:
    Replace this placeholder with Supabase Storage upload logic.
    Student documents must not be saved permanently in the project folder.
    Use a private Supabase Storage bucket and store only file metadata in Postgres.
    """
    allowed_types = {"application/pdf", "image/jpeg", "image/png"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, and PNG files are allowed.")

    return {
        "message": "Upload endpoint placeholder. Connect this to Supabase Storage before production launch.",
        "filename": file.filename,
        "content_type": file.content_type,
    }
