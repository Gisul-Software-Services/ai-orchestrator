#!/usr/bin/env python3
"""Combine all schema files into one."""
import json

# Load all schema files
classic = json.load(open('dataset_creation/classic_databases_schemas.json'))
synthetic = json.load(open('dataset_creation/synthetic_schemas.json'))

# Combine
all_schemas = classic + synthetic

# Save combined
with open('dataset_creation/all_schemas_combined.json', 'w') as f:
    json.dump(all_schemas, f, indent=2)

print(f'✅ Combined {len(classic)} classic + {len(synthetic)} synthetic = {len(all_schemas)} total schemas')
print(f'   Total tables: {sum(s["metadata"]["table_count"] for s in all_schemas)}')
print(f'   Total columns: {sum(s["metadata"]["total_columns"] for s in all_schemas)}')
print()
print('Breakdown by domain:')
from collections import Counter
domains = Counter(s['domain'] for s in all_schemas)
for domain, count in sorted(domains.items()):
    print(f'  {domain}: {count} schemas')
