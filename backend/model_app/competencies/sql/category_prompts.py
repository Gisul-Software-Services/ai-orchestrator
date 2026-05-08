"""
Category-Specific SQL Prompts — Production Ready (SQLite Compatible)

Provides tailored instructions for each SQL category to guide LLM generation.
All prompts enforce SQLite-compatible syntax for validation.
"""
from __future__ import annotations

# Category-specific instructions injected into the LLM prompt
CATEGORY_INSTRUCTIONS = {
    "select": """
CATEGORY: SELECT (Basic Queries) - SQLITE SYNTAX
- Use SELECT with WHERE, ORDER BY, LIMIT
- Filter with comparison operators (=, >, <, >=, <=, !=, LIKE, IN, BETWEEN)
- Sort results with ORDER BY (ASC/DESC)
- Limit results with LIMIT
- Use DISTINCT to remove duplicates
- Reference ONLY exact column names from the provided schema
- Do NOT use columns that don't exist in the schema
""",
    
    "join": """
CATEGORY: JOIN (Table Relationships) - SQLITE SYNTAX
- Use INNER JOIN or LEFT JOIN only (SQLite doesn't support RIGHT JOIN or FULL OUTER JOIN)
- Join ON foreign key relationships provided in the schema
- Reference the relationships section to identify correct join conditions
- Use table aliases for clarity (e.g., c for customers, o for orders)
- Join 2-4 tables maximum for readability
- Ensure all joined tables and columns exist in the provided schema
- Do NOT hallucinate column names
""",
    
    "aggregation": """
CATEGORY: AGGREGATION (Group By & Aggregate Functions) - SQLITE SYNTAX
- Use GROUP BY with aggregate functions: COUNT, SUM, AVG, MIN, MAX
- Include all non-aggregated columns in GROUP BY
- Use HAVING to filter aggregated results (not WHERE)
- Aggregate functions must wrap column names: COUNT(column), SUM(column)
- Use meaningful aliases for aggregated columns: AS total_sales, AS avg_price
- Consider NULL handling in aggregations
- Only use columns that exist in the schema
""",
    
    "subquery": """
CATEGORY: SUBQUERY (Nested Queries) - SQLITE SYNTAX
- Use subquery in WHERE clause (e.g., WHERE id IN (SELECT...))
- Or use subquery in FROM clause (e.g., FROM (SELECT...) AS subquery)
- Or use subquery in SELECT clause (e.g., SELECT col, (SELECT...) AS sub)
- Subquery can be correlated (references outer query) or non-correlated
- Use EXISTS, IN, NOT IN operators with subqueries
- Ensure subquery returns appropriate data type for comparison
- Only reference columns that exist in the schema
""",
    
    "window": """
CATEGORY: WINDOW FUNCTIONS (Analytical Queries) - SQLITE SYNTAX
- Use window functions: ROW_NUMBER(), RANK(), DENSE_RANK(), LAG(), LEAD(), NTILE()
- MUST include OVER clause with PARTITION BY and/or ORDER BY
- Syntax: FUNCTION() OVER (PARTITION BY col1 ORDER BY col2)
- PARTITION BY groups data (like GROUP BY but doesn't collapse rows)
- ORDER BY within OVER determines ranking/ordering
- Use meaningful aliases: AS row_num, AS rank, AS prev_value
- Window functions cannot be used in WHERE clause (use subquery if needed)
- Only use columns from the schema
""",
    
    "cte": """
CATEGORY: CTE (Common Table Expressions) - PostgreSQL SYNTAX
- Start with WITH clause: WITH cte_name AS (SELECT...)
- Define ONE simple CTE before the main SELECT (keep it simple)
- Reference CTE in main query like a regular table
- Use CTEs to pre-aggregate or pre-filter data before the main query
- Keep the CTE simple: one SELECT with GROUP BY or basic filtering
- Main query should SELECT from the CTE with minimal additional logic
- Only use columns that exist in the provided schema
- Do NOT invent column names or chain multiple CTEs
- Example: WITH summary AS (SELECT col, COUNT(*) as cnt FROM tbl GROUP BY col) SELECT * FROM summary
""",
    
    "recursive_cte": """
CATEGORY: RECURSIVE CTE (Hierarchical Queries) - SQLITE SYNTAX
- Use WITH RECURSIVE for hierarchical data (org charts, category trees)
- Structure: WITH RECURSIVE cte AS (base_case UNION ALL recursive_case)
- Base case: SELECT initial rows (e.g., top-level nodes WHERE parent_id IS NULL)
- Recursive case: SELECT ... FROM cte JOIN table ON parent-child relationship
- MUST have termination condition to avoid infinite recursion
- Common use cases: employee hierarchies, bill of materials, graph traversal
- Reference the self-join relationship in the schema
- Only use columns that actually exist in the schema
""",
    
    "case_when": """
CATEGORY: CASE WHEN (Conditional Logic) - SQLITE SYNTAX
- Use CASE WHEN...THEN...ELSE...END for conditional logic
- Syntax: CASE WHEN condition THEN value WHEN condition2 THEN value2 ELSE default END
- Can be used in SELECT, WHERE, ORDER BY, or HAVING
- Use for categorization, bucketing, or conditional calculations
- Always include ELSE clause for completeness
- Use meaningful aliases: AS category, AS status_label, AS price_tier
- Only reference columns from the provided schema
""",
    
    "date_functions": """
CATEGORY: DATE FUNCTIONS (Date/Time Operations) - POSTGRESQL SYNTAX
- Use PostgreSQL date functions: CURRENT_DATE, CURRENT_TIMESTAMP, NOW(), AGE(), EXTRACT()
- Date arithmetic: date_column + INTERVAL '1 day', date_column - INTERVAL '1 month'
- Extract parts: EXTRACT(YEAR FROM date_column), EXTRACT(MONTH FROM date_column)
- Date truncation: DATE_TRUNC('month', date_column), DATE_TRUNC('year', date_column)
- Date comparison: WHERE date_column > CURRENT_DATE - INTERVAL '30 days'
- Format dates: TO_CHAR(date_column, 'YYYY-MM-DD')
- CRITICAL: Only use date/timestamp columns that exist in the provided schema
- Do NOT invent column names like created_at, updated_at unless they're in the schema
""",
    
    "string_functions": """
CATEGORY: STRING FUNCTIONS (Text Operations) - SQLITE SYNTAX
- Use SQLite string functions: length(), substr(), upper(), lower(), trim(), replace()
- Concatenation: col1 || ' ' || col2 (use || operator, NOT CONCAT function)
- Substring: substr(col, start, length)
- Pattern matching: LIKE (% for wildcard, _ for single char)
- String manipulation: upper(col), lower(col), trim(col)
- Length: length(col)
- Replace: replace(col, 'old', 'new')
- Use meaningful aliases for transformed strings
- Only use columns from the schema
""",
    
    "null_handling": """
CATEGORY: NULL HANDLING (NULL Value Management) - SQLITE SYNTAX
- Use COALESCE(col, default) to provide default for NULL values
- Use NULLIF(col1, col2) to return NULL if col1 = col2
- Use IS NULL or IS NOT NULL for NULL checks (not = NULL)
- Use CASE WHEN col IS NULL THEN default ELSE col END
- Consider NULL behavior in aggregations (COUNT ignores NULLs)
- Use ifnull(col, default) as alternative to COALESCE in SQLite
- Handle NULLs in joins and comparisons explicitly
- Only reference columns from the schema
""",
    
    "self_join": """
CATEGORY: SELF JOIN (Table Joined to Itself) - SQLITE SYNTAX
- Join a table to itself using different aliases
- Syntax: FROM table t1 JOIN table t2 ON t1.col = t2.col
- Common use case: hierarchical data (employees and managers)
- Use clear aliases: e for employee, m for manager
- Join condition typically: employee.manager_id = manager.employee_id
- Reference the self-join relationship in the schema
- Can combine with other joins if needed
- Only use columns that exist in the schema
""",
    
    "cross_join": """
CATEGORY: CROSS JOIN (Cartesian Product) - SQLITE SYNTAX
- Use CROSS JOIN to get all combinations of rows from two tables
- Syntax: FROM table1 CROSS JOIN table2
- Or implicit: FROM table1, table2 (without ON clause)
- Result has rows = table1_rows × table2_rows
- Use cases: generating combinations, calendar tables, test data
- Usually combined with WHERE to filter the cartesian product
- Be careful with large tables (can produce huge result sets)
- Only use tables and columns from the schema
""",
    
    "set_operations": """
CATEGORY: SET OPERATIONS (Combining Query Results) - SQLITE SYNTAX
- Use UNION, INTERSECT, or EXCEPT to combine query results
- UNION: combines results, removes duplicates (use UNION ALL to keep duplicates)
- INTERSECT: returns rows present in both queries
- EXCEPT: returns rows in first query but not in second
- Both queries must have same number of columns with compatible types
- Column names come from first query
- Use ORDER BY after the set operation (not in individual queries)
- Only use columns from the schema
""",
    
    "manipulation": """
CATEGORY: MANIPULATION (INSERT/UPDATE/DELETE) - SQLITE SYNTAX
- Use INSERT INTO table (col1, col2) VALUES (val1, val2)
- Use UPDATE table SET col1 = val1 WHERE condition
- Use DELETE FROM table WHERE condition
- Always include WHERE clause for UPDATE/DELETE (unless intentional full table operation)
- For INSERT, can use SELECT: INSERT INTO table SELECT ... FROM other_table
- Consider constraints and foreign keys
- Only use tables and columns from the schema
"""
}


def get_category_instruction(category: str) -> str:
    """
    Get the instruction text for a specific category.
    
    Args:
        category: Canonical category name
    
    Returns:
        Instruction text, or empty string if category not found
    """
    return CATEGORY_INSTRUCTIONS.get(category, "")


def get_all_categories() -> list[str]:
    """Get list of all categories with instructions."""
    return list(CATEGORY_INSTRUCTIONS.keys())


def has_instruction(category: str) -> bool:
    """Check if a category has specific instructions."""
    return category in CATEGORY_INSTRUCTIONS
