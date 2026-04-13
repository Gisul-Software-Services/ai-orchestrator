import logging
import random
import re

import numpy as np


logger = logging.getLogger(__name__)


def _parse_feature_range(type_str: str):
    """
    Parse range from type strings like:
      'numerical (continuous, range: 20 to 150)'
      'numerical (continuous, range: 50 to 500 GB)'
      'numerical (continuous, range: 10 Mbps to 1000 Mbps)'
      'numerical (integer, range: 1 to 60 months)'
    Units after numbers are stripped automatically.
    """
    # Allow optional unit words (GB, Mbps, minutes, months, etc.) after numbers
    match = re.search(
        r'range[:\s]+([0-9\.\-\$k%]+)\s*[a-zA-Z/]*\s+to\s+([0-9\.\-\$k%]+)',
        type_str, re.IGNORECASE
    )
    if not match:
        return None, None
    def _clean(v):
        v = v.strip().replace('$', '').replace('%', '').replace(',', '')
        if v.lower().endswith('k'):
            return float(v[:-1]) * 1000
        return float(v)
    try:
        return _clean(match.group(1)), _clean(match.group(2))
    except:
        return None, None

def _parse_categorical_values(type_str: str):
    """Parse values from 'categorical (values: A, B, C)'"""
    match = re.search(r'values[:\s]+(.+?)(?:\)|\Z)', type_str, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1)
    values = [v.strip().strip('"\'') for v in raw.split(',') if v.strip()]
    return values if values else None

def generate_aiml_dataset(schema: dict, num_rows: int = 150) -> list:
    """
    Generate realistic dataset rows from a schema dict.
    Returns list of dicts (one per row), with target column included.
    """
    features = schema.get("features", [])
    feature_types = schema.get("feature_types", {})
    target = schema.get("target", "target")
    target_type_str = schema.get("target_type", "binary (0: no, 1: yes)")
    class_dist = schema.get("class_distribution", {})

    rng = np.random.default_rng(seed=42)

    is_binary = "binary" in target_type_str.lower()
    is_continuous = "continuous" in target_type_str.lower() or "regression" in target_type_str.lower()
    is_multiclass = "multiclass" in target_type_str.lower() or "multi-class" in target_type_str.lower()

    if is_continuous:
        t_min, t_max = _parse_feature_range(target_type_str)
        if t_min is None:
            t_min, t_max = 0.0, 100.0
        target_values = rng.uniform(t_min, t_max, num_rows).round(2).tolist()
    elif is_multiclass:
        match = re.search(r'classes[:\s]+(.+?)(?:\)|\Z)', target_type_str, re.IGNORECASE)
        if match:
            classes = [c.strip() for c in match.group(1).split(',')]
        else:
            classes = list(class_dist.keys()) if class_dist else ["A", "B", "C"]
        if class_dist:
            total_pct = sum(class_dist.values())
            counts = {c: max(1, int(num_rows * v / total_pct)) for c, v in class_dist.items()}
        else:
            per_class = num_rows // len(classes)
            counts = {c: per_class for c in classes}
        target_list = []
        for cls, cnt in counts.items():
            target_list.extend([cls] * cnt)
        while len(target_list) < num_rows:
            target_list.append(classes[0])
        target_values = target_list[:num_rows]
        rng.shuffle(target_values)
    else:
        # Binary
        label_match = re.search(r'0[:\s]+(\w+).*?1[:\s]+(\w+)', target_type_str)
        label0 = label_match.group(1) if label_match else "0"
        label1 = label_match.group(2) if label_match else "1"
        keys = list(class_dist.keys())
        vals = list(class_dist.values())
        if len(vals) >= 2:
            total = sum(vals)
            n_class1 = max(1, int(num_rows * vals[-1] / total))
        else:
            n_class1 = num_rows // 4
        n_class0 = num_rows - n_class1
        target_values = [0] * n_class0 + [1] * n_class1
        rng.shuffle(target_values)

    rows = []
    for row_idx in range(num_rows):
        row = {}
        target_val = target_values[row_idx]
        is_minority_row = (target_val == 1) if is_binary else False

        for feat in features:
            type_str = feature_types.get(feat, "numerical (continuous, range: 0 to 100)")
            type_lower = type_str.lower()

            if "categorical" in type_lower:
                cats = _parse_categorical_values(type_str)
                if not cats:
                    cats = ["A", "B", "C"]
                if is_minority_row and len(cats) >= 2:
                    weights = [0.3] + [0.7 / (len(cats) - 1)] * (len(cats) - 1)
                    row[feat] = str(rng.choice(cats, p=weights))
                else:
                    row[feat] = str(rng.choice(cats))
            elif "integer" in type_lower:
                lo, hi = _parse_feature_range(type_str)
                if lo is None:
                    lo, hi = 0, 10
                lo, hi = int(lo), int(hi)
                if is_minority_row:
                    val = int(rng.integers(max(lo, int((lo + hi) * 0.5)), hi + 1))
                else:
                    val = int(rng.integers(lo, hi + 1))
                row[feat] = val
            else:
                lo, hi = _parse_feature_range(type_str)
                if lo is None:
                    lo, hi = 0.0, 100.0
                base = rng.uniform(lo, hi)
                noise = rng.normal(0, (hi - lo) * 0.03)
                val = float(np.clip(base + noise, lo, hi))
                row[feat] = round(val, 2)

        row[target] = target_val
        rows.append(row)

    logger.info(f"Generated {len(rows)} dataset rows for {len(features)} features")
    return rows


# ============================================================================
# AIML VALIDATION (unchanged)
# ============================================================================

def validate_aiml_response(obj: dict) -> None:
    """
    Structural validation — checks dataset schema integrity.
    """
    if "dataset" not in obj:
        return

    dataset  = obj["dataset"]
    target   = dataset.get("target")
    features = dataset.get("features", [])

    if not target:
        raise ValueError("Target variable not specified")
    if not features:
        raise ValueError("Features list is empty")
    if target in features:
        raise ValueError(f"DATA LEAKAGE: Target '{target}' in features list")

    if "data" not in dataset or not dataset["data"]:
        logger.info("AIML validation: no data array (Pass 2 will generate rows) — schema checks passed")
        return

    data_rows = dataset["data"]
    if not isinstance(data_rows, list) or len(data_rows) == 0:
        logger.warning("Dataset data array is empty — Pass 2 will fill it")
        return

    first_row = data_rows[0]
    if not isinstance(first_row, dict):
        raise ValueError("First data row is not a dict")
    if target in first_row:
        raise ValueError(f"DATA LEAKAGE: Target '{target}' in data rows")

    expected_features = set(features)
    actual_features   = set(first_row.keys())
    if expected_features != actual_features:
        missing = expected_features - actual_features
        extra   = actual_features   - expected_features
        logger.warning(
            f"Feature mismatch — missing: {missing}, extra: {extra} — "
            f"reconciling features list to match actual data columns"
        )
        dataset["features"] = list(actual_features)
        features = dataset["features"]

    last_row = data_rows[-1]
    if not isinstance(last_row, dict) or len(last_row) == 0:
        raise ValueError("Last data row is empty — likely truncated JSON")
    if len(last_row) < len(features):
        raise ValueError(f"Last row incomplete: {len(last_row)} fields, expected {len(features)}")

    logger.info(f"AIML validation PASSED: {len(data_rows)} rows, {len(features)} features")


def validate_and_fix_aiml_response(obj: dict) -> dict:
    """
    Auto-fix layer — removes target from features if leaked, then validates.
    """
    if "dataset" not in obj:
        return obj

    dataset  = obj["dataset"]
    target   = dataset.get("target")
    features = dataset.get("features", [])

    if target and target in features:
        logger.warning(f"AUTO-FIX: Removing '{target}' from features")
        dataset["features"] = [f for f in features if f != target]

    if target and "data" in dataset:
        for row in dataset["data"]:
            if isinstance(row, dict) and target in row:
                del row[target]

    validate_aiml_response(obj)
    return obj


def validate_aiml_output(
    result: dict,
    topic: str,
    concepts: list,
    difficulty: str,
    matched_dataset: dict | None = None,
) -> tuple:
    """
    Semantic validation layer — runs AFTER LLM generation.

    Checks:
      1. Problem statement is non-trivial and exists
      2. Tasks reference actual feature names (not generic placeholders)
      3. Difficulty field matches what was requested — auto-corrects if not
      4. No generic feature names (feature_0, feature_1, ...) leaked through
      5. evaluationCriteria match target_type — auto-corrects if not
      6. Concepts are reflected in at least one task
      7. If library dataset was matched, problem domain is consistent

    Returns (is_valid: bool, issues: list[str])
    """

import json
import logging
import os

import numpy as np

from backend.model_app.services import dsa as _dsa_retrieval


logger = logging.getLogger(__name__)


def _aiml_catalog_path() -> str:
    from backend.model_app.core.settings import get_settings

    return str(get_settings().aiml_catalog_path)


def _aiml_faiss_path() -> str:
    from backend.model_app.core.settings import get_settings

    return str(get_settings().aiml_faiss_path)


def _aiml_metadata_path() -> str:
    from backend.model_app.core.settings import get_settings

    return str(get_settings().aiml_metadata_path)

_aiml_catalog_cache  = None
_aiml_faiss_index    = None
_aiml_meta_cache     = None
_aiml_embed_model    = None


def _load_aiml_catalog() -> list:
    global _aiml_catalog_cache
    if _aiml_catalog_cache is None:
        p = _aiml_catalog_path()
        if not os.path.exists(p):
            logger.warning(f"AIML catalog not found at {p}")
            return []
        with open(p, encoding="utf-8") as f:
            _aiml_catalog_cache = json.load(f)
        logger.info(f"Loaded {len(_aiml_catalog_cache)} datasets from AIML catalog")
    return _aiml_catalog_cache


def _load_aiml_faiss() -> bool:
    """
    Loads AIML FAISS index + metadata + embedding model.
    Returns True if successful, False if index not available.
    Falls back to keyword matching when False.
    """
    global _aiml_faiss_index, _aiml_meta_cache, _aiml_embed_model
    if _aiml_faiss_index is not None:
        return True
    if not os.path.exists(_aiml_faiss_path()):
        logger.warning("AIML FAISS index not found — falling back to keyword matching")
        return False
    try:
        import faiss as _faiss
        from sentence_transformers import SentenceTransformer as _ST
        logger.info("Loading AIML FAISS index...")
        _aiml_faiss_index = _faiss.read_index(_aiml_faiss_path())
        with open(_aiml_metadata_path(), encoding="utf-8") as f:
            _aiml_meta_cache = json.load(f)
        # Reuse DSA embed model if already loaded — same model
        if _dsa_retrieval._dsa_embed_model is not None:
            _aiml_embed_model = _dsa_retrieval._dsa_embed_model
        else:
            logger.info("Loading AIML embedding model...")
            _aiml_embed_model = _ST("all-MiniLM-L6-v2")
        logger.info(f"AIML FAISS ready: {_aiml_faiss_index.ntotal} vectors")
        return True
    except Exception as e:
        logger.warning(f"AIML FAISS load failed: {e} — falling back to keyword matching")
        return False



# ============================================================================
# AIML DATASET REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
# Maps topic-signal keywords → required catalog tags.
# When a topic matches an entry here, the returned dataset MUST contain ALL
# of the listed required_tags in its own tags list.  If no catalog entry
# satisfies both the semantic/keyword score AND these required tags, the
# system falls back to synthetic generation rather than returning a wrong
# dataset.
#
# This is the single source of truth that prevents FAISS from drifting:
#   "flower classification" → beans (plant), NOT fashion-mnist (retail)
#   "iris"                 → sklearn-iris, NOT penguins
#   "customer churn"       → churn dataset, NOT generic binary classification
#
# RULES FOR EDITING:
#   - topic_signals: lowercase substrings that trigger this entry
#   - required_tags: ALL must appear in the matched dataset's tags
#   - preferred_ids: catalog IDs checked first before any search (exact match)
#   - forbidden_ids: catalog IDs that must NEVER be returned for this topic
# ============================================================================

_AIML_DATASET_REGISTRY: list = [
    # ── Classification — specific named datasets ──────────────────────────
    {
        "topic_signals": ["iris", "iris flower", "iris classification"],
        "required_tags": ["flowers"],
        "preferred_ids": ["sklearn-iris"],
        "forbidden_ids": ["seaborn-penguins", "hf-beans"],
    },
    {
        "topic_signals": ["penguin", "palmer penguin"],
        "required_tags": ["biology"],
        "preferred_ids": ["seaborn-penguins"],
        "forbidden_ids": ["sklearn-iris"],
    },
    {
        "topic_signals": ["titanic", "titanic survival", "passenger survival"],
        "required_tags": ["titanic"],
        "preferred_ids": ["seaborn-titanic", "openml-titanic", "openml-titanic-survival"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["mnist", "handwritten digit", "digit recognition", "handwriting recognition"],
        "required_tags": ["digits"],
        "preferred_ids": ["keras-mnist", "openml-mnist-784", "sklearn-digits"],
        "forbidden_ids": ["keras-fashion-mnist"],
    },
    {
        "topic_signals": ["fashion mnist", "clothing classification", "apparel classification", "fashion product"],
        "required_tags": ["fashion"],
        "preferred_ids": ["keras-fashion-mnist"],
        "forbidden_ids": ["keras-mnist"],
    },
    {
        "topic_signals": ["cifar", "cifar-10", "cifar10", "object recognition", "object classification"],
        "required_tags": ["object-recognition"],
        "preferred_ids": ["keras-cifar10", "hf-cifar10-hf"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["flower classification", "flower recognition", "flower detection"],
        "required_tags": ["agriculture"],
        "preferred_ids": ["hf-beans", "hf-oxford-pets"],
        "forbidden_ids": ["sklearn-iris", "keras-fashion-mnist", "keras-mnist"],
    },
    # ── Churn / Retention ─────────────────────────────────────────────────
    {
        "topic_signals": ["customer churn", "churn prediction", "churn analysis",
                          "churn detection", "user churn", "subscriber churn",
                          "retention prediction", "customer retention"],
        "required_tags": ["churn"],
        "preferred_ids": ["openml-telco-churn", "openml-bank-churn"],
        "forbidden_ids": ["sklearn-make-classification", "sklearn-make-blobs",
                          "sklearn-make-moons", "sklearn-make-circles"],
    },
    # ── HR / Attrition ────────────────────────────────────────────────────
    {
        "topic_signals": ["employee attrition", "hr attrition", "staff turnover",
                          "employee churn", "workforce attrition", "talent retention"],
        "required_tags": ["attrition"],
        "preferred_ids": ["openml-hr-attrition"],
        "forbidden_ids": ["openml-telco-churn"],
    },
    # ── Fraud / Anomaly ───────────────────────────────────────────────────
    {
        "topic_signals": ["fraud detection", "credit card fraud", "transaction fraud",
                          "payment fraud", "financial fraud"],
        "required_tags": ["fraud"],
        "preferred_ids": ["openml-fraud-detection"],
        "forbidden_ids": ["sklearn-make-classification"],
    },
    # ── Healthcare ────────────────────────────────────────────────────────
    {
        "topic_signals": ["diabetes prediction", "diabetes detection", "diabetes classification",
                          "blood sugar prediction", "glucose prediction"],
        "required_tags": ["diabetes"],
        "preferred_ids": ["openml-pima-diabetes", "sklearn-diabetes"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["heart disease", "cardiac prediction", "heart attack prediction",
                          "cardiovascular", "heart failure"],
        "required_tags": ["heart-disease"],
        "preferred_ids": ["openml-heart-disease", "statsmodels-heart"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["breast cancer", "cancer detection", "tumor classification",
                          "malignant benign", "cancer prediction"],
        "required_tags": ["cancer"],
        "preferred_ids": ["sklearn-breast-cancer"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["stroke prediction", "stroke detection", "stroke risk"],
        "required_tags": ["stroke"],
        "preferred_ids": ["openml-stroke-prediction"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["covid", "covid-19", "coronavirus", "pandemic prediction"],
        "required_tags": ["covid-19"],
        "preferred_ids": ["openml-covid-symptoms"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["obesity", "bmi prediction", "weight classification"],
        "required_tags": ["obesity"],
        "preferred_ids": ["openml-obesity-levels"],
        "forbidden_ids": [],
    },
    # ── Finance / Credit ──────────────────────────────────────────────────
    {
        "topic_signals": ["credit risk", "loan default", "credit default",
                          "credit scoring", "default prediction"],
        "required_tags": ["credit"],
        "preferred_ids": ["openml-default-credit", "openml-credit-g",
                          "openml-loan-approval", "openml-givemecredit"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["stock price", "stock prediction", "stock market",
                          "financial forecasting", "equity prediction"],
        "required_tags": ["stock"],
        "preferred_ids": ["openml-stock-sp500", "openml-bitcoin-price"],
        "forbidden_ids": [],
    },
    # ── NLP ───────────────────────────────────────────────────────────────
    {
        "topic_signals": ["sentiment analysis", "opinion mining", "review sentiment",
                          "text sentiment", "positive negative classification"],
        "required_tags": ["sentiment"],
        "preferred_ids": ["hf-imdb", "hf-sst2", "hf-yelp-review",
                          "nltk-movie-reviews", "keras-imdb"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["spam detection", "email spam", "sms spam", "spam classification"],
        "required_tags": ["spam"],
        "preferred_ids": ["hf-spam-detection"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["fake news", "misinformation detection", "news credibility"],
        "required_tags": ["fake-news"],
        "preferred_ids": ["hf-fake-news"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["named entity recognition", "ner", "entity extraction",
                          "information extraction"],
        "required_tags": ["ner"],
        "preferred_ids": ["hf-conll2003"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["text summarization", "document summarization", "abstractive summarization",
                          "extractive summarization", "news summarization"],
        "required_tags": ["summarization"],
        "preferred_ids": ["hf-pubmed-summarization", "hf-abstractive-summarization"],
        "forbidden_ids": [],
    },
    # ── CV / Image ────────────────────────────────────────────────────────
    {
        "topic_signals": ["medical image", "chest x-ray", "xray classification",
                          "pneumonia detection", "radiology"],
        "required_tags": ["medical-imaging"],
        "preferred_ids": ["hf-chest-xray", "hf-pneumonia-xray", "hf-brain-tumor-mri"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["plant disease", "crop disease", "leaf disease",
                          "plant classification", "agriculture classification"],
        "required_tags": ["agriculture"],
        "preferred_ids": ["hf-beans", "hf-plant-village"],
        "forbidden_ids": ["sklearn-iris"],
    },
    {
        "topic_signals": ["face emotion", "facial emotion", "emotion recognition",
                          "facial expression", "affect recognition"],
        "required_tags": ["emotion"],
        "preferred_ids": ["hf-emotion-face"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["traffic sign", "road sign detection", "sign recognition",
                          "autonomous driving"],
        "required_tags": ["traffic-signs"],
        "preferred_ids": ["hf-traffic-signs"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["satellite image", "remote sensing", "aerial image",
                          "land cover", "land use classification"],
        "required_tags": ["satellite"],
        "preferred_ids": ["hf-eurosat", "hf-satellite-land-use"],
        "forbidden_ids": [],
    },
    # ── Time Series ───────────────────────────────────────────────────────
    {
        "topic_signals": ["energy forecasting", "electricity forecasting",
                          "power consumption", "energy prediction"],
        "required_tags": ["energy"],
        "preferred_ids": ["openml-electricity", "hf-ett-time-series",
                          "openml-power-consumption"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["weather forecasting", "temperature prediction",
                          "climate forecasting", "meteorological prediction"],
        "required_tags": ["weather"],
        "preferred_ids": ["hf-weather-jena"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["predictive maintenance", "equipment failure",
                          "rul prediction", "remaining useful life", "iot anomaly"],
        "required_tags": ["predictive-maintenance"],
        "preferred_ids": ["openml-iot-predictive-maintenance"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["air quality", "pollution prediction", "pm2.5", "aqi prediction"],
        "required_tags": ["air-quality"],
        "preferred_ids": ["openml-air-quality", "openml-pm25-beijing"],
        "forbidden_ids": [],
    },
    # ── Recommendation / Clustering ───────────────────────────────────────
    {
        "topic_signals": ["recommendation", "movie recommendation", "collaborative filtering",
                          "rating prediction", "recommender system"],
        "required_tags": ["recommendation"],
        "preferred_ids": ["openml-movielens-100k"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["customer segmentation", "market segmentation",
                          "user clustering", "k-means clustering"],
        "required_tags": ["segmentation"],
        "preferred_ids": ["openml-mall-customers"],
        "forbidden_ids": [],
    },
    # ── Network / Security ────────────────────────────────────────────────
    {
        "topic_signals": ["network intrusion", "intrusion detection", "cybersecurity",
                          "dos attack", "network attack detection"],
        "required_tags": ["network-intrusion"],
        "preferred_ids": ["openml-nsl-kdd"],
        "forbidden_ids": [],
    },
    # ── Housing / Real Estate ─────────────────────────────────────────────
    {
        "topic_signals": ["house price", "housing price", "real estate prediction",
                          "property price", "home price"],
        "required_tags": ["real-estate"],
        "preferred_ids": ["sklearn-california-housing"],
        "forbidden_ids": [],
    },
    # ── Supply Chain / Logistics ──────────────────────────────────────────
    {
        "topic_signals": ["supply chain", "delivery prediction", "logistics",
                          "shipping delay", "on-time delivery"],
        "required_tags": ["supply-chain"],
        "preferred_ids": ["openml-ecommerce-shipping"],
        "forbidden_ids": [],
    },
]

# ── Concept → expected tag mapping ───────────────────────────────────────────
# If a concept keyword is present in the request, the matched dataset's tags
# should contain at least one of the allowed_tags.  This prevents concept drift:
# e.g. concept="time series forecasting" should not match a tabular classifier.
_CONCEPT_TAG_MAP: dict = {
    "time series":        ["time-series", "forecasting", "arima", "lstm", "temporal"],
    "forecasting":        ["time-series", "forecasting", "regression"],
    "nlp":                ["nlp", "text", "sentiment", "bert", "language"],
    "text classification": ["nlp", "text", "classification"],
    "image classification": ["cv", "image", "cnn", "vision"],
    "computer vision":    ["cv", "image", "cnn", "vision"],
    "deep learning":      ["deep-learning", "cnn", "lstm", "transformer", "bert"],
    "transfer learning":  ["transfer-learning", "cnn", "resnet"],
    "clustering":         ["clustering", "unsupervised", "segmentation", "kmeans"],
    "anomaly detection":  ["anomaly-detection", "fraud", "intrusion", "outlier"],
    "recommendation":     ["recommendation", "collaborative-filtering", "ratings"],
    "graph":              ["graph", "gnn", "node-classification"],
    "regression":         ["regression", "continuous"],
    "classification":     ["classification", "binary", "multiclass"],
    "imbalanced":         ["imbalanced"],
    "fraud":              ["fraud", "anomaly-detection"],
    "churn":              ["churn"],
    "sentiment":          ["sentiment", "nlp"],
    "speech":             ["speech", "audio", "asr"],
    "audio":              ["audio", "speech", "mfcc"],
}


def _registry_lookup(topic: str, concepts: list, catalog: list) -> dict | None:
    """
    Check the registry for an exact topic signal match.
    Returns the best preferred_id dataset from the catalog if found,
    or the first catalog entry that satisfies required_tags.
    Returns None if topic does not match any registry entry.
    """
    topic_lower = topic.lower()
    all_text    = topic_lower + " " + " ".join(c.lower() for c in concepts)

    for entry in _AIML_DATASET_REGISTRY:
        # Check if any signal matches
        matched_signal = any(sig in all_text for sig in entry["topic_signals"])
        if not matched_signal:
            continue

        required_tags = set(entry.get("required_tags", []))
        forbidden_ids = set(entry.get("forbidden_ids", []))
        preferred_ids = entry.get("preferred_ids", [])

        # Try preferred IDs first — exact catalog lookup
        for pid in preferred_ids:
            for ds in catalog:
                if ds["id"] == pid and pid not in forbidden_ids:
                    logger.info(f"Registry exact match: '{ds['name']}' for topic='{topic}'")
                    return ds

        # Fall back to required_tags scan within catalog
        for ds in catalog:
            if ds["id"] in forbidden_ids:
                continue
            ds_tags = set(t.lower() for t in ds.get("tags", []))
            if required_tags and required_tags.issubset(ds_tags):
                logger.info(
                    f"Registry tag match: '{ds['name']}' "
                    f"(required_tags={required_tags}) for topic='{topic}'"
                )
                return ds

        # Signal matched but no valid dataset found — stop here, do NOT fall through
        # to FAISS which would return the wrong dataset
        logger.warning(
            f"Registry signal matched '{topic}' but no valid catalog entry "
            f"satisfies required_tags={required_tags} — will use synthetic"
        )
        return None  # Explicit: synthetic is better than wrong dataset

    return None  # No registry entry matched — proceed to FAISS/keyword


def _concept_tags_satisfied(dataset: dict, concepts: list) -> bool:
    """
    Check that the matched dataset's tags are compatible with the requested concepts.
    Prevents concept drift — e.g. concept='time series' matched to a tabular classifier.
    Returns True if no concept conflict is detected.
    """
    if not concepts:
        return True

    ds_tags = set(t.lower() for t in dataset.get("tags", []))
    ds_category = dataset.get("category", "").lower()
    ds_tags.add(ds_category)  # category counts as a tag for this check

    for concept in concepts:
        concept_lower = concept.lower()
        for key, allowed_tags in _CONCEPT_TAG_MAP.items():
            if key in concept_lower:
                # At least one allowed tag must appear in dataset tags
                if not any(at in ds_tags for at in allowed_tags):
                    logger.warning(
                        f"Concept conflict: concept='{concept}' requires one of "
                        f"{allowed_tags} but dataset '{dataset['name']}' has tags={ds_tags}"
                    )
                    return False
    return True


def _difficulty_compatible(dataset: dict, difficulty: str) -> bool:
    """
    Check difficulty compatibility.
    IMPORTANT: same dataset is used across difficulties — only task complexity changes.
    This function checks if a dataset is broadly appropriate for the difficulty level,
    NOT that it must be an exact match.  A 'Hard' dataset can also be used for Easy
    (task complexity is scaled by _build_task_scaffold, not by swapping datasets).
    """
    ds_diffs = [d.lower() for d in dataset.get("difficulty", [])]
    if not ds_diffs:
        return True  # No difficulty restriction in catalog entry
    difficulty_lower = difficulty.lower()
    # Hard can always use Medium/Hard datasets; Easy can use Easy/Medium
    compat = {
        "easy":   {"easy", "medium"},
        "medium": {"easy", "medium", "hard"},
        "hard":   {"easy", "medium", "hard"},
    }
    allowed = compat.get(difficulty_lower, {"easy", "medium", "hard"})
    return bool(set(ds_diffs) & allowed)


def _match_dataset(topic: str, concepts: list, difficulty: str):
    """
    Production-grade dataset matching.

    Pipeline (in order, stop at first success):
      1. Registry lookup  — exact topic signal → required_tags check
      2. FAISS search     — semantic similarity, then _validate_match()
      3. Keyword fallback — tag/domain overlap, then _validate_match()
      4. None             — caller falls back to synthetic generation

    Key properties:
      - Registry always wins over FAISS for known topics
      - FAISS result is validated for concept compatibility before returning
      - Difficulty does NOT swap datasets — all difficulties can use the same dataset
      - Forbidden dataset list prevents known-wrong pairings
    """
    catalog = _load_aiml_catalog()
    if not catalog:
        return None

    difficulty_lower = difficulty.lower()

    # ── Step 1: Registry lookup ───────────────────────────────────────────────
    registry_result = _registry_lookup(topic, concepts, catalog)
    if registry_result is not None:
        # Registry returned a dataset — validate concept compatibility
        if _concept_tags_satisfied(registry_result, concepts):
            return registry_result
        else:
            logger.warning(
                f"Registry match '{registry_result['name']}' failed concept check "
                f"for concepts={concepts} — falling back to FAISS"
            )
            # Do NOT return it; continue to FAISS

    # ── Step 2: FAISS semantic search ─────────────────────────────────────────
    faiss_available = _load_aiml_faiss()

    if faiss_available:
        try:
            query = f"{topic} {' '.join(concepts)} machine learning dataset"
            query_vec = _aiml_embed_model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            ).astype(np.float32)

            # Search top 30 — validate each result before accepting
            scores, indices = _aiml_faiss_index.search(
                query_vec, min(30, _aiml_faiss_index.ntotal)
            )

            for idx, score in zip(indices[0], scores[0]):
                if idx < 0 or idx >= len(_aiml_meta_cache):
                    continue
                meta         = _aiml_meta_cache[idx]
                catalog_idx  = meta.get("index", idx)
                if catalog_idx >= len(catalog):
                    continue

                dataset = catalog[catalog_idx]

                # Guard 1: difficulty compatibility
                if not _difficulty_compatible(dataset, difficulty_lower):
                    continue

                # Guard 2: concept compatibility — reject drift
                if not _concept_tags_satisfied(dataset, concepts):
                    logger.info(
                        f"FAISS: skipping '{dataset['name']}' — concept mismatch "
                        f"(score={score:.3f})"
                    )
                    continue

                # Guard 3: minimum FAISS confidence threshold
                # Below 0.25 the match is too weak — better to go synthetic
                if score < 0.25:
                    logger.info(
                        f"FAISS: score {score:.3f} too low for '{dataset['name']}' "
                        f"— stopping FAISS scan"
                    )
                    break

                logger.info(
                    f"AIML FAISS match: '{dataset['name']}' "
                    f"(score={score:.3f}, difficulty={difficulty})"
                )
                return dataset

            logger.info("AIML FAISS: no valid match after guards — trying keyword fallback")
        except Exception as e:
            logger.warning(f"AIML FAISS search failed: {e} — falling back to keyword")

    # ── Step 3: Keyword fallback ──────────────────────────────────────────────
    topic_words   = set(topic.lower().split())
    concept_words = set(" ".join(concepts).lower().split())
    best_match    = None
    best_score    = 0

    for dataset in catalog:
        score    = 0
        tags     = [t.lower() for t in dataset.get("tags", [])]
        domain   = dataset.get("domain", "").lower()
        ds_diffs = [d.lower() for d in dataset.get("difficulty", [])]

        for tag in tags:
            for word in topic_words:
                if word in tag or tag in word:
                    score += 3
                    break

        for tag in tags:
            for word in concept_words:
                if word in tag or tag in word:
                    score += 2
                    break

        for word in topic_words | concept_words:
            if word in domain:
                score += 1

        if difficulty_lower in ds_diffs:
            score += 1

        if score > best_score:
            best_score = score
            best_match = dataset

    # Minimum score AND concept check before accepting keyword match
    if best_score >= 4 and best_match and _concept_tags_satisfied(best_match, concepts):
        logger.info(f"AIML keyword match: '{best_match['name']}' (score={best_score})")
        return best_match

    logger.info(
        f"No valid dataset match (keyword score={best_score}, "
        f"topic='{topic}') — using synthetic generation"
    )
    return None

"""AIML service compatibility layer."""


import asyncio
import time
import uuid

from fastapi import HTTPException


from backend.model_app.billing.metering import bind_usage_meta_from_request


async def aiml_library_catalog_preview(catalog_id: str):
    rows, err = preview_catalog_by_id(catalog_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail=f"Unknown catalog_id: {catalog_id}")
    if rows is not None:
        return {
            "catalog_id": catalog_id,
            "preview_available": True,
            "data_preview": True,
            "rows": rows,
            "row_count": len(rows),
        }
    return {
        "catalog_id": catalog_id,
        "preview_available": False,
        "data_preview": False,
        "rows": [],
        "reason": err or "unavailable",
    }


async def generate_aiml_library(body, http_request):
    from backend.model_app.core.app import _emit_usage_metering
    from backend.model_app.core.state import STATS
    from backend.model_app.prompts.aiml import (
        _build_aiml_library_prompt,
        build_aiml_prompt,
        calculate_aiml_token_limit,
    )
    from backend.model_app.services.batching import add_to_batch_and_wait
    from backend.model_app.services.cache import generate_cache_key, get_from_cache, save_to_cache
    from backend.model_app.services.generation import extract_json
    from backend.model_app.services.jobs import _job_store_set, _job_store_update
    from backend.model_app.services.model import _llm_chat_single

    STATS["total_requests"] += 1
    STATS["requests_by_endpoint"]["aiml"] = STATS["requests_by_endpoint"].get("aiml", 0) + 1
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()

    job_id = str(uuid.uuid4())
    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _task():
        t_outer = time.time()
        await _job_store_update(job_id, status="processing")
        try:
            item_data = {k: v for k, v in data.items()}
            cache_key = generate_cache_key("aiml_library", item_data)

            if body.use_cache:
                cached = get_from_cache(cache_key)
                if cached:
                    cached["cache_hit"] = True
                    await _job_store_set(job_id, {
                        "status": "complete",
                        "result": {"aiml_problems": [cached], "generation_time_seconds": 0, "cache_hit": True, "batched": False, "batch_size": 1},
                        "error": None,
                    })
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml-library",
                        cache_hit=True,
                        latency_ms=(time.time() - t_outer) * 1000,
                        status="success",
                    )
                    return

            matched = _match_dataset(body.topic, body.concepts, body.difficulty)

            if matched:
                logger.info("Using library dataset: %s", matched["name"])
                prompt = _build_aiml_library_prompt(item_data, matched)

                try:
                    messages = [
                        {"role": "system", "content": "You are an expert AI/ML assessment designer. Return only valid JSON."},
                        {"role": "user", "content": prompt},
                    ]
                    gen_t0 = time.time()
                    decoded, in_tok, out_tok = _llm_chat_single(
                        messages,
                        temperature=0.6,
                        top_p=0.9,
                        repetition_penalty=1.1,
                        max_tokens=2000,
                    )
                    try:
                        from backend.model_app.billing.metering import current_token_counts

                        current_token_counts.set(
                            {
                                "prompt_tokens": in_tok,
                                "completion_tokens": max(0, out_tok),
                                "total_tokens": max(0, in_tok + out_tok),
                            }
                        )
                    except Exception:
                        pass
                    gen_time = time.time() - gen_t0
                    result = extract_json(decoded)

                    load_code = matched.get("load_code", "")
                    starter = (
                        f"# Dataset: {matched['name']} ({matched['source']})\n"
                        f"# Run this cell to load your data\n\n"
                        f"{load_code}\n\n"
                        f"# Your solution below\n"
                    )

                    problem = {
                        "problemStatement": result.get("problemStatement", ""),
                        "tasks": result.get("tasks", []),
                        "preprocessing_requirements": result.get("preprocessing_requirements", []),
                        "expectedApproach": result.get("expectedApproach", ""),
                        "evaluationCriteria": result.get("evaluationCriteria", []),
                        "difficulty": result.get("difficulty", body.difficulty),
                        "bloomLevel": result.get("bloomLevel", "Apply"),
                        "dataset": {
                            "catalog_id": matched.get("id", ""),
                            "name": matched.get("name", ""),
                            "source": matched.get("source", ""),
                            "description": matched.get("description", ""),
                            "domain": matched.get("domain", ""),
                            "size": matched.get("size", ""),
                            "target": matched.get("target", ""),
                            "target_type": matched.get("target_type", ""),
                            "load_code": load_code,
                            "import_code": matched.get("import_code", ""),
                            "pip_install": matched.get("pip_install", ""),
                            "features_info": matched.get("features_info", ""),
                            "tags": matched.get("tags", []),
                            "use_case": matched.get("use_case", ""),
                            "category": matched.get("category", ""),
                            "direct_load": True,
                            "storage_type": "library",
                            "file_id": None,
                        },
                        "starter_code": {"python3": starter},
                        "dataset_load_code": load_code,
                        "dataset_strategy": "library",
                        "generation_time_seconds": round(gen_time, 3),
                        "cache_hit": False,
                    }

                    try:
                        prev_rows = try_library_preview_rows(matched)
                        if prev_rows:
                            problem["dataset"]["data"] = prev_rows
                            problem["dataset"]["data_preview"] = True
                    except Exception as prev_err:
                        logger.debug("AIML library data preview skipped: %s", prev_err)

                    is_valid, issues = validate_aiml_output(
                        problem,
                        item_data.get("topic", ""),
                        item_data.get("concepts", []),
                        item_data.get("difficulty", "Medium"),
                        matched_dataset=matched,
                    )
                    if not is_valid:
                        logger.warning("Library AIML output has quality issues - returning with warnings: %s", issues)
                        problem["validation_warnings"] = issues

                    save_to_cache(cache_key, problem)
                    await _job_store_set(job_id, {
                        "status": "complete",
                        "result": {"aiml_problems": [problem], "generation_time_seconds": round(gen_time, 3), "cache_hit": False, "batched": False, "batch_size": 1},
                        "error": None,
                    })
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml-library",
                        cache_hit=False,
                        latency_ms=(time.time() - t_outer) * 1000,
                        status="success",
                    )
                except Exception as e:
                    logger.error("Library generation failed: %s - falling back to synthetic", e)
                    token_limit = calculate_aiml_token_limit(item_data)
                    result = await add_to_batch_and_wait("aiml", item_data, cache_key, build_aiml_prompt, token_limit)
                    result["dataset_strategy"] = "synthetic_fallback"
                    is_valid, issues = validate_aiml_output(
                        result,
                        item_data.get("topic", ""),
                        item_data.get("concepts", []),
                        item_data.get("difficulty", "Medium"),
                        matched_dataset=None,
                    )
                    if not is_valid:
                        result["validation_warnings"] = issues
                    save_to_cache(cache_key, result)
                    await _job_store_set(job_id, {
                        "status": "complete",
                        "result": {"aiml_problems": [result], "generation_time_seconds": round(result.get("generation_time_seconds", 0), 3), "cache_hit": False, "batched": False, "batch_size": 1},
                        "error": None,
                    })
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml-library",
                        cache_hit=False,
                        latency_ms=(time.time() - t_outer) * 1000,
                        status="success",
                    )
            else:
                logger.info("No catalog match - using synthetic generation")
                token_limit = calculate_aiml_token_limit(item_data)
                result = await add_to_batch_and_wait("aiml", item_data, cache_key, build_aiml_prompt, token_limit)
                result["dataset_strategy"] = "synthetic"
                is_valid, issues = validate_aiml_output(
                    result,
                    item_data.get("topic", ""),
                    item_data.get("concepts", []),
                    item_data.get("difficulty", "Medium"),
                    matched_dataset=None,
                )
                if not is_valid:
                    result["validation_warnings"] = issues
                save_to_cache(cache_key, result)
                await _job_store_set(job_id, {
                    "status": "complete",
                    "result": {"aiml_problems": [result], "generation_time_seconds": round(result.get("generation_time_seconds", 0), 3), "cache_hit": False, "batched": False, "batch_size": 1},
                    "error": None,
                })
                _emit_usage_metering(
                    job_id=job_id,
                    usage_meta=um,
                    route="generate-aiml-library",
                    cache_hit=False,
                    latency_ms=(time.time() - t_outer) * 1000,
                    status="success",
                )
        except Exception as e:
            STATS["errors"] += 1
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(e)})
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=um,
                route="generate-aiml-library",
                cache_hit=False,
                latency_ms=(time.time() - t_outer) * 1000,
                status="error",
                error_detail=str(e)[:500],
            )

    asyncio.create_task(_task())
    return {"job_id": job_id, "status": "pending"}




"""
Optional tabular preview rows for AIML *library* responses.

Library datasets normally ship metadata + load_code only. When enabled, we fetch a
small head() via sklearn's fetch_openml (same contract as catalog load_code) so the
frontend can render a table. Skips large catalogs to avoid heavy downloads.
"""

import json
import logging
import math
import os
import re
from typing import Any

logger = logging.getLogger(__name__)


def load_catalog_entry(catalog_id: str) -> dict[str, Any] | None:
    """Return one AIML catalog row by ``id`` (e.g. ``openml-telco-churn``)."""
    try:
        from backend.model_app.core.settings import get_settings
    except ImportError:
        return None
    path = get_settings().assets_dir / "aiml-data" / "aiml_dataset_catalog.json"
    if not path.is_file():
        logger.warning("AIML catalog file missing: %s", path)
        return None
    with open(path, encoding="utf-8") as f:
        catalog = json.load(f)
    if not isinstance(catalog, list):
        return None
    for row in catalog:
        if isinstance(row, dict) and row.get("id") == catalog_id:
            return row
    return None


def preview_catalog_by_id(catalog_id: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """
    Load catalog entry and return preview rows (same rules as ``try_library_preview_rows``).

    Returns ``(rows, None)`` on success, or ``(None, reason_code)`` on failure.
    """
    entry = load_catalog_entry(catalog_id)
    if not entry:
        return None, "not_found"
    if not _preview_enabled():
        return None, "preview_disabled"
    rows = try_library_preview_rows(entry)
    if rows:
        return rows, None
    load_code = str(entry.get("load_code") or "")
    if "fetch_openml" not in load_code:
        return None, "openml_only"
    return None, "fetch_failed_or_too_large"


def _preview_enabled() -> bool:
    try:
        from backend.model_app.core.settings import get_settings

        return bool(get_settings().aiml_library_data_preview)
    except Exception:
        v = os.environ.get("AIML_LIBRARY_DATA_PREVIEW", "true").strip().lower()
        return v not in ("0", "false", "no", "off")


def _max_rows() -> int:
    try:
        from backend.model_app.core.settings import get_settings

        return max(1, min(500, int(get_settings().aiml_library_preview_max_rows)))
    except Exception:
        try:
            return max(1, min(100, int(os.environ.get("AIML_LIBRARY_PREVIEW_MAX_ROWS", "15"))))
        except ValueError:
            return 15


def _max_catalog_rows() -> int:
    """Skip preview if catalog ``size`` reports more rows than this (avoids huge OpenML pulls)."""
    try:
        from backend.model_app.core.settings import get_settings

        return max(1, int(get_settings().aiml_library_preview_max_catalog_rows))
    except Exception:
        try:
            return max(5_000, int(os.environ.get("AIML_LIBRARY_PREVIEW_MAX_CATALOG_ROWS", "30000")))
        except ValueError:
            return 30_000


def _estimated_row_count(matched: dict[str, Any]) -> int | None:
    s = str(matched.get("size") or "").replace(",", "")
    m = re.search(r"(\d+)\s*rows", s, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,9})", s)
    return int(m.group(1)) if m else None


def _df_to_records(df: Any, max_rows: int) -> list[dict[str, Any]]:
    sub = df.head(max_rows)
    try:
        return json.loads(sub.to_json(orient="records", date_format="iso"))
    except Exception:
        out: list[dict[str, Any]] = []
        for _, row in sub.iterrows():
            rec: dict[str, Any] = {}
            for k, v in row.items():
                rec[str(k)] = _jsonify_cell(v)
            out.append(rec)
        return out


def _jsonify_cell(v: Any) -> Any:
    try:
        import numpy as np
    except ImportError:
        np = None  # type: ignore

    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if np is not None:
        if isinstance(v, getattr(np, "integer", ())):
            return int(v)
        if isinstance(v, getattr(np, "floating", ())):
            x = float(v)
            return None if math.isnan(x) or math.isinf(x) else x
        if isinstance(v, np.ndarray):
            return v.tolist()
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return v


def try_library_preview_rows(matched: dict[str, Any]) -> list[dict[str, Any]] | None:
    """
    Return JSON-serializable row dicts for UI, or None if disabled / unsafe / failed.
    """
    if not _preview_enabled():
        return None
    est = _estimated_row_count(matched)
    cap = _max_catalog_rows()
    if est is not None and est > cap:
        logger.info(
            "AIML library preview skipped: catalog ~%s rows > limit %s (%s)",
            est,
            cap,
            matched.get("id"),
        )
        return None

    load_code = matched.get("load_code") or ""
    if not isinstance(load_code, str) or not load_code.strip():
        return None

    try:
        from sklearn.datasets import fetch_openml
    except ImportError as e:
        logger.warning("AIML library preview skipped: sklearn not available (%s)", e)
        return None

    mr = _max_rows()

    m = re.search(r"data_id\s*=\s*(\d+)", load_code)
    if m:
        try:
            did = int(m.group(1))
            data = fetch_openml(data_id=did, as_frame=True, parser="auto")
            return _df_to_records(data.frame, mr)
        except Exception as e:
            logger.warning(
                "AIML library OpenML data_id preview failed (%s): %s",
                matched.get("id"),
                e,
            )
            return None

    m = re.search(r"fetch_openml\s*\(\s*['\"]([^'\"]+)['\"]", load_code)
    if m:
        name = m.group(1)
        vm = re.search(r"version\s*=\s*(\d+)", load_code)
        ver: int | str = int(vm.group(1)) if vm else "active"
        try:
            data = fetch_openml(name=name, version=ver, as_frame=True, parser="auto")
            return _df_to_records(data.frame, mr)
        except Exception as e:
            logger.warning(
                "AIML library OpenML name=%s preview failed (%s): %s",
                name,
                matched.get("id"),
                e,
            )
            return None

    return None


