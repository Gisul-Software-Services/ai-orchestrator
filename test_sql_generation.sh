#!/bin/bash
# Test SQL question generation endpoint

GATEWAY="http://localhost:7000"
API_KEY="adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"

echo "Testing SQL Question Generation..."
echo "=================================="

curl -X POST "${GATEWAY}/api/v1/generate-sql-question" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: ${API_KEY}" \
  -d '{
    "difficulty": "Medium",
    "topic": "joins",
    "count": 1
  }' | jq '.'

echo ""
echo "=================================="
echo "Test complete!"
