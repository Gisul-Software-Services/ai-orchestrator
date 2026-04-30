import json
from collections import Counter

catalog = json.load(open('sql_dataset_final_clean.json'))
print(f'Total entries: {len(catalog)}')

for cat in ['join','select','aggregation','subquery','window']:
    entries = [e for e in catalog if e.get('sql_category') == cat]
    if not entries:
        continue
    avg_tables = sum(len(e.get('schemas',{})) for e in entries) / len(entries)
    single = sum(1 for e in entries if len(e.get('schemas',{})) < 2)
    no_join = sum(1 for e in entries if cat == 'join' and 'JOIN' not in e.get('reference_query','').upper())
    print(f'{cat:15s}: total={len(entries)}, avg_tables={avg_tables:.1f}, single_table={single}, no_JOIN_keyword={no_join}')
