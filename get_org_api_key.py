"""
Fetch ORG003's API key from MongoDB and run the token tracking test.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import requests
import time

GATEWAY = "http://localhost:7000"
MONGODB_URI = "mongodb+srv://gisul2102_db_user:5cNJ1DcNCxwaJDaU@cluster0.dwcfp0l.mongodb.net/?appName=Cluster0"
DB_NAME = "aaptor_model"

async def get_org_api_key(org_id="ORG003"):
    """Fetch API key for the specified org from MongoDB"""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    
    # Try to find the org's API key
    # Check in api_keys collection
    api_keys_collection = db["api_keys"]
    api_key_doc = await api_keys_collection.find_one({"org_id": org_id})
    
    if api_key_doc:
        client.close()
        return api_key_doc.get("key")
    
    # If not found, check orgs collection for embedded key
    orgs_collection = db["orgs"]
    org_doc = await orgs_collection.find_one({"org_id": org_id})
    
    client.close()
    
    if org_doc and "api_key" in org_doc:
        return org_doc["api_key"]
    
    return None

async def test_with_org_key():
    """Run token tracking test with ORG003's API key"""
    print("=" * 60)
    print("Fetching ORG003 API Key from MongoDB")
    print("=" * 60)
    
    api_key = await get_org_api_key("ORG003")
    
    if not api_key:
        print("✗ Could not find API key for ORG003")
        print("\nTrying to list available orgs...")
        
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client[DB_NAME]
        
        # List orgs
        orgs_collection = db["orgs"]
        cursor = orgs_collection.find({}, {"org_id": 1, "org_name": 1, "_id": 0}).limit(10)
        orgs = await cursor.to_list(length=10)
        
        print("\nAvailable orgs:")
        for org in orgs:
            print(f"  - {org.get('org_id')}: {org.get('org_name')}")
        
        # List API keys
        api_keys_collection = db["api_keys"]
        cursor = api_keys_collection.find({}, {"org_id": 1, "key": 1, "_id": 0}).limit(10)
        keys = await cursor.to_list(length=10)
        
        print("\nAvailable API keys:")
        for key in keys:
            print(f"  - {key.get('org_id')}: {key.get('key')[:20]}...")
        
        client.close()
        return False
    
    print(f"✓ Found API key: {api_key[:20]}...\n")
    
    print("=" * 60)
    print("Token Tracking Test with ORG003 API Key")
    print("=" * 60)
    
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }
    
    payload = {
        "question": {
            "id": f"token-test-org-{int(time.time())}",
            "title": "Create a file",
            "description": "Create a file named test.txt",
            "instructions": "Use touch command",
            "difficulty": "beginner",
        },
        "submission": {
            "terminal_history": [
                {"command": "touch test.txt", "output": ""}
            ],
            "engine_response": {"exit_code": 0, "stdout": "", "stderr": ""},
            "validation_signals": {"passed": True, "question_score": 100, "max_score": 100},
        },
        "use_cache": False,
    }
    
    print(f"\nSubmitting evaluation for ORG003...")
    
    try:
        resp = requests.post(
            f"{GATEWAY}/api/v1/evaluation/linux/async",
            json=payload,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        print(f"✓ Job submitted: {job_id}")
        
        # Poll for completion
        for i in range(300):
            time.sleep(2)
            poll_resp = requests.get(
                f"{GATEWAY}/api/v1/job/{job_id}",
                headers=headers,
                timeout=10,
            )
            poll_resp.raise_for_status()
            data = poll_resp.json()
            
            status = data.get("status", "unknown")
            if i % 5 == 0:
                print(f"  [{i*2}s] Status: {status}")
            
            if status == "complete":
                print(f"\n✓ Job completed in {i*2}s")
                print(f"  Score: {data['result'].get('overall_score', 0)}/100")
                print("\n" + "=" * 60)
                print("✓ SUCCESS!")
                print("=" * 60)
                print("\nNow check the dashboard for ORG003:")
                print("- Total tokens should be > 0")
                print("- PROMPT column should show ~200-400")
                print("- COMPLETION column should show ~300-500")
                print(f"\nJob ID: {job_id}")
                return True
            elif status == "failed":
                print(f"\n✗ Job failed: {data.get('error')}")
                return False
        
        print("\n✗ Job timed out")
        return False
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_with_org_key())
