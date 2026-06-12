import csv
import os
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, create_client

load_dotenv()

APP_NAME = "Korea University Admissions KUA API"
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
UNIVERSITY_BUCKET = os.getenv("SUPABASE_UNIVERSITY_BUCKET", "kua-university-assets")

app = FastAPI(title=APP_NAME, version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_supabase: Optional[Client] = None

def get_supabase() -> Client:
    global _supabase
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=503, detail="Supabase is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to the backend environment variables.")
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase

def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

def slugify(text: str) -> str:
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", text.lower()))

def read_csv(name: str) -> list[dict[str, Any]]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]

def default_universities() -> list[dict[str, Any]]:
    rows = read_csv("universities.csv")
    if not rows:
        return []
    items = []
    for row in rows:
        name = row.get("name") or row.get("university") or "University"
        items.append({
            "slug": slugify(name),
            "name": name,
            "location": row.get("location") or row.get("city") or "",
            "region": row.get("region") or row.get("location") or "",
            "students": row.get("students") or row.get("total_students") or "Not updated",
            "internationalStudents": row.get("international_students") or row.get("internationalStudents") or "Not updated",
            "type": row.get("type") or "Partner University",
            "established": row.get("established") or "Not updated",
            "accreditation": row.get("accreditation") or "Not updated",
            "accreditationBadge": row.get("accreditation_badge_url") or "/assets/certified_information_badge_custom.png",
            "homepage": row.get("homepage") or row.get("website") or "",
            "email": row.get("email") or "koreastudypartner@gmail.com",
            "phone": row.get("phone") or "",
            "address": row.get("address") or "",
            "overview": row.get("overview") or "",
            "tuition": row.get("tuition") or row.get("tuition_range") or "Not updated",
            "intake": row.get("intake") or "March, September",
            "topMajors": [x.strip() for x in (row.get("top_majors") or row.get("majors") or "").split("|") if x.strip()],
            "graduatePrograms": [x.strip() for x in (row.get("graduate_programs") or "").split("|") if x.strip()],
            "klpPrograms": [x.strip() for x in (row.get("klp_programs") or "D4-1 (4 semester)|Korean Language Program|KLP / EAP").split("|") if x.strip()],
            "image": row.get("image") or row.get("card_image_url") or "/assets/kyungsung.webp",
            "logo": row.get("logo") or row.get("logo_url") or "",
            "heroImage": row.get("hero_image_url") or row.get("image") or "/assets/kyungsung.webp",
            "videoUrl": row.get("video_url") or "",
            "brochureUrl": row.get("brochure_url") or "",
            "facebookUrl": row.get("facebook_url") or "",
            "instagramUrl": row.get("instagram_url") or "",
            "youtubeUrl": row.get("youtube_url") or "",
            "admissions": [
                {"program": "Undergraduate", "open": "", "close": "", "status": "Not fixed yet", "tone": "notfixed"},
                {"program": "Graduate (Masters/Ph.D.)", "open": "", "close": "", "status": "Not fixed yet", "tone": "notfixed"},
                {"program": "KLP / EAP", "open": "", "close": "", "status": "Not fixed yet", "tone": "notfixed"},
            ],
        })
    return items

def normalize_university(row: dict[str, Any], admissions: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    name = row.get("name") or "University"
    slug = row.get("slug") or slugify(name)
    def arr(key: str) -> list[str]:
        value = row.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [x.strip() for x in value.split("|") if x.strip()]
        return []
    return {
        "slug": slug,
        "name": name,
        "location": row.get("location") or "",
        "region": row.get("region") or "",
        "students": row.get("students") or "Not updated",
        "internationalStudents": row.get("international_students") or row.get("internationalStudents") or "Not updated",
        "type": row.get("type") or "Partner University",
        "established": row.get("established") or "Not updated",
        "accreditation": row.get("accreditation") or "Not updated",
        "accreditationBadge": row.get("accreditation_badge_url") or row.get("accreditationBadge") or "",
        "homepage": row.get("homepage") or "",
        "email": row.get("email") or "",
        "phone": row.get("phone") or "",
        "address": row.get("address") or "",
        "overview": row.get("overview") or "",
        "tuition": row.get("tuition") or "Not updated",
        "intake": row.get("intake") or "March, September",
        "topMajors": arr("top_majors") or arr("topMajors"),
        "graduatePrograms": arr("graduate_programs") or arr("graduatePrograms"),
        "klpPrograms": arr("klp_programs") or arr("klpPrograms"),
        "image": row.get("card_image_url") or row.get("image") or "",
        "logo": row.get("logo_url") or row.get("logo") or "",
        "heroImage": row.get("hero_image_url") or row.get("heroImage") or row.get("card_image_url") or row.get("image") or "",
        "videoUrl": row.get("video_url") or row.get("videoUrl") or "",
        "brochureUrl": row.get("brochure_url") or row.get("brochureUrl") or "",
        "facebookUrl": row.get("facebook_url") or row.get("facebookUrl") or "",
        "instagramUrl": row.get("instagram_url") or row.get("instagramUrl") or "",
        "youtubeUrl": row.get("youtube_url") or row.get("youtubeUrl") or "",
        "admissions": admissions or row.get("admissions") or [],
    }

class AdmissionPayload(BaseModel):
    program: str
    open: str = ""
    close: str = ""
    status: str = "Not fixed yet"
    tone: str = "notfixed"

class UniversityPayload(BaseModel):
    name: str
    location: str = ""
    region: str = ""
    students: str = ""
    internationalStudents: str = ""
    type: str = "Partner University"
    established: str = "Not updated"
    accreditation: str = "Not updated"
    accreditationBadge: str = ""
    homepage: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    overview: str = ""
    tuition: str = ""
    intake: str = ""
    topMajors: list[str] = Field(default_factory=list)
    graduatePrograms: list[str] = Field(default_factory=list)
    klpPrograms: list[str] = Field(default_factory=list)
    image: str = ""
    logo: str = ""
    heroImage: str = ""
    videoUrl: str = ""
    brochureUrl: str = ""
    facebookUrl: str = ""
    instagramUrl: str = ""
    youtubeUrl: str = ""
    admissions: list[AdmissionPayload] = Field(default_factory=list)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": APP_NAME, "runtime": "fastapi", "supabase": supabase_configured()}

@app.get("/api/universities")
def list_universities():
    if not supabase_configured():
        return {"items": default_universities(), "source": "csv-fallback"}
    sb = get_supabase()
    res = sb.table("universities").select("*").order("sort_order").execute()
    items = []
    for row in res.data or []:
        adm = sb.table("admission_timelines").select("program,open_date,close_date,status,tone").eq("university_slug", row["slug"]).order("sort_order").execute()
        admissions = [{"program": a.get("program"), "open": a.get("open_date") or "", "close": a.get("close_date") or "", "status": a.get("status") or "Not fixed yet", "tone": a.get("tone") or "notfixed"} for a in (adm.data or [])]
        items.append(normalize_university(row, admissions))
    return {"items": items, "source": "supabase"}

@app.get("/api/universities/{slug}")
def get_university(slug: str):
    if not supabase_configured():
        item = next((u for u in default_universities() if u["slug"] == slug), None)
        if not item:
            raise HTTPException(status_code=404, detail="University not found")
        return item
    sb = get_supabase()
    res = sb.table("universities").select("*").eq("slug", slug).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="University not found")
    row = res.data[0]
    adm = sb.table("admission_timelines").select("program,open_date,close_date,status,tone").eq("university_slug", slug).order("sort_order").execute()
    admissions = [{"program": a.get("program"), "open": a.get("open_date") or "", "close": a.get("close_date") or "", "status": a.get("status") or "Not fixed yet", "tone": a.get("tone") or "notfixed"} for a in (adm.data or [])]
    return normalize_university(row, admissions)

@app.put("/api/admin/universities/{slug}")
def upsert_university(slug: str, payload: UniversityPayload):
    sb = get_supabase()
    new_slug = slugify(payload.name)
    record = {
        "slug": new_slug,
        "name": payload.name,
        "location": payload.location,
        "region": payload.region,
        "students": payload.students,
        "international_students": payload.internationalStudents,
        "type": payload.type,
        "established": payload.established,
        "accreditation": payload.accreditation,
        "accreditation_badge_url": payload.accreditationBadge,
        "homepage": payload.homepage,
        "email": payload.email,
        "phone": payload.phone,
        "address": payload.address,
        "overview": payload.overview,
        "tuition": payload.tuition,
        "intake": payload.intake,
        "top_majors": "|".join(payload.topMajors),
        "graduate_programs": "|".join(payload.graduatePrograms),
        "klp_programs": "|".join(payload.klpPrograms),
        "card_image_url": payload.image,
        "logo_url": payload.logo,
        "hero_image_url": payload.heroImage,
        "video_url": payload.videoUrl,
        "brochure_url": payload.brochureUrl,
        "facebook_url": payload.facebookUrl,
        "instagram_url": payload.instagramUrl,
        "youtube_url": payload.youtubeUrl,
    }
    # If name/slug changed, keep using upsert on new slug. Old slug can be cleaned manually if needed.
    sb.table("universities").upsert(record, on_conflict="slug").execute()
    sb.table("admission_timelines").delete().eq("university_slug", new_slug).execute()
    rows = []
    for idx, a in enumerate(payload.admissions):
        rows.append({
            "university_slug": new_slug,
            "program": a.program,
            "open_date": a.open,
            "close_date": a.close,
            "status": a.status,
            "tone": a.tone,
            "sort_order": idx,
        })
    if rows:
        sb.table("admission_timelines").insert(rows).execute()
    return {"ok": True, "slug": new_slug, "item": normalize_university(record, [a.model_dump() for a in payload.admissions])}

@app.post("/api/admin/universities/{slug}/upload")
async def upload_university_asset(slug: str, asset_type: str = Form(...), file: UploadFile = File(...)):
    allowed = {"logo", "card_image", "hero_image", "accreditation_badge", "brochure"}
    if asset_type not in allowed:
        raise HTTPException(status_code=400, detail=f"asset_type must be one of {sorted(allowed)}")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")
    sb = get_supabase()
    ext = Path(file.filename).suffix.lower() or ".bin"
    folder = asset_type.replace("_", "-")
    path = f"{slug}/{folder}{ext}"
    body = await file.read()
    try:
        sb.storage.from_(UNIVERSITY_BUCKET).upload(path, body, file_options={"content-type": file.content_type or "application/octet-stream", "upsert": "true"})
    except Exception:
        # Supabase upload may throw if object exists despite upsert; remove and retry.
        try:
            sb.storage.from_(UNIVERSITY_BUCKET).remove([path])
        except Exception:
            pass
        sb.storage.from_(UNIVERSITY_BUCKET).upload(path, body, file_options={"content-type": file.content_type or "application/octet-stream"})
    public_url = sb.storage.from_(UNIVERSITY_BUCKET).get_public_url(path)
    column = {
        "logo": "logo_url",
        "card_image": "card_image_url",
        "hero_image": "hero_image_url",
        "accreditation_badge": "accreditation_badge_url",
        "brochure": "brochure_url",
    }[asset_type]
    sb.table("universities").update({column: public_url}).eq("slug", slug).execute()
    return {"ok": True, "asset_type": asset_type, "url": public_url}

@app.post("/api/admin/seed")
def seed_default_universities():
    sb = get_supabase()
    items = default_universities()
    for idx, item in enumerate(items):
        payload = UniversityPayload(**item)
        record = {
            "slug": item["slug"], "name": payload.name, "location": payload.location, "region": payload.region,
            "students": payload.students, "international_students": payload.internationalStudents,
            "type": payload.type, "established": payload.established, "accreditation": payload.accreditation,
            "accreditation_badge_url": payload.accreditationBadge, "homepage": payload.homepage, "email": payload.email,
            "phone": payload.phone, "address": payload.address, "overview": payload.overview, "tuition": payload.tuition,
            "intake": payload.intake, "top_majors": "|".join(payload.topMajors), "graduate_programs": "|".join(payload.graduatePrograms),
            "klp_programs": "|".join(payload.klpPrograms), "card_image_url": payload.image, "logo_url": payload.logo,
            "hero_image_url": payload.heroImage, "video_url": payload.videoUrl, "brochure_url": payload.brochureUrl,
            "facebook_url": payload.facebookUrl, "instagram_url": payload.instagramUrl, "youtube_url": payload.youtubeUrl, "sort_order": idx,
        }
        sb.table("universities").upsert(record, on_conflict="slug").execute()
        rows = [{"university_slug": item["slug"], "program": a["program"], "open_date": a.get("open", ""), "close_date": a.get("close", ""), "status": a.get("status", "Not fixed yet"), "tone": a.get("tone", "notfixed"), "sort_order": i} for i, a in enumerate(item["admissions"])]
        if rows:
            sb.table("admission_timelines").upsert(rows).execute()
    return {"ok": True, "inserted": len(items)}

@app.get("/api/admission-criteria")
def list_admission_criteria():
    return {"items": read_csv("admission_criteria.csv")}

@app.post("/api/uploads/student-document")
async def upload_student_document(file: UploadFile = File(...)):
    allowed_types = {"application/pdf", "image/jpeg", "image/png"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, and PNG files are allowed.")
    return {"message": "Received. For production, store in Supabase Storage.", "filename": file.filename, "content_type": file.content_type}
