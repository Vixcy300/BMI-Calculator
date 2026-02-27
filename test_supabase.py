import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print(f"Testing connection to: {SUPABASE_URL}")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    # Try a simple select from a public table if exists, or just health check
    # But since we don't know tables, we'll try to list users (needs service_role auth)
    # Or just hit an endpoint.
    response = supabase.table("users").select("count", count="exact").limit(1).execute()
    print("✓ Connection successful!")
    print(f"Data: {response.data}")
except Exception as e:
    print(f"✗ Connection failed: {e}")
