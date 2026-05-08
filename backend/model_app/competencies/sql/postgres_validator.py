"""
PostgreSQL Query Validator — Production Ready

Validates generated SQL queries by executing them against PostgreSQL.
This matches the production evaluation engine.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class QueryValidationError(Exception):
    """Raised when query validation fails."""
    pass


def validate_query_postgres(
    query: str,
    schema: Dict[str, Any],
    sample_data: Dict[str, List[Dict]] = None
) -> Tuple[bool, str, List[Dict]]:
    """
    Validate a SQL query by executing it against PostgreSQL.
    
    This uses PostgreSQL syntax which matches production evaluation.
    No more SQLite compatibility issues!
    
    Args:
        query: SQL query to validate
        schema: Schema definition with tables and columns
        sample_data: Optional sample data to insert
    
    Returns:
        Tuple of (is_valid, message, results)
    """
    try:
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        logger.warning("psycopg2 not installed. Falling back to SQLite validation")
        # Fallback to SQLite validation
        from backend.model_app.competencies.sql.query_validator import validate_query
        return validate_query(query, schema, sample_data)
    
    if not query or not query.strip():
        return False, "Query is empty", []
    
    if not schema or "tables" not in schema:
        raise QueryValidationError("Invalid schema: missing 'tables' key")
    
    tables = schema["tables"]
    if not tables:
        raise QueryValidationError("Schema has no tables")
    
    # Use provided sample_data or fall back to schema's sample_data
    if sample_data is None:
        sample_data = schema.get("sample_data", {})
    
    conn = None
    try:
        # Connect to PostgreSQL — URL from settings (loaded from .env)
        import os
        try:
            from backend.model_app.core.settings import get_settings
            db_url = get_settings().validation_db_url
        except Exception:
            db_url = os.getenv("VALIDATION_DB_URL", "postgresql://aaptor:aaptor_validation@localhost:5432/validation_db")
        
        try:
            conn = psycopg2.connect(db_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            # Clean up any stale validation schemas from previous failed runs
            try:
                _cur = conn.cursor()
                _cur.execute(
                    "SELECT schema_name FROM information_schema.schemata "
                    "WHERE schema_name LIKE 'validation_%'"
                )
                stale = [r[0] for r in _cur.fetchall()]
                for s in stale:
                    try:
                        _cur.execute(f"DROP SCHEMA {s} CASCADE")
                    except Exception:
                        pass
                _cur.close()
            except Exception:
                pass
        except Exception as conn_error:
            logger.warning(f"PostgreSQL connection failed: {conn_error}. Falling back to SQLite validation")
            # Fallback to SQLite validation
            from backend.model_app.competencies.sql.query_validator import validate_query
            return validate_query(query, schema, sample_data)
        
        cursor = conn.cursor()
        
        # Create a temporary schema for validation
        import uuid
        temp_schema = f"validation_{uuid.uuid4().hex[:8]}"
        cursor.execute(f"CREATE SCHEMA {temp_schema}")
        
        try:
            # Create tables in temp schema
            for table_name, table_def in tables.items():
                columns = table_def.get("columns", [])
                if not columns:
                    logger.warning(f"Table '{table_name}' has no columns, skipping")
                    continue
                
                # Build CREATE TABLE statement
                col_defs = []
                for col in columns:
                    col_name = col.get("name", "")
                    col_type = col.get("type", "TEXT")
                    constraints = col.get("constraints", "")
                    
                    if not col_name:
                        continue
                    
                    # Normalize MySQL/non-standard types to valid PostgreSQL
                    col_type, constraints = _normalize_pg_type(col_type, constraints)
                    
                    col_def = f'"{col_name}" {col_type}'
                    if constraints:
                        col_def += f" {constraints}"
                    
                    col_defs.append(col_def)
                
                if not col_defs:
                    logger.warning(f"Table '{table_name}' has no valid columns, skipping")
                    continue
                
                create_sql = f'CREATE TABLE {temp_schema}."{table_name}" ({", ".join(col_defs)})'
                
                try:
                    cursor.execute(create_sql)
                    logger.debug(f"Created table: {table_name}")
                except Exception as e:
                    raise QueryValidationError(f"Failed to create table '{table_name}': {e}")
            
            # Insert sample data
            for table_name, rows in sample_data.items():
                if table_name not in tables:
                    logger.warning(f"Sample data for unknown table '{table_name}', skipping")
                    continue
                
                if not rows:
                    logger.debug(f"No sample data for table '{table_name}'")
                    continue
                
                if not isinstance(rows[0], dict):
                    logger.warning(f"Sample data for '{table_name}' is not a list of dicts, skipping")
                    continue
                
                col_names = list(rows[0].keys())
                col_str = ", ".join([f'"{col}"' for col in col_names])
                placeholders = ", ".join(["%s" for _ in col_names])
                
                insert_sql = f'INSERT INTO {temp_schema}."{table_name}" ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

                for row in rows:
                    try:
                        values = [row.get(col) for col in col_names]
                        cursor.execute(insert_sql, values)
                    except Exception as e:
                        logger.debug(f"Skipped row in '{table_name}': {e}")
                        # Continue with other rows
                
                logger.debug(f"Inserted {len(rows)} rows into '{table_name}'")
            
            # Modify query to use temp schema
            modified_query = _add_schema_prefix(query, temp_schema, list(tables.keys()))
            
            # Execute the query
            try:
                cursor.execute(modified_query)
                
                # Fetch results if it's a SELECT query
                if cursor.description:
                    results = cursor.fetchall()
                    col_names = [desc[0] for desc in cursor.description]
                    
                    # Convert to list of dicts
                    results_list = [dict(zip(col_names, row)) for row in results]
                    
                    row_count = len(results_list)
                    col_count = len(col_names)
                    
                    message = f"Query executed successfully. Returned {row_count} rows, {col_count} columns."
                    
                    logger.info(f"Query validation passed: {row_count} rows returned")
                    
                    return True, message, results_list
                else:
                    # DML query (INSERT/UPDATE/DELETE)
                    message = f"Query executed successfully. {cursor.rowcount} rows affected."
                    logger.info(f"Query validation passed: {cursor.rowcount} rows affected")
                    return True, message, []
                
            except Exception as e:
                error_msg = str(e)
                
                # Enhance error message with helpful hints
                if "does not exist" in error_msg.lower():
                    if "column" in error_msg.lower():
                        # Extract table name if possible
                        available_tables = ", ".join(tables.keys())
                        error_msg += f" (Available tables: {available_tables})"
                    elif "relation" in error_msg.lower() or "table" in error_msg.lower():
                        available_tables = ", ".join(tables.keys())
                        error_msg += f" (Available tables: {available_tables})"
                
                logger.warning(f"Query validation failed: {error_msg}")
                
                return False, f"SQL Error: {error_msg}", []
        
        finally:
            # Clean up temp schema
            try:
                cursor.execute(f"DROP SCHEMA {temp_schema} CASCADE")
            except Exception as e:
                logger.warning(f"Failed to drop temp schema: {e}")
    
    except QueryValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during query validation: {e}")
        return False, f"Validation error: {str(e)}", []
    
    finally:
        if conn:
            conn.close()



def _normalize_pg_type(col_type: str, constraints: str = "") -> tuple:
    """
    Normalize MySQL/non-standard SQL types to valid PostgreSQL types.
    Also cleans up MySQL-specific constraints.

    Returns: (normalized_type, normalized_constraints)
    """
    t = col_type.strip()
    c = constraints.strip() if constraints else ""

    # Remove MySQL-specific constraint keywords
    c = c.replace("AUTO_INCREMENT", "").replace("auto_increment", "")
    c = c.replace("UNSIGNED", "").replace("unsigned", "")
    c = c.replace("ZEROFILL", "").replace("zerofill", "")
    c = " ".join(c.split())  # collapse whitespace

    t_upper = t.upper()

    # ENUM and SET → VARCHAR
    if t_upper.startswith("ENUM") or t_upper.startswith("SET"):
        return "VARCHAR(100)", c

    # MySQL integer types → Postgres equivalents
    if t_upper in ("TINYINT", "TINYINT(1)"):
        return "SMALLINT", c
    if t_upper.startswith("TINYINT"):
        return "SMALLINT", c
    if t_upper.startswith("MEDIUMINT"):
        return "INTEGER", c
    if t_upper.startswith("BIGINT"):
        return "BIGINT", c

    # DATETIME → TIMESTAMP
    if t_upper == "DATETIME" or t_upper.startswith("DATETIME"):
        return "TIMESTAMP", c

    # YEAR → SMALLINT
    if t_upper == "YEAR" or t_upper.startswith("YEAR("):
        return "SMALLINT", c

    # TINYTEXT, MEDIUMTEXT, LONGTEXT → TEXT
    if t_upper in ("TINYTEXT", "MEDIUMTEXT", "LONGTEXT"):
        return "TEXT", c

    # TINYBLOB, MEDIUMBLOB, LONGBLOB → BYTEA
    if t_upper in ("TINYBLOB", "MEDIUMBLOB", "LONGBLOB", "BLOB"):
        return "BYTEA", c

    # DOUBLE → DOUBLE PRECISION
    if t_upper == "DOUBLE":
        return "DOUBLE PRECISION", c

    # BIT → BOOLEAN
    if t_upper == "BIT" or t_upper == "BIT(1)":
        return "BOOLEAN", c
    if t_upper.startswith("BIT("):
        return "INTEGER", c

    # Strip UNSIGNED from numeric types
    if "UNSIGNED" in t_upper:
        t = t_upper.replace("UNSIGNED", "").strip()
        t = " ".join(t.split())

    return t, c

def _add_schema_prefix(query: str, schema_name: str, table_names: List[str]) -> str:
    """
    Add schema prefix to table names in query.
    
    Example: SELECT * FROM users -> SELECT * FROM validation_abc123.users
    """
    modified = query
    
    # Sort table names by length (longest first) to avoid partial matches
    sorted_tables = sorted(table_names, key=len, reverse=True)
    
    for table in sorted_tables:
        # Match table name with word boundaries
        # Handle: FROM table, JOIN table, UPDATE table, INSERT INTO table, DELETE FROM table
        patterns = [
            (rf'\bFROM\s+"{table}"', f'FROM {schema_name}."{table}"'),
            (rf'\bFROM\s+{table}\b', f'FROM {schema_name}."{table}"'),
            (rf'\bJOIN\s+"{table}"', f'JOIN {schema_name}."{table}"'),
            (rf'\bJOIN\s+{table}\b', f'JOIN {schema_name}."{table}"'),
            (rf'\bUPDATE\s+"{table}"', f'UPDATE {schema_name}."{table}"'),
            (rf'\bUPDATE\s+{table}\b', f'UPDATE {schema_name}."{table}"'),
            (rf'\bINTO\s+"{table}"', f'INTO {schema_name}."{table}"'),
            (rf'\bINTO\s+{table}\b', f'INTO {schema_name}."{table}"'),
        ]
        
        for pattern, replacement in patterns:
            modified = re.sub(pattern, replacement, modified, flags=re.IGNORECASE)
    
    return modified


def quick_syntax_check(query: str) -> Tuple[bool, str, List]:
    """
    Quick syntax check without executing the query.
    Checks for common issues before full validation.
    
    Args:
        query: SQL query to check
    
    Returns:
        Tuple of (is_valid, message, empty_list)
    """
    if not query or not query.strip():
        return False, "Query is empty", []
    
    query_upper = query.upper().strip()
    
    # Must contain SELECT, INSERT, UPDATE, or DELETE
    if not any(keyword in query_upper for keyword in ["SELECT", "INSERT", "UPDATE", "DELETE"]):
        return False, "Query must contain SELECT, INSERT, UPDATE, or DELETE statement", []
    
    # Check for balanced parentheses
    if query.count("(") != query.count(")"):
        return False, "Unbalanced parentheses", []
    
    # Check for SQL injection patterns (basic)
    dangerous_patterns = [
        r";\s*DROP\s+TABLE",
        r";\s*DROP\s+SCHEMA",
        r";\s*DELETE\s+FROM.*WHERE\s+1\s*=\s*1",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, query_upper):
            return False, f"Query contains potentially dangerous pattern", []
    
    return True, "Syntax check passed", []


def validate_query_with_retry(
    query: str,
    schema: Dict[str, Any],
    sample_data: Dict[str, List[Dict]] = None,
    max_retries: int = 0
) -> Tuple[bool, str, List[Dict], int]:
    """
    Validate query with optional retry logic.
    
    Args:
        query: SQL query to validate
        schema: Schema definition
        sample_data: Optional sample data
        max_retries: Number of retries (0 = no retry, just validate once)
    
    Returns:
        Tuple of (is_valid, message, results, attempts)
    """
    # Quick syntax check first
    syntax_ok, syntax_msg, _ = quick_syntax_check(query)
    if not syntax_ok:
        return False, syntax_msg, [], 0
    
    # Full validation
    for attempt in range(max_retries + 1):
        is_valid, message, results = validate_query_postgres(query, schema, sample_data)
        
        if is_valid:
            return True, message, results, attempt + 1
        
        if attempt < max_retries:
            logger.info(f"Validation attempt {attempt + 1} failed, retrying...")
    
    return False, message, [], max_retries + 1
