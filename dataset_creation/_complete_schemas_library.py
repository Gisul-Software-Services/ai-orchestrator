#!/usr/bin/env python3
"""Append hand-crafted schemas and main() to build_sql_schemas_library.py"""
from pathlib import Path

target = Path(__file__).parent / "build_sql_schemas_library.py"

# Read current content
content = target.read_text(encoding="utf-8")

# Remove the "# hand crafted" marker
if content.endswith("# hand crafted\n"):
    content = content[:-15]
elif content.endswith("# hand crafted"):
    content = content[:-14]

# Append the hand-crafted schemas and main function
addition = '''

# ─────────────────────────────────────────────────────────────
# Source 3: Hand-crafted schemas
# ─────────────────────────────────────────────────────────────

def load_handcrafted_schemas() -> List[dict]:
    """
    Hand-crafted schemas covering categories not well-represented in open-source:
    - Chinook-style (music store)
    - Northwind-style (trading company)  
    - Sakila-style (DVD rental)
    - Org hierarchy (recursive CTE)
    - E-commerce (window, CTE, case_when)
    """
    schemas = []
    
    # ── 1. Chinook-style: Music Store ──────────────────────────
    chinook_tables = {
        "artists": {"columns": [
            {"name": "artist_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "name", "type": "VARCHAR(255)", "constraints": "NOT NULL"},
        ]},
        "albums": {"columns": [
            {"name": "album_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "title", "type": "VARCHAR(255)", "constraints": "NOT NULL"},
            {"name": "artist_id", "type": "INTEGER", "constraints": ""},
            {"name": "release_year", "type": "INTEGER", "constraints": ""},
        ]},
        "tracks": {"columns": [
            {"name": "track_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "name", "type": "VARCHAR(255)", "constraints": "NOT NULL"},
            {"name": "album_id", "type": "INTEGER", "constraints": ""},
            {"name": "genre", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "duration_ms", "type": "INTEGER", "constraints": ""},
            {"name": "unit_price", "type": "DECIMAL", "constraints": ""},
        ]},
        "invoices": {"columns": [
            {"name": "invoice_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "customer_id", "type": "INTEGER", "constraints": ""},
            {"name": "invoice_date", "type": "TIMESTAMP", "constraints": ""},
            {"name": "total", "type": "DECIMAL", "constraints": ""},
            {"name": "billing_country", "type": "VARCHAR(100)", "constraints": ""},
        ]},
        "customers": {"columns": [
            {"name": "customer_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "name", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "email", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "country", "type": "VARCHAR(100)", "constraints": ""},
        ]},
    }
    chinook_sample = {
        "artists": [
            {"artist_id": 1, "name": "AC/DC"},
            {"artist_id": 2, "name": "Accept"},
            {"artist_id": 3, "name": "Aerosmith"},
        ],
        "albums": [
            {"album_id": 1, "title": "For Those About To Rock", "artist_id": 1, "release_year": 1981},
            {"album_id": 2, "title": "Balls to the Wall", "artist_id": 2, "release_year": 1983},
        ],
        "tracks": [
            {"track_id": 1, "name": "For Those About To Rock", "album_id": 1, "genre": "Rock", "duration_ms": 343719, "unit_price": 0.99},
            {"track_id": 2, "name": "Balls to the Wall", "album_id": 2, "genre": "Rock", "duration_ms": 342562, "unit_price": 0.99},
        ],
        "invoices": [
            {"invoice_id": 1, "customer_id": 1, "invoice_date": "2023-01-01", "total": 1.98, "billing_country": "Germany"},
            {"invoice_id": 2, "customer_id": 2, "invoice_date": "2023-01-02", "total": 3.96, "billing_country": "USA"},
        ],
        "customers": [
            {"customer_id": 1, "name": "Luís Gonçalves", "email": "luis@email.com", "country": "Brazil"},
            {"customer_id": 2, "name": "Leonie Köhler", "email": "leonie@email.com", "country": "Germany"},
        ],
    }
    schemas.append(make_schema_doc(
        schema_id="hc_music_store_001",
        name="Chinook Music Store",
        domain="music retail",
        tables=chinook_tables,
        sample_data=chinook_sample,
        difficulty_levels=["easy", "medium", "hard"],
        sql_categories=["select", "join", "aggregation", "window", "subquery", "cte"],
        source="hand_crafted"
    ))
    
    # ── 2. Northwind-style: Trading Company ────────────────────
    northwind_tables = {
        "customers": {"columns": [
            {"name": "customer_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "company_name", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "country", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "city", "type": "VARCHAR(100)", "constraints": ""},
        ]},
        "employees": {"columns": [
            {"name": "employee_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "first_name", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "last_name", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "title", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "reports_to", "type": "INTEGER", "constraints": ""},
            {"name": "hire_date", "type": "TIMESTAMP", "constraints": ""},
        ]},
        "orders": {"columns": [
            {"name": "order_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "customer_id", "type": "INTEGER", "constraints": ""},
            {"name": "employee_id", "type": "INTEGER", "constraints": ""},
            {"name": "order_date", "type": "TIMESTAMP", "constraints": ""},
            {"name": "shipped_date", "type": "TIMESTAMP", "constraints": ""},
        ]},
        "products": {"columns": [
            {"name": "product_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "product_name", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "unit_price", "type": "DECIMAL", "constraints": ""},
            {"name": "units_in_stock", "type": "INTEGER", "constraints": ""},
        ]},
        "order_details": {"columns": [
            {"name": "order_id", "type": "INTEGER", "constraints": ""},
            {"name": "product_id", "type": "INTEGER", "constraints": ""},
            {"name": "quantity", "type": "INTEGER", "constraints": ""},
            {"name": "unit_price", "type": "DECIMAL", "constraints": ""},
        ]},
    }
    northwind_sample = {
        "customers": [
            {"customer_id": 1, "company_name": "Alfreds Futterkiste", "country": "Germany", "city": "Berlin"},
            {"customer_id": 2, "company_name": "Ana Trujillo", "country": "Mexico", "city": "Mexico D.F."},
        ],
        "employees": [
            {"employee_id": 1, "first_name": "Nancy", "last_name": "Davolio", "title": "Sales Rep", "reports_to": 2, "hire_date": "2022-01-01"},
            {"employee_id": 2, "first_name": "Andrew", "last_name": "Fuller", "title": "VP Sales", "reports_to": None, "hire_date": "2021-01-01"},
        ],
        "orders": [
            {"order_id": 1, "customer_id": 1, "employee_id": 1, "order_date": "2023-01-15", "shipped_date": "2023-01-20"},
            {"order_id": 2, "customer_id": 2, "employee_id": 1, "order_date": "2023-02-10", "shipped_date": "2023-02-15"},
        ],
        "products": [
            {"product_id": 1, "product_name": "Chai", "unit_price": 18.0, "units_in_stock": 39},
            {"product_id": 2, "product_name": "Chang", "unit_price": 19.0, "units_in_stock": 17},
        ],
        "order_details": [
            {"order_id": 1, "product_id": 1, "quantity": 12, "unit_price": 18.0},
            {"order_id": 1, "product_id": 2, "quantity": 10, "unit_price": 19.0},
        ],
    }
    schemas.append(make_schema_doc(
        schema_id="hc_trading_company_001",
        name="Northwind Trading Company",
        domain="retail",
        tables=northwind_tables,
        sample_data=northwind_sample,
        difficulty_levels=["easy", "medium", "hard"],
        sql_categories=["select", "join", "aggregation", "window", "subquery", "cte", "self_join", "date_functions"],
        source="hand_crafted"
    ))
    
    # ── 3. Sakila-style: DVD Rental ────────────────────────────
    sakila_tables = {
        "films": {"columns": [
            {"name": "film_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "title", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "release_year", "type": "INTEGER", "constraints": ""},
            {"name": "rental_rate", "type": "DECIMAL", "constraints": ""},
            {"name": "length", "type": "INTEGER", "constraints": ""},
            {"name": "rating", "type": "VARCHAR(10)", "constraints": ""},
        ]},
        "actors": {"columns": [
            {"name": "actor_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "first_name", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "last_name", "type": "VARCHAR(100)", "constraints": ""},
        ]},
        "film_actors": {"columns": [
            {"name": "film_id", "type": "INTEGER", "constraints": ""},
            {"name": "actor_id", "type": "INTEGER", "constraints": ""},
        ]},
        "customers": {"columns": [
            {"name": "customer_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "first_name", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "last_name", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "email", "type": "VARCHAR(255)", "constraints": ""},
        ]},
        "rentals": {"columns": [
            {"name": "rental_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "customer_id", "type": "INTEGER", "constraints": ""},
            {"name": "film_id", "type": "INTEGER", "constraints": ""},
            {"name": "rental_date", "type": "TIMESTAMP", "constraints": ""},
            {"name": "return_date", "type": "TIMESTAMP", "constraints": ""},
        ]},
    }
    sakila_sample = {
        "films": [
            {"film_id": 1, "title": "Academy Dinosaur", "release_year": 2006, "rental_rate": 0.99, "length": 86, "rating": "PG"},
            {"film_id": 2, "title": "Ace Goldfinger", "release_year": 2006, "rental_rate": 4.99, "length": 48, "rating": "G"},
        ],
        "actors": [
            {"actor_id": 1, "first_name": "Penelope", "last_name": "Guiness"},
            {"actor_id": 2, "first_name": "Nick", "last_name": "Wahlberg"},
        ],
        "film_actors": [
            {"film_id": 1, "actor_id": 1},
            {"film_id": 1, "actor_id": 2},
            {"film_id": 2, "actor_id": 1},
        ],
        "customers": [
            {"customer_id": 1, "first_name": "Mary", "last_name": "Smith", "email": "mary@email.com"},
            {"customer_id": 2, "first_name": "Patricia", "last_name": "Johnson", "email": "pat@email.com"},
        ],
        "rentals": [
            {"rental_id": 1, "customer_id": 1, "film_id": 1, "rental_date": "2023-01-01", "return_date": "2023-01-07"},
            {"rental_id": 2, "customer_id": 2, "film_id": 2, "rental_date": "2023-01-02", "return_date": "2023-01-05"},
        ],
    }
    schemas.append(make_schema_doc(
        schema_id="hc_dvd_rental_001",
        name="Sakila DVD Rental",
        domain="entertainment",
        tables=sakila_tables,
        sample_data=sakila_sample,
        difficulty_levels=["easy", "medium", "hard"],
        sql_categories=["select", "join", "aggregation", "window", "subquery", "cte"],
        source="hand_crafted"
    ))
    
    # ── 4. Org Hierarchy (Recursive CTE) ───────────────────────
    org_tables = {
        "employees": {"columns": [
            {"name": "emp_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "name", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "manager_id", "type": "INTEGER", "constraints": ""},
            {"name": "level", "type": "INTEGER", "constraints": ""},
            {"name": "department", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "salary", "type": "DECIMAL", "constraints": ""},
        ]},
    }
    org_sample = {
        "employees": [
            {"emp_id": 1, "name": "CEO Alice", "manager_id": None, "level": 1, "department": "Executive", "salary": 200000},
            {"emp_id": 2, "name": "VP Bob", "manager_id": 1, "level": 2, "department": "Engineering", "salary": 150000},
            {"emp_id": 3, "name": "VP Carol", "manager_id": 1, "level": 2, "department": "Sales", "salary": 140000},
            {"emp_id": 4, "name": "Manager Dave", "manager_id": 2, "level": 3, "department": "Engineering", "salary": 110000},
            {"emp_id": 5, "name": "Engineer Eve", "manager_id": 4, "level": 4, "department": "Engineering", "salary": 90000},
        ],
    }
    schemas.append(make_schema_doc(
        schema_id="hc_org_hierarchy_001",
        name="Organization Hierarchy",
        domain="corporate",
        tables=org_tables,
        sample_data=org_sample,
        difficulty_levels=["medium", "hard"],
        sql_categories=["recursive_cte", "cte", "self_join", "window"],
        source="hand_crafted"
    ))
    
    # ── 5. E-Commerce (Window, CTE, Case When) ─────────────────
    ecommerce_tables = {
        "customers": {"columns": [
            {"name": "customer_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "name", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "email", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "country", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "created_at", "type": "TIMESTAMP", "constraints": ""},
        ]},
        "products": {"columns": [
            {"name": "product_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "name", "type": "VARCHAR(255)", "constraints": ""},
            {"name": "category", "type": "VARCHAR(100)", "constraints": ""},
            {"name": "price", "type": "DECIMAL", "constraints": ""},
            {"name": "stock", "type": "INTEGER", "constraints": ""},
        ]},
        "orders": {"columns": [
            {"name": "order_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "customer_id", "type": "INTEGER", "constraints": ""},
            {"name": "order_date", "type": "TIMESTAMP", "constraints": ""},
            {"name": "status", "type": "VARCHAR(50)", "constraints": ""},
            {"name": "total_amount", "type": "DECIMAL", "constraints": ""},
        ]},
        "order_items": {"columns": [
            {"name": "item_id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "order_id", "type": "INTEGER", "constraints": ""},
            {"name": "product_id", "type": "INTEGER", "constraints": ""},
            {"name": "quantity", "type": "INTEGER", "constraints": ""},
            {"name": "unit_price", "type": "DECIMAL", "constraints": ""},
        ]},
    }
    ecommerce_sample = {
        "customers": [
            {"customer_id": 1, "name": "Alice Johnson", "email": "alice@email.com", "country": "USA", "created_at": "2023-01-15"},
            {"customer_id": 2, "name": "Bob Smith", "email": "bob@email.com", "country": "UK", "created_at": "2023-02-20"},
            {"customer_id": 3, "name": "Carol White", "email": "carol@email.com", "country": "USA", "created_at": "2023-03-10"},
        ],
        "products": [
            {"product_id": 1, "name": "Laptop Pro", "category": "Electronics", "price": 1299.99, "stock": 50},
            {"product_id": 2, "name": "Wireless Mouse", "category": "Electronics", "price": 29.99, "stock": 200},
            {"product_id": 3, "name": "Office Chair", "category": "Furniture", "price": 349.99, "stock": 30},
        ],
        "orders": [
            {"order_id": 1, "customer_id": 1, "order_date": "2023-03-01", "status": "delivered", "total_amount": 1329.98},
            {"order_id": 2, "customer_id": 2, "order_date": "2023-03-15", "status": "pending", "total_amount": 349.99},
            {"order_id": 3, "customer_id": 1, "order_date": "2023-04-01", "status": "delivered", "total_amount": 29.99},
        ],
        "order_items": [
            {"item_id": 1, "order_id": 1, "product_id": 1, "quantity": 1, "unit_price": 1299.99},
            {"item_id": 2, "order_id": 1, "product_id": 2, "quantity": 1, "unit_price": 29.99},
            {"item_id": 3, "order_id": 2, "product_id": 3, "quantity": 1, "unit_price": 349.99},
        ],
    }
    schemas.append(make_schema_doc(
        schema_id="hc_ecommerce_001",
        name="E-Commerce Platform",
        domain="e-commerce",
        tables=ecommerce_tables,
        sample_data=ecommerce_sample,
        difficulty_levels=["easy", "medium", "hard"],
        sql_categories=["select", "join", "aggregation", "window", "subquery", "cte", "case_when", "date_functions"],
        source="hand_crafted"
    ))
    
    print(f"  ✓ Created {len(schemas)} hand-crafted schemas")
    return schemas


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("SQL Schemas Library Builder")
    print("=" * 60)
    
    all_schemas = []
    seen_sigs = set()
    
    # Source 1: Spider
    print("\\n1. Loading Spider schemas...")
    spider = load_spider_schemas()
    for s in spider:
        sig = schema_signature(s["tables"])
        if sig not in seen_sigs:
            seen_sigs.add(sig)
            all_schemas.append(s)
    print(f"   Added {len(spider)} Spider schemas")
    
    # Source 2: gretelai
    print("\\n2. Loading gretelai schemas...")
    gretelai = load_gretelai_schemas(max_schemas=500)
    added = 0
    for s in gretelai:
        sig = schema_signature(s["tables"])
        if sig not in seen_sigs:
            seen_sigs.add(sig)
            all_schemas.append(s)
            added += 1
    print(f"   Added {added} gretelai schemas (deduped)")
    
    # Source 3: Hand-crafted
    print("\\n3. Adding hand-crafted schemas...")
    hc = load_handcrafted_schemas()
    for s in hc:
        all_schemas.append(s)
    print(f"   Added {len(hc)} hand-crafted schemas")
    
    # Stats
    print(f"\\n{'=' * 60}")
    print(f"Total schemas: {len(all_schemas)}")
    
    # Category coverage
    from collections import Counter
    cat_count = Counter()
    diff_count = Counter()
    domain_count = Counter()
    
    for s in all_schemas:
        for c in s.get("sql_categories", []):
            cat_count[c] += 1
        for d in s.get("difficulty_levels", []):
            diff_count[d] += 1
        domain_count[s.get("domain", "unknown")] += 1
    
    print("\\nCategory coverage:")
    for cat, cnt in sorted(cat_count.items()):
        print(f"  {cat:20s}: {cnt} schemas")
    
    print("\\nDifficulty coverage:")
    for diff, cnt in sorted(diff_count.items()):
        print(f"  {diff:10s}: {cnt} schemas")
    
    print(f"\\nUnique domains: {len(domain_count)}")
    
    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_schemas, f, indent=2, ensure_ascii=False)
    
    print(f"\\n✓ Saved {len(all_schemas)} schemas to {OUTPUT_FILE}")
    print("\\nNext step: python ../backend/scripts/import_sql_schemas.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
'''

# Write the complete file
target.write_text(content + addition, encoding="utf-8")
print("✓ Completed build_sql_schemas_library.py")
print("\\nRun: python dataset_creation/build_sql_schemas_library.py")
