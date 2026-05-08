#!/usr/bin/env python3
"""
Import SQL schemas from sql_schemas_library.json to MongoDB via RAG service API.

This sends the 636 schemas we just built to the RAG service.
"""
import json
import requests
from pathlib import Path

RAG_SERVICE_URL = "http://103.173.99.217:7003"
ADMIN_API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
SCHEMAS_FILE = Path(__file__).parent / "sql_schemas_library.json"

def main():
    print("=" * 70)
    print("SQL Schema Import to RAG Service")
    print("=" * 70)
    
    # Check RAG service
    print(f"\n1. Checking RAG service at {RAG_SERVICE_URL}...")
    try:
        response = requests.get(f"{RAG_SERVICE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("   ✓ RAG service is accessible")
        else:
            print(f"   ✗ RAG service returned status {response.status_code}")
            return
    except Exception as e:
        print(f"   ✗ Cannot reach RAG service: {e}")
        return
    
    # Load schemas
    print(f"\n2. Loading schemas from {SCHEMAS_FILE.name}...")
    if not SCHEMAS_FILE.exists():
        print(f"   ✗ File not found: {SCHEMAS_FILE}")
        return
    
    with open(SCHEMAS_FILE, "r", encoding="utf-8") as f:
        schemas = json.load(f)
    
    print(f"   ✓ Loaded {len(schemas)} schemas")
    
    # Send to RAG service
    print(f"\n3. Sending schemas to RAG service...")
    try:
        response = requests.post(
            f"{RAG_SERVICE_URL}/api/v1/import-sql-schemas",
            headers={
                "Content-Type": "application/json",
                "X-Admin-Api-Key": ADMIN_API_KEY
            },
            json={"schemas": schemas},
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Imported: {result.get('imported', 0)} new schemas")
            print(f"   ✓ Updated: {result.get('updated', 0)} existing schemas")
            print(f"   ✓ Total: {result.get('total', 0)} schemas in MongoDB")
        else:
            print(f"   ✗ Import failed: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return
    except Exception as e:
        print(f"   ✗ Failed to send schemas: {e}")
        return
    
    # Get statistics
    print(f"\n4. Schema Statistics:")
    try:
        response = requests.get(f"{RAG_SERVICE_URL}/api/v1/sql-schemas/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"\n   Total Schemas: {stats.get('total_schemas', 0)}")
            
            if 'by_domain' in stats:
                print(f"\n   Top 10 Domains:")
                for stat in stats['by_domain'][:10]:
                    print(f"   - {stat['_id']}: {stat['count']}")
            
            if 'by_category' in stats:
                print(f"\n   Schemas by SQL Category:")
                for stat in stats['by_category']:
                    print(f"   - {stat['_id']}: {stat['count']}")
    except Exception as e:
        print(f"   ⚠ Could not fetch statistics: {e}")
    
    print(f"\n" + "=" * 70)
    print(f"✓ Import completed successfully!")
    print(f"Schemas are now in MongoDB at {RAG_SERVICE_URL}")
    print(f"=" * 70)

if __name__ == "__main__":
    main()
