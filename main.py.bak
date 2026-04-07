from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from jose import jwt, JWTError
from pydantic import BaseModel
import os
import json
import io
import zipfile
import pyzipper
from datetime import datetime, timedelta, timezone

from database import insert_entry, get_entries, delete_entry
from supabase import create_client

# --------------------------------------------------
# Configuración
# --------------------------------------------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

APP_PASSWORD = os.getenv("APP_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "43200"))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not set")

if not APP_PASSWORD or not JWT_SECRET:
    raise RuntimeError("Auth environment variables not set")

ALGORITHM = "HS256"
security = HTTPBearer()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # OK para uso personal
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# AUTH
# --------------------------------------------------

class LoginRequest(BaseModel):
    password: str

def create_access_token():
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRES_MINUTES)
    payload = {"sub": "diario_user", "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def require_auth(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(creds.credentials, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/auth/login")
def login(body: LoginRequest):
    if body.password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong password")
    return {"access_token": create_access_token()}

# --------------------------------------------------
# Endpoints del diario (PROTEGIDOS)
# --------------------------------------------------

@app.post("/entry")
def create_entry_endpoint(data: dict, _=Depends(require_auth)):
    text = data.get("text", "")
    insert_entry(text)
    return {"message": "Entrada guardada"}

@app.get("/entries")
def read_entries(_=Depends(require_auth)):
    return get_entries()

@app.delete("/entry/{entry_id}")
def remove_entry(entry_id: int, _=Depends(require_auth)):
    delete_entry(entry_id)
    return {"message": "Entrada eliminada"}

@app.get("/entries/search")
def search_entries(q: str, _=Depends(require_auth)):
    response = supabase.table("entries").select("*").execute()
    results = []

    for row in response.data:
        if q.lower() in row["text"].lower() or q in row["created_at"]:
            results.append(row)

    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results

# --------------------------------------------------
# Backup cifrado (PROTEGIDO)
# --------------------------------------------------

@app.get("/backup")
def backup_entries(_=Depends(require_auth)):
    response = supabase.table("entries").select("*").execute()
    entries = response.data

    memory_zip = io.BytesIO()
    password = APP_PASSWORD.encode()

    with pyzipper.AESZipFile(
        memory_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zf:
        zf.setpassword(password)
        json_bytes = json.dumps(
            entries,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")
        zf.writestr("diario_backup.json", json_bytes)

    memory_zip.seek(0)

    return StreamingResponse(
        memory_zip,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=diario_backup.zip"
        },
    )

# --------------------------------------------------
# Health & Keepalive (NO protegidos)
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "diario-backend",
        "ts": datetime.utcnow().isoformat(),
    }

@app.get("/keepalive")
def keepalive():
    try:
        resp = supabase.table("entries").select("id").limit(1).execute()
        return {
            "status": "ok",
            "rows": len(resp.data),
            "ts": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Supabase keepalive failed: {str(e)}"
        )