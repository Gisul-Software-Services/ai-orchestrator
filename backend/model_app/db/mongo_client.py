"""
MongoDB client for RAG database access
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_rag_client: AsyncIOMotorClient | None = None
RAG_DB_NAME = "rag_db"
# Use local RAG MongoDB (same as aaptor-rag-service)
RAG_MONGODB_URI = os.getenv("RAG_MONGODB_URI", "mongodb://localhost:27018")


def get_rag_client() -> AsyncIOMotorClient:
    """Get MongoDB client for RAG database"""
    global _rag_client
    if _rag_client is None:
        _rag_client = AsyncIOMotorClient(RAG_MONGODB_URI)
    return _rag_client


async def get_rag_db() -> AsyncIOMotorDatabase:
    """Get RAG database instance"""
    client = get_rag_client()
    return client[RAG_DB_NAME]


async def ensure_schema_indexes() -> None:
    """Create indexes for sql_schemas collection"""
    db = await get_rag_db()
    collection = db["sql_schemas"]
    
    await collection.create_index("schema_id", unique=True)
    await collection.create_index([("domain", 1), ("difficulty_levels", 1), ("sql_categories", 1)])
    await collection.create_index([("usage_count", 1), ("last_used_at", 1)])
