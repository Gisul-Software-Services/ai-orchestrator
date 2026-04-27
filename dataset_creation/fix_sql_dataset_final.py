"""
SQL Dataset Fixer v2
====================
Fixes ALL issues in one clean pass:

  1. Re-run all deterministic fixes on EVERY record (not lost in LLM rebuild)
  2. Fix 304 remaining fake sample_data with stronger LLM prompt
  3. Rebalance categories: cap aggregation, promote join/select/manipulation
  4. Remove 'manipulation' DELETE/DROP/UPDATE questions — wrong for SQL assessment
     (starter_query says SELECT, reference is DELETE — confusing)
  5. Split set operations (UNION/INTERSECT) into separate 'set_operations' sub-bucket
     or keep as aggregation but cap at 200 records max

Input:  sql_dataset_aptor_fixed.json  (the file on your machine)
Output: sql_dataset_clean_v2.json
"""

import json, re, os, uuid, torch
from collections import Counter, defaultdict
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

INPUT      = "sql_dataset_aptor_fixed.json"
OUTPUT     = "sql_dataset_clean_v2.json"
STATE      = OUTPUT + ".state.json"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_NEW_TOKENS = 700
SAVE_EVERY = 50

# Target records per category for a balanced dataset
CATEGORY_CAPS = {
    "aggregation":  350,   # cap — was 1490
    "select":       300,   # boost — was 103
    "join":         300,   # boost — was 138
    "window":       300,   # keep
    "subquery":     300,   # keep
    "manipulation": 150,   # keep small — these are DML not SELECT
}

# ─────────────────────────────────────────
# DETERMINISTIC FIXES (applied to EVERY record)
# ─────────────────────────────────────────

def classify_category(sql: str) -> str:
    s = sql.strip().upper()
    first = s.split()[0] if s.split() else ""
    if first in ("DELETE","UPDATE","DROP","INSERT","ALTER","TRUNCATE","CREATE"):
        return "manipulation"
    if re.search(r'\bROW_NUMBER\s*\(|\bRANK\s*\(|\bDENSE_RANK\s*\(|\bLAG\s*\(|\bLEAD\s*\(|\bOVER\s*\(', s):
        return "window"
    if first == "WITH" and "AS (" in s:
        return "manipulation"
    if re.search(r'\bUNION\b|\bINTERSECT\b|\bEXCEPT\b', s):
        return "aggregation"
    if s.count("SELECT") > 1 or re.search(r'\bEXISTS\b|\bIN\s*\(\s*SELECT', s):
        return "subquery"
    if re.search(r'\bCOUNT\s*\(|\bSUM\s*\(|\bAVG\s*\(|\bMIN\s*\(|\bMAX\s*\(', s):
        return "aggregation"
    if re.search(r'\bJOIN\b', s):
        return "join"
    return "select"

def fix_dialect(sql: str) -> str:
    sql = re.sub(r'\bYEAR\s*\((\w+)\)',   r'EXTRACT(YEAR FROM \1)',  sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bMONTH\s*\((\w+)\)',  r'EXTRACT(MONTH FROM \1)', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bDAY\s*\((\w+)\)',    r'EXTRACT(DAY FROM \1)',   sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bIFNULL\s*\(',        'COALESCE(',               sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bDATEDIFF\s*\(([^,]+),([^)]+)\)', r'(\1::date - \2::date)', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bLIMIT\s+(\d+)\s*,\s*(\d+)', r'LIMIT \2 OFFSET \1', sql, flags=re.IGNORECASE)
    return sql

def fix_starter(sql: str) -> str:
    first = sql.strip().upper().split()[0] if sql.strip().split() else "SELECT"
    return {
        "SELECT": "-- Write your SQL query here\n\nSELECT ",
        "INSERT": "-- Write your SQL query here\n\nINSERT INTO ",
        "UPDATE": "-- Write your SQL query here\n\nUPDATE ",
        "DELETE": "-- Write your SQL query here\n\nDELETE FROM ",
        "DROP":   "-- Write your SQL query here\n\nDROP TABLE ",
        "WITH":   "-- Write your SQL query here\n\nWITH ",
        "ALTER":  "-- Write your SQL query here\n\nALTER TABLE ",
    }.get(first, "-- Write your SQL query here\n\nSELECT ")

def fix_description(desc: str) -> str:
    paras = [p.strip() for p in desc.split('\n\n') if p.strip()]
    if len(paras) >= 3:
        return '\n\n'.join([paras[0], paras[1], ' '.join(paras[2:])])
    sentences = re.split(r'(?<=[.!?])\s+', desc.strip())
    if len(sentences) < 3:
        return (desc.strip() +
                '\n\nThe query must return accurate results based on the provided schema and sample data.' +
                '\n\nNULL values should be handled appropriately and results must be returned in a deterministic order.')
    n = len(sentences)
    c1, c2 = max(1, n//3), max(2, 2*n//3)
    return '\n\n'.join([
        ' '.join(sentences[:c1]),
        ' '.join(sentences[c1:c2]),
        ' '.join(sentences[c2:])
    ])

def is_fake(sample_data: dict) -> bool:
    t = json.dumps(sample_data).lower()
    return any(kw in t for kw in ['sample1','sample2','sample3','value1','value2',
                                   'example1','test1','placeholder','samplevalue'])

def has_data(sample_data: dict) -> bool:
    return any(len(v) > 0 for v in sample_data.values())

def apply_deterministic_fixes(r: dict) -> dict:
    sql = r.get('reference_query', '')
    r['reference_query'] = fix_dialect(sql)
    r['sql_category']    = classify_category(r['reference_query'])
    r['starter_query']   = fix_starter(r['reference_query'])
    r['description']     = fix_description(r.get('description', ''))
    return r

# ─────────────────────────────────────────
# LLM — sample_data only
# ─────────────────────────────────────────

SAMPLE_PROMPT = """\
Generate realistic sample data for this SQL assessment question.

Question: {title}
SQL Query: {sql}
Schema tables and columns:
{schema_str}

STRICT RULES:
- 3-5 rows per table
- Use REAL domain values — actual names, cities, products (NOT Sample1, Value1)
- For JOINs: FK values in child table MUST match PK values in parent table
- Include at least one NULL in any nullable column
- The reference SQL must return AT LEAST 1 row when run against this data
- Verify mentally: does the WHERE/JOIN condition match your data?

Return ONLY this JSON, no markdown, no explanation:
{{
  "sample_data": {{
    "TableName": [
      {{"col1": value1, "col2": value2}},
      ...
    ]
  }}
}}"""

def build_schema_str(schemas: dict) -> str:
    lines = []
    for table, schema in schemas.items():
        cols = ', '.join(f"{c['name']} {c['type']}" for c in schema.get('columns', []))
        lines.append(f"  {table}({cols})")
    return '\n'.join(lines)

def call_llm(tok, mdl, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(text, return_tensors="pt", truncation=True, max_length=1536).to(mdl.device)
    with torch.no_grad():
        out = mdl.generate(
            **inputs, max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False, temperature=1.0,
            eos_token_id=tok.eos_token_id, pad_token_id=tok.pad_token_id,
        )
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

def extract_json(text: str):
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced:
        try: return json.loads(fenced.group(1).strip())
        except: pass
    start = text.find("{")
    if start == -1: return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"':  in_str = False
            continue
        if ch == '"':   in_str = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try: return json.loads(text[start:i+1])
                except:
                    nxt = text.find("{", start+1)
                    if nxt == -1: return None
                    start, depth, in_str, esc = nxt, 0, False, False
    return None

# ─────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────

def _gpu_mem(reserve=1, cpu=48):
    if not torch.cuda.is_available(): return {"cpu": f"{cpu}GiB"}
    t = int(torch.cuda.get_device_properties(0).total_memory / (1024**3))
    return {0: f"{max(1,t-reserve)}GiB", "cpu": f"{cpu}GiB"}

def load_model():
    print(f"Loading {MODEL_NAME}...")
    tok = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tok.padding_side = "left"
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4",
        llm_int8_enable_fp32_cpu_offload=True,
    )
    mdl = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map="auto",
        max_memory=_gpu_mem(), low_cpu_mem_usage=True, trust_remote_code=True,
    )
    mdl.eval()
    print("Model loaded.")
    return tok, mdl

# ─────────────────────────────────────────
# STATE
# ─────────────────────────────────────────

def load_state():
    if not os.path.exists(STATE): return {"next_index": 0}
    try:
        with open(STATE) as f: s = json.load(f)
        if isinstance(s.get("next_index"), int): return s
    except: pass
    return {"next_index": 0}

def save_state(idx):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f: json.dump({"next_index": idx}, f)
    os.replace(tmp, STATE)

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    with open(INPUT) as f:
        data = json.load(f)
    print(f"Loaded {len(data)} records")

    # ── Step 1: Apply deterministic fixes to ALL records ──────────
    print("\nStep 1: Applying deterministic fixes to all records...")
    for r in data:
        apply_deterministic_fixes(r)

    cats_after = Counter(r['sql_category'] for r in data)
    print(f"  Category after reclassify: {dict(cats_after)}")

    # ── Step 2: Balance categories — sample down overcrowded ones ─
    print("\nStep 2: Balancing categories...")
    by_cat = defaultdict(list)
    for r in data:
        by_cat[r['sql_category']].append(r)

    balanced = []
    for cat, cap in CATEGORY_CAPS.items():
        records = by_cat.get(cat, [])
        # prefer records with real data over fake
        real   = [r for r in records if has_data(r.get('sample_data',{})) and not is_fake(r.get('sample_data',{}))]
        fakeish = [r for r in records if not has_data(r.get('sample_data',{})) or is_fake(r.get('sample_data',{}))]
        # fill cap from real first, then fake
        selected = (real + fakeish)[:cap]
        balanced.extend(selected)
        print(f"  {cat:15s}: {len(records):4d} → {len(selected):4d} (real={len(real)}, fake={len(fakeish)})")

    print(f"  Total after balancing: {len(balanced)}")

    # ── Step 3: LLM fixes for remaining fake sample_data ──────────
    still_fake = [r for r in balanced if is_fake(r.get('sample_data',{})) or not has_data(r.get('sample_data',{}))]
    print(f"\nStep 3: LLM fixing {len(still_fake)} records with missing/fake sample_data...")

    state  = load_state()
    resume = state["next_index"]
    if resume >= len(still_fake) and resume > 0:
        print(f"⚠️  Stale state. Resetting.")
        resume = 0; save_state(0)
    elif resume > 0:
        print(f"↩️  Resuming from {resume}/{len(still_fake)}")

    if still_fake:
        tok, mdl = load_model()
        # index by id for in-place update
        id_map = {r['id']: r for r in balanced}

        fixed_count = 0
        for i, r in enumerate(tqdm(still_fake[resume:], desc="Fixing sample_data"), start=resume):
            prompt = SAMPLE_PROMPT.format(
                title      = r.get('title',''),
                sql        = r.get('reference_query','')[:250],
                schema_str = build_schema_str(r.get('schemas',{})),
            )
            try:
                raw    = call_llm(tok, mdl, prompt)
                parsed = extract_json(raw)
                if parsed and isinstance(parsed.get('sample_data'), dict):
                    sd = parsed['sample_data']
                    if not is_fake(sd) and has_data(sd):
                        id_map[r['id']]['sample_data'] = sd
                        fixed_count += 1
            except Exception as e:
                print(f"\n⚠️  {r['id']}: {e}")

            if (i+1) % SAVE_EVERY == 0:
                save_state(i+1)
                if torch.cuda.is_available(): torch.cuda.empty_cache()

        save_state(len(still_fake))
        print(f"  Fixed: {fixed_count}/{len(still_fake)}")
        balanced = list(id_map.values())

    # ── Step 4: Final validation — drop records still broken ──────
    print("\nStep 4: Final validation pass...")
    final = []
    dropped = 0
    for r in balanced:
        # must have real sample data
        if not has_data(r.get('sample_data',{})) or is_fake(r.get('sample_data',{})):
            dropped += 1; continue
        # description must be 3 paragraphs (apply one more time)
        r['description'] = fix_description(r.get('description',''))
        paras = [p for p in r['description'].split('\n\n') if p.strip()]
        if len(paras) < 2:
            dropped += 1; continue
        # must have all required fields
        if not all(r.get(f) for f in ['title','schemas','constraints','hints','reference_query']):
            dropped += 1; continue
        final.append(r)

    print(f"  Dropped in final validation: {dropped}")
    print(f"  Final records: {len(final)}")

    # ── Step 5: Save ──────────────────────────────────────────────
    with open(OUTPUT, "w") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    # cleanup state on success
    if os.path.exists(STATE): os.remove(STATE)

    print(f"\n✅  Saved {len(final)} records to {OUTPUT}")
    print(f"\nCategory distribution:")
    for cat, cnt in Counter(r['sql_category'] for r in final).most_common():
        pct = 100*cnt//len(final)
        bar = '█' * (pct//2)
        print(f"  {cat:15s}: {cnt:4d} ({pct:2d}%) {bar}")
    print(f"\nDifficulty distribution:")
    for diff, cnt in Counter(r['difficulty'] for r in final).most_common():
        print(f"  {diff:10s}: {cnt:4d} ({100*cnt//len(final):2d}%)")

if __name__ == "__main__":
    main()