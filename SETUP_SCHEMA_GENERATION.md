# Schema-Based SQL Question Generation - Setup Guide

## ✅ Changes Made

Updated the system to use **local RAG MongoDB** (port 27018) instead of cloud MongoDB.

### Files Updated:
1. ✅ `backend/model_app/db/mongo_client.py` - Uses `mongodb://localhost:27018`
2. ✅ `backend/scripts/import_sql_schemas.py` - Uses `mongodb://localhost:27018`
3. ✅ `backend/.env` - Added `RAG_MONGODB_URI=mongodb://localhost:27018`
4. ✅ `backend/.env.example` - Added RAG MongoDB documentation

---

## 🚀 Setup Instructions

### Step 1: Start RAG MongoDB Container

The RAG service has its own MongoDB instance. Start it:

```bash
cd aaptor-rag-service
docker-compose up -d mongo
```

**Verify it's running:**
```bash
docker ps | grep rag-mongo
```

**Expected output:**
```
rag-mongo   mongo:7.0   Up X minutes   0.0.0.0:27018->27017/tcp
```

### Step 2: Test MongoDB Connection

```bash
# Test connection from host
docker exec rag-mongo mongosh --eval "db.adminCommand('ping')"
```

**Expected output:**
```
{ ok: 1 }
```

### Step 3: Import SQL Schemas

```bash
cd /root/gisul_model/backend
python scripts/import_sql_schemas.py
```

**Expected output:**
```
======================================================================
SQL Schema Import Tool
======================================================================

1. Connecting to MongoDB...
   URI: mongodb://localhost:27018...
   Database: rag_db
   ✓ Connected successfully

2. Loading SQL dataset...
   ✓ Loaded 1000+ questions

3. Grouping questions by schema...
   ✓ Found 50-100 unique schemas

4. Importing schemas to MongoDB...
   [50/50] schema_rural_health_abc123...
   ✓ Imported: 50 new schemas
   ✓ Updated: 0 existing schemas

5. Creating indexes...
   ✓ Indexes created

6. Schema Statistics:
   Schemas by Domain:
   - rural health: 15
   - e-commerce: 12
   - finance: 10
   ...
```

### Step 4: Verify Schemas in MongoDB

```bash
# Connect to MongoDB
docker exec -it rag-mongo mongosh rag_db

# In mongosh:
db.sql_schemas.countDocuments()
db.sql_schemas.findOne()
```

### Step 5: Restart Backend Service

The backend needs to be restarted to pick up the new code:

```bash
# If running in Docker
cd /root/gisul_model
docker-compose restart backend-api

# Or if running directly
cd /root/gisul_model/backend
# Kill and restart your uvicorn process
```

### Step 6: Test the Endpoint

```bash
curl -X POST "http://localhost:7000/api/v1/generate-sql-question-from-schema" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg" \
  -d '{
    "difficulty": "Medium",
    "topic": "joins",
    "sql_category": "join",
    "count": 1
  }'
```

**Expected response:**
```json
{
  "title": "Customer Order Analysis",
  "description": "...",
  "difficulty": "medium",
  "sql_category": "join",
  "schemas": {...},
  "sample_data": {...},
  "reference_query": "SELECT ...",
  "hints": [...],
  "ai_generated": true,
  "schema_id": "schema_ecommerce_abc123",
  "token_usage": {
    "prompt_tokens": 450,
    "completion_tokens": 200,
    "total_tokens": 650
  }
}
```

---

## 🔧 MongoDB Configuration

### RAG MongoDB (Local)
- **Container**: `rag-mongo`
- **Image**: `mongo:7.0`
- **Host Port**: `27018`
- **Container Port**: `27017`
- **Database**: `rag_db`
- **Collection**: `sql_schemas`
- **URI from host**: `mongodb://localhost:27018`
- **URI from container**: `mongodb://mongo:27017`

### Billing MongoDB (Cloud)
- **URI**: `mongodb+srv://...@cluster0.dwcfp0l.mongodb.net/`
- **Database**: `aaptor_model`
- **Used for**: Billing, API keys, usage logs

---

## 🐛 Troubleshooting

### Issue: "Connection refused" when importing schemas

**Cause**: RAG MongoDB container is not running

**Solution**:
```bash
cd aaptor-rag-service
docker-compose up -d mongo
docker ps | grep rag-mongo
```

### Issue: "No schemas found" when generating questions

**Cause**: Schemas not imported yet

**Solution**:
```bash
cd /root/gisul_model/backend
python scripts/import_sql_schemas.py
```

### Issue: Backend can't connect to MongoDB

**Cause**: Backend is running in Docker and trying to connect to `localhost:27018`

**Solution**: Update backend docker-compose to use network connection:
```yaml
environment:
  - RAG_MONGODB_URI=mongodb://rag-mongo:27017
```

Or run backend outside Docker for development.

### Issue: Port 27018 already in use

**Cause**: Another service is using port 27018

**Solution**:
```bash
# Check what's using the port
lsof -i :27018

# Or change the port in aaptor-rag-service/docker-compose.yml
ports:
  - "27019:27017"  # Use 27019 instead

# Then update RAG_MONGODB_URI in backend/.env
RAG_MONGODB_URI=mongodb://localhost:27019
```

---

## 📊 Verify Everything Works

Run the test script:

```bash
cd /root/gisul_model
python test_schema_generation.py
```

**Expected output:**
```
======================================================================
Schema-Based SQL Question Generation Test
======================================================================

1. Testing: Easy Select Query
   Difficulty: Easy
   Category: select
   ✓ Success!
   Title: Find All Active Users...
   Schema ID: schema_ecommerce_abc123
   Tokens: 650

2. Testing: Medium Join Query
   Difficulty: Medium
   Category: join
   ✓ Success!
   ...

======================================================================
Test Summary
======================================================================

Total Tests: 4
✓ Passed: 4
✗ Failed: 0
⚠ Errors: 0

🎉 All tests passed!

Uniqueness Check:
  Unique titles: 4/4
  Unique schemas: 3/4
  ✓ All questions are unique!
```

---

## 📈 Next Steps

Once everything is working:

1. ✅ Verify schemas are imported
2. ✅ Test question generation
3. ✅ Check token tracking in usage_logs
4. ✅ Monitor question quality
5. 🔄 Add more schemas (target: 200+)
6. 🔄 Implement full SQL validation
7. 🔄 A/B test with RAG approach

---

## 🎉 Summary

The system is now configured to:
- ✅ Use local RAG MongoDB (port 27018)
- ✅ Store schemas in `rag_db.sql_schemas` collection
- ✅ Generate unique SQL questions dynamically
- ✅ Track token usage for billing
- ✅ Maintain backward compatibility with RAG endpoint

**Ready to start!** Follow the setup instructions above.
