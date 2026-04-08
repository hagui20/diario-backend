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

from database import (
    insert_entry,
    get_entries,
    delete_entry,
    update_entry,
    update_entry_context,
    insert_body_log,
    get_body_logs,
    delete_body_log
)
from supabase import create_client
from openai import OpenAI

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
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# AUTH
# --------------------------------------------------

class LoginRequest(BaseModel):
    password: str

class EntryCreateRequest(BaseModel):
    text: str
    context: str = "normal"

class EntryUpdateRequest(BaseModel):
    text: str

class EntryContextRequest(BaseModel):
    context: str
    
class AIQuestionRequest(BaseModel):
    question: str
    
class BodyLogRequest(BaseModel):
    week_date: str
    weight: float
    body_fat: float
    muscle_mass: float
    sleep_score: int
    sleep_duration: float
    resting_hr: int
    intensity_minutes: int
    notes: str = ""

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
def create_entry_endpoint(body: EntryCreateRequest, _=Depends(require_auth)):
    insert_entry(body.text, body.context)
    return {"message": "Entrada guardada"}

@app.get("/entries")
def read_entries(_=Depends(require_auth)):
    return get_entries()

@app.put("/entry/{entry_id}")
def edit_entry(entry_id: int, body: EntryUpdateRequest, _=Depends(require_auth)):
    response = update_entry(entry_id, body.text)
    return {
        "message": "Entrada actualizada",
        "data": response.data
    }

@app.post("/ai/ask")
def ask_ai(body: AIQuestionRequest, _=Depends(require_auth)):
    try:
        entries = get_entries()
        body_logs = get_body_logs()

        entries_text = "\n\n".join([
            f"{e['created_at']} | contexto: {e.get('context', 'normal')} | texto: {e['text']}"
            for e in entries
        ]) if entries else "No hay entradas de diario."

        body_text = "\n\n".join([
            (
                f"Semana {log['week_date']} | "
                f"peso: {log['weight']} kg | "
                f"grasa: {log['body_fat']}% | "
                f"musculo: {log['muscle_mass']} kg | "
                f"sleep_score: {log['sleep_score']} | "
                f"sleep_duration: {log['sleep_duration']} h | "
                f"resting_hr: {log['resting_hr']} | "
                f"intensity_minutes: {log['intensity_minutes']} | "
                f"notes: {log.get('notes', '')}"
            )
            for log in body_logs
        ]) if body_logs else "No hay registros corporales."

        prompt = f"""
Eres un asistente que analiza de forma útil y prudente datos personales.

Tienes dos fuentes:
1. Diario emocional
2. Registros corporales semanales

DIARIO:
{entries_text}

CUERPO:
{body_text}

PREGUNTA DEL USUARIO:
{body.question}

Instrucciones:
- Responde en español.
- Usa tanto el diario como el cuerpo si es relevante.
- Si no hay evidencia suficiente, dilo claramente.
- No inventes datos ni conclusiones tajantes.
- Señala patrones, relaciones o tendencias si parecen razonables.
- Si procede, da recomendaciones prácticas sobre descanso, ejercicio, comida o enfoque personal.
- Sé claro, útil y humano.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return {
            "answer": response.choices[0].message.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.put("/entry/{entry_id}/context")
def set_entry_context(entry_id: int, body: EntryContextRequest, _=Depends(require_auth)):
    response = update_entry_context(entry_id, body.context)
    return {
        "message": "Contexto actualizado",
        "data": response.data
    }

@app.delete("/entry/{entry_id}")
def remove_entry(entry_id: int, _=Depends(require_auth)):
    delete_entry(entry_id)
    return {"message": "Entrada eliminada"}

@app.get("/entries/search")
def search_entries(q: str, _=Depends(require_auth)):
    response = supabase.table("entries").select("*").execute()
    results = []

    for row in response.data:
        text_value = row.get("text", "")
        created_at_value = row.get("created_at", "")
        context_value = row.get("context", "")
        if (
            q.lower() in text_value.lower()
            or q in created_at_value
            or q.lower() in context_value.lower()
        ):
            results.append(row)

    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results
    
@app.post("/body")
def create_body_log(body: BodyLogRequest, _=Depends(require_auth)):
    insert_body_log(body.dict())
    return {"message": "Body log saved"}

@app.get("/body")
def read_body_logs(_=Depends(require_auth)):
    return get_body_logs()

@app.delete("/body/{log_id}")
def remove_body_log(log_id: int, _=Depends(require_auth)):
    delete_body_log(log_id)
    return {"message": "Body log deleted"}

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