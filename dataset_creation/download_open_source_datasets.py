#!/usr/bin/env python3
"""
Step 1: Download open-source SQL datasets for schema library building.

Sources:
  1. Spider (Yale) - 200 databases, 138 domains, via HuggingFace
  2. gretelai/synthetic_text_to_sql - extended pull (all categories)

Output:
  spider_raw/          - Spider databases (tables.json + db folders)
  gretelai_extended.parquet - Full gretelai dataset cached locally

Usage:
  pip install datasets huggingface_hub pandas pyarrow
  python download_open_source_datasets.py

NOTE: This script is OFFLINE only. It does NOT touch any running service.
"""

import json
import os
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Check dependencies
# ─────────────────────────────────────────────────────────────

def check_deps():
    missing = []
    for pkg in ["datasets", "pandas", "pyarrow", "huggingface_hub"]:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)

check_deps()

import pandas as pd
from datasets import load_dataset
from huggingface_hub import hf_hub_download

BASE_DIR = Path(__file__).parent
SPIDER_DIR = BASE_DIR / "spider_raw"
GRETELAI_CACHE = BASE_DIR / "gretelai_extended.parquet"

# ─────────────────────────────────────────────────────────────
# Download Spider dataset
# ─────────────────────────────────────────────────────────────

def download_spider():
    """
    Download Spider dataset from HuggingFace.
    Spider has 200 databases across 138 domains.
    Each database has: tables.json (schema) + SQLite db file.
    """
    print("\n" + "=" * 60)
    print("Downloading Spider dataset (Yale, 200 databases)")
    print("=" * 60)

    SPIDER_DIR.mkdir(exist_ok=True)

    tables_file = SPIDER_DIR / "tables.json"
    train_file = SPIDER_DIR / "train_spider.json"

    if tables_file.exists() and train_file.exists():
        print(f"  ✓ Spider already downloaded at {SPIDER_DIR}")
        with open(tables_file) as f:
            tables = json.load(f)
        print(f"  ✓ {len(tables)} databases found")
        return tables

    try:
        print("  Downloading via HuggingFace datasets (xlangai/spider)...")
        dataset = load_dataset("xlangai/spider", trust_remote_code=True)

        # Save train split
        train_data = list(dataset["train"])
        with open(train_file, "w") as f:
            json.dump(train_data, f, indent=2)
        print(f"  ✓ Saved {len(train_data)} train Q&A pairs")

        # Save validation split
        val_data = list(dataset["validation"])
        val_file = SPIDER_DIR / "dev.json"
        with open(val_file, "w") as f:
            json.dump(val_data, f, indent=2)
        print(f"  ✓ Saved {len(val_data)} validation Q&A pairs")

        # Extract unique db_ids and schemas from the dataset
        # Spider HF version includes db_id and query fields
        db_schemas = {}
        for item in train_data + val_data:
            db_id = item.get("db_id", "")
            if db_id and db_id not in db_schemas:
                db_schemas[db_id] = {
                    "db_id": db_id,
                    "questions": []
                }
            if db_id:
                db_schemas[db_id]["questions"].append({
                    "question": item.get("question", ""),
                    "query": item.get("query", "")
                })

        # Save db summary
        db_summary_file = SPIDER_DIR / "db_summary.json"
        with open(db_summary_file, "w") as f:
            json.dump(list(db_schemas.values()), f, indent=2)
        print(f"  ✓ Found {len(db_schemas)} unique databases")

        # Try to get tables.json from HuggingFace hub
        try:
            tables_path = hf_hub_download(
                repo_id="xlangai/spider",
                filename="tables.json",
                repo_type="dataset"
            )
            import shutil
            shutil.copy(tables_path, tables_file)
            with open(tables_file) as f:
                tables = json.load(f)
            print(f"  ✓ Downloaded tables.json with {len(tables)} database schemas")
            return tables
        except Exception as e:
            print(f"  ⚠ Could not download tables.json: {e}")
            print("  ℹ Using db_summary.json instead")
            return list(db_schemas.values())

    except Exception as e:
        print(f"  ✗ Spider download failed: {e}")
        print("  ℹ Continuing without Spider (gretelai will be used)")
        return []


# ─────────────────────────────────────────────────────────────
# Download gretelai extended
# ─────────────────────────────────────────────────────────────

def download_gretelai_extended():
    """
    Download full gretelai/synthetic_text_to_sql dataset.
    105k rows covering all SQL complexity levels.
    Already have 2k in catalog — this gets the rest.
    """
    print("\n" + "=" * 60)
    print("Downloading gretelai/synthetic_text_to_sql (full)")
    print("=" * 60)

    if GRETELAI_CACHE.exists():
        df = pd.read_parquet(GRETELAI_CACHE)
        print(f"  ✓ Already cached: {len(df):,} rows at {GRETELAI_CACHE}")
        print(f"  Distribution: {df['sql_complexity'].value_counts().to_dict()}")
        return df

    try:
        print("  Downloading from HuggingFace (this may take a few minutes)...")
        dataset = load_dataset(
            "gretelai/synthetic_text_to_sql",
            split="train",
            trust_remote_code=True
        )
        df = dataset.to_pandas()
        df.to_parquet(GRETELAI_CACHE, index=False)
        print(f"  ✓ Downloaded {len(df):,} rows")
        print(f"  Distribution: {df['sql_complexity'].value_counts().to_dict()}")
        return df

    except Exception as e:
        print(f"  ✗ gretelai download failed: {e}")
        # Try loading existing local cache
        existing = BASE_DIR / "gretel_sql_cache.parquet"
        if existing.exists():
            df = pd.read_parquet(existing)
            print(f"  ✓ Using existing cache: {len(df):,} rows")
            return df
        return None


# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────

def print_summary(spider_tables, gretelai_df):
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    if spider_tables:
        print(f"  Spider databases: {len(spider_tables)}")
    else:
        print("  Spider databases: 0 (skipped)")

    if gretelai_df is not None:
        print(f"  gretelai rows: {len(gretelai_df):,}")
        complexities = gretelai_df["sql_complexity"].value_counts().to_dict()
        for k, v in sorted(complexities.items()):
            print(f"    {k:25s}: {v:,}")
    else:
        print("  gretelai rows: 0 (failed)")

    print("\n  Next step: python build_sql_schemas_library.py")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("SQL Open Source Dataset Downloader")
    print("Safe: Does NOT touch any running service")
    print("=" * 60)

    spider_tables = download_spider()
    gretelai_df = download_gretelai_extended()
    print_summary(spider_tables, gretelai_df)
