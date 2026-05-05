"""Check the status of a specific job"""
import requests
import sys

GATEWAY = "http://localhost:7000"
API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
HEADERS = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

job_id = "8412d9e7-f087-47ad-942c-e75ccce76fde"
if len(sys.argv) > 1:
    job_id = sys.argv[1]

print(f"Checking job: {job_id}")
resp = requests.get(
    f"{GATEWAY}/api/v1/job/{job_id}",
    headers=HEADERS,
    timeout=10,
)
resp.raise_for_status()
data = resp.json()

import json
print(json.dumps(data, indent=2))
