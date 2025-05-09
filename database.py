from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_entry(text):
    supabase.table("entries").insert({"text": text}).execute()

def get_entries():
    response = supabase.table("entries").select("*").order("created_at", desc=True).execute()
    return response.data

def delete_entry(entry_id):
    supabase.table("entries").delete().eq("id", entry_id).execute()

def create_table():
    pass  # Ya no se necesita con Supabase, la tabla existe en la nube

