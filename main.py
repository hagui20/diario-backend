from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os
import json
import io
import zipfile
import pyzipper

from database import insert_entry, get_entries, delete_entry
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/entry")
def create_entry(data: dict):
    text = data.get("text", "")
    insert_entry(text)
    return {"message": "Entrada guardada"}

@app.get("/entries")
def read_entries():
    return get_entries()

@app.delete("/entry/{entry_id}")
def remove_entry(entry_id: int):
    delete_entry(entry_id)
    return {"message": "Entrada eliminada"}

@app.get("/entries/search")
def search_entries(q: str):
    response = supabase.table("entries").select("*").execute()
    results = []

    for row in response.data:
        if q.lower() in row["text"].lower() or q in row["created_at"]:
            results.append(row)

    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results

@app.get("/backup")
def backup_entries():
    response = supabase.table("entries").select("*").execute()
    entries = response.data

    # Crear buffer en memoria
    memory_zip = io.BytesIO()
    password = b"10528"

    with pyzipper.AESZipFile(memory_zip, "w", compression=zipfile.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password)
        json_bytes = json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
        zf.writestr("diario_backup.json", json_bytes)

    memory_zip.seek(0)
    return StreamingResponse(memory_zip, media_type="application/zip", headers={
        "Content-Disposition": "attachment; filename=diario_backup.zip"
    })
