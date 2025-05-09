from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
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

    # Ordenar por fecha descendente
    results.sort(key=lambda x: x["created_at"], reverse=True)

    return results
