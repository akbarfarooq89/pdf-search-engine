import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env file for local development
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# --- CONFIGURATION ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    """
    In the cloud version, we handle table creation via the Supabase SQL Editor.
    This function remains for compatibility.
    """
    pass
