#!/usr/bin/env python3
"""Add sample data to classic database schemas."""
import json, sys
sys.path.insert(0, '.')
from dataset_creation.generate_synthetic_schemas import generate_sample_rows

classic = json.load(open('dataset_creation/classic_databases_schemas.json'))

for schema in classic:
    # Always regenerate sample data with latest generator
    sample_data = {}
    for tname, tdef in schema['tables'].items():
        sample_data[tname] = generate_sample_rows(tname, tdef['columns'], n=5)
    schema['sample_data'] = sample_data
    print(f"✅ Regenerated sample data for {schema['name']}: {list(sample_data.keys())}")

with open('dataset_creation/classic_databases_schemas.json', 'w') as f:
    json.dump(classic, f, indent=2)

# Rebuild combined
synthetic = json.load(open('dataset_creation/synthetic_schemas.json'))
all_schemas = classic + synthetic
with open('dataset_creation/all_schemas_combined.json', 'w') as f:
    json.dump(all_schemas, f, indent=2)

print(f"\n✅ Rebuilt combined: {len(all_schemas)} schemas, all with sample data")
