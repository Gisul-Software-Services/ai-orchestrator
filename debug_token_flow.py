"""
Debug script to check if tokens are being passed through the chain.
Checks the database directly after a test evaluation.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_recent_usage():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["gisul_model"]
    usage_logs = db["usage_logs"]
    
    # Get the most recent 5 records
    cursor = usage_logs.find().sort("created_at", -1).limit(5)
    records = await cursor.to_list(length=5)
    
    print("=" * 60)
    print("Recent Usage Logs (last 5)")
    print("=" * 60)
    
    for i, record in enumerate(records, 1):
        print(f"\n{i}. Job ID: {record.get('job_id', 'N/A')}")
        print(f"   Org ID: {record.get('org_id', 'N/A')}")
        print(f"   Route: {record.get('route', 'N/A')}")
        print(f"   Prompt Tokens: {record.get('prompt_tokens', 0)}")
        print(f"   Completion Tokens: {record.get('completion_tokens', 0)}")
        print(f"   Total Tokens: {record.get('total_tokens', 0)}")
        print(f"   Status: {record.get('status', 'N/A')}")
        print(f"   Created: {record.get('created_at', 'N/A')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_recent_usage())
