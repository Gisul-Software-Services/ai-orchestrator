"""
Script to fetch datasets from HuggingFace and generate new AIML catalog entries
in the same format as aiml_dataset_catalog.json.

Usage:
    python build_aiml_catalog_from_hf.py

Output:
    assets/aiml-data/new_catalog_entries.json  — review and merge into aiml_dataset_catalog.json
"""

import json
import time
import requests

HF_API = "https://huggingface.co/api/datasets"
OUTPUT_PATH = "assets/aiml-data/new_catalog_entries.json"

# ── Topics to search for ──────────────────────────────────────────────────────
# Add/remove topics as needed. Each entry: (search_query, tags, domain, category, target_type, difficulty)
SEARCH_TOPICS = [
    # (query, required_tags, domain, category, target_type, difficulty_list)
    ("customer churn telecom",          ["churn", "classification", "binary"],      "Business",     "tabular", "binary",     ["Medium", "Hard"]),
    ("credit card fraud detection",     ["fraud", "classification", "imbalanced"],  "Finance",      "tabular", "binary",     ["Hard"]),
    ("house price prediction",          ["regression", "real-estate"],              "Real Estate",  "tabular", "regression", ["Medium"]),
    ("sentiment analysis movie review", ["nlp", "sentiment", "text"],               "NLP",          "text",    "binary",     ["Medium", "Hard"]),
    ("image classification cifar",      ["cv", "image", "classification"],          "Computer Vision", "image", "multiclass", ["Hard"]),
    ("diabetes prediction health",      ["diabetes", "healthcare", "binary"],       "Healthcare",   "tabular", "binary",     ["Easy", "Medium"]),
    ("stock price forecasting",         ["time-series", "finance", "regression"],   "Finance",      "tabular", "regression", ["Hard"]),
    ("spam email classification",       ["nlp", "spam", "text"],                    "NLP",          "text",    "binary",     ["Easy", "Medium"]),
    ("wine quality classification",     ["classification", "food", "multiclass"],   "Food Science", "tabular", "multiclass", ["Medium"]),
    ("air quality prediction",          ["time-series", "environment"],             "Environment",  "tabular", "regression", ["Medium", "Hard"]),
]


def search_hf_datasets(query: str, limit: int = 5) -> list:
    """Search HuggingFace datasets API."""
    try:
        resp = requests.get(
            HF_API,
            params={"search": query, "limit": limit, "full": "true"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [WARN] HF search failed for '{query}': {e}")
        return []


def fetch_dataset_info(dataset_id: str) -> dict:
    """Fetch detailed info for a specific dataset."""
    try:
        resp = requests.get(f"{HF_API}/{dataset_id}", timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [WARN] HF fetch failed for '{dataset_id}': {e}")
        return {}


def build_catalog_entry(ds: dict, info: dict, tags: list, domain: str,
                         category: str, target_type: str, difficulty: list) -> dict | None:
    """Build a catalog entry from HF dataset metadata."""
    ds_id = ds.get("id", "")
    if not ds_id:
        return None

    name = ds.get("id", "").replace("-", " ").replace("_", " ").title()
    description = (
        info.get("cardData", {}).get("description", "")
        or ds.get("description", "")
        or f"A {category} dataset for {domain.lower()} tasks."
    )[:500]

    # Build load_code based on source
    load_code = (
        f'from datasets import load_dataset\n'
        f'import pandas as pd\n\n'
        f'dataset = load_dataset("{ds_id}", split="train")\n'
        f'df = dataset.to_pandas()\n'
        f'print(df.shape)\n'
        f'print(df.head())'
    )

    # Try to get features from card data
    card_data = info.get("cardData", {})
    features_info = ""
    if "dataset_info" in card_data:
        di = card_data["dataset_info"]
        if isinstance(di, dict) and "features" in di:
            feat_names = [f.get("name", "") for f in di["features"][:10] if isinstance(f, dict)]
            features_info = f"Features: {', '.join(feat_names)}"
    if not features_info:
        features_info = f"See dataset card for full feature list"

    # Infer target from common patterns
    target_map = {
        "binary": "label",
        "multiclass": "label",
        "regression": "target",
    }
    target = target_map.get(target_type, "label")

    # Build tags combining provided + HF tags
    hf_tags = [t.lower().replace(" ", "-") for t in (ds.get("tags") or [])[:8]]
    all_tags = list(set(tags + hf_tags))[:10]

    entry = {
        "id": f"hf-{ds_id.replace('/', '-').lower()}",
        "name": name,
        "source": "huggingface",
        "category": category,
        "pip_install": "pip install datasets pandas",
        "import_code": "from datasets import load_dataset\nimport pandas as pd",
        "load_code": load_code,
        "description": description,
        "use_case": f"{domain} - {target_type} task using {name}",
        "features_info": features_info,
        "target": target,
        "target_type": target_type,
        "size": f"~{ds.get('downloads', 0):,} downloads",
        "tags": all_tags,
        "domain": domain,
        "difficulty": difficulty,
        "direct_load": True,
    }
    return entry


def main():
    print("Building AIML catalog from HuggingFace...\n")
    new_entries = []
    seen_ids = set()

    for query, tags, domain, category, target_type, difficulty in SEARCH_TOPICS:
        print(f"Searching: '{query}'")
        results = search_hf_datasets(query, limit=3)

        for ds in results:
            ds_id = ds.get("id", "")
            if not ds_id or ds_id in seen_ids:
                continue

            print(f"  Fetching info for: {ds_id}")
            info = fetch_dataset_info(ds_id)
            time.sleep(0.5)  # be polite to HF API

            entry = build_catalog_entry(ds, info, tags, domain, category, target_type, difficulty)
            if entry:
                new_entries.append(entry)
                seen_ids.add(ds_id)
                print(f"  ✅ Added: {entry['name']} ({entry['id']})")

        time.sleep(1)

    print(f"\nTotal new entries: {len(new_entries)}")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(new_entries, f, indent=2, ensure_ascii=False)
    print(f"Saved to: {OUTPUT_PATH}")
    print("\nReview the file, then merge into assets/aiml-data/aiml_dataset_catalog.json")


if __name__ == "__main__":
    main()
