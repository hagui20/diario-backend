from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from database import DiarioEntry, SessionLocal
from datetime import datetime

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ o usa ["https://diario-frontend.vercel.app"] para más seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Permitir conexión desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de entrada
class Entry(BaseModel):
    text: str

# Guardar nueva entrada
@app.post("/entry")
def save_entry(entry: Entry):
    db = SessionLocal()
    new_entry = DiarioEntry(text=entry.text)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    db.close()
    return {
        "message": "Entrada guardada.",
        "entry": {
            "id": new_entry.id,
            "text": new_entry.text,
            "created_at": new_entry.created_at
        }
    }

# Obtener todas las entradas
@app.get("/entries")
def get_entries():
    db = SessionLocal()
    entries = db.query(DiarioEntry).order_by(DiarioEntry.created_at.desc()).all()
    db.close()
    return [
        {
            "id": e.id,
            "text": e.text,
            "created_at": e.created_at
        }
        for e in entries
    ]

# Eliminar entrada por ID
@app.delete("/entry/{entry_id}")
def delete_entry(entry_id: int):
    db = SessionLocal()
    entry = db.query(DiarioEntry).filter(DiarioEntry.id == entry_id).first()
    if not entry:
        db.close()
        raise HTTPException(status_code=404, detail="Entrada no encontrada.")
    db.delete(entry)
    db.commit()
    db.close()
    return {"message": "Entrada eliminada correctamente."}
