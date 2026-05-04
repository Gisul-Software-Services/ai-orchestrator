"""Fix count_star() column names in sql_expected_output."""
import json, re

catalog = json.load(open('sql_dataset_final_clean.json'))
fixed = 0

for entry in catalog:
    output = entry.get('sql_expected_output', [])
    if not output:
        continue
    new_output = []
    changed = False
    for row in output:
        new_row = {}
        for k, v in row.items():
            # Fix count_star() -> count, count_star(*) -> count
            new_key = re.sub(r'count_star\(\*?\)', 'count', k, flags=re.IGNORECASE)
            # Fix other aggregate aliases like avg(col) -> avg_col
            new_key = re.sub(r'(\w+)\((\w+)\)', r'\1_\2', new_key)
            if new_key != k:
                changed = True
            new_row[new_key] = v
        new_output.append(new_row)
    if changed:
        entry['sql_expected_output'] = new_output
        fixed += 1

print(f'Fixed {fixed} entries')
json.dump(catalog, open('sql_dataset_final_clean.json', 'w'), indent=2, ensure_ascii=False)
print('Saved.')
