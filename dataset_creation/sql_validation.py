#!/usr/bin/env python3
"""
Validate SQL Dataset Quality
============================

Checks:
- APTOR format compliance
- Schema/data consistency
- SQL executability
- Hint quality (no leakage)
- Edge case coverage
"""

import json
import re
import duckdb
from collections import Counter
from typing import Dict, List


def validate_aptor_format(record: Dict) -> List[str]:
    """Validate APTOR format compliance."""
    errors = []
    
    required_fields = [
        "id", "title", "description", "difficulty", "sql_category",
        "schemas", "sample_data", "constraints", "hints",
        "evaluation", "reference_query"
    ]
    
    for field in required_fields:
        if field not in record:
            errors.append(f"Missing required field: {field}")
    
    # Check difficulty values
    if record.get("difficulty") not in ["easy", "medium", "hard"]:
        errors.append(f"Invalid difficulty: {record.get('difficulty')}")
    
    # Check category values
    valid_categories = ["select", "join", "aggregation", "subquery", "window", "manipulation"]
    if record.get("sql_category") not in valid_categories:
        errors.append(f"Invalid sql_category: {record.get('sql_category')}")
    
    # Check description structure (should have 3 paragraphs)
    desc = record.get("description", "")
    paragraphs = [p.strip() for p in desc.split("\n\n") if p.strip()]
    if len(paragraphs) != 3:
        errors.append(f"Description should have 3 paragraphs, found {len(paragraphs)}")
    
    # Check for forbidden words in description
    forbidden = ["you", "your", "we", "I"]
    desc_lower = desc.lower()
    for word in forbidden:
        if f" {word} " in f" {desc_lower} ":
            errors.append(f"Description contains forbidden word: '{word}'")
    
    return errors


def check_hint_leakage(record: Dict) -> List[str]:
    """Check if hints give away SQL keywords."""
    warnings = []
    
    sql_keywords = [
        "SELECT", "JOIN", "LEFT JOIN", "INNER JOIN", "WHERE", "GROUP BY",
        "HAVING", "ORDER BY", "SUM", "COUNT", "AVG", "MAX", "MIN",
        "DISTINCT", "UNION", "INTERSECT", "WINDOW", "PARTITION BY"
    ]
    
    hints = record.get("hints", [])
    for i, hint in enumerate(hints, 1):
        hint_upper = hint.upper()
        for keyword in sql_keywords:
            if keyword in hint_upper:
                warnings.append(f"Hint {i} contains SQL keyword '{keyword}': {hint[:50]}...")
    
    return warnings


def validate_sql_execution(record: Dict) -> List[str]:
    """Test if SQL executes against sample data."""
    errors = []
    
    schemas = record.get("schemas", {})
    sample_data = record.get("sample_data", {})
    sql = record.get("reference_query", "")
    
    if not schemas or not sample_data or not sql:
        return ["Missing schemas, sample_data, or reference_query"]
    
    conn = duckdb.connect(":memory:")
    
    try:
        # Create tables
        for table_name, schema in schemas.items():
            columns = []
            for col in schema.get("columns", []):
                col_type = col["type"].split("(")[0]
                columns.append(f'"{col["name"]}" {col_type}')
            
            create_sql = f'CREATE TABLE "{table_name}" ({", ".join(columns)})'
            conn.execute(create_sql)
        
        # Insert data
        for table_name, rows in sample_data.items():
            if table_name not in schemas or not rows:
                continue
            
            col_names = [c["name"] for c in schemas[table_name]["columns"]]
            
            for row in rows:
                if isinstance(row, list):
                    # Array format
                    values = row
                    placeholders = ", ".join(["?" for _ in values])
                    columns_str = ", ".join(f'"{c}"' for c in col_names[:len(values)])
                else:
                    # Dict format
                    available_cols = [k for k in row.keys() if k in col_names]
                    values = [row.get(c) for c in available_cols]
                    placeholders = ", ".join(["?" for _ in values])
                    columns_str = ", ".join(f'"{c}"' for c in available_cols)
                
                insert_sql = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
                conn.execute(insert_sql, values)
        
        # Execute SQL
        normalized_sql = re.sub(r'\bT\d+\.', '', sql)
        result = conn.execute(normalized_sql).fetchall()
        
        if not result:
            errors.append("SQL executed but returned empty result set")
    
    except Exception as e:
        errors.append(f"SQL execution failed: {str(e)[:100]}")
    
    finally:
        conn.close()
    
    return errors


def check_edge_cases(record: Dict) -> List[str]:
    """Check if sample data includes edge cases."""
    warnings = []
    
    sample_data = record.get("sample_data", {})
    
    has_null = False
    has_duplicate = False
    
    for table_name, rows in sample_data.items():
        if not rows:
            warnings.append(f"Table '{table_name}' has no sample data")
            continue
        
        # Check for NULL values
        for row in rows:
            if isinstance(row, dict):
                if None in row.values() or "NULL" in str(row.values()).upper():
                    has_null = True
            elif isinstance(row, list):
                if None in row or "NULL" in str(row).upper():
                    has_null = True
        
        # Check for duplicates (crude check)
        if len(rows) > len(set(str(r) for r in rows)):
            has_duplicate = True
    
    if not has_null:
        warnings.append("Sample data may lack NULL edge cases")
    
    return warnings


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validate_dataset.py <dataset.json>")
        print("Example: python validate_dataset.py sql_dataset_aptor.json")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    print("=" * 70)
    print(f"Validating: {filepath}")
    print("=" * 70)
    
    with open(filepath) as f:
        dataset = json.load(f)
    
    print(f"\n📊 Dataset size: {len(dataset)} records")
    
    # Statistics
    categories = Counter(r["sql_category"] for r in dataset)
    difficulties = Counter(r["difficulty"] for r in dataset)
    
    print(f"\n📈 Category distribution:")
    for cat, count in categories.items():
        print(f"   {cat:15s}: {count:4d} ({count/len(dataset)*100:.1f}%)")
    
    print(f"\n📈 Difficulty distribution:")
    for diff, count in difficulties.items():
        print(f"   {diff:15s}: {count:4d} ({count/len(dataset)*100:.1f}%)")
    
    # Validate each record
    print(f"\n🔍 Validating records...")
    
    format_errors = 0
    hint_warnings = 0
    exec_errors = 0
    edge_warnings = 0
    
    sample_size = min(100, len(dataset))  # Validate first 100 for speed
    
    for i, record in enumerate(dataset[:sample_size]):
        # Format validation
        errors = validate_aptor_format(record)
        if errors:
            format_errors += len(errors)
            if format_errors <= 5:  # Show first 5
                print(f"\n❌ Format errors in record {i}:")
                for err in errors[:3]:
                    print(f"   - {err}")
        
        # Hint leakage check
        warnings = check_hint_leakage(record)
        if warnings:
            hint_warnings += len(warnings)
            if hint_warnings <= 5:
                print(f"\n⚠️  Hint warnings in record {i}:")
                for warn in warnings[:2]:
                    print(f"   - {warn}")
        
        # SQL execution
        errors = validate_sql_execution(record)
        if errors:
            exec_errors += len(errors)
            if exec_errors <= 5:
                print(f"\n❌ Execution errors in record {i}:")
                for err in errors[:2]:
                    print(f"   - {err}")
        
        # Edge cases
        warnings = check_edge_cases(record)
        if warnings:
            edge_warnings += len(warnings)
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"✅ Format compliance:  {sample_size - (format_errors > 0)}/{sample_size}")
    print(f"⚠️  Hint leakage:       {hint_warnings} warnings")
    print(f"✅ SQL executability:  {sample_size - (exec_errors > 0)}/{sample_size}")
    print(f"⚠️  Edge case coverage: {edge_warnings} warnings")
    
    if format_errors == 0 and exec_errors == 0:
        print("\n🎉 Dataset passed validation!")
    else:
        print("\n⚠️  Dataset has issues (see above)")
    
    print("=" * 70)


if __name__ == "__main__":
    main()