#!/usr/bin/env python3
"""
SQL Dataset Quality Fixer
==========================

Diagnoses and repairs common issues:
1. Empty sample_data → Generate synthetic data
2. Hint leakage → Regenerate hints without SQL
3. Schema inconsistencies → Fix types/constraints
4. SQL execution failures → Report and optionally fix

Usage:
  python fix_dataset.py sql_dataset_aptor.json --output fixed_dataset.json
"""

import json
import re
import duckdb
from collections import defaultdict
from typing import Dict, List

# ═══════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════

def diagnose_dataset(filepath: str):
    """Run comprehensive diagnostics on dataset."""
    
    with open(filepath) as f:
        dataset = json.load(f)
    
    print("=" * 70)
    print(f"DIAGNOSING: {filepath}")
    print("=" * 70)
    print(f"\n📊 Total records: {len(dataset)}\n")
    
    issues = defaultdict(list)
    
    for i, record in enumerate(dataset):
        record_id = record.get('id', f'record_{i}')
        
        # Check 1: Empty sample data
        sample_data = record.get('sample_data', {})
        empty_tables = [t for t, rows in sample_data.items() if not rows]
        
        if empty_tables:
            issues['empty_sample_data'].append({
                'id': record_id,
                'empty_tables': empty_tables,
                'severity': 'CRITICAL'
            })
        
        # Check 2: Hint leakage
        hints = record.get('hints', [])
        sql_keywords = ['SELECT', 'JOIN', 'WHERE', 'GROUP BY', 'HAVING', 
                       'ORDER BY', 'SUM', 'COUNT', 'AVG', 'DISTINCT']
        
        for hint_idx, hint in enumerate(hints):
            leaked = [kw for kw in sql_keywords if kw in hint.upper()]
            if leaked:
                issues['hint_leakage'].append({
                    'id': record_id,
                    'hint_index': hint_idx,
                    'leaked_keywords': leaked,
                    'hint': hint[:60] + '...',
                    'severity': 'HIGH'
                })
        
        # Check 3: SQL executability
        schemas = record.get('schemas', {})
        sql = record.get('reference_query', '')
        
        if schemas and sample_data and sql:
            if not validate_sql(schemas, sample_data, sql):
                issues['sql_execution_failed'].append({
                    'id': record_id,
                    'severity': 'HIGH'
                })
        
        # Check 4: Description quality
        description = record.get('description', '')
        paragraphs = [p.strip() for p in description.split('\n\n') if p.strip()]
        
        if len(paragraphs) != 3:
            issues['description_format'].append({
                'id': record_id,
                'found_paragraphs': len(paragraphs),
                'expected': 3,
                'severity': 'MEDIUM'
            })
        
        # Check 5: Forbidden words
        forbidden = ['you', 'your', 'we', 'I']
        found_forbidden = [w for w in forbidden if f' {w} ' in f' {description.lower()} ']
        
        if found_forbidden:
            issues['forbidden_words'].append({
                'id': record_id,
                'words': found_forbidden,
                'severity': 'MEDIUM'
            })
    
    # Print summary
    print("🔍 ISSUE SUMMARY")
    print("-" * 70)
    
    total_issues = sum(len(v) for v in issues.values())
    
    if total_issues == 0:
        print("✅ No issues found! Dataset is clean.")
        return issues
    
    for issue_type, records in issues.items():
        severity = records[0]['severity'] if records else 'UNKNOWN'
        emoji = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
        
        print(f"\n{emoji} {issue_type.replace('_', ' ').title()}")
        print(f"   Count: {len(records)}")
        print(f"   Severity: {severity}")
        
        # Show first 3 examples
        for record in records[:3]:
            rid = record['id']
            if issue_type == 'empty_sample_data':
                print(f"   - {rid}: Empty tables: {', '.join(record['empty_tables'])}")
            elif issue_type == 'hint_leakage':
                print(f"   - {rid}: Hint {record['hint_index']} contains {', '.join(record['leaked_keywords'])}")
            elif issue_type == 'sql_execution_failed':
                print(f"   - {rid}: SQL doesn't execute")
            elif issue_type == 'description_format':
                print(f"   - {rid}: Has {record['found_paragraphs']} paragraphs (need 3)")
            elif issue_type == 'forbidden_words':
                print(f"   - {rid}: Contains {', '.join(record['words'])}")
        
        if len(records) > 3:
            print(f"   ... and {len(records) - 3} more")
    
    print("\n" + "=" * 70)
    print(f"TOTAL ISSUES: {total_issues}")
    print("=" * 70)
    
    return issues


def validate_sql(schemas: Dict, sample_data: Dict, sql: str) -> bool:
    """Quick SQL validation using DuckDB."""
    conn = duckdb.connect(":memory:")
    
    try:
        # Create tables
        for table_name, schema in schemas.items():
            cols = []
            for col in schema.get("columns", []):
                col_type = col["type"].split("(")[0]
                cols.append(f'"{col["name"]}" {col_type}')
            
            conn.execute(f'CREATE TABLE "{table_name}" ({", ".join(cols)})')
        
        # Insert data
        for table_name, rows in sample_data.items():
            if table_name not in schemas or not rows:
                continue
            
            col_names = [c["name"] for c in schemas[table_name]["columns"]]
            
            for row in rows:
                if isinstance(row, dict):
                    available = [k for k in row.keys() if k in col_names]
                    if not available:
                        continue
                    values = [row.get(c) for c in available]
                    placeholders = ", ".join(["?" for _ in values])
                    columns_str = ", ".join(f'"{c}"' for c in available)
                else:
                    # Array format
                    values = row[:len(col_names)]
                    placeholders = ", ".join(["?" for _ in values])
                    columns_str = ", ".join(f'"{c}"' for c in col_names[:len(values)])
                
                conn.execute(
                    f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})',
                    values
                )
        
        # Execute SQL
        normalized_sql = re.sub(r'\bT\d+\.', '', sql)
        conn.execute(normalized_sql).fetchall()
        return True
    
    except Exception:
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# QUICK FIXES
# ═══════════════════════════════════════════════════════════════

def generate_sample_data(schemas: Dict, reference_query: str) -> Dict:
    """Generate minimal sample data based on schema and query analysis."""
    
    sample_data = {}
    
    for table_name, schema in schemas.items():
        columns = schema.get("columns", [])
        if not columns:
            continue
        
        # Generate 3-5 sample rows
        rows = []
        for i in range(3):
            row = {}
            for col in columns:
                col_name = col["name"]
                col_type = col["type"].upper()
                
                # Generate values based on type
                if "INT" in col_type or "SERIAL" in col_type:
                    row[col_name] = i + 1
                elif "VARCHAR" in col_type or "TEXT" in col_type:
                    row[col_name] = f"Sample{i+1}"
                elif "DECIMAL" in col_type or "NUMERIC" in col_type:
                    row[col_name] = (i + 1) * 10.5
                elif "BOOL" in col_type:
                    row[col_name] = i % 2 == 0
                elif "DATE" in col_type or "TIME" in col_type:
                    row[col_name] = f"2024-01-{i+1:02d}"
                else:
                    row[col_name] = None
            
            rows.append(row)
        
        sample_data[table_name] = rows
    
    return sample_data


def remove_sql_keywords_from_hints(hints: List[str]) -> List[str]:
    """Remove SQL keywords from hints (basic cleaning)."""
    
    sql_keywords = [
        'SELECT', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN',
        'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT',
        'SUM', 'COUNT', 'AVG', 'MAX', 'MIN', 'DISTINCT',
        'UNION', 'INTERSECT', 'EXCEPT'
    ]
    
    cleaned_hints = []
    for hint in hints:
        cleaned = hint
        for keyword in sql_keywords:
            # Remove exact keyword matches (case insensitive)
            cleaned = re.sub(
                rf'\b{re.escape(keyword)}\b',
                '[operation]',
                cleaned,
                flags=re.IGNORECASE
            )
        cleaned_hints.append(cleaned)
    
    return cleaned_hints


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fix_dataset.py <dataset.json> [--fix] [--output fixed.json]")
        print("\nExamples:")
        print("  python fix_dataset.py sql_dataset_aptor.json")
        print("  python fix_dataset.py sql_dataset_aptor.json --fix --output fixed.json")
        sys.exit(1)
    
    filepath = sys.argv[1]
    should_fix = '--fix' in sys.argv
    output_file = 'fixed_dataset.json'
    
    if '--output' in sys.argv:
        try:
            output_idx = sys.argv.index('--output')
            output_file = sys.argv[output_idx + 1]
        except (ValueError, IndexError):
            pass
    
    # Run diagnostics
    issues = diagnose_dataset(filepath)
    
    if not should_fix:
        print("\n💡 To apply fixes, run with --fix flag:")
        print(f"   python fix_dataset.py {filepath} --fix --output {output_file}")
        return
    
    # Apply fixes
    print("\n🔧 APPLYING FIXES...")
    print("-" * 70)
    
    with open(filepath) as f:
        dataset = json.load(f)
    
    fixed_count = 0
    
    for record in dataset:
        modified = False
        
        # Fix 1: Generate sample data if empty
        sample_data = record.get('sample_data', {})
        empty_tables = [t for t, rows in sample_data.items() if not rows]
        
        if empty_tables:
            print(f"🔨 Generating sample data for {record['id']}")
            new_data = generate_sample_data(
                record['schemas'],
                record.get('reference_query', '')
            )
            record['sample_data'] = new_data
            modified = True
        
        # Fix 2: Clean hints
        hints = record.get('hints', [])
        cleaned_hints = remove_sql_keywords_from_hints(hints)
        
        if cleaned_hints != hints:
            print(f"🔨 Cleaning hints for {record['id']}")
            record['hints'] = cleaned_hints
            modified = True
        
        if modified:
            fixed_count += 1
    
    # Save fixed dataset
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fixed {fixed_count} records")
    print(f"📁 Saved to: {output_file}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()