from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import create_table, insert_entry, get_entries, delete_entry
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# Permitir acceso desde el frontend (React en Vercel, por ejemplo)
origins = [
    "http://localhost:5173",  # desarrollo local
    "https://diario-frontend.vercel.app"  # producción en Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Entry(BaseModel):
    text: str

@app.on_event("startup")
def startup():
    create_table()

@app.post("/entry")
def add_entry(entry: Entry):
    try:
        insert_entry(entry.text)
        return {"message": "Entrada guardada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/entries")
def read_entries():
    return get_entries()

@app.delete("/entry/{entry_id}")
def remove_entry(entry_id: int):
    try:
        delete_entry(entry_id)
        return {"message": f"Entrada {entry_id} borrada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

