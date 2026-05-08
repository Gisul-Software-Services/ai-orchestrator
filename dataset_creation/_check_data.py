import json
from pathlib import Path

base = Path('/root/gisul_model/dataset_creation')

files = [
    'sql_dataset_clean_v2.json',
    'sql_dataset_final_clean.json',
    'sql_dataset_aptor_fixed.json',
]

for f in files:
    p = base / f
    if p.exists():
        d = json.load(open(p))
        print(f"{f}: {len(d)} entries")
    else:
        print(f"{f}: NOT FOUND")

# Check spider
spider = base / 'spider_raw' / 'train_spider.json'
if spider.exists():
    d = json.load(open(spider))
    print(f"spider train_spider.json: {len(d)} Q&A pairs")

# Check gretelai
import pandas as pd
g = base / 'gretelai_extended.parquet'
if g.exists():
    df = pd.read_parquet(g)
    print(f"gretelai_extended.parquet: {len(df)} rows, cols: {list(df.columns)}")

# Check schemas library
sl = base / 'sql_schemas_library.json'
if sl.exists():
    d = json.load(open(sl))
    print(f"sql_schemas_library.json: {len(d)} schemas")
else:
    print("sql_schemas_library.json: NOT BUILT YET")
