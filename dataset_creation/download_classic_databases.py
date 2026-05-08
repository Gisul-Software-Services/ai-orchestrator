"""
Download and convert classic open-source databases to schema format.

This script downloads well-known sample databases (Chinook, Northwind, Sakila, etc.)
and converts them to our JSON schema format for SQL question generation.
"""
import requests
import json
import re
from typing import Dict, List, Any
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Function
from sqlparse.tokens import Keyword, DML

# Classic databases with production-quality schemas
CLASSIC_DATABASES = {
    "chinook": {
        "url": "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_PostgreSql.sql",
        "domain": "music",
        "description": "Digital music store with artists, albums, tracks, customers, invoices"
    },
    "northwind": {
        "url": "https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql",
        "domain": "e-commerce",
        "description": "Trading company with products, orders, customers, employees"
    },
    "sakila": {
        "url": "https://raw.githubusercontent.com/jOOQ/sakila/main/sqlite-sakila-db/sqlite-sakila-schema.sql",
        "domain": "entertainment",
        "description": "DVD rental store with films, actors, customers, rentals, inventory"
    },
    "employees": {
        "url": "https://raw.githubusercontent.com/datacharmer/test_db/master/employees.sql",
        "domain": "hr",
        "description": "Employee database with departments, salaries, titles, managers"
    },
    "classicmodels": {
        "url": "https://raw.githubusercontent.com/harryho/db-samples/master/mysql/mysqlsampledatabase.sql",
        "domain": "manufacturing",
        "description": "Scale model cars company with products, orders, customers, payments"
    },
    "world": {
        "url": "https://raw.githubusercontent.com/ghusta/world-database/master/world-postgresql.sql",
        "domain": "geography",
        "description": "Countries, cities, and languages worldwide"
    },
    "pagila": {
        "url": "https://raw.githubusercontent.com/devrimgunduz/pagila/master/pagila-schema.sql",
        "domain": "entertainment",
        "description": "DVD rental database similar to Sakila with PostgreSQL features"
    },
    "adventureworks_person": {
        "url": "https://raw.githubusercontent.com/Microsoft/sql-server-samples/master/samples/databases/adventure-works/oltp-install-script/instawdb.sql",
        "domain": "hr",
        "description": "Person and employee data from AdventureWorks manufacturing company"
    },
    "adventureworks_sales": {
        "url": "https://raw.githubusercontent.com/Microsoft/sql-server-samples/master/samples/databases/adventure-works/oltp-install-script/instawdb.sql",
        "domain": "sales",
        "description": "Sales orders, customers, and products from AdventureWorks"
    },
    "adventureworks_production": {
        "url": "https://raw.githubusercontent.com/Microsoft/sql-server-samples/master/samples/databases/adventure-works/oltp-install-script/instawdb.sql",
        "domain": "manufacturing",
        "description": "Product manufacturing and inventory from AdventureWorks"
    },
}

def parse_create_table(sql_statement: str) -> Dict[str, Any]:
    """
    Parse a CREATE TABLE statement to extract schema information.
    
    Returns dict with table_name, columns, and constraints.
    """
    # Extract table name
    table_match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?["`]?(\w+)["`]?', sql_statement, re.IGNORECASE)
    if not table_match:
        return None
    
    table_name = table_match.group(1)
    
    # Extract column definitions
    columns = []
    
    # Find the content between parentheses
    paren_content = re.search(r'\((.*)\)', sql_statement, re.DOTALL)
    if not paren_content:
        return None
    
    content = paren_content.group(1)
    
    # Split by commas (but not within parentheses)
    lines = []
    paren_depth = 0
    current_line = ""
    
    for char in content:
        if char == '(':
            paren_depth += 1
        elif char == ')':
            paren_depth -= 1
        elif char == ',' and paren_depth == 0:
            lines.append(current_line.strip())
            current_line = ""
            continue
        current_line += char
    
    if current_line.strip():
        lines.append(current_line.strip())
    
    # Parse each line
    for line in lines:
        line = line.strip()
        
        # Skip constraints
        if line.upper().startswith(('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'CONSTRAINT')):
            continue
        
        # Parse column definition
        parts = line.split()
        if len(parts) < 2:
            continue
        
        col_name = parts[0].strip('"`')
        col_type = parts[1].upper()
        
        # Extract constraints
        constraints = ""
        if 'PRIMARY KEY' in line.upper():
            constraints = "PRIMARY KEY"
        elif 'NOT NULL' in line.upper():
            constraints = "NOT NULL"
        elif 'UNIQUE' in line.upper():
            constraints = "UNIQUE"
        
        columns.append({
            "name": col_name,
            "type": col_type,
            "constraints": constraints
        })
    
    return {
        "table_name": table_name,
        "columns": columns
    }


def extract_foreign_keys(sql_content: str) -> List[Dict[str, str]]:
    """
    Extract foreign key relationships from SQL.
    """
    relationships = []
    
    # Pattern: FOREIGN KEY (column) REFERENCES table(column)
    fk_pattern = r'FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)'
    
    matches = re.finditer(fk_pattern, sql_content, re.IGNORECASE)
    
    for match in matches:
        from_col = match.group(1).strip('"`')
        to_table = match.group(2).strip('"`')
        to_col = match.group(3).strip('"`')
        
        relationships.append({
            "from_column": from_col,
            "to_table": to_table,
            "to_column": to_col,
            "relationship_type": "many-to-one"
        })
    
    return relationships


def sql_to_schema(sql_content: str, domain: str, description: str) -> Dict[str, Any]:
    """
    Convert SQL CREATE TABLE statements to our schema format.
    """
    # Split into individual statements
    statements = sqlparse.split(sql_content)
    
    tables = {}
    all_relationships = []
    
    for statement in statements:
        if 'CREATE TABLE' in statement.upper():
            table_info = parse_create_table(statement)
            if table_info:
                tables[table_info["table_name"]] = {
                    "columns": table_info["columns"]
                }
            
            # Extract foreign keys from this table
            fks = extract_foreign_keys(statement)
            all_relationships.extend(fks)
    
    if not tables:
        return None
    
    # Generate schema ID
    schema_id = f"classic_{domain}_{list(tables.keys())[0].lower()}"
    
    schema = {
        "schema_id": schema_id,
        "name": f"Classic - {domain.title()}",
        "domain": domain,
        "description": description,
        "source": "classic_database",
        "tables": tables,
        "relationships": all_relationships,
        "sample_data": {},  # Will be populated separately
        "difficulty_levels": ["easy", "medium", "hard"],
        "sql_categories": ["select", "join", "aggregation", "subquery", "window", "cte"],
        "metadata": {
            "table_count": len(tables),
            "total_columns": sum(len(t["columns"]) for t in tables.values()),
            "has_foreign_keys": len(all_relationships) > 0,
            "has_numeric_columns": True,
            "has_date_columns": True,
        }
    }
    
    return schema


def download_and_convert():
    """
    Download all classic databases and convert to schema format.
    """
    schemas = []
    
    for db_name, db_info in CLASSIC_DATABASES.items():
        print(f"Downloading {db_name}...")
        
        try:
            response = requests.get(db_info["url"], timeout=30)
            response.raise_for_status()
            
            sql_content = response.text
            
            print(f"Converting {db_name} to schema...")
            schema = sql_to_schema(sql_content, db_info["domain"], db_info["description"])
            
            if schema:
                schemas.append(schema)
                print(f"✅ {db_name}: {schema['metadata']['table_count']} tables, {schema['metadata']['total_columns']} columns")
            else:
                print(f"❌ {db_name}: Failed to parse")
        
        except Exception as e:
            print(f"❌ {db_name}: Error - {e}")
    
    # Save to file
    output_file = "dataset_creation/classic_databases_schemas.json"
    with open(output_file, 'w') as f:
        json.dump(schemas, f, indent=2)
    
    print(f"\n✅ Saved {len(schemas)} schemas to {output_file}")
    print(f"\nNext step: python dataset_creation/import_schemas_to_rag.py {output_file}")
    
    return schemas


if __name__ == "__main__":
    print("="*60)
    print("Classic Database Schema Downloader")
    print("="*60)
    print()
    
    schemas = download_and_convert()
    
    print()
    print("Summary:")
    print(f"  Total schemas: {len(schemas)}")
    print(f"  Total tables: {sum(s['metadata']['table_count'] for s in schemas)}")
    print(f"  Total columns: {sum(s['metadata']['total_columns'] for s in schemas)}")
