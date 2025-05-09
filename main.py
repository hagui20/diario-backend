from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import json
import tempfile
import zipfile
import pyzipper

from database import insert_entry, get_entries, delete_entry
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# CORS (permite que el frontend se conecte)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puedes restringir a ["https://tu-app.vercel.app"]
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
    """
    Buscar entradas que contengan el texto `q` en el campo `text`
    o entradas creadas en una fecha exacta (YYYY-MM-DD).
    """
    response = supabase.table("entries").select("*").execute()
    results = []

    for row in response.data:
        if q.lower() in row["text"].lower() or q in row["created_at"]:
            results.append(row)

    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results

@app.get("/backup")
def backup_entries():
    """
    Crea un archivo ZIP cifrado con las entradas en JSON.
    La contraseña del ZIP es la misma que la de acceso al diario: 10528
    """
    response = supabase.table("entries").select("*").execute()
    entries = response.data

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "diario_backup.json")
        zip_path = os.path.join(tmpdir, "diario_backup.zip")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

        password = b"10528"
        with pyzipper.AESZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password)
            zf.write(json_path, arcname="diario_backup.json")  # ← esta línea es clave

        return FileResponse(zip_path, filename="diario_backup.zip", media_type="application/zip")
