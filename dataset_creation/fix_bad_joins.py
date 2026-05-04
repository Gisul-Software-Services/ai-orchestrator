import json, re, uuid, duckdb
from tqdm import tqdm

# Load catalog
catalog = json.load(open('sql_dataset_final_clean.json'))
print(f'Loaded {len(catalog)} entries')

# Find bad join entries (no JOIN keyword in query)
bad_joins = [e for e in catalog if e.get('sql_category') == 'join' and 'JOIN' not in e.get('reference_query','').upper()]
print(f'Bad join entries (no JOIN keyword): {len(bad_joins)}')

# Remove bad joins
bad_ids = set(e['id'] for e in bad_joins)
catalog = [e for e in catalog if e['id'] not in bad_ids]
print(f'After removal: {len(catalog)} entries')

# Pull replacements from gretel
import pandas as pd
df = pd.read_parquet('gretel_sql_cache.parquet')
join_rows = df[df['sql_complexity'].str.lower().str.strip().isin(['single join','multiple_joins'])]
join_rows = join_rows.sample(frac=1, random_state=99).reset_index(drop=True)

existing_titles = set(e.get('title','') for e in catalog)

def parse_sql_context(sql_context):
    schemas, sample_data = {}, {}
    create_pattern = re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(([^;]+)\)', re.IGNORECASE|re.DOTALL)
    for table_name, columns_raw in create_pattern.findall(sql_context):
        columns = []
        for col_line in columns_raw.split(','):
            col_line = col_line.strip()
            if re.match(r'^\s*(PRIMARY|FOREIGN|UNIQUE|CHECK|INDEX|CONSTRAINT)\s+', col_line, re.I):
                continue
            parts = col_line.split()
            if len(parts) < 2:
                continue
            col_name = parts[0].strip('`"[]')
            col_type_raw = parts[1].upper()
            if 'INT' in col_type_raw or 'SERIAL' in col_type_raw:
                col_type = 'INTEGER'
            elif any(t in col_type_raw for t in ['NUMERIC','DECIMAL','FLOAT','DOUBLE','REAL','NUMBER']):
                col_type = 'DECIMAL'
            elif any(t in col_type_raw for t in ['CHAR','TEXT','STRING','VARCHAR','NVARCHAR']):
                col_type = 'VARCHAR(255)'
            elif 'BOOL' in col_type_raw:
                col_type = 'BOOLEAN'
            elif any(t in col_type_raw for t in ['DATE','TIME','TIMESTAMP']):
                col_type = 'TIMESTAMP'
            else:
                col_type = 'TEXT'
            constraint = ''
            if 'PRIMARY KEY' in col_line.upper():
                constraint = 'PRIMARY KEY'
            elif 'NOT NULL' in col_line.upper():
                constraint = 'NOT NULL'
            columns.append({'name': col_name, 'type': col_type, 'constraints': constraint})
        if columns:
            schemas[table_name] = {'columns': columns}
            sample_data[table_name] = []
    insert_pattern = re.compile(r'INSERT\s+INTO\s+[`"]?(\w+)[`"]?\s*(?:\(([^)]+)\))?\s*VALUES\s*((?:\([^)]+\)\s*,?\s*)+)', re.IGNORECASE|re.DOTALL)
    for table_name, cols_str, values_str in insert_pattern.findall(sql_context):
        if table_name not in schemas:
            continue
        col_names = [c.strip().strip('`"') for c in cols_str.split(',')] if cols_str.strip() else [c['name'] for c in schemas[table_name]['columns']]
        for value_tuple in re.findall(r'\(([^)]+)\)', values_str):
            raw_values = re.split(r',(?=(?:[^\']*\'[^\']*\')*[^\']*$)', value_tuple)
            row = {}
            for col_name, raw_val in zip(col_names, raw_values):
                val = raw_val.strip().strip("'\"")
                if val.upper() in ('NULL','NONE',''):
                    val = None
                else:
                    try: val = int(val)
                    except:
                        try: val = float(val)
                        except: pass
                row[col_name] = val
            if row:
                sample_data[table_name].append(row)
    return schemas, sample_data

def verify_and_capture(schemas, sample_data, sql):
    conn = duckdb.connect(':memory:')
    try:
        for t, s in schemas.items():
            col_defs = [f'"{c["name"]}" {c["type"].split("(")[0]}' for c in s.get('columns',[])]
            conn.execute(f'CREATE TABLE "{t}" ({", ".join(col_defs)})')
        for t, rows in sample_data.items():
            if t not in schemas or not rows:
                continue
            col_names = [c['name'] for c in schemas[t]['columns']]
            for row in rows:
                if not isinstance(row, dict):
                    continue
                cols = [k for k in row if k in col_names]
                if not cols:
                    continue
                vals = [row[c] for c in cols]
                cols_str_q = ','.join(f'"{c}"' for c in cols)
                placeholders = ','.join(['?']*len(vals))
                conn.execute(f'INSERT INTO "{t}" ({cols_str_q}) VALUES ({placeholders})', vals)
        normalized = re.sub(r'\bT\d+\.', '', sql)
        result = conn.execute(normalized).fetchall()
        columns = [d[0] for d in conn.description]
        if not result:
            return False, None
        output = []
        for row in result:
            rd = {}
            for col, val in zip(columns, row):
                rd[col] = None if val is None else (val if isinstance(val, (int,float,str,bool)) else str(val))
            output.append(rd)
        return True, output
    except:
        return False, None
    finally:
        conn.close()

added = 0
needed = len(bad_joins)
print(f'Finding {needed} replacement join entries...')

for _, row in tqdm(join_rows.iterrows(), total=len(join_rows)):
    if added >= needed:
        break
    title = str(row.get('sql_prompt','')).strip()
    sql = str(row.get('sql','')).strip()
    if title in existing_titles or 'JOIN' not in sql.upper():
        continue
    schemas, sample_data = parse_sql_context(str(row.get('sql_context','')))
    if not schemas or len(schemas) < 2:
        continue
    success, output = verify_and_capture(schemas, sample_data, sql)
    if not success or not output:
        continue
    complexity = str(row.get('sql_complexity','')).lower().strip()
    difficulty = 'easy' if complexity == 'single join' else 'medium'
    record = {
        'id': f'sql_join_{difficulty}_{uuid.uuid4().hex[:8]}',
        'title': title,
        'description': f"A relational database manages data across multiple tables.\n\n{title}\n\nThe query must handle NULL values appropriately and return results in a deterministic order.",
        'difficulty': difficulty,
        'sql_category': 'join',
        'domain': str(row.get('domain','')),
        'schemas': schemas,
        'sample_data': sample_data,
        'constraints': ['Results must be returned in a deterministic order','NULL values should be handled appropriately','Include only records matching the specified conditions'],
        'starter_query': '-- Write your SQL query here\n\nSELECT ',
        'hints': ['Examine how the tables relate to each other through common fields','Consider what JOIN conditions are needed','Think about edge cases like NULL values or missing records'],
        'evaluation': {'engine': 'postgres', 'comparison': 'result_set', 'order_sensitive': 'ORDER BY' in sql.upper()},
        'reference_query': sql,
        'sql_expected_output': output,
        'source': 'gretelai/synthetic_text_to_sql',
        'source_complexity': complexity,
    }
    catalog.append(record)
    existing_titles.add(title)
    added += 1

print(f'Added {added} replacement entries')
print(f'Final total: {len(catalog)}')

from collections import Counter
cats = Counter(e['sql_category'] for e in catalog)
print('Categories:', dict(cats))

json.dump(catalog, open('sql_dataset_final_clean.json','w'), indent=2, ensure_ascii=False)
print('Saved.')
