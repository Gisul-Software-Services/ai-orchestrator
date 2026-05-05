"""
Simple script to retrieve and display ORG003's API key from MongoDB.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = "mongodb+srv://gisul2102_db_user:5cNJ1DcNCxwaJDaU@cluster0.dwcfp0l.mongodb.net/?appName=Cluster0"
DB_NAME = "aaptor_model"

async def show_api_key():
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    print("Connecting to MongoDB...")
    
    # Check api_keys collection structure
    api_keys_collection = db["api_keys"]
    print("\n=== API Keys Collection ===")
    cursor = api_keys_collection.find({"org_id": "ORG003"})
    keys = await cursor.to_list(length=10)
    
    if keys:
        print(f"Found {len(keys)} API key(s) for ORG003:")
        for key_doc in keys:
            print(f"\n  Document:")
            for k, v in key_doc.items():
                if k == "_id":
                    continue
                print(f"    {k}: {v}")
    else:
        print("No API keys found for ORG003 in api_keys collection")
    
    # Check orgs collection
    orgs_collection = db["orgs"]
    org_doc = await orgs_collection.find_one({"org_id": "ORG003"})
    
    if org_doc:
        print(f"\n=== Orgs Collection ===")
        print(f"Org Name: {org_doc.get('name')}")
        print(f"Org ID: {org_doc.get('orgId')}")
        if 'model_api_key' in org_doc:
            print(f"Model API Key: {org_doc.get('model_api_key')}")
        
        # Show all fields
        print(f"\nAll fields in org document:")
        for k, v in org_doc.items():
            if k not in ["_id", "model_api_key"]:
                print(f"  {k}: {v}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(show_api_key())
