"""
SQL Category Router — Production Ready

Routes any user SQL category input to the appropriate generation path.
Handles normalization, validation, and fallback logic.
"""
from __future__ import annotations

import logging
from typing import Literal, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Category Mappings
# ─────────────────────────────────────────────────────────────

# Canonical category names
CANONICAL_CATEGORIES = {
    "select",
    "join", 
    "aggregation",
    "subquery",
    "window",
    "cte",
    "recursive_cte",
    "case_when",
    "date_functions",
    "string_functions",
    "null_handling",
    "self_join",
    "cross_join",
    "set_operations",
    "manipulation",
}

# User input → canonical category mapping
CATEGORY_ALIASES = {
    # Direct matches
    "select": "select",
    "join": "join",
    "joins": "join",
    "aggregation": "aggregation",
    "aggregate": "aggregation",
    "aggregations": "aggregation",
    "group_by": "aggregation",
    "groupby": "aggregation",
    "having": "aggregation",
    "subquery": "subquery",
    "subqueries": "subquery",
    "nested": "subquery",
    "nested_query": "subquery",
    "correlated": "subquery",
    "exists": "subquery",
    "in": "subquery",
    "window": "window",
    "window_function": "window",
    "window_functions": "window",
    "rank": "window",
    "partition": "window",
    "row_number": "window",
    "lag": "window",
    "lead": "window",
    
    # CTE variants
    "cte": "cte",
    "ctes": "cte",
    "with": "cte",
    "common_table_expression": "cte",
    "recursive": "recursive_cte",
    "recursive_cte": "recursive_cte",
    "recursive_query": "recursive_cte",
    
    # Case/conditional
    "case": "case_when",
    "case_when": "case_when",
    "case_statement": "case_when",
    "conditional": "case_when",
    
    # Date/time
    "date": "date_functions",
    "date_functions": "date_functions",
    "datetime": "date_functions",
    "timestamp": "date_functions",
    "time": "date_functions",
    "date_arithmetic": "date_functions",
    
    # String operations
    "string": "string_functions",
    "string_functions": "string_functions",
    "text": "string_functions",
    "concat": "string_functions",
    "substring": "string_functions",
    
    # NULL handling
    "null": "null_handling",
    "null_handling": "null_handling",
    "coalesce": "null_handling",
    "nullif": "null_handling",
    "is_null": "null_handling",
    
    # Join types
    "self_join": "self_join",
    "self": "self_join",
    "cross_join": "cross_join",
    "cross": "cross_join",
    "inner_join": "join",
    "left_join": "join",
    "right_join": "join",
    "outer_join": "join",
    "full_join": "join",
    
    # Set operations
    "union": "set_operations",
    "intersect": "set_operations",
    "except": "set_operations",
    "set_operations": "set_operations",
    "set": "set_operations",
    
    # DML
    "insert": "manipulation",
    "update": "manipulation",
    "delete": "manipulation",
    "manipulation": "manipulation",
    "dml": "manipulation",
}

# Categories supported by RAG catalog (existing 2,288 questions)
# Kept for reference but all categories now use schema-based generation
RAG_SUPPORTED: set = set()  # Empty - all categories go schema-based

# All categories use schema-based generation with 56 high-quality schemas
SCHEMA_BASED = {
    "select",
    "join",
    "aggregation",
    "subquery",
    "window",
    "cte",
    "recursive_cte",
    "case_when",
    "date_functions",
    "string_functions",
    "null_handling",
    "self_join",
    "cross_join",
    "set_operations",
    "manipulation",
}

# Categories not yet supported
UNSUPPORTED = set()  # All categories are now supported

GenerationPath = Literal["rag", "schema", "unknown"]


# ─────────────────────────────────────────────────────────────
# Router Functions
# ─────────────────────────────────────────────────────────────

def normalize_category(user_input: str) -> str:
    """
    Normalize user input to canonical category name.
    
    Args:
        user_input: Raw category string from user (e.g., "GROUP BY", "window_function")
    
    Returns:
        Canonical category name (e.g., "aggregation", "window")
    
    Examples:
        >>> normalize_category("GROUP BY")
        'aggregation'
        >>> normalize_category("window_function")
        'window'
        >>> normalize_category("recursive")
        'recursive_cte'
    """
    if not user_input:
        return "select"  # Default fallback
    
    # Normalize: lowercase, replace spaces/hyphens with underscores
    normalized = user_input.lower().strip()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    
    # Look up in aliases
    canonical = CATEGORY_ALIASES.get(normalized, normalized)
    
    # Log unknown categories for future expansion
    if canonical not in CANONICAL_CATEGORIES:
        logger.warning(f"Unknown SQL category: '{user_input}' (normalized: '{normalized}')")
        return normalized  # Return as-is, will be marked as unknown
    
    return canonical


def route_category(user_input: str) -> Tuple[str, GenerationPath]:
    """
    Route a user category input to the appropriate generation path.
    
    Args:
        user_input: Raw category string from user
    
    Returns:
        Tuple of (canonical_category, generation_path)
        - canonical_category: Normalized category name
        - generation_path: "rag", "schema", or "unknown"
    
    Examples:
        >>> route_category("join")
        ('join', 'rag')
        >>> route_category("CTE")
        ('cte', 'schema')
        >>> route_category("unknown_category")
        ('unknown_category', 'unknown')
    """
    canonical = normalize_category(user_input)
    
    # Determine path
    if canonical in RAG_SUPPORTED:
        path: GenerationPath = "rag"
    elif canonical in SCHEMA_BASED:
        path = "schema"
    elif canonical in UNSUPPORTED:
        path = "unknown"
    else:
        # Unknown category
        path = "unknown"
        logger.warning(f"Category '{canonical}' not mapped to any generation path")
    
    logger.info(f"Routed category '{user_input}' → canonical='{canonical}', path='{path}'")
    
    return canonical, path


def get_supported_categories() -> dict:
    """
    Get all supported categories grouped by generation path.
    
    Returns:
        Dict with keys: rag_supported, schema_based, all_supported
    """
    return {
        "rag_supported": sorted(list(RAG_SUPPORTED)),
        "schema_based": sorted(list(SCHEMA_BASED)),
        "all_supported": sorted(list(RAG_SUPPORTED | SCHEMA_BASED)),
        "total_count": len(RAG_SUPPORTED | SCHEMA_BASED)
    }


def is_supported(category: str) -> bool:
    """
    Check if a category is supported.
    
    Args:
        category: Category name (will be normalized)
    
    Returns:
        True if supported, False otherwise
    """
    canonical = normalize_category(category)
    return canonical in (RAG_SUPPORTED | SCHEMA_BASED)


def get_category_info(category: str) -> dict:
    """
    Get detailed information about a category.
    
    Args:
        category: Category name (will be normalized)
    
    Returns:
        Dict with category metadata
    """
    canonical = normalize_category(category)
    
    if canonical in RAG_SUPPORTED:
        path = "rag"
        description = "Supported via RAG catalog (fast, proven quality)"
    elif canonical in SCHEMA_BASED:
        path = "schema"
        description = "Supported via schema-based generation (flexible, unlimited)"
    else:
        path = "unknown"
        description = "Not supported"
    
    return {
        "canonical_name": canonical,
        "generation_path": path,
        "is_supported": path != "unknown",
        "description": description,
        "aliases": [k for k, v in CATEGORY_ALIASES.items() if v == canonical]
    }
