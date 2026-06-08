import csv
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "UniQuest Partner Portal API"
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

app = FastAPI(title=APP_NAME, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def read_csv(name: str) -> list[dict[str, Any]]:
    path = DATA_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing data file: {name}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]

@app.get("/health")
def health_check():
    return {"status": "ok", "service": APP_NAME, "runtime": "fastapi"}

@app.get("/api/universities")
def list_universities():
    return {"items": read_csv("universities.csv")}

@app.get("/api/admission-criteria")
def list_admission_criteria():
    return {"items": read_csv("admission_criteria.csv")}

@app.post("/api/uploads/student-document")
async def upload_student_document(file: UploadFile = File(...)):
    allowed_types = {"application/pdf", "image/jpeg", "image/png"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, and PNG files are allowed.")
    # Production: upload to Supabase Storage, then insert metadata into Postgres.
    return {
        "message": "Received. Connect this endpoint to Supabase Storage before production document collection.",
        "filename": file.filename,
        "content_type": file.content_type,
    }
