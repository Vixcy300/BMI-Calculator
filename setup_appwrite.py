from appwrite.client import Client
from appwrite.services.databases import Databases
import os
from dotenv import load_dotenv

load_dotenv()

# Appwrite Connection
APPWRITE_ENDPOINT = os.getenv("APPWRITE_ENDPOINT")
APPWRITE_PROJECT_ID = os.getenv("APPWRITE_PROJECT_ID")
APPWRITE_API_KEY = os.getenv("APPWRITE_API_KEY")

client = Client()
client.set_endpoint(APPWRITE_ENDPOINT)
client.set_project(APPWRITE_PROJECT_ID)
client.set_key(APPWRITE_API_KEY)

databases = Databases(client)

DATABASE_NAME = "upgraded_lifestyle"
DATABASE_ID = "upgraded_lifestyle_db"

def setup():
    print(f"Starting setup for Appwrite Project: {APPWRITE_PROJECT_ID}")
    
    # 1. Create Database
    try:
        databases.create(database_id=DATABASE_ID, name=DATABASE_NAME)
        print(f"✓ Created Database: {DATABASE_NAME} ({DATABASE_ID})")
    except Exception as e:
        print(f"! Database might already exist: {e}")

    # 2. Create Collections
    collections = {
        "users": [
            {"key": "username", "type": "string", "size": 255, "required": True},
            {"key": "email", "type": "string", "size": 255, "required": True},
            {"key": "password", "type": "string", "size": 255, "required": True},
            {"key": "created_at", "type": "string", "size": 255, "required": False}
        ],
        "bmi_records": [
            {"key": "user_id", "type": "string", "size": 255, "required": True},
            {"key": "name", "type": "string", "size": 255, "required": True},
            {"key": "age", "type": "integer", "required": True},
            {"key": "sex", "type": "string", "size": 10, "required": True},
            {"key": "height", "type": "float", "required": True},
            {"key": "weight", "type": "float", "required": True},
            {"key": "bmi", "type": "float", "required": True},
            {"key": "category", "type": "string", "size": 50, "required": True},
            {"key": "created_at", "type": "string", "size": 255, "required": False}
        ],
        "analyzed_reports": [
            {"key": "user_id", "type": "string", "size": 255, "required": True},
            {"key": "image_filename", "type": "string", "size": 255, "required": False},
            {"key": "analysis_text", "type": "string", "size": 5000, "required": False},
            {"key": "suggestions", "type": "string", "size": 5000, "required": False},
            {"key": "overview", "type": "string", "size": 5000, "required": False},
            {"key": "report_type", "type": "string", "size": 255, "required": False},
            {"key": "created_at", "type": "string", "size": 255, "required": False}
        ],
        "chat_messages": [
            {"key": "user_id", "type": "string", "size": 255, "required": True},
            {"key": "role", "type": "string", "size": 50, "required": True},
            {"key": "message", "type": "string", "size": 5000, "required": True},
            {"key": "created_at", "type": "string", "size": 255, "required": False}
        ],
        "user_goals": [
            {"key": "user_id", "type": "string", "size": 255, "required": True},
            {"key": "goal_type", "type": "string", "size": 255, "required": False},
            {"key": "target_value", "type": "float", "required": False},
            {"key": "status", "type": "string", "size": 50, "required": False},
            {"key": "activities", "type": "string", "size": 1000, "required": False},
            {"key": "created_at", "type": "string", "size": 255, "required": False}
        ],
        "water_logs": [
            {"key": "user_id", "type": "string", "size": 255, "required": True},
            {"key": "amount_ml", "type": "integer", "required": True},
            {"key": "date", "type": "string", "size": 50, "required": True},
            {"key": "created_at", "type": "string", "size": 255, "required": False}
        ]
    }

    for coll_id, attrs in collections.items():
        try:
            databases.create_collection(database_id=DATABASE_ID, collection_id=coll_id, name=coll_id)
            print(f"✓ Created Collection: {coll_id}")
            
            # Add attributes
            for attr in attrs:
                if attr["type"] == "string":
                    databases.create_string_attribute(DATABASE_ID, coll_id, attr["key"], attr["size"], attr["required"])
                elif attr["type"] == "integer":
                    databases.create_integer_attribute(DATABASE_ID, coll_id, attr["key"], attr["required"])
                elif attr["type"] == "float":
                    databases.create_float_attribute(DATABASE_ID, coll_id, attr["key"], attr["required"])
                print(f"  - Added attribute: {attr['key']}")
            
        except Exception as e:
            print(f"! Collection {coll_id} might already exist: {e}")

    print("\nSetup complete! Update your .env with these IDs:")
    print(f"APPWRITE_DATABASE_ID={DATABASE_ID}")
    print("APPWRITE_USERS_COLLECTION_ID=users")
    print("APPWRITE_BMI_RECORDS_COLLECTION_ID=bmi_records")
    print("APPWRITE_REPORTS_COLLECTION_ID=analyzed_reports")
    print("APPWRITE_MESSAGES_COLLECTION_ID=chat_messages")
    print("APPWRITE_GOALS_COLLECTION_ID=user_goals")
    print("APPWRITE_WATER_COLLECTION_ID=water_logs")

if __name__ == "__main__":
    setup()
