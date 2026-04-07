from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_entry(text, context="normal"):
    return supabase.table("entries").insert({
        "text": text,
        "context": context
    }).execute()

def get_entries():
    response = supabase.table("entries").select("*").order("created_at", desc=True).execute()
    return response.data

def delete_entry(entry_id):
    return supabase.table("entries").delete().eq("id", entry_id).execute()

def update_entry(entry_id: int, text: str):
    return supabase.table("entries").update({"text": text}).eq("id", entry_id).execute()

def update_entry_context(entry_id: int, context: str):
    return supabase.table("entries").update({"context": context}).eq("id", entry_id).execute()