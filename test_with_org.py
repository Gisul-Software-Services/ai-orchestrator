"""
Test token tracking using admin key with explicit org metadata.
Since we can't retrieve the plain text API key, we'll use the admin key
and pass org_id explicitly via X-Usage-Meta header.
"""
import requests
import time
import base64
import json

GATEWAY = "http://localhost:7000"
ADMIN_API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"

def test_with_org_metadata():
    """Test with explicit org metadata in header"""
    
    # Create usage metadata for ORG003
    usage_meta = {
        "org_id": "ORG003",
        "org_name": "Gisul softwares",
        "org_verified": True,
        "client_ip": "127.0.0.1",
        "user_agent": "token-tracking-test",
        "correlation_id": f"test-{int(time.time())}",
    }
    
    # Encode as base64
    meta_json = json.dumps(usage_meta)
    meta_b64 = base64.b64encode(meta_json.encode('utf-8')).decode('ascii')
    
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": ADMIN_API_KEY,
        "X-Usage-Meta": meta_b64,  # Pass org info explicitly
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
    
    print("=" * 60)
    print("Token Tracking Test with ORG003 Metadata")
    print("=" * 60)
    print(f"\nSubmitting evaluation for ORG003...")
    print(f"Using admin key with X-Usage-Meta header")
    
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
    test_with_org_metadata()
