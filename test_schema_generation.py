"""
Test script for schema-based SQL question generation

Usage:
    python test_schema_generation.py
"""
import asyncio
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
BASE_URL = "http://localhost:7000"
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg")


def test_schema_generation():
    """Test schema-based SQL question generation"""
    print("=" * 70)
    print("Schema-Based SQL Question Generation Test")
    print("=" * 70)
    
    # Test cases
    test_cases = [
        {
            "name": "Easy Select Query",
            "difficulty": "Easy",
            "topic": "select",
            "sql_category": "select"
        },
        {
            "name": "Medium Join Query",
            "difficulty": "Medium",
            "topic": "joins",
            "sql_category": "join"
        },
        {
            "name": "Medium Aggregation Query",
            "difficulty": "Medium",
            "topic": "aggregation",
            "sql_category": "aggregation"
        },
        {
            "name": "Hard Window Function Query",
            "difficulty": "Hard",
            "topic": "window",
            "sql_category": "window"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"   Difficulty: {test_case['difficulty']}")
        print(f"   Category: {test_case['sql_category']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/generate-sql-question-from-schema",
                headers={
                    "Content-Type": "application/json",
                    "X-Api-Key": ADMIN_API_KEY
                },
                json={
                    "difficulty": test_case["difficulty"],
                    "topic": test_case["topic"],
                    "sql_category": test_case["sql_category"],
                    "count": 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Success!")
                print(f"   Title: {data.get('title', 'N/A')[:60]}...")
                print(f"   Schema ID: {data.get('schema_id', 'N/A')}")
                print(f"   Domain: {data.get('schemas', {}).keys()}")
                print(f"   Query: {data.get('reference_query', 'N/A')[:80]}...")
                
                if data.get('token_usage'):
                    tokens = data['token_usage']
                    print(f"   Tokens: {tokens.get('total_tokens', 0)} (prompt: {tokens.get('prompt_tokens', 0)}, completion: {tokens.get('completion_tokens', 0)})")
                
                results.append({
                    "test": test_case["name"],
                    "status": "PASS",
                    "title": data.get('title', ''),
                    "schema_id": data.get('schema_id', ''),
                    "tokens": data.get('token_usage', {}).get('total_tokens', 0)
                })
            else:
                print(f"   ✗ Failed: {response.status_code}")
                print(f"   Error: {response.text[:200]}")
                results.append({
                    "test": test_case["name"],
                    "status": "FAIL",
                    "error": response.text[:200]
                })
        
        except requests.exceptions.ConnectionError:
            print(f"   ✗ Connection Error: Is the server running at {BASE_URL}?")
            results.append({
                "test": test_case["name"],
                "status": "ERROR",
                "error": "Connection refused"
            })
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            results.append({
                "test": test_case["name"],
                "status": "ERROR",
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⚠ Errors: {errors}")
    
    if passed == len(results):
        print("\n🎉 All tests passed!")
    elif errors > 0:
        print("\n⚠ Some tests had errors. Check if the server is running.")
    else:
        print("\n❌ Some tests failed. Check the logs above.")
    
    # Check uniqueness
    if passed > 1:
        titles = [r.get("title", "") for r in results if r["status"] == "PASS"]
        schema_ids = [r.get("schema_id", "") for r in results if r["status"] == "PASS"]
        
        print(f"\nUniqueness Check:")
        print(f"  Unique titles: {len(set(titles))}/{len(titles)}")
        print(f"  Unique schemas: {len(set(schema_ids))}/{len(schema_ids)}")
        
        if len(set(titles)) == len(titles):
            print("  ✓ All questions are unique!")
        else:
            print("  ⚠ Some questions have duplicate titles")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_schema_generation()
