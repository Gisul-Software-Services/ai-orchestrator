from __future__ import annotations


def build_aiml_prompt(request_data):
    """
    Pass 1 prompt — model generates SCHEMA ONLY (no data rows).
    Data rows are generated programmatically in Pass 2 by generate_aiml_dataset().

    Improvements over previous version:
      - Strict anti-generic-feature enforcement with auto-reject signal
      - Concept list injected so tasks must address requested concepts
      - Difficulty-aware complexity instruction (same dataset, different depth)
      - Explicit target_type → evaluationCriteria pairing rules
      - Forbidden placeholder list prevents template echo
    """
    topic = request_data["topic"]
    difficulty = request_data["difficulty"]
    concepts = request_data.get("concepts", [])
    concepts_str = (
        f"\nCONCEPTS TO DEMONSTRATE: {', '.join(concepts)}"
        f"\n  → Each task MUST address at least one of these concepts by name."
        if concepts else ""
    )

    difficulty_instruction = {
        "Easy": (
            "DIFFICULTY = Easy: Design basic features (5-10), straightforward target, "
            "simple preprocessing (one encoding step, one scaling step). "
            "Tasks should use a single baseline model with standard metrics."
        ),
        "Medium": (
            "DIFFICULTY = Medium: Design realistic features (10-15) with mixed types, "
            "moderate class imbalance if classification, real-world missing value patterns. "
            "Tasks should compare 2 model families and include feature importance."
        ),
        "Hard": (
            "DIFFICULTY = Hard: Design complex features (12-15) including derived/interaction "
            "features, significant class imbalance, or skewed distribution. "
            "Tasks should include hyperparameter tuning, cross-validation, SHAP analysis, "
            "and a deployment consideration."
        ),
    }.get(difficulty, "DIFFICULTY = Medium: realistic features, moderate complexity.")

    return f"""You are a senior ML assessment architect. Your job is to design a SYNTHETIC dataset
schema for a machine learning problem. You generate SCHEMA ONLY — no data rows.

═══════════════════════════════════════════════════════════════
TOPIC    : {topic}
DIFFICULTY: {difficulty}{concepts_str}
═══════════════════════════════════════════════════════════════

{difficulty_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT FEATURE NAMING RULES (VIOLATIONS CAUSE REJECTION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ REQUIRED: Every feature name MUST be domain-specific and self-explanatory.
❌ FORBIDDEN: feature_0, feature_1, feature_2 ... feature_N
❌ FORBIDDEN: var_1, col_1, x_1, f1, feat1, attribute_1
❌ FORBIDDEN: any name that does not describe what it measures

Domain-specific examples (use these as a guide for YOUR topic):
  customer churn  → tenure_months, monthly_charge, num_support_calls, contract_type, has_fiber_optic
  house prices    → sqft_living, num_bedrooms, year_built, garage_spaces, neighborhood_quality
  fraud detection → transaction_amount, merchant_category, hour_of_day, distance_from_home, is_foreign
  medical         → age, bmi, blood_pressure_systolic, cholesterol_level, smoker_status, glucose_mg_dl
  loan default    → loan_amount, annual_income, debt_to_income_ratio, credit_score, employment_years
  sentiment NLP   → review_length, avg_word_length, exclamation_count, polarity_score, neg_word_ratio

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE TYPE FORMAT (EXACT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use EXACTLY one of:
  numerical (continuous, range: X to Y)   ← float values, NO units in string
  numerical (integer, range: X to Y)      ← int values, NO units in string
  categorical (values: A, B, C)           ← comma-separated category values

BAD:  "numerical (continuous, range: 50 to 500 GB)"    ← no units
BAD:  "numerical (continuous, range: 10 Mbps to 1000)" ← no units
GOOD: "numerical (continuous, range: 50 to 500)"
GOOD: "categorical (values: monthly, annual, bi-annual)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each task MUST:
  - Reference ACTUAL feature names you defined (minimum 2 features per task)
  - Be specific to the domain of '{topic}' — NOT generic boilerplate
  - Match the difficulty level above
  - Address the requested concepts if provided

FORBIDDEN task phrases (do not use these):
  "load the dataset and inspect it"
  "plot correlations between features"
  "train at least 2 models"
  "evaluate using appropriate metrics"
  Any sentence that could apply to ANY dataset unchanged

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVALUATION CRITERIA RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Match evaluationCriteria to target_type EXACTLY:
  binary/multiclass classification → Accuracy, Precision, Recall, F1-Score, ROC-AUC
  continuous/regression            → RMSE, MAE, R² Score, MAPE
  clustering                       → Silhouette Score, Inertia, Davies-Bouldin Index
Do NOT mix regression and classification metrics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT — RETURN ONLY VALID JSON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "problemStatement": "2-3 sentence real-world problem for '{topic}': who needs this, what decision it enables, what happens without it.",
  "dataset": {{
    "description": "What this SYNTHETIC dataset represents in the real-world context of '{topic}'",
    "features": ["domain_specific_name_1", "domain_specific_name_2", "...10-15 names for {topic}"],
    "feature_types": {{
      "domain_specific_name_1": "numerical (continuous, range: 20 to 150)",
      "domain_specific_name_2": "categorical (values: option_a, option_b, option_c)"
    }},
    "target": "target_variable_name_specific_to_{topic.replace(' ','_')}",
    "target_type": "binary (0: no_event, 1: event) OR continuous OR multiclass (classes: A, B, C)",
    "class_distribution": {{"class0": 70, "class1": 30}},
    "size": "400 samples"
  }},
  "tasks": [
    "Task 1: [Specific to {topic} — name at least 2 actual feature names from above. State what domain-specific patterns to look for in the data.]",
    "Task 2: [Name which specific features need encoding by name, which need scaling by name. State whether stratification is needed.]",
    "Task 3: [Name 2-3 specific plots relevant to {topic} with actual feature names on axes — e.g. 'plot tenure_months vs churn_flag coloured by contract_type'.]",
    "Task 4: [Name 2 algorithms justified for this exact target_type and domain. State evaluation metrics. Include difficulty-appropriate depth.]",
    "Task 5: [Domain-specific business insight questions referencing actual feature names. Answer what the model reveals about the real-world problem.]"
  ],
  "preprocessing_requirements": [
    "Encode [actual_categorical_feature_name] using LabelEncoder / OneHotEncoder",
    "Scale [actual_numerical_feature_name_1] and [actual_numerical_feature_name_2] using StandardScaler",
    "Handle class imbalance / missing values / skew — specific to this dataset"
  ],
  "expectedApproach": "Name 2-3 algorithms for '{topic}' with WHY each suits this target_type, feature types, and domain.",
  "evaluationCriteria": ["metric_matched_to_target_type_1", "metric_2", "metric_3"],
  "difficulty": "{difficulty}"
}}

Generate now:"""


def calculate_aiml_token_limit(request_data: dict) -> int:
    # Generous limits — AIML problems with 80-150 rows need significant tokens.
    # Easy gets 10k, Medium 14k, Hard 16k. No artificial cap.
    difficulty = request_data.get("difficulty", "medium").lower()
    return {"easy": 10000, "medium": 14000, "hard": 16000}.get(difficulty, 14000)

from backend.model_app.prompts.dsa import _build_aiml_library_prompt

