from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import create_table, insert_entry, get_entries, delete_entry

app = FastAPI()

# 🔒 Middleware CORS para permitir peticiones desde el frontend en Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://diario-frontend.vercel.app"],  # más seguro que usar "*"
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
    insert_entry(entry.text)
    return {"message": "Guardado correctamente"}

@app.get("/entries")
def read_entries():
    return get_entries()

@app.delete("/entry/{entry_id}")
def delete(entry_id: int):
    delete_entry(entry_id)
    return {"message": "Entrada eliminada"}
