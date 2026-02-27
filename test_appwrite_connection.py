import os
from dotenv import load_dotenv
from appwrite.client import Client
from appwrite.services.databases import Databases

load_dotenv()

APPWRITE_ENDPOINT = os.getenv("APPWRITE_ENDPOINT")
APPWRITE_PROJECT_ID = os.getenv("APPWRITE_PROJECT_ID")
APPWRITE_API_KEY = os.getenv("APPWRITE_API_KEY")

print(f"Testing Appwrite Connection...")
print(f"Endpoint: {APPWRITE_ENDPOINT}")
print(f"Project ID: {APPWRITE_PROJECT_ID}")

client = Client()
client.set_endpoint(APPWRITE_ENDPOINT)
client.set_project(APPWRITE_PROJECT_ID)
client.set_key(APPWRITE_API_KEY)

databases = Databases(client)

try:
    # Test by listing databases
    resp = databases.list()
    print("✓ Success! Databases found:")
    for db in resp['databases']:
        print(f" - {db['name']} (ID: {db['$id']})")
except Exception as e:
    print(f"✗ Failed: {e}")
