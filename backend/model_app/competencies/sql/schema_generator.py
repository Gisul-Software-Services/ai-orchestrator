"""
Schema-Based SQL Question Generator

Generates SQL questions dynamically from database schemas stored in MongoDB.
"""
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import HTTPException

from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single
from backend.model_app.db.mongo_client import get_rag_db

logger = logging.getLogger(__name__)

# LLM Configuration
LLM_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.1,
    "max_tokens": 800,
}

# Prompt template
SCHEMA_QUESTION_GENERATION_PROMPT = """You are an expert SQL instructor creating practice questions.

## Database Schema

Domain: {domain}

Tables and Columns:
{schema_details}

Relationships:
{relationships}

Sample Data Preview:
{sample_data_preview}

## Task

Generate a {difficulty} difficulty SQL question that requires {sql_category}.

## Requirements

1. **Business Context**: Create a realistic business scenario related to {domain}
2. **Question Title**: Clear, concise (10-80 characters)
3. **Description**: Detailed explanation (100-250 words) including:
   - Business context and why this query is needed
   - What data should be retrieved
   - Expected output format
4. **Reference Query**: Valid PostgreSQL SQL using EXACT table and column names from schema above
5. **Hints**: 3 progressive hints that guide without revealing the solution
6. **Constraints**: 2-3 specific requirements (sorting, filtering, null handling, etc.)

## Difficulty Guidelines

- **easy**: Single table or simple join, basic aggregation (COUNT, SUM, AVG)
- **medium**: Multiple joins, GROUP BY with HAVING, subqueries, DISTINCT
- **hard**: Complex joins, window functions, nested subqueries, CTEs, advanced aggregations

## Output Format (JSON)

{{
  "title": "...",
  "description": "...",
  "reference_query": "SELECT ...",
  "hints": ["hint1", "hint2", "hint3"],
  "constraints": ["constraint1", "constraint2", "constraint3"]
}}

## Critical Rules

- Use ONLY tables and columns from the schema above
- Reference query MUST be valid PostgreSQL syntax
- Do NOT invent new tables or columns
- Ensure query matches the {difficulty} difficulty level
- Focus on {sql_category} as the primary SQL concept
- Query must return meaningful results with the sample data provided
"""


async def select_schema(
    difficulty: str,
    sql_category: str,
    domain: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Select an appropriate schema from MongoDB based on criteria.
    Prioritizes least recently used schemas.
    """
    db = await get_rag_db()
    collection = db["sql_schemas"]
    
    # Build query
    query = {
        "difficulty_levels": difficulty.lower(),
        "sql_categories": sql_category
    }
    
    if domain:
        query["domain"] = domain
    
    # Get schemas, prioritize least recently used
    cursor = collection.find(query).sort("usage_count", 1).limit(10)
    schemas = await cursor.to_list(length=10)
    
    if not schemas:
        logger.warning(f"No schema found for difficulty={difficulty}, category={sql_category}, domain={domain}")
        return None
    
    # Random selection from top 10 least used
    selected = random.choice(schemas)
    logger.info(f"Selected schema: {selected['schema_id']} (used {selected['usage_count']} times)")
    
    return selected


def build_schema_details(tables: Dict[str, Any]) -> str:
    """
    Format schema details for LLM prompt
    """
    lines = []
    for table_name, table_def in tables.items():
        columns = table_def.get("columns", [])
        lines.append(f"\nTable: {table_name}")
        for col in columns:
            col_name = col.get("name", "")
            col_type = col.get("type", "")
            constraints = col.get("constraints", "")
            line = f"  - {col_name} ({col_type})"
            if constraints:
                line += f" {constraints}"
            lines.append(line)
    
    return "\n".join(lines)


def build_relationships_text(relationships: List[Dict[str, Any]]) -> str:
    """
    Format relationships for LLM prompt
    """
    if not relationships:
        return "No explicit foreign key relationships defined."
    
    lines = []
    for rel in relationships:
        from_ref = f"{rel['from_table']}.{rel['from_column']}"
        to_ref = f"{rel['to_table']}.{rel['to_column']}"
        lines.append(f"- {from_ref} → {to_ref} ({rel['relationship_type']})")
    
    return "\n".join(lines)


def build_sample_data_preview(sample_data: Dict[str, List[Dict]]) -> str:
    """
    Format sample data preview for LLM prompt (first 3 rows per table)
    """
    lines = []
    for table_name, rows in sample_data.items():
        lines.append(f"\n{table_name}:")
        preview_rows = rows[:3]  # First 3 rows only
        if preview_rows:
            # Show first row as example
            first_row = preview_rows[0]
            lines.append(f"  Example row: {first_row}")
            lines.append(f"  Total rows: {len(rows)}")
        else:
            lines.append("  (empty)")
    
    return "\n".join(lines)


def build_generation_prompt(
    schema: Dict[str, Any],
    difficulty: str,
    sql_category: str
) -> str:
    """
    Build complete LLM prompt for question generation
    """
    schema_details = build_schema_details(schema["tables"])
    relationships = build_relationships_text(schema.get("relationships", []))
    sample_data_preview = build_sample_data_preview(schema.get("sample_data", {}))
    
    return SCHEMA_QUESTION_GENERATION_PROMPT.format(
        domain=schema["domain"],
        schema_details=schema_details,
        relationships=relationships,
        sample_data_preview=sample_data_preview,
        difficulty=difficulty.lower(),
        sql_category=sql_category
    )


async def call_llm_with_retry(prompt: str, max_retries: int = 3) -> tuple[str, Dict[str, int]]:
    """
    Call LLM with retry logic
    """
    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": "You are an expert SQL instructor. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ]
            
            decoded, prompt_tokens, completion_tokens = _llm_chat_single(
                messages,
                temperature=LLM_CONFIG["temperature"],
                top_p=LLM_CONFIG["top_p"],
                repetition_penalty=LLM_CONFIG["repetition_penalty"],
                max_tokens=LLM_CONFIG["max_tokens"],
            )
            
            tokens = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
            
            return decoded, tokens
            
        except Exception as e:
            logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
    
    raise Exception("LLM call failed after retries")


def parse_llm_response(response: str) -> Dict[str, Any]:
    """
    Parse LLM JSON response
    """
    try:
        return extract_json(response)
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        logger.error(f"Response: {response[:500]}")
        raise HTTPException(500, f"Failed to parse LLM response: {str(e)}")


async def validate_generated_query(query: str, schema: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate generated SQL query
    
    TODO: Implement full validation:
    - SQL syntax check
    - Table/column existence check
    - Execute against sample data
    """
    # Basic validation: check if query is not empty
    if not query or len(query.strip()) < 10:
        return False, "Query is too short or empty"
    
    # Check if query contains SELECT
    if "SELECT" not in query.upper():
        return False, "Query must contain SELECT statement"
    
    # Check if tables from schema are referenced
    tables = list(schema["tables"].keys())
    query_upper = query.upper()
    
    # At least one table should be referenced
    if not any(table.upper() in query_upper for table in tables):
        return False, f"Query must reference at least one table from: {tables}"
    
    # TODO: Add more sophisticated validation
    # - Parse SQL with sqlparse
    # - Verify all columns exist
    # - Execute against sample_data
    
    return True, ""


def build_question_response(
    schema: Dict[str, Any],
    generated: Dict[str, Any],
    tokens: Dict[str, int]
) -> Dict[str, Any]:
    """
    Build final question response in Aaptor format
    """
    return {
        "title": generated.get("title", "SQL Query Challenge"),
        "description": generated.get("description", ""),
        "difficulty": schema["difficulty_levels"][0] if schema["difficulty_levels"] else "medium",
        "question_type": "SQL",
        "sql_category": schema["sql_categories"][0] if schema["sql_categories"] else "select",
        "schemas": schema["tables"],
        "sample_data": schema.get("sample_data", {}),
        "starter_query": "-- Write your SQL query here\n\nSELECT ",
        "reference_query": generated.get("reference_query", ""),
        "sql_expected_output": "",  # Will be computed by evaluation engine
        "hints": generated.get("hints", []),
        "evaluation": {
            "engine": "postgres",
            "comparison": "result_set",
            "order_sensitive": False,
        },
        "constraints": generated.get("constraints", []),
        "ai_generated": True,
        "model": "qwen",
        "schema_id": schema["schema_id"],
        "token_usage": tokens
    }


async def update_schema_usage(schema_id: str):
    """
    Update schema usage tracking
    """
    db = await get_rag_db()
    collection = db["sql_schemas"]
    
    await collection.update_one(
        {"schema_id": schema_id},
        {
            "$inc": {"usage_count": 1},
            "$set": {"last_used_at": datetime.utcnow()}
        }
    )


async def generate_question_from_schema(
    difficulty: str,
    sql_category: str,
    domain: Optional[str] = None,
    http_request=None
) -> Dict[str, Any]:
    """
    Main function to generate SQL question from schema
    
    Args:
        difficulty: Easy, Medium, or Hard
        sql_category: join, aggregation, window, subquery, select, etc.
        domain: Optional domain filter (e-commerce, healthcare, etc.)
        http_request: FastAPI request object for token tracking
    
    Returns:
        Complete question dict in Aaptor format
    """
    # 1. Select appropriate schema
    schema = await select_schema(difficulty, sql_category, domain)
    
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"No schema found for difficulty='{difficulty}', category='{sql_category}', domain='{domain}'"
        )
    
    # 2. Build LLM prompt
    prompt = build_generation_prompt(schema, difficulty, sql_category)
    
    # 3. Call LLM
    try:
        response, tokens = await call_llm_with_retry(prompt, max_retries=3)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(500, f"Question generation failed: {str(e)}")
    
    # 4. Parse response
    generated = parse_llm_response(response)
    
    # 5. Validate query
    is_valid, error = await validate_generated_query(
        generated.get("reference_query", ""),
        schema
    )
    
    if not is_valid:
        logger.warning(f"Generated query validation failed: {error}")
        # For now, log and continue - TODO: implement retry logic
        # raise HTTPException(500, f"Generated query validation failed: {error}")
    
    # 6. Build final response
    question = build_question_response(schema, generated, tokens)
    
    # 7. Update usage tracking
    await update_schema_usage(schema["schema_id"])
    
    logger.info(f"Successfully generated question from schema {schema['schema_id']}")
    
    return question


async def generate_sql_questions_from_schema_bulk(
    difficulty: str,
    sql_category: str,
    domain: Optional[str],
    count: int = 1,
    http_request=None
):
    """
    Generator that yields multiple SQL questions from different schemas
    """
    for i in range(count):
        try:
            question = await generate_question_from_schema(
                difficulty=difficulty,
                sql_category=sql_category,
                domain=domain,
                http_request=http_request
            )
            question["question_index"] = i + 1
            question["total"] = count
            yield question
        except Exception as e:
            logger.error(f"Failed to generate question {i+1}/{count}: {e}")
            # Continue with next question
            continue
