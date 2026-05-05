# Schema-Based SQL Question Generation - Changes Summary

## ✅ All Changes Complete

Updated the system to use **local RAG MongoDB (port 27018)** for schema storage.

---

## 📝 Files Modified

### 1. **backend/model_app/db/mongo_client.py**
**Change**: Updated to use local RAG MongoDB instead of cloud MongoDB

**Before:**
```python
_rag_client = AsyncIOMotorClient(get_settings().mongodb_uri)  # Cloud MongoDB
```

**After:**
```python
RAG_MONGODB_URI = os.getenv("RAG_MONGODB_URI", "mongodb://localhost:27018")
_rag_client = AsyncIOMotorClient(RAG_MONGODB_URI)  # Local RAG MongoDB
```

---

### 2. **backend/scripts/import_sql_schemas.py**
**Change**: Updated default MongoDB URI to use port 27018

**Before:**
```python
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
```

**After:**
```python
MONGODB_URI = os.getenv("RAG_MONGODB_URI", "mongodb://localhost:27018")
```

---

### 3. **backend/.env**
**Change**: Added RAG MongoDB configuration

**Added:**
```bash
# --- RAG MongoDB (local, for schema storage and RAG embeddings) ---
# This is the MongoDB instance running in aaptor-rag-service docker-compose
# Port 27018 on host maps to 27017 in container
RAG_MONGODB_URI=mongodb://localhost:27018
```

---

### 4. **backend/.env.example**
**Change**: Added RAG MongoDB documentation

**Added:**
```bash
# --- RAG MongoDB (local, for schema storage and RAG embeddings) ---
# This is the MongoDB instance running in aaptor-rag-service docker-compose
# Port 27018 on host maps to 27017 in container
RAG_MONGODB_URI=mongodb://localhost:27018
```

---

## 🗂️ Files Created (Previously)

### Core Implementation
1. ✅ `backend/model_app/competencies/sql/schema_generator.py` - Question generator
2. ✅ `backend/model_app/db/__init__.py` - DB module init
3. ✅ `backend/model_app/db/mongo_client.py` - MongoDB client
4. ✅ `backend/scripts/import_sql_schemas.py` - Schema import script
5. ✅ `backend/model_app/api/routes/sql.py` - Updated with new endpoint

### Documentation
6. ✅ `.kiro/specs/schema-based-sql-generation/requirements.md`
7. ✅ `.kiro/specs/schema-based-sql-generation/design.md`
8. ✅ `.kiro/specs/schema-based-sql-generation/IMPLEMENTATION_GUIDE.md`
9. ✅ `.kiro/specs/schema-based-sql-generation/SUMMARY.md`

### Testing & Setup
10. ✅ `test_schema_generation.py` - Test script
11. ✅ `SETUP_SCHEMA_GENERATION.md` - Setup guide
12. ✅ `CHANGES_SUMMARY.md` - This file

---

## 🔧 MongoDB Architecture

### Before (Incorrect)
```
Backend → Cloud MongoDB (mongodb+srv://...)
          └─ aaptor_model (billing)
          └─ organization_db (orgs)
          └─ rag_db (❌ doesn't exist here)
```

### After (Correct)
```
Backend → Cloud MongoDB (mongodb+srv://...)
          └─ aaptor_model (billing)
          └─ organization_db (orgs)

Backend → Local RAG MongoDB (localhost:27018)
          └─ rag_db
             └─ sql_schemas (✅ new collection)
             └─ [RAG embeddings from aaptor-rag-service]
```

---

## 🎯 Why This Change?

### ✅ Benefits of Using Local RAG MongoDB

1. **Logical Grouping**: Schemas stored alongside RAG embeddings
2. **Performance**: Local access is faster than cloud
3. **Cost**: No cloud storage costs
4. **Consistency**: Same database as RAG service uses
5. **Simplicity**: One MongoDB for all RAG-related data

### 📊 MongoDB Usage

| Database | MongoDB Instance | Purpose |
|----------|-----------------|---------|
| `aaptor_model` | Cloud (Atlas) | Billing, usage logs, API keys |
| `organization_db` | Cloud (Atlas) | Organization data |
| `rag_db` | Local (port 27018) | RAG embeddings + SQL schemas |

---

## 🚀 Next Steps to Deploy

### 1. Start RAG MongoDB
```bash
cd aaptor-rag-service
docker-compose up -d mongo
```

### 2. Import Schemas
```bash
cd /root/gisul_model/backend
python scripts/import_sql_schemas.py
```

### 3. Restart Backend
```bash
cd /root/gisul_model
docker-compose restart backend-api
```

### 4. Test
```bash
python test_schema_generation.py
```

---

## 📋 Verification Checklist

- [ ] RAG MongoDB container is running (`docker ps | grep rag-mongo`)
- [ ] Port 27018 is accessible (`docker exec rag-mongo mongosh --eval "db.adminCommand('ping')"`)
- [ ] Schemas imported successfully (`python backend/scripts/import_sql_schemas.py`)
- [ ] Backend can connect to MongoDB (check logs)
- [ ] Endpoint returns questions (`curl http://localhost:7000/api/v1/generate-sql-question-from-schema ...`)
- [ ] Token tracking works (check `usage_logs` collection)
- [ ] Questions are unique (run test script)

---

## 🐛 Common Issues

### Issue: Connection refused to localhost:27018
**Solution**: Start RAG MongoDB container
```bash
cd aaptor-rag-service && docker-compose up -d mongo
```

### Issue: Backend in Docker can't reach localhost:27018
**Solution**: Use container network name instead
```yaml
# In docker-compose.yml
environment:
  - RAG_MONGODB_URI=mongodb://rag-mongo:27017
```

### Issue: No schemas found
**Solution**: Run import script
```bash
cd backend && python scripts/import_sql_schemas.py
```

---

## ✅ Summary

**All changes complete!** The system now uses:
- ✅ Local RAG MongoDB (port 27018) for schema storage
- ✅ Cloud MongoDB for billing and organizations
- ✅ Environment variable `RAG_MONGODB_URI` for configuration
- ✅ Same database as aaptor-rag-service

**Ready to deploy!** Follow the setup instructions in `SETUP_SCHEMA_GENERATION.md`
