"""
Quick test to verify token tracking is working end-to-end.
Run after restarting the model service.
"""
import requests
import time

GATEWAY = "http://localhost:7000"
API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
HEADERS = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

def test_linux_eval():
    """Test Linux evaluation - simplest evaluator"""
    payload = {
        "question": {
            "id": f"token-test-{int(time.time())}",  # Unique ID to avoid cache
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
        "use_cache": False,  # Disable cache to force LLM call
    }
    
    print("Submitting Linux evaluation...")
    resp = requests.post(
        f"{GATEWAY}/api/v1/evaluation/linux/async",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    job_id = resp.json()["job_id"]
    print(f"✓ Job submitted: {job_id}")
    
    # Poll for completion
    for i in range(300):  # 10 minutes max
        time.sleep(2)
        poll_resp = requests.get(
            f"{GATEWAY}/api/v1/job/{job_id}",
            headers=HEADERS,
            timeout=10,
        )
        poll_resp.raise_for_status()
        data = poll_resp.json()
        
        status = data.get("status", "unknown")
        if i % 5 == 0:  # Print every 10 seconds
            print(f"  [{i*2}s] Status: {status}")
        
        if status == "complete":  # Backend uses "complete" not "completed"
            print(f"✓ Job completed in {i*2}s")
            print(f"  Score: {data['result'].get('overall_score', 0)}/100")
            return job_id
        elif status == "failed":
            print(f"✗ Job failed: {data.get('error')}")
            print(f"  Full response: {data}")
            return None
    
    print("✗ Job timed out after 600s")
    print(f"  Last status: {status}")
    return None

if __name__ == "__main__":
    print("=" * 60)
    print("Token Tracking Test")
    print("=" * 60)
    
    job_id = test_linux_eval()
    
    if job_id:
        print("\n" + "=" * 60)
        print("✓ Test completed successfully!")
        print("=" * 60)
        print("\nNow check the dashboard:")
        print("1. Look for the org in Usage & Billing")
        print("2. Verify 'Total tokens' is > 0")
        print("3. Check that PROMPT and COMPLETION columns show values")
        print(f"\nJob ID for reference: {job_id}")
    else:
        print("\n✗ Test failed")
