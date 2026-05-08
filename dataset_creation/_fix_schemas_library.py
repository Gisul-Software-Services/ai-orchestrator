#!/usr/bin/env python3
"""Fix build_sql_schemas_library.py by truncating garbled ending and appending the rest."""
from pathlib import Path

target = Path(__file__).parent / "build_sql_schemas_library.py"
content = target.read_text(encoding="utf-8")

MARKER = '    print(f"  \\u2713 Extracted {len(schemas)} unique schemas from gretelai")\n    return schemas'
idx = content.rfind(MARKER)
if idx == -1:
    # Try ASCII version
    MARKER = '    print(f"  \u2713 Extracted {len(schemas)} unique schemas from gretelai")\n    return schemas'
    idx = content.rfind(MARKER)

if idx == -1:
    print("ERROR: marker not found")
    print("Last 200 chars:", repr(content[-200:]))
else:
    clean = content[:idx + len(MARKER)]
    target.write_text(clean, encoding="utf-8")
    print(f"Truncated to {len(clean)} chars (was {len(content)})")
    print("Done — garbled ending removed")
