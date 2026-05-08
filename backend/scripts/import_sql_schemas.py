"""
Import SQL schemas from sql_dataset_clean_v2.json to MongoDB via RAG service API

This script extracts unique database schemas from the existing SQL dataset
and sends them to the RAG service for import into MongoDB.
"""
import asyncio
import json
import hashlib
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RAG Service URL (uses port 7003 which is accessible)
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://103.173.99.217:7003")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def generate_schema_signature(schemas: dict) -> str:
    """
    Generate unique signature for a schema based on table structure
    """
    # Sort tables and columns for consistent hashing
    tables_sig = []
    for table_name in sorted(schemas.keys()):
        table = schemas[table_name]
        columns = table.get("columns", [])
        col_sig = "_".join(sorted([f"{c['name']}:{c['type']}" for c in columns]))
        tables_sig.append(f"{table_name}:{col_sig}")
    
    signature = "|".join(tables_sig)
    return hashlib.md5(signature.encode()).hexdigest()[:12]


def detect_relationships(schemas: dict) -> List[Dict[str, Any]]:
    """
    Detect foreign key relationships between tables
    """
    relationships = []
    
    for table_name, table_def in schemas.items():
        columns = table_def.get("columns", [])
        
        for col in columns:
            col_name = col.get("name", "")
            
            # Heuristic: column ending with _id likely references another table
            if col_name.endswith("_id"):
                # Try to find referenced table
                potential_table = col_name[:-3]  # Remove _id suffix
                
                # Check if table exists (exact match or plural form)
                for other_table in schemas.keys():
                    if other_table == potential_table or other_table == potential_table + "s":
                        relationships.append({
                            "from_table": table_name,
                            "from_column": col_name,
                            "to_table": other_table,
                            "to_column": "id",
                            "relationship_type": "many-to-one"
                        })
                        break
    
    return relationships


def calculate_metadata(schemas: dict) -> Dict[str, Any]:
    """
    Calculate schema metadata for selection and filtering
    """
    table_count = len(schemas)
    total_columns = sum(len(t.get("columns", [])) for t in schemas.values())
    
    numeric_columns = []
    categorical_columns = []
    date_columns = []
    
    for table_name, table_def in schemas.items():
        for col in table_def.get("columns", []):
            col_name = f"{table_name}.{col['name']}"
            col_type = col.get("type", "").upper()
            
            if any(t in col_type for t in ["INT", "FLOAT", "DECIMAL", "NUMERIC", "DOUBLE"]):
                numeric_columns.append(col_name)
            elif any(t in col_type for t in ["DATE", "TIME", "TIMESTAMP"]):
                date_columns.append(col_name)
            elif any(t in col_type for t in ["VARCHAR", "TEXT", "CHAR"]):
                categorical_columns.append(col_name)
    
    # Calculate complexity score
    complexity_score = (
        table_count * 1.0 +
        total_columns * 0.1 +
        len(numeric_columns) * 0.2 +
        len(date_columns) * 0.3
    )
    
    return {
        "table_count": table_count,
        "total_columns": total_columns,
        "has_foreign_keys": any("_id" in col["name"] for t in schemas.values() for col in t.get("columns", [])),
        "has_numeric_columns": len(numeric_columns) > 0,
        "has_date_columns": len(date_columns) > 0,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "date_columns": date_columns,
        "complexity_score": round(complexity_score, 2)
    }


def infer_schema_name(question: dict) -> str:
    """
    Infer a descriptive name for the schema from the question
    """
    domain = question.get("domain", "general")
    tables = list(question.get("schemas", {}).keys())
    
    if len(tables) <= 2:
        table_names = " and ".join(tables)
        return f"{domain.title()} - {table_names}"
    else:
        return f"{domain.title()} Database ({len(tables)} tables)"


def extract_difficulties(questions: List[dict]) -> List[str]:
    """
    Extract unique difficulty levels from questions using this schema
    """
    difficulties = set()
    for q in questions:
        diff = q.get("difficulty", "medium").lower()
        difficulties.add(diff)
    return sorted(list(difficulties))


def extract_categories(questions: List[dict]) -> List[str]:
    """
    Extract unique SQL categories from questions using this schema
    """
    categories = set()
    for q in questions:
        cat = q.get("sql_category", "select")
        categories.add(cat)
    return sorted(list(categories))


def group_by_schema(dataset: List[dict]) -> Dict[str, List[dict]]:
    """
    Group questions by their schema signature
    """
    schema_groups = defaultdict(list)
    
    for question in dataset:
        schemas = question.get("schemas", {})
        if not schemas:
            continue
        
        signature = generate_schema_signature(schemas)
        schema_groups[signature].append(question)
    
    return schema_groups


def import_schemas():
    """
    Main import function - sends schemas to RAG service API
    """
    print("=" * 70)
    print("SQL Schema Import Tool (via RAG Service API)")
    print("=" * 70)
    
    # Check RAG service
    print(f"\n1. Checking RAG service...")
    print(f"   URL: {RAG_SERVICE_URL}")
    
    try:
        response = requests.get(f"{RAG_SERVICE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("   ✓ RAG service is accessible")
        else:
            print(f"   ✗ RAG service returned status {response.status_code}")
            return
    except Exception as e:
        print(f"   ✗ Cannot reach RAG service: {e}")
        print(f"   Make sure RAG service is running at {RAG_SERVICE_URL}")
        return
    
    # Load dataset
    print(f"\n2. Loading SQL dataset...")
    dataset_path = Path(__file__).parent.parent.parent / "dataset_creation" / "sql_dataset_clean_v2.json"
    
    if not dataset_path.exists():
        print(f"   ✗ Dataset not found: {dataset_path}")
        return
    
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
    
    print(f"   ✓ Loaded {len(dataset)} questions")
    
    # Group by schema
    print(f"\n3. Grouping questions by schema...")
    schema_groups = group_by_schema(dataset)
    print(f"   ✓ Found {len(schema_groups)} unique schemas")
    
    # Build schema documents
    print(f"\n4. Building schema documents...")
    schemas_list = []
    
    for schema_sig, questions in schema_groups.items():
        # Use first question as representative
        representative = questions[0]
        
        schema_id = f"schema_{representative.get('domain', 'general').replace(' ', '_')}_{schema_sig}"
        
        schema_doc = {
            "schema_id": schema_id,
            "name": infer_schema_name(representative),
            "domain": representative.get("domain", "general"),
            "difficulty_levels": extract_difficulties(questions),
            "sql_categories": extract_categories(questions),
            "tables": representative.get("schemas", {}),
            "sample_data": representative.get("sample_data", {}),
            "relationships": detect_relationships(representative.get("schemas", {})),
            "metadata": calculate_metadata(representative.get("schemas", {})),
            "usage_count": 0,
            "last_used_at": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "source": "sql_dataset_clean_v2.json",
            "question_count": len(questions)  # How many questions use this schema
        }
        
        schemas_list.append(schema_doc)
    
    print(f"   ✓ Built {len(schemas_list)} schema documents")
    
    # Send to RAG service
    print(f"\n5. Sending schemas to RAG service...")
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        if ADMIN_API_KEY:
            headers["X-Admin-Api-Key"] = ADMIN_API_KEY
        
        response = requests.post(
            f"{RAG_SERVICE_URL}/api/v1/import-sql-schemas",
            headers=headers,
            json={"schemas": schemas_list},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Imported: {result['imported']} new schemas")
            print(f"   ✓ Updated: {result['updated']} existing schemas")
            print(f"   ✓ Total: {result['total']} schemas processed")
            if not result['success']:
                print(f"   ⚠ Warning: {result['message']}")
        else:
            print(f"   ✗ Import failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return
            
    except Exception as e:
        print(f"   ✗ Failed to send schemas: {e}")
        return
    
    # Get statistics
    print(f"\n6. Schema Statistics:")
    
    try:
        response = requests.get(f"{RAG_SERVICE_URL}/api/v1/sql-schemas/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            
            print(f"\n   Total Schemas: {stats['total_schemas']}")
            
            print(f"\n   Schemas by Domain:")
            for stat in stats['by_domain']:
                print(f"   - {stat['_id']}: {stat['count']}")
            
            print(f"\n   Schemas by Difficulty:")
            for stat in stats['by_difficulty']:
                print(f"   - {stat['_id']}: {stat['count']}")
            
            print(f"\n   Schemas by SQL Category:")
            for stat in stats['by_category']:
                print(f"   - {stat['_id']}: {stat['count']}")
    except Exception as e:
        print(f"   ⚠ Could not fetch statistics: {e}")
    
    print(f"\n" + "=" * 70)
    print(f"✓ Import completed successfully!")
    print(f"=" * 70)


if __name__ == "__main__":
    import_schemas()
