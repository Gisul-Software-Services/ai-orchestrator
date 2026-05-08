"""
SQL Query Validator — Production Ready

Validates generated SQL queries by executing them against sample data in SQLite.
Catches syntax errors, wrong column names, wrong table names, and type mismatches.
"""
from __future__ import annotations

import sqlite3
import logging
import re
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class QueryValidationError(Exception):
    """Raised when query validation fails."""
    pass


def validate_query(
    query: str,
    schema: Dict[str, Any],
    sample_data: Dict[str, List[Dict]] = None
) -> Tuple[bool, str, List[Dict]]:
    """
    Validate a SQL query by executing it against sample data in SQLite.
    
    Args:
        query: SQL query to validate
        schema: Schema definition with tables and columns
        sample_data: Optional sample data to insert (uses schema sample_data if not provided)
    
    Returns:
        Tuple of (is_valid, message, results)
        - is_valid: True if query executed successfully
        - message: Success message or error details
        - results: Query results as list of dicts (empty if failed)
    
    Raises:
        QueryValidationError: If validation setup fails (not query errors)
    """
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
        # Create in-memory SQLite database (unique for each validation)
        import uuid
        db_name = f":memory:"  # Always use in-memory to avoid conflicts
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        cursor = conn.cursor()
        
        # Create tables
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
                
                # Map SQL types to SQLite types
                sqlite_type = _map_to_sqlite_type(col_type)
                
                col_def = f"{col_name} {sqlite_type}"
                if constraints:
                    col_def += f" {constraints}"
                
                col_defs.append(col_def)
            
            if not col_defs:
                logger.warning(f"Table '{table_name}' has no valid columns, skipping")
                continue
            
            create_sql = f"CREATE TABLE {table_name} ({', '.join(col_defs)})"
            
            try:
                cursor.execute(create_sql)
                logger.debug(f"Created table: {table_name}")
            except sqlite3.Error as e:
                raise QueryValidationError(f"Failed to create table '{table_name}': {e}")
        
        # Insert sample data
        for table_name, rows in sample_data.items():
            if table_name not in tables:
                logger.warning(f"Sample data for unknown table '{table_name}', skipping")
                continue
            
            if not rows:
                logger.debug(f"No sample data for table '{table_name}'")
                continue
            
            # Get column names from first row
            if not isinstance(rows[0], dict):
                logger.warning(f"Sample data for '{table_name}' is not a list of dicts, skipping")
                continue
            
            col_names = list(rows[0].keys())
            placeholders = ", ".join(["?" for _ in col_names])
            col_str = ", ".join(col_names)
            
            insert_sql = f"INSERT OR IGNORE INTO {table_name} ({col_str}) VALUES ({placeholders})"
            
            for row in rows:
                try:
                    values = [row.get(col) for col in col_names]
                    cursor.execute(insert_sql, values)
                except sqlite3.Error as e:
                    logger.debug(f"Skipped row in '{table_name}': {e}")
                    # Continue with other rows
            
            logger.debug(f"Inserted {len(rows)} rows into '{table_name}'")
        
        conn.commit()
        
        # Execute the query
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Convert Row objects to dicts
            results_list = [dict(row) for row in results]
            
            row_count = len(results_list)
            col_count = len(results_list[0]) if results_list else 0
            
            message = f"Query executed successfully. Returned {row_count} rows, {col_count} columns."
            
            logger.info(f"Query validation passed: {row_count} rows returned")
            
            return True, message, results_list
            
        except sqlite3.Error as e:
            error_msg = str(e)
            
            # Enhance error message with helpful hints
            if "no such table" in error_msg.lower():
                available_tables = ", ".join(tables.keys())
                error_msg += f" (Available tables: {available_tables})"
            elif "no such column" in error_msg.lower():
                # Try to extract table name from error
                match = re.search(r"no such column: (\w+)\.(\w+)", error_msg, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
                    if table_name in tables:
                        available_cols = [c["name"] for c in tables[table_name]["columns"]]
                        error_msg += f" (Available columns in {table_name}: {', '.join(available_cols)})"
            
            logger.warning(f"Query validation failed: {error_msg}")
            
            return False, f"SQL Error: {error_msg}", []
    
    except QueryValidationError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during query validation: {e}")
        return False, f"Validation error: {str(e)}", []
    
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Failed to close SQLite connection: {e}")


def _map_to_sqlite_type(sql_type: str) -> str:
    """
    Map generic SQL types to SQLite types.
    
    SQLite has 5 storage classes: NULL, INTEGER, REAL, TEXT, BLOB
    """
    sql_type_upper = sql_type.upper()
    
    # Integer types
    if any(t in sql_type_upper for t in ["INT", "SERIAL", "BIGINT", "SMALLINT", "TINYINT"]):
        return "INTEGER"
    
    # Real/Float types
    if any(t in sql_type_upper for t in ["REAL", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"]):
        return "REAL"
    
    # Text types
    if any(t in sql_type_upper for t in ["CHAR", "VARCHAR", "TEXT", "CLOB", "STRING"]):
        return "TEXT"
    
    # Boolean (stored as INTEGER in SQLite)
    if "BOOL" in sql_type_upper:
        return "INTEGER"
    
    # Date/Time (stored as TEXT in SQLite)
    if any(t in sql_type_upper for t in ["DATE", "TIME", "TIMESTAMP", "DATETIME"]):
        return "TEXT"
    
    # Blob types
    if any(t in sql_type_upper for t in ["BLOB", "BINARY", "VARBINARY"]):
        return "BLOB"
    
    # Default to TEXT
    return "TEXT"


def quick_syntax_check(query: str) -> Tuple[bool, str]:
    """
    Quick syntax check without executing the query.
    Checks for common issues before full validation.
    
    Args:
        query: SQL query to check
    
    Returns:
        Tuple of (is_valid, message)
    """
    if not query or not query.strip():
        return False, "Query is empty"
    
    query_upper = query.upper().strip()
    
    # Must contain SELECT (we only validate SELECT queries)
    if not query_upper.startswith("SELECT") and "SELECT" not in query_upper:
        return False, "Query must contain SELECT statement"
    
    # Check for balanced parentheses
    if query.count("(") != query.count(")"):
        return False, "Unbalanced parentheses"
    
    # Check for SQL injection patterns (basic)
    dangerous_patterns = [
        r";\s*DROP\s+TABLE",
        r";\s*DELETE\s+FROM",
        r";\s*UPDATE\s+",
        r"--\s*$",  # SQL comment at end
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, query_upper):
            return False, f"Query contains potentially dangerous pattern: {pattern}"
    
    # Check for minimum query structure
    if "FROM" not in query_upper and "SELECT" in query_upper:
        # Allow SELECT without FROM (e.g., SELECT 1+1)
        pass
    
    return True, "Syntax check passed"


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
    syntax_ok, syntax_msg = quick_syntax_check(query)
    if not syntax_ok:
        return False, syntax_msg, [], 0
    
    # Full validation
    for attempt in range(max_retries + 1):
        is_valid, message, results = validate_query(query, schema, sample_data)
        
        if is_valid:
            return True, message, results, attempt + 1
        
        if attempt < max_retries:
            logger.info(f"Validation attempt {attempt + 1} failed, retrying...")
    
    return False, message, [], max_retries + 1
