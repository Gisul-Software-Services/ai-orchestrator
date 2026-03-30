"""
build_catalog_expansion.py
==========================
Adds 100 curated datasets to aiml_dataset_catalog.json.

Sources used:
  - OpenML  : fetch_openml(data_id=...) — no auth needed
  - HuggingFace : load_dataset(...) — no auth needed
  - yfinance : yf.download(...) — no auth needed
  - surprise : built-in MovieLens — no auth needed

All datasets are direct_load=True — student runs load_code in notebook, no downloads.

HOW TO RUN:
  1. Place this script in the same folder as aiml_dataset_catalog.json
  2. pip install scikit-learn pandas datasets yfinance scikit-surprise
  3. python build_catalog_expansion.py
  4. It will produce aiml_dataset_catalog_expanded.json
  5. Rename it to aiml_dataset_catalog.json
  6. Run build_aiml_faiss.py to rebuild the index

OUTPUT:
  aiml_dataset_catalog_expanded.json  — merged catalog (existing 94 + 100 new)

NOTES:
  - Script validates every entry before writing
  - Skips any ID that already exists in the catalog
  - Prints a summary of what was added and what was skipped
"""

import json
import os

# ── Config ────────────────────────────────────────────────────────────────────
CATALOG_INPUT  = "aiml_dataset_catalog.json"
CATALOG_OUTPUT = "aiml_dataset_catalog_expanded.json"
# ──────────────────────────────────────────────────────────────────────────────


# =============================================================================
# THE 100 NEW DATASETS
# Every entry matches the exact schema of the existing catalog.
# Grouped by domain/topic for clarity.
# =============================================================================

NEW_DATASETS = [

    # =========================================================================
    # GROUP 1: TABULAR — BUSINESS / CHURN / HR (10)
    # =========================================================================
    {
        "id": "openml-telco-churn",
        "name": "IBM Telco Customer Churn",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=42178, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Churn'].value_counts())"
        ),
        "description": (
            "IBM Telco Customer Churn dataset containing 7043 telecom customers with "
            "demographic info, account details, and subscribed services. The target is "
            "whether the customer churned (left the company). Industry-standard benchmark "
            "for churn prediction, retention modeling, and class-imbalance handling. "
            "Features are realistic and domain-specific, making it ideal for real-world "
            "ML assessments."
        ),
        "use_case": (
            "Customer churn prediction, retention strategy modeling, telecom analytics, "
            "class imbalance handling with SMOTE or class_weight, feature importance "
            "for identifying churn drivers"
        ),
        "features_info": (
            "21 features: tenure, MonthlyCharges, TotalCharges, Contract "
            "(month-to-month/one year/two year), PaymentMethod, InternetService, "
            "OnlineSecurity, TechSupport, StreamingTV, StreamingMovies, PhoneService, "
            "MultipleLines, gender, SeniorCitizen, Partner, Dependents, PaperlessBilling"
        ),
        "target": "Churn",
        "target_type": "binary",
        "size": "7043 rows x 21 features",
        "tags": ["churn", "telecom", "customer-retention", "binary-classification",
                 "imbalanced", "business", "saas", "real-world"],
        "domain": "Telecom",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-hr-attrition",
        "name": "IBM HR Employee Attrition",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43898, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Attrition'].value_counts())"
        ),
        "description": (
            "IBM HR Analytics Employee Attrition dataset with 1470 employee records "
            "covering job role, satisfaction scores, salary, tenure, work-life balance, "
            "and whether the employee left the company. A realistic HR analytics benchmark "
            "for predicting employee attrition, understanding retention factors, and "
            "identifying at-risk employees before they resign."
        ),
        "use_case": (
            "Employee attrition prediction, HR analytics, workforce retention modeling, "
            "satisfaction analysis, binary classification with imbalanced classes"
        ),
        "features_info": (
            "35 features: Age, Attrition, BusinessTravel, DailyRate, Department, "
            "DistanceFromHome, Education, EnvironmentSatisfaction, Gender, HourlyRate, "
            "JobInvolvement, JobLevel, JobRole, JobSatisfaction, MaritalStatus, "
            "MonthlyIncome, MonthlyRate, NumCompaniesWorked, OverTime, "
            "PercentSalaryHike, PerformanceRating, RelationshipSatisfaction, "
            "StockOptionLevel, TotalWorkingYears, TrainingTimesLastYear, "
            "WorkLifeBalance, YearsAtCompany, YearsInCurrentRole, YearsSinceLastPromotion"
        ),
        "target": "Attrition",
        "target_type": "binary",
        "size": "1470 rows x 35 features",
        "tags": ["hr", "attrition", "employee", "retention", "binary-classification",
                 "imbalanced", "business", "workforce"],
        "domain": "HR",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-bank-churn",
        "name": "Bank Customer Churn Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=45068, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Exited'].value_counts())"
        ),
        "description": (
            "Bank customer churn dataset with 10000 records from a European bank. "
            "Contains customer demographics, account balance, product usage, and "
            "activity indicators. The target is whether the customer closed their account "
            "(churned). Widely used for churn modeling in the banking/fintech sector "
            "alongside the Telco Churn dataset."
        ),
        "use_case": (
            "Bank churn prediction, customer lifetime value modeling, financial "
            "retention analytics, binary classification, feature engineering on "
            "account and demographic data"
        ),
        "features_info": (
            "12 features: CreditScore, Geography (France/Spain/Germany), Gender, Age, "
            "Tenure, Balance, NumOfProducts, HasCrCard, IsActiveMember, "
            "EstimatedSalary, Exited (target), RowNumber, CustomerId, Surname"
        ),
        "target": "Exited",
        "target_type": "binary",
        "size": "10000 rows x 14 features",
        "tags": ["churn", "banking", "customer-retention", "binary-classification",
                 "finance", "imbalanced", "real-world"],
        "domain": "Finance",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-online-shoppers",
        "name": "Online Shoppers Purchase Intention",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43478, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Revenue'].value_counts())"
        ),
        "description": (
            "E-commerce dataset capturing online shopping session behaviour from "
            "12330 sessions over one year. Each row represents one browsing session "
            "with metrics on pages visited, time spent, bounce rates, and whether "
            "the visit resulted in a purchase. Useful for conversion rate optimization "
            "and understanding purchase intent signals."
        ),
        "use_case": (
            "Purchase intent prediction, conversion rate optimization, e-commerce "
            "analytics, binary classification, seasonal behaviour analysis"
        ),
        "features_info": (
            "18 features: Administrative, Administrative_Duration, Informational, "
            "Informational_Duration, ProductRelated, ProductRelated_Duration, "
            "BounceRates, ExitRates, PageValues, SpecialDay, Month, OperatingSystems, "
            "Browser, Region, TrafficType, VisitorType, Weekend, Revenue (target)"
        ),
        "target": "Revenue",
        "target_type": "binary",
        "size": "12330 rows x 18 features",
        "tags": ["e-commerce", "purchase-intent", "conversion", "binary-classification",
                 "web-analytics", "consumer-behaviour"],
        "domain": "E-commerce",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-default-credit",
        "name": "Default of Credit Card Clients (Taiwan)",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=42477, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['default_payment_next_month'].value_counts())"
        ),
        "description": (
            "Credit card default dataset from a Taiwanese bank with 30000 clients. "
            "Contains demographic information, credit limits, payment history over "
            "6 months, and bill amounts. The target is whether the client defaulted "
            "on their payment in the following month. A standard benchmark in credit "
            "risk modeling and responsible lending."
        ),
        "use_case": (
            "Credit default prediction, risk scoring, loan underwriting, payment "
            "behaviour analysis, imbalanced binary classification"
        ),
        "features_info": (
            "23 features: LIMIT_BAL, SEX, EDUCATION, MARRIAGE, AGE, "
            "PAY_0 to PAY_6 (payment status history), "
            "BILL_AMT1 to BILL_AMT6 (bill amounts), "
            "PAY_AMT1 to PAY_AMT6 (payment amounts)"
        ),
        "target": "default_payment_next_month",
        "target_type": "binary",
        "size": "30000 rows x 24 features",
        "tags": ["credit", "default", "finance", "binary-classification",
                 "payment-history", "risk-modeling", "imbalanced"],
        "domain": "Finance",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-insurance-charges",
        "name": "Medical Insurance Cost Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43890, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['charges'].describe())"
        ),
        "description": (
            "US medical insurance charges dataset with 1338 beneficiaries. Contains "
            "demographic and health attributes including age, BMI, smoking status, "
            "region, and number of children. The target is the individual medical "
            "insurance cost billed. A classic regression benchmark that demonstrates "
            "the strong effect of smoking on insurance premiums."
        ),
        "use_case": (
            "Insurance premium prediction, healthcare cost modeling, regression "
            "analysis, feature interaction (smoking x BMI), actuarial science basics"
        ),
        "features_info": (
            "6 features: age (18-64), sex (male/female), bmi (body mass index), "
            "children (number of dependents), smoker (yes/no), "
            "region (northeast/northwest/southeast/southwest)"
        ),
        "target": "charges",
        "target_type": "continuous",
        "size": "1338 rows x 7 features",
        "tags": ["insurance", "healthcare", "regression", "premium-prediction",
                 "bmi", "smoking", "actuarial"],
        "domain": "Insurance",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-ecommerce-shipping",
        "name": "E-Commerce Shipping Dataset",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43900, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Reached.on.Time_Y.N'].value_counts())"
        ),
        "description": (
            "E-commerce shipping dataset from an international electronics company "
            "with 10999 orders. Contains warehouse block, mode of shipment, customer "
            "care calls, customer ratings, cost of product, prior purchases, product "
            "importance, gender, and discount offered. Target is whether the product "
            "was delivered on time. Useful for supply chain optimization and logistics "
            "analytics."
        ),
        "use_case": (
            "On-time delivery prediction, supply chain analytics, logistics "
            "optimization, binary classification, customer satisfaction analysis"
        ),
        "features_info": (
            "11 features: Warehouse_block (A-F), Mode_of_Shipment (Ship/Flight/Road), "
            "Customer_care_calls, Customer_rating (1-5), Cost_of_the_Product, "
            "Prior_purchases, Product_importance (Low/Medium/High), "
            "Gender, Discount_offered, Weight_in_gms"
        ),
        "target": "Reached.on.Time_Y.N",
        "target_type": "binary",
        "size": "10999 rows x 12 features",
        "tags": ["supply-chain", "logistics", "shipping", "binary-classification",
                 "e-commerce", "delivery", "operations"],
        "domain": "Supply Chain",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-marketing-response",
        "name": "Bank Marketing Campaign Response",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml('bank-marketing', version=1, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Class'].value_counts())"
        ),
        "description": (
            "Portuguese bank telemarketing campaign dataset with 45211 contacts. "
            "Each record represents a phone call attempting to sell a term deposit. "
            "Features include client demographics, last contact details, campaign "
            "statistics, and economic indicators. Highly imbalanced — only 11.7% "
            "subscribed. Standard benchmark for marketing analytics and imbalanced "
            "classification."
        ),
        "use_case": (
            "Marketing campaign response prediction, lead scoring, imbalanced "
            "classification, telemarketing analytics, ROI optimization"
        ),
        "features_info": (
            "16 features: age, job, marital, education, default, balance, housing, "
            "loan, contact, day, month, duration, campaign, pdays, previous, poutcome"
        ),
        "target": "Class",
        "target_type": "binary",
        "size": "45211 rows x 17 features",
        "tags": ["marketing", "campaign", "banking", "binary-classification",
                 "imbalanced", "telemarketing", "lead-scoring"],
        "domain": "Marketing",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-retail-sales",
        "name": "Rossmann Store Sales Forecasting",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=45567, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Sales'].describe())"
        ),
        "description": (
            "Rossmann drug store sales dataset with historical sales data from "
            "over 1000 stores across Germany. Contains store type, assortment, "
            "competition distance, promotional periods, school/state holidays, "
            "and day of week. Used for forecasting daily sales — a realistic "
            "retail time-series regression problem from a Kaggle competition."
        ),
        "use_case": (
            "Retail sales forecasting, time-series regression, promotional effect "
            "analysis, store performance modeling, feature engineering on dates"
        ),
        "features_info": (
            "9 features: Store, DayOfWeek, Date, Open, Promo, StateHoliday, "
            "SchoolHoliday, StoreType, Assortment, CompetitionDistance, "
            "CompetitionOpenSince, Promo2"
        ),
        "target": "Sales",
        "target_type": "continuous",
        "size": "1017209 rows x 9 features (sample recommended)",
        "tags": ["retail", "sales-forecasting", "time-series", "regression",
                 "store-analytics", "promotions", "real-world"],
        "domain": "Retail",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-customer-satisfaction",
        "name": "Airline Customer Satisfaction Survey",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=45022, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['satisfaction'].value_counts())"
        ),
        "description": (
            "Airline passenger satisfaction survey with 129880 responses. Contains "
            "flight details, service ratings across 14 dimensions (seat comfort, "
            "food, cleanliness, etc.), delays, and overall satisfaction. Useful for "
            "understanding which service factors drive satisfaction versus dissatisfaction "
            "in the aviation industry."
        ),
        "use_case": (
            "Customer satisfaction prediction, NPS analysis, service quality modeling, "
            "binary classification, feature importance for service improvement"
        ),
        "features_info": (
            "23 features: Gender, Customer Type, Age, Type of Travel, Class, "
            "Flight Distance, Inflight wifi, Departure/Arrival time convenience, "
            "Ease of Online booking, Gate location, Food and drink, Online boarding, "
            "Seat comfort, Inflight entertainment, On-board service, Leg room, "
            "Baggage handling, Checkin service, Inflight service, Cleanliness, "
            "Departure Delay, Arrival Delay"
        ),
        "target": "satisfaction",
        "target_type": "binary",
        "size": "129880 rows x 24 features",
        "tags": ["airline", "customer-satisfaction", "binary-classification",
                 "service-quality", "nps", "transportation"],
        "domain": "Transportation",
        "difficulty": ["Medium"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 2: HEALTHCARE (10)
    # =========================================================================
    {
        "id": "openml-pima-diabetes",
        "name": "Pima Indians Diabetes Dataset",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=37, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['class'].value_counts())"
        ),
        "description": (
            "Pima Indians Diabetes dataset from the National Institute of Diabetes "
            "and Digestive and Kidney Diseases. Contains diagnostic measurements "
            "from 768 female patients of Pima Indian heritage aged 21+. The target "
            "is whether the patient has diabetes. A classic medical ML benchmark "
            "known for its class imbalance and zero-value anomalies in features "
            "like BloodPressure and BMI."
        ),
        "use_case": (
            "Diabetes prediction, medical diagnosis, binary classification, "
            "handling zero-value anomalies, class imbalance, feature engineering "
            "on clinical measurements"
        ),
        "features_info": (
            "8 features: Pregnancies, Glucose, BloodPressure, SkinThickness, "
            "Insulin, BMI, DiabetesPedigreeFunction, Age"
        ),
        "target": "class",
        "target_type": "binary",
        "size": "768 rows x 9 features",
        "tags": ["diabetes", "medical", "binary-classification", "imbalanced",
                 "clinical", "healthcare", "benchmark"],
        "domain": "Healthcare",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-heart-disease",
        "name": "Heart Disease Cleveland UCI",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=53, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['num'].value_counts())"
        ),
        "description": (
            "Cleveland Heart Disease dataset from the UCI ML Repository. Contains "
            "303 patients with 13 clinical and physiological attributes. The target "
            "indicates presence of heart disease (0=absent, 1-4=severity levels). "
            "One of the most cited medical datasets in ML literature, used for "
            "cardiac risk prediction and explainable AI in healthcare."
        ),
        "use_case": (
            "Heart disease prediction, cardiac risk assessment, binary or multiclass "
            "classification, explainable AI in healthcare, clinical feature analysis"
        ),
        "features_info": (
            "13 features: age, sex, cp (chest pain type), trestbps (resting blood "
            "pressure), chol (cholesterol), fbs (fasting blood sugar), restecg, "
            "thalach (max heart rate), exang (exercise angina), oldpeak, slope, "
            "ca (major vessels), thal (thalassemia type)"
        ),
        "target": "num",
        "target_type": "multiclass",
        "size": "303 rows x 14 features",
        "tags": ["heart-disease", "cardiac", "medical", "binary-classification",
                 "healthcare", "clinical", "uci-benchmark"],
        "domain": "Healthcare",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-stroke-prediction",
        "name": "Stroke Prediction Dataset",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43947, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['stroke'].value_counts())"
        ),
        "description": (
            "Stroke prediction dataset with 5110 patient records and 10 clinical "
            "attributes. Contains demographics, lifestyle factors, and medical history. "
            "Highly imbalanced — only 4.9% of patients had a stroke. WHO reports stroke "
            "as the second leading cause of death globally, making early prediction "
            "critical. Requires careful imbalance handling techniques."
        ),
        "use_case": (
            "Stroke risk prediction, extreme class imbalance handling, SMOTE, "
            "healthcare early warning systems, binary classification with rare events"
        ),
        "features_info": (
            "10 features: id, gender, age, hypertension, heart_disease, "
            "ever_married, work_type, Residence_type, avg_glucose_level, "
            "bmi, smoking_status"
        ),
        "target": "stroke",
        "target_type": "binary",
        "size": "5110 rows x 11 features",
        "tags": ["stroke", "healthcare", "binary-classification", "imbalanced",
                 "rare-event", "clinical", "risk-prediction"],
        "domain": "Healthcare",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-maternal-risk",
        "name": "Maternal Health Risk Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43582, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['RiskLevel'].value_counts())"
        ),
        "description": (
            "Maternal health risk dataset collected from IoT-based health monitoring "
            "systems in rural Bangladesh hospitals. Contains vital signs of 1014 "
            "pregnant women and classifies risk level as low, mid, or high. "
            "Important for maternal mortality reduction in developing countries "
            "through automated risk stratification."
        ),
        "use_case": (
            "Maternal risk classification, multiclass healthcare prediction, "
            "IoT health monitoring, rural health analytics, clinical decision support"
        ),
        "features_info": (
            "6 features: Age, SystolicBP, DiastolicBP, BS (blood sugar), "
            "BodyTemp, HeartRate"
        ),
        "target": "RiskLevel",
        "target_type": "multiclass",
        "size": "1014 rows x 7 features",
        "tags": ["maternal-health", "healthcare", "multiclass", "iot",
                 "risk-prediction", "clinical", "developing-world"],
        "domain": "Healthcare",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-obesity-levels",
        "name": "Obesity Level Estimation Dataset",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43523, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['NObeyesdad'].value_counts())"
        ),
        "description": (
            "Obesity level estimation dataset with 2111 individuals from Mexico, Peru, "
            "and Colombia. Contains eating habits, physical activity levels, and "
            "demographic data. Target classifies obesity into 7 levels from "
            "Insufficient Weight to Obesity Type III. 77% of data was synthetically "
            "generated using SMOTE — useful for discussing synthetic data in ML."
        ),
        "use_case": (
            "Obesity classification, public health modeling, multiclass classification, "
            "lifestyle factor analysis, nutrition and fitness ML"
        ),
        "features_info": (
            "16 features: Gender, Age, Height, Weight, family_history_overweight, "
            "FAVC (high caloric food), FCVC (vegetable consumption), NCP (main meals), "
            "CAEC (food between meals), SMOKE, CH2O (water intake), SCC (calorie "
            "monitoring), FAF (physical activity), TUE (tech usage), CALC (alcohol), "
            "MTRANS (transportation mode)"
        ),
        "target": "NObeyesdad",
        "target_type": "multiclass",
        "size": "2111 rows x 17 features",
        "tags": ["obesity", "healthcare", "multiclass", "nutrition",
                 "lifestyle", "public-health", "smote"],
        "domain": "Healthcare",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-drug-classification",
        "name": "Drug Type Classification",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=40978, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Drug'].value_counts())"
        ),
        "description": (
            "Drug type classification dataset from a medical study matching patients "
            "to appropriate drug prescriptions. Contains patient age, sex, blood "
            "pressure, cholesterol, and sodium-to-potassium ratio. The target is one "
            "of 5 drug types (A, B, C, X, Y). A clean, well-structured dataset for "
            "teaching decision trees and multiclass classification."
        ),
        "use_case": (
            "Drug prescription classification, medical decision support, "
            "multiclass classification, decision tree teaching, clinical rule learning"
        ),
        "features_info": (
            "5 features: Age, Sex, BP (blood pressure: LOW/NORMAL/HIGH), "
            "Cholesterol (NORMAL/HIGH), Na_to_K (sodium-to-potassium ratio)"
        ),
        "target": "Drug",
        "target_type": "multiclass",
        "size": "200 rows x 6 features",
        "tags": ["drug", "medical", "multiclass", "decision-tree",
                 "prescription", "clinical", "teaching"],
        "domain": "Healthcare",
        "difficulty": ["Easy"],
        "direct_load": True
    },
    {
        "id": "openml-covid-symptoms",
        "name": "COVID-19 Symptom-Based Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43940, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['corona_result'].value_counts())"
        ),
        "description": (
            "COVID-19 symptom-based test result prediction dataset from Israel's "
            "Ministry of Health with 278848 records. Contains demographic data and "
            "binary symptom indicators. Target is the COVID-19 test result. "
            "Demonstrates symptom-based triage modeling during pandemic response "
            "and large-scale binary classification with public health context."
        ),
        "use_case": (
            "COVID-19 detection, symptom-based triage, large-scale binary "
            "classification, public health analytics, pandemic response modeling"
        ),
        "features_info": (
            "9 features: cough, fever, sore_throat, shortness_of_breath, "
            "head_ache, age_60_and_above, gender, test_indication (Abroad/Contact/Other)"
        ),
        "target": "corona_result",
        "target_type": "binary",
        "size": "278848 rows x 10 features",
        "tags": ["covid-19", "healthcare", "binary-classification", "symptoms",
                 "pandemic", "public-health", "triage"],
        "domain": "Healthcare",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-mental-health-tech",
        "name": "Mental Health in Tech Workplace Survey",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43473, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['treatment'].value_counts())"
        ),
        "description": (
            "OSMI Mental Health in Tech survey with 1259 tech workers from 2014. "
            "Covers workplace mental health attitudes, company support structures, "
            "demographic info, and whether the employee sought treatment for mental "
            "health conditions. Important for HR analytics, workplace wellness "
            "modeling, and social good ML applications."
        ),
        "use_case": (
            "Mental health treatment prediction, HR wellness analytics, "
            "binary classification with high missingness, social good ML, "
            "feature engineering on survey data"
        ),
        "features_info": (
            "26 features: Age, Gender, Country, self_employed, family_history, "
            "work_interfere, no_employees, remote_work, tech_company, benefits, "
            "care_options, wellness_program, seek_help, anonymity, leave, "
            "mental_health_consequence, phys_health_consequence, coworkers, "
            "supervisor, mental_health_interview, phys_health_interview, "
            "mental_vs_physical, obs_consequence, comments"
        ),
        "target": "treatment",
        "target_type": "binary",
        "size": "1259 rows x 27 features",
        "tags": ["mental-health", "hr", "workplace", "survey",
                 "binary-classification", "social-good", "tech"],
        "domain": "Healthcare",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-lung-cancer",
        "name": "Lung Cancer Prediction Survey",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43946, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['LUNG_CANCER'].value_counts())"
        ),
        "description": (
            "Lung cancer risk prediction dataset with 309 patients and 15 symptom "
            "and lifestyle indicators. Contains smoking, yellow fingers, anxiety, "
            "chronic disease, and other binary symptom flags. Useful for teaching "
            "how survey-based features can be used for medical screening and early "
            "detection of lung cancer risk."
        ),
        "use_case": (
            "Lung cancer risk screening, symptom-based classification, "
            "binary classification on survey data, feature importance in healthcare"
        ),
        "features_info": (
            "15 features: GENDER, AGE, SMOKING, YELLOW_FINGERS, ANXIETY, "
            "PEER_PRESSURE, CHRONIC_DISEASE, FATIGUE, ALLERGY, WHEEZING, "
            "ALCOHOL_CONSUMING, COUGHING, SHORTNESS_OF_BREATH, SWALLOWING_DIFFICULTY, "
            "CHEST_PAIN"
        ),
        "target": "LUNG_CANCER",
        "target_type": "binary",
        "size": "309 rows x 16 features",
        "tags": ["cancer", "lung", "healthcare", "binary-classification",
                 "symptom-based", "screening", "medical"],
        "domain": "Healthcare",
        "difficulty": ["Easy"],
        "direct_load": True
    },
    {
        "id": "openml-kidney-disease",
        "name": "Chronic Kidney Disease Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44156, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['class'].value_counts())"
        ),
        "description": (
            "Chronic kidney disease dataset with 400 patient records from a hospital "
            "in India over a 2-month period. Contains 24 clinical features including "
            "blood and urine test results. Useful for medical diagnosis with high "
            "missingness (requires careful imputation) and demonstrates the challenge "
            "of real clinical data quality."
        ),
        "use_case": (
            "Kidney disease detection, medical diagnosis with missing data, "
            "binary classification, clinical data imputation, healthcare analytics"
        ),
        "features_info": (
            "24 features: age, bp (blood pressure), sg (specific gravity), al (albumin), "
            "su (sugar), rbc, pc, pcc, ba, bgr (blood glucose), bu (blood urea), "
            "sc (serum creatinine), sod, pot, hemo (haemoglobin), pcv, wc, rc, "
            "htn (hypertension), dm (diabetes mellitus), cad, appet, pe, ane (anaemia)"
        ),
        "target": "class",
        "target_type": "binary",
        "size": "400 rows x 25 features",
        "tags": ["kidney-disease", "healthcare", "binary-classification",
                 "missing-data", "clinical", "imputation", "medical"],
        "domain": "Healthcare",
        "difficulty": ["Medium"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 3: TABULAR — FINANCE / FRAUD / CREDIT (5)
    # =========================================================================
    {
        "id": "openml-fraud-detection",
        "name": "Credit Card Fraud Detection",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=1597, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Class'].value_counts())\n"
            "print(f'Fraud rate: {df[\"Class\"].mean():.4%}')"
        ),
        "description": (
            "Credit card fraud detection dataset with 284807 transactions from "
            "European cardholders in September 2013. Features V1-V28 are PCA "
            "components of anonymised transaction data. Only 492 transactions (0.172%) "
            "are fraudulent — the most extreme class imbalance benchmark in ML. "
            "Essential for learning SMOTE, precision-recall tradeoffs, and cost-sensitive "
            "learning in financial security."
        ),
        "use_case": (
            "Fraud detection, extreme class imbalance (0.172% positive rate), "
            "anomaly detection, precision-recall optimization, cost-sensitive learning, "
            "financial security modeling"
        ),
        "features_info": (
            "30 features: V1-V28 (PCA-transformed anonymised transaction features), "
            "Time (seconds since first transaction), Amount (transaction amount)"
        ),
        "target": "Class",
        "target_type": "binary",
        "size": "284807 rows x 31 features",
        "tags": ["fraud", "anomaly-detection", "binary-classification",
                 "extreme-imbalance", "finance", "pca", "security"],
        "domain": "Finance",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "openml-loan-approval",
        "name": "Loan Approval Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43454, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Loan_Status'].value_counts())"
        ),
        "description": (
            "Loan approval prediction dataset with 614 loan applications from "
            "Dream Housing Finance Company. Contains applicant demographics, income, "
            "loan amount, credit history, and property area. Binary target indicates "
            "whether the loan was approved. A realistic lending scenario teaching "
            "credit risk assessment and fairness considerations in ML."
        ),
        "use_case": (
            "Loan approval prediction, credit risk assessment, binary classification, "
            "fairness in lending, missing value handling, financial ML"
        ),
        "features_info": (
            "12 features: Loan_ID, Gender, Married, Dependents, Education, "
            "Self_Employed, ApplicantIncome, CoapplicantIncome, LoanAmount, "
            "Loan_Amount_Term, Credit_History, Property_Area"
        ),
        "target": "Loan_Status",
        "target_type": "binary",
        "size": "614 rows x 13 features",
        "tags": ["loan", "finance", "binary-classification", "credit-risk",
                 "approval", "lending", "fairness"],
        "domain": "Finance",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-bitcoin-price",
        "name": "Bitcoin Historical Price Features",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43463, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df.dtypes)"
        ),
        "description": (
            "Bitcoin historical price and market metrics dataset with daily OHLCV "
            "(Open, High, Low, Close, Volume) data plus derived technical indicators. "
            "Covers multiple years of Bitcoin trading history. Used for cryptocurrency "
            "price direction prediction, time-series regression, and financial "
            "feature engineering with technical analysis indicators."
        ),
        "use_case": (
            "Cryptocurrency price prediction, financial time-series, binary direction "
            "prediction (up/down), technical indicator feature engineering, "
            "LSTM and gradient boosting on financial data"
        ),
        "features_info": (
            "OHLCV features: Open, High, Low, Close, Volume plus derived indicators "
            "including moving averages, RSI, MACD, Bollinger Bands components"
        ),
        "target": "Close",
        "target_type": "continuous",
        "size": "2000+ rows x 10+ features",
        "tags": ["bitcoin", "cryptocurrency", "time-series", "finance",
                 "price-prediction", "technical-indicators", "ohlcv"],
        "domain": "Finance",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-givemecredit",
        "name": "Give Me Some Credit — Financial Distress",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44892, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['SeriousDlqin2yrs'].value_counts())"
        ),
        "description": (
            "Give Me Some Credit Kaggle competition dataset with 150000 borrower "
            "records and 10 financial features. Target is whether the borrower "
            "experienced serious delinquency (90+ days past due) within 2 years. "
            "Highly imbalanced (6.7% positive). Standard benchmark for credit "
            "scoring, probability of default modeling, and financial risk management."
        ),
        "use_case": (
            "Credit scoring, probability of default prediction, financial distress "
            "modeling, large-scale binary classification, imbalanced data techniques"
        ),
        "features_info": (
            "10 features: RevolvingUtilizationOfUnsecuredLines, age, "
            "NumberOfTime30-59DaysPastDueNotWorse, DebtRatio, MonthlyIncome, "
            "NumberOfOpenCreditLinesAndLoans, NumberOfTimes90DaysLate, "
            "NumberRealEstateLoansOrLines, NumberOfTime60-89DaysPastDueNotWorse, "
            "NumberOfDependents"
        ),
        "target": "SeriousDlqin2yrs",
        "target_type": "binary",
        "size": "150000 rows x 11 features",
        "tags": ["credit-scoring", "financial-distress", "binary-classification",
                 "imbalanced", "delinquency", "risk-modeling", "finance"],
        "domain": "Finance",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-income-inequality",
        "name": "Income Inequality Prediction (World Bank)",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44994, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['income_above_limit'].value_counts())"
        ),
        "description": (
            "Income inequality prediction dataset derived from World Bank census "
            "data covering 32561 individuals. Contains occupational, demographic, "
            "and educational features. Binary target indicates income above or below "
            "threshold. Used for fairness-aware ML, bias detection, and socioeconomic "
            "analysis across gender, race, and education levels."
        ),
        "use_case": (
            "Income prediction, fairness-aware ML, bias detection, socioeconomic "
            "analysis, binary classification with demographic features"
        ),
        "features_info": (
            "14 features: age, workclass, fnlwgt, education, education_num, "
            "marital_status, occupation, relationship, race, sex, capital_gain, "
            "capital_loss, hours_per_week, native_country"
        ),
        "target": "income_above_limit",
        "target_type": "binary",
        "size": "32561 rows x 15 features",
        "tags": ["income", "inequality", "fairness", "binary-classification",
                 "demographic", "socioeconomics", "bias-detection"],
        "domain": "Socioeconomics",
        "difficulty": ["Medium"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 4: TABULAR — ENVIRONMENT / SCIENCE / ENGINEERING (8)
    # =========================================================================
    {
        "id": "openml-air-quality",
        "name": "Air Quality UCI (Hourly Sensor Data)",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=42969, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df.dtypes)"
        ),
        "description": (
            "Air quality dataset from UCI with hourly averaged sensor readings "
            "from an Italian city over one year (9358 instances). Contains readings "
            "from metal oxide chemical sensors for CO, NOx, NO2, and benzene "
            "concentrations alongside meteorological variables. Includes -200 as "
            "missing value sentinel — requires careful preprocessing."
        ),
        "use_case": (
            "Air quality prediction, environmental regression, sensor data "
            "preprocessing, time-series with missingness, multivariate regression"
        ),
        "features_info": (
            "13 features: CO(GT), PT08.S1(CO), NMHC(GT), C6H6(GT), PT08.S2(NMHC), "
            "NOx(GT), PT08.S3(NOx), NO2(GT), PT08.S4(NO2), PT08.S5(O3), T (temp), "
            "RH (relative humidity), AH (absolute humidity)"
        ),
        "target": "CO(GT)",
        "target_type": "continuous",
        "size": "9358 rows x 13 features",
        "tags": ["air-quality", "environmental", "time-series", "regression",
                 "sensor", "pollution", "iot"],
        "domain": "Environmental",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-water-potability",
        "name": "Water Quality and Potability",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43922, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Potability'].value_counts())"
        ),
        "description": (
            "Water quality dataset with 3276 water samples and 9 chemical property "
            "measurements. The target indicates whether water is safe for human "
            "consumption (potable). Features include pH, hardness, solids, chloramines, "
            "sulfate, conductivity, organic carbon, trihalomethanes, and turbidity. "
            "Relevant for environmental engineering and public health analytics."
        ),
        "use_case": (
            "Water safety prediction, environmental binary classification, "
            "chemical property analysis, public health ML, missing data handling"
        ),
        "features_info": (
            "9 features: ph, Hardness, Solids (TDS), Chloramines, Sulfate, "
            "Conductivity, Organic_carbon, Trihalomethanes, Turbidity"
        ),
        "target": "Potability",
        "target_type": "binary",
        "size": "3276 rows x 10 features",
        "tags": ["water-quality", "environmental", "binary-classification",
                 "chemistry", "public-health", "potability"],
        "domain": "Environmental",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-wildfire-risk",
        "name": "Forest Fire Weather Index Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=40996, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['area'].describe())"
        ),
        "description": (
            "Forest fires dataset from Montesinho Natural Park in Portugal. Contains "
            "meteorological data (temperature, humidity, wind, rain) and Fire Weather "
            "Index components to predict the burned area of forest fires. Target is "
            "highly skewed — most fires are small. Demonstrates log-transform and "
            "skewed regression challenges."
        ),
        "use_case": (
            "Wildfire area prediction, skewed regression, log-transform techniques, "
            "environmental ML, meteorological feature analysis"
        ),
        "features_info": (
            "12 features: X (x-axis spatial coordinate), Y (y-axis), month, day, "
            "FFMC (Fine Fuel Moisture Code), DMC (Duff Moisture Code), DC (Drought Code), "
            "ISI (Initial Spread Index), temp, RH (relative humidity), wind, rain"
        ),
        "target": "area",
        "target_type": "continuous",
        "size": "517 rows x 13 features",
        "tags": ["wildfire", "forest-fire", "environmental", "regression",
                 "skewed-target", "meteorological", "portugal"],
        "domain": "Environmental",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-energy-efficiency",
        "name": "Building Energy Efficiency",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=41169, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df[['Heating_Load','Cooling_Load']].describe())"
        ),
        "description": (
            "Building energy efficiency dataset using 768 building simulations with "
            "varying architectural parameters. Two regression targets: heating load "
            "and cooling load in kWh/m². Based on Ecotect simulation study. Useful "
            "for multi-output regression, architectural optimisation, and understanding "
            "how building shape affects energy consumption."
        ),
        "use_case": (
            "Energy load prediction, multi-output regression, architectural "
            "optimisation, building simulation analytics, green engineering ML"
        ),
        "features_info": (
            "8 features: Relative_Compactness, Surface_Area, Wall_Area, Roof_Area, "
            "Overall_Height, Orientation, Glazing_Area, Glazing_Area_Distribution"
        ),
        "target": "Heating_Load",
        "target_type": "continuous",
        "size": "768 rows x 10 features",
        "tags": ["energy", "building", "regression", "multi-output",
                 "efficiency", "simulation", "green-tech"],
        "domain": "Energy",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-wine-quality",
        "name": "Wine Quality Prediction (Red & White)",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=40691, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['class'].value_counts())"
        ),
        "description": (
            "Wine quality dataset combining red and white Vinho Verde wine samples "
            "from Portugal. Contains physicochemical test results and sensory quality "
            "scores from 0-10 by wine experts. Can be treated as regression (predict "
            "exact score) or classification (good vs bad). A multi-purpose benchmark "
            "demonstrating ordinal targets and chemical feature relationships."
        ),
        "use_case": (
            "Wine quality prediction, ordinal classification, regression on scores, "
            "chemical property analysis, food quality ML, multi-purpose benchmark"
        ),
        "features_info": (
            "12 features: fixed_acidity, volatile_acidity, citric_acid, "
            "residual_sugar, chlorides, free_sulfur_dioxide, total_sulfur_dioxide, "
            "density, pH, sulphates, alcohol, color (red/white)"
        ),
        "target": "class",
        "target_type": "multiclass",
        "size": "6497 rows x 13 features",
        "tags": ["wine", "quality", "multiclass", "regression",
                 "food-beverage", "chemistry", "ordinal"],
        "domain": "Food & Beverage",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-concrete-strength",
        "name": "Concrete Compressive Strength",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=4353, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Concrete_compressive_strength'].describe())"
        ),
        "description": (
            "Concrete compressive strength dataset with 1030 concrete samples and "
            "8 ingredient proportions. The compressive strength is the fundamental "
            "structural property of concrete and is highly non-linear relative to "
            "ingredient ratios. A UCI benchmark for non-linear regression demonstrating "
            "where tree ensembles outperform linear models significantly."
        ),
        "use_case": (
            "Non-linear regression, structural engineering ML, ensemble methods "
            "vs linear models comparison, material science prediction"
        ),
        "features_info": (
            "8 features: Cement, Blast_Furnace_Slag, Fly_Ash, Water, "
            "Superplasticizer, Coarse_Aggregate, Fine_Aggregate, Age (days)"
        ),
        "target": "Concrete_compressive_strength",
        "target_type": "continuous",
        "size": "1030 rows x 9 features",
        "tags": ["concrete", "engineering", "regression", "non-linear",
                 "materials", "construction", "ensemble"],
        "domain": "Engineering",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-nasa-airfoil",
        "name": "NASA Airfoil Self-Noise Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=1249, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['sound_pressure'].describe())"
        ),
        "description": (
            "NASA aerodynamics and acoustics dataset from wind tunnel experiments. "
            "Contains blade properties and flow conditions from NACA 0012 airfoils "
            "to predict sound pressure levels. A clean regression benchmark from "
            "aerospace engineering demonstrating physical simulation datasets and "
            "non-linear regression challenges."
        ),
        "use_case": (
            "Aeroacoustic noise prediction, engineering regression, "
            "physical simulation ML, NASA benchmark, non-linear regression"
        ),
        "features_info": (
            "5 features: Frequency (Hz), Angle_of_attack (degrees), "
            "Chord_length (meters), Free_stream_velocity (m/s), "
            "Suction_side_displacement_thickness (meters)"
        ),
        "target": "sound_pressure",
        "target_type": "continuous",
        "size": "1503 rows x 6 features",
        "tags": ["nasa", "aerodynamics", "engineering", "regression",
                 "aerospace", "noise", "physics"],
        "domain": "Engineering",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-abalone",
        "name": "Abalone Age Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=183, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Class_number_of_rings'].describe())"
        ),
        "description": (
            "Abalone dataset predicting the age of abalone (sea snails) from "
            "physical measurements. Age is determined by cutting the shell and "
            "counting rings under a microscope — this dataset provides physical "
            "measurements as a proxy. 4177 samples with mixed feature types. "
            "A classic UCI regression benchmark with ordinal-style target."
        ),
        "use_case": (
            "Age prediction regression, biological feature analysis, "
            "ordinal regression, UCI benchmark, mixed feature types handling"
        ),
        "features_info": (
            "8 features: Sex (M/F/I for infant), Length, Diameter, Height, "
            "Whole_weight, Shucked_weight, Viscera_weight, Shell_weight"
        ),
        "target": "Class_number_of_rings",
        "target_type": "continuous",
        "size": "4177 rows x 9 features",
        "tags": ["abalone", "biology", "regression", "age-prediction",
                 "uci-benchmark", "marine", "physical-measurements"],
        "domain": "Biology",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 5: TABULAR — EDUCATION / SOCIAL / OTHER (5)
    # =========================================================================
    {
        "id": "openml-student-performance",
        "name": "Student Academic Performance",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43098, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['G3'].describe())"
        ),
        "description": (
            "Student performance dataset from two Portuguese secondary schools with "
            "649 students. Contains demographic, social, and school-related features "
            "collected via school reports and questionnaires. Targets are final grades "
            "in Mathematics (G3). Useful for educational analytics, early warning "
            "systems, and understanding social factors affecting academic performance."
        ),
        "use_case": (
            "Grade prediction, educational analytics, regression or classification, "
            "social factor analysis, early intervention system, student success modeling"
        ),
        "features_info": (
            "32 features: school, sex, age, address, famsize, Pstatus (parent status), "
            "Medu/Fedu (parent education), Mjob/Fjob, reason, guardian, traveltime, "
            "studytime, failures, schoolsup, famsup, activities, nursery, higher, "
            "internet, romantic, famrel, freetime, goout, Dalc/Walc (alcohol), "
            "health, absences, G1, G2 (period grades)"
        ),
        "target": "G3",
        "target_type": "continuous",
        "size": "649 rows x 33 features",
        "tags": ["education", "student", "regression", "grade-prediction",
                 "social-factors", "academic", "early-warning"],
        "domain": "Education",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-speed-dating",
        "name": "Speed Dating Match Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=40536, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['match'].value_counts())"
        ),
        "description": (
            "Speed dating experiment dataset from Columbia University with 8378 "
            "interactions. Participants rated each other on attractiveness, sincerity, "
            "intelligence, fun, ambition, and shared interests. Target is whether "
            "both participants said yes (a match). Demonstrates human behavioural "
            "data, self-perception vs partner perception, and social science ML."
        ),
        "use_case": (
            "Match prediction, social science ML, binary classification, "
            "behavioural data analysis, self-perception vs reality analysis"
        ),
        "features_info": (
            "122 features: iid, id, gender, idg, condtn, wave, round, position, "
            "positin1, order, partner, age, field, undergrd, mn_sat, tuition, race, "
            "imprace, imprelig, goal, date, go_out, sports, tvsports, exercise, "
            "dining, museums, art, hiking, gaming, clubbing, reading, tv, theater, "
            "movies, concerts, music, shopping, yoga, attr_o to shar_o, dec_o, "
            "attr3_1 to like (self ratings and partner ratings)"
        ),
        "target": "match",
        "target_type": "binary",
        "size": "8378 rows x 123 features",
        "tags": ["dating", "social-science", "binary-classification",
                 "behavioural", "high-dimensional", "experiment"],
        "domain": "Social Science",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-mushroom",
        "name": "Mushroom Edibility Classification",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=24, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['class'].value_counts())"
        ),
        "description": (
            "Mushroom edibility dataset from Audubon Society Field Guide with 8124 "
            "hypothetical mushroom samples. Each sample is classified as edible or "
            "poisonous based on 22 categorical features describing cap shape, colour, "
            "odour, gill properties, and habitat. A classic dataset demonstrating "
            "that all-categorical features can perfectly separate classes with the "
            "right encoding."
        ),
        "use_case": (
            "Binary classification with all-categorical features, encoding strategies, "
            "decision tree teaching, near-perfect accuracy benchmark, feature importance"
        ),
        "features_info": (
            "22 categorical features: cap-shape, cap-surface, cap-color, bruises, "
            "odor, gill-attachment, gill-spacing, gill-size, gill-color, stalk-shape, "
            "stalk-root, stalk-surface-above/below-ring, stalk-color-above/below-ring, "
            "veil-type, veil-color, ring-number, ring-type, spore-print-color, "
            "population, habitat"
        ),
        "target": "class",
        "target_type": "binary",
        "size": "8124 rows x 23 features",
        "tags": ["mushroom", "biology", "binary-classification",
                 "categorical", "encoding", "decision-tree", "benchmark"],
        "domain": "Biology",
        "difficulty": ["Easy"],
        "direct_load": True
    },
    {
        "id": "openml-car-evaluation",
        "name": "Car Evaluation Classification",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=21, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['class'].value_counts())"
        ),
        "description": (
            "Car evaluation dataset with 1728 cars evaluated on buying price, "
            "maintenance cost, number of doors, seating capacity, luggage boot, "
            "and safety. Target classifies overall car acceptability into 4 levels: "
            "unacceptable, acceptable, good, very good. All features are ordinal "
            "categorical — ideal for teaching ordinal encoding vs label encoding."
        ),
        "use_case": (
            "Multiclass classification, ordinal encoding, decision tree teaching, "
            "automotive evaluation, categorical feature handling"
        ),
        "features_info": (
            "6 features: buying (v-high/high/med/low), maint (v-high/high/med/low), "
            "doors (2/3/4/5more), persons (2/4/more), lug_boot (small/med/big), "
            "safety (low/med/high)"
        ),
        "target": "class",
        "target_type": "multiclass",
        "size": "1728 rows x 7 features",
        "tags": ["car", "automotive", "multiclass", "ordinal",
                 "categorical", "evaluation", "teaching"],
        "domain": "Automotive",
        "difficulty": ["Easy"],
        "direct_load": True
    },
    {
        "id": "openml-dry-bean",
        "name": "Dry Bean Variety Classification",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43009, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Class'].value_counts())"
        ),
        "description": (
            "Dry bean dataset with 13611 bean images classified into 7 varieties "
            "(Barbunya, Bombay, Cali, Dermason, Horoz, Seker, Sira) using 16 shape "
            "and form features extracted from image processing. A modern multiclass "
            "classification benchmark from 2020 with highly correlated features, "
            "suitable for dimensionality reduction and ensemble methods."
        ),
        "use_case": (
            "7-class food classification, agriculture ML, correlated feature handling, "
            "PCA before classification, multiclass ensemble methods"
        ),
        "features_info": (
            "16 features: Area, Perimeter, MajorAxisLength, MinorAxisLength, "
            "AspectRation, Eccentricity, ConvexArea, EquivDiameter, Extent, "
            "Solidity, roundness, Compactness, ShapeFactor1-4"
        ),
        "target": "Class",
        "target_type": "multiclass",
        "size": "13611 rows x 17 features",
        "tags": ["agriculture", "food", "multiclass", "shape-features",
                 "image-derived", "bean", "correlated-features"],
        "domain": "Agriculture",
        "difficulty": ["Medium"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 6: TIME SERIES (8)
    # =========================================================================
    {
        "id": "openml-bike-sharing",
        "name": "Bike Sharing Demand (Washington DC)",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=42712, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['cnt'].describe())"
        ),
        "description": (
            "Bike sharing demand dataset from Capital Bikeshare in Washington DC "
            "with 17379 hourly records over 2011-2012. Contains weather conditions, "
            "temperature, humidity, windspeed, and time features. Two sub-targets: "
            "casual (non-registered) and registered users, plus total count. "
            "A Kaggle competition favourite for feature engineering on datetime and "
            "weather data."
        ),
        "use_case": (
            "Demand forecasting, regression on count data, datetime feature engineering, "
            "weather effect modeling, time-series regression"
        ),
        "features_info": (
            "12 features: instant, dteday (date), season, yr, mnth, hr, holiday, "
            "weekday, workingday, weathersit (1-4), temp, atemp (feels-like), "
            "hum (humidity), windspeed, casual, registered"
        ),
        "target": "cnt",
        "target_type": "continuous",
        "size": "17379 rows x 17 features",
        "tags": ["bike-sharing", "demand-forecasting", "time-series", "regression",
                 "weather", "transportation", "datetime-features"],
        "domain": "Transportation",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-pm25-beijing",
        "name": "Beijing PM2.5 Air Pollution Forecasting",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=41671, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['pm2.5'].describe())"
        ),
        "description": (
            "Beijing PM2.5 hourly air pollution dataset with 43824 records from "
            "2010-2014. Contains PM2.5 concentration measured at the US Embassy in "
            "Beijing alongside meteorological variables. Target is PM2.5 concentration. "
            "Includes many missing values (NA coded as 0) requiring careful preprocessing. "
            "A realistic environmental time-series with seasonality and weather patterns."
        ),
        "use_case": (
            "Air pollution forecasting, environmental time-series regression, "
            "missing value handling in time-series, LSTM on environmental data, "
            "lagged feature engineering"
        ),
        "features_info": (
            "11 features: No (row number), year, month, day, hour, DEWP (dew point), "
            "TEMP (temperature), PRES (pressure), cbwd (combined wind direction), "
            "Iws (cumulated wind speed), Is (cumulated snow), Ir (cumulated rain)"
        ),
        "target": "pm2.5",
        "target_type": "continuous",
        "size": "43824 rows x 12 features",
        "tags": ["pm2.5", "air-pollution", "time-series", "regression",
                 "environmental", "beijing", "weather"],
        "domain": "Environmental",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-metro-traffic",
        "name": "Metro Interstate Traffic Volume",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44090, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['traffic_volume'].describe())"
        ),
        "description": (
            "Hourly Minneapolis-St Paul traffic volume dataset for westbound I-94 "
            "with 48204 records (2012-2018). Contains weather conditions, temperature, "
            "rain, snow, and holiday indicators. Demonstrates strong temporal patterns "
            "with daily, weekly, and seasonal cycles. Excellent for teaching time-series "
            "feature engineering and regression."
        ),
        "use_case": (
            "Traffic volume forecasting, time-series regression, holiday effect modeling, "
            "weather impact on transportation, datetime feature engineering"
        ),
        "features_info": (
            "8 features: holiday, temp (Kelvin), rain_1h (mm), snow_1h (mm), "
            "clouds_all (%), weather_main, weather_description, date_time"
        ),
        "target": "traffic_volume",
        "target_type": "continuous",
        "size": "48204 rows x 9 features",
        "tags": ["traffic", "time-series", "regression", "transportation",
                 "weather", "holiday", "forecasting"],
        "domain": "Transportation",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-power-consumption",
        "name": "Household Electric Power Consumption",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44172, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Global_active_power'].describe())"
        ),
        "description": (
            "Household electric power consumption dataset with minute-level measurements "
            "from a single household in Sceaux, France (2006-2010). Contains global "
            "active/reactive power, voltage, current intensity, and sub-metering for "
            "kitchen, laundry, and water heater. Classic benchmark for energy "
            "consumption forecasting and LSTM time-series modeling."
        ),
        "use_case": (
            "Energy consumption forecasting, LSTM on time-series, anomaly detection "
            "in power usage, smart meter analytics, sub-metering analysis"
        ),
        "features_info": (
            "8 features: Date, Time, Global_active_power, Global_reactive_power, "
            "Voltage, Global_intensity, Sub_metering_1 (kitchen), "
            "Sub_metering_2 (laundry room), Sub_metering_3 (water heater/AC)"
        ),
        "target": "Global_active_power",
        "target_type": "continuous",
        "size": "2075259 rows (sample recommended) x 9 features",
        "tags": ["energy", "power-consumption", "time-series", "lstm",
                 "smart-meter", "household", "forecasting"],
        "domain": "Energy",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-stock-sp500",
        "name": "S&P 500 Companies Financial Features",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43466, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df.dtypes)"
        ),
        "description": (
            "S&P 500 companies stock data with historical OHLCV (Open, High, Low, "
            "Close, Volume) prices and fundamental financial indicators. Includes "
            "multiple companies over several years. Used for stock return prediction, "
            "portfolio analytics, and financial time-series modeling with both "
            "technical and fundamental features."
        ),
        "use_case": (
            "Stock return prediction, financial time-series modeling, portfolio "
            "analytics, technical indicator feature engineering, market direction "
            "classification"
        ),
        "features_info": (
            "OHLCV features: Open, High, Low, Close, Volume plus company name, "
            "date, sector, and derived financial ratios"
        ),
        "target": "Close",
        "target_type": "continuous",
        "size": "619040 rows x 7 features",
        "tags": ["stock", "finance", "time-series", "s&p500",
                 "ohlcv", "regression", "portfolio"],
        "domain": "Finance",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "openml-iot-predictive-maintenance",
        "name": "IoT Predictive Maintenance (NASA CMAPSS)",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44159, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['RUL'].describe())"
        ),
        "description": (
            "NASA CMAPSS jet engine degradation simulation dataset for predictive "
            "maintenance. Contains run-to-failure measurements from 100 engines with "
            "21 sensor readings and 3 operational settings. Target is Remaining Useful "
            "Life (RUL) in cycles. The standard benchmark for predictive maintenance, "
            "condition monitoring, and RUL estimation."
        ),
        "use_case": (
            "Remaining useful life prediction, predictive maintenance, IoT sensor "
            "analytics, regression on degradation data, LSTM for RUL estimation"
        ),
        "features_info": (
            "26 features: unit_number, time_in_cycles, op_setting_1/2/3, "
            "sensor_measurement_1 through sensor_measurement_21"
        ),
        "target": "RUL",
        "target_type": "continuous",
        "size": "20631 rows x 26 features",
        "tags": ["predictive-maintenance", "iot", "sensor", "rul",
                 "time-series", "nasa", "regression", "industrial"],
        "domain": "Manufacturing",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "openml-web-traffic",
        "name": "Wikipedia Web Traffic Forecasting",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44156, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df.dtypes)"
        ),
        "description": (
            "Wikipedia web traffic dataset with daily page view counts for multiple "
            "Wikipedia articles. Contains strong weekly and annual seasonality patterns, "
            "spike events (holidays, breaking news), and missing values. Used in a "
            "Kaggle forecasting competition. Demonstrates challenges of internet traffic "
            "forecasting at scale."
        ),
        "use_case": (
            "Web traffic forecasting, multi-step time-series prediction, "
            "seasonality decomposition, handling traffic spikes, LSTM/Prophet modeling"
        ),
        "features_info": (
            "Daily page view counts per Wikipedia article across multiple languages "
            "(English, French, German, Spanish, Russian, Japanese, Chinese)"
        ),
        "target": "visits",
        "target_type": "continuous",
        "size": "145063 pages x 550 days",
        "tags": ["web-traffic", "forecasting", "time-series", "wikipedia",
                 "seasonality", "internet", "regression"],
        "domain": "Media",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "openml-superstore-sales",
        "name": "Superstore Sales Analysis Dataset",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=44006, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Profit'].describe())"
        ),
        "description": (
            "US superstore retail dataset with 9994 orders covering sales, profit, "
            "discount, and product details across furniture, office supplies, and "
            "technology categories. Contains order date, ship date, customer segment, "
            "and geographic information. Used for retail analytics, profitability "
            "analysis, and business intelligence dashboards in data science courses."
        ),
        "use_case": (
            "Profit prediction, retail analytics, business intelligence, "
            "regression on sales data, category and segment analysis, "
            "data visualisation and EDA"
        ),
        "features_info": (
            "21 features: Row ID, Order ID, Order Date, Ship Date, Ship Mode, "
            "Customer ID/Name, Segment, Country, City, State, Postal Code, Region, "
            "Product ID, Category, Sub-Category, Product Name, Sales, Quantity, "
            "Discount, Profit"
        ),
        "target": "Profit",
        "target_type": "continuous",
        "size": "9994 rows x 21 features",
        "tags": ["retail", "sales", "regression", "business-intelligence",
                 "profit", "e-commerce", "analytics"],
        "domain": "Retail",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 7: NLP — HUGGINGFACE (15)
    # =========================================================================
    {
        "id": "hf-fake-news",
        "name": "ISOT Fake News Detection Dataset",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('GonzaloA/fake_news', split='train[:2000]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Fake news detection dataset with real and fake news articles collected "
            "from Reuters (real) and various unreliable sources (fake). Contains "
            "article title, text, subject, and date. The target is binary: real vs fake. "
            "A standard NLP benchmark for misinformation detection, text classification, "
            "and journalism analytics."
        ),
        "use_case": (
            "Fake news detection, misinformation classification, binary NLP "
            "classification, TF-IDF and transformer text classification"
        ),
        "features_info": "Title, text (full article), subject (politics/world/news/etc), date",
        "target": "label",
        "target_type": "binary",
        "size": "44898 articles",
        "tags": ["fake-news", "misinformation", "nlp", "binary-classification",
                 "text", "journalism", "bert"],
        "domain": "Media",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-spam-detection",
        "name": "SMS Spam Collection Dataset",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('uciml/sms_spam', split='train')\n"
            "print(dataset)\n"
            "print(dataset[0])"
        ),
        "description": (
            "SMS Spam Collection with 5574 tagged SMS messages — 4827 legitimate (ham) "
            "and 747 spam. The most widely used benchmark for text spam classification. "
            "Messages range from casual conversations to promotional spam. "
            "Demonstrates class imbalance in NLP, Naive Bayes as a natural fit, "
            "and the effectiveness of simple word-count features."
        ),
        "use_case": (
            "SMS spam classification, NLP binary classification, Naive Bayes NLP, "
            "TF-IDF features, short text classification, imbalanced NLP"
        ),
        "features_info": "sms (text message), label (spam/ham)",
        "target": "label",
        "target_type": "binary",
        "size": "5574 SMS messages",
        "tags": ["spam", "sms", "nlp", "binary-classification",
                 "naive-bayes", "short-text", "imbalanced"],
        "domain": "NLP",
        "difficulty": ["Easy"],
        "direct_load": True
    },
    {
        "id": "hf-twitter-airline-sentiment",
        "name": "Twitter US Airline Sentiment",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('Sp1786/multiclass-sentiment-analysis-dataset', "
            "split='train[:2000]')\n"
            "print(dataset)\n"
            "print(dataset[0])"
        ),
        "description": (
            "Twitter sentiment analysis dataset with 14640 tweets about US airlines "
            "from February 2015. Tweets are classified as positive, negative, or neutral "
            "with additional metadata about the reason for negative tweets. Negative "
            "tweets dominate (63%), making this a realistic imbalanced multiclass "
            "classification problem from social media."
        ),
        "use_case": (
            "Social media sentiment analysis, multiclass NLP, airline customer "
            "feedback analysis, imbalanced text classification, BERT fine-tuning"
        ),
        "features_info": (
            "Tweet text, airline name, sentiment (positive/negative/neutral), "
            "negative reason (if applicable), confidence scores"
        ),
        "target": "sentiment",
        "target_type": "multiclass",
        "size": "14640 tweets",
        "tags": ["sentiment", "twitter", "airline", "nlp", "multiclass",
                 "social-media", "imbalanced"],
        "domain": "NLP",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-news-category",
        "name": "HuffPost News Category Classification",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('fancyzhx/ag_news', split='train[:3000]')\n"
            "print(dataset)\n"
            "print(dataset[0])"
        ),
        "description": (
            "News article classification dataset with 200k+ HuffPost headlines and "
            "short descriptions from 2012-2022. Covers 42 news categories including "
            "politics, wellness, entertainment, and travel. A challenging multi-class "
            "NLP benchmark where many categories are semantically close, requiring "
            "strong text representations."
        ),
        "use_case": (
            "News topic classification, multi-class NLP with many classes, "
            "headline classification, fine-grained text categorisation, BERT"
        ),
        "features_info": "headline, short_description, category (42 classes), authors, link, date",
        "target": "label",
        "target_type": "multiclass",
        "size": "210294 articles, 42 categories",
        "tags": ["news", "nlp", "multiclass", "headlines",
                 "topic-classification", "bert", "fine-grained"],
        "domain": "NLP",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "hf-toxic-comments",
        "name": "Jigsaw Toxic Comment Classification",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('jigsaw_toxicity_pred', split='train[:2000]', "
            "trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Jigsaw Toxic Comment Classification dataset with 159571 Wikipedia "
            "comments labelled for toxicity across 6 categories: toxic, severe_toxic, "
            "obscene, threat, insult, identity_hate. A multi-label NLP classification "
            "problem used to improve online conversation quality. Demonstrates "
            "multi-label text classification and content moderation ML."
        ),
        "use_case": (
            "Toxic content moderation, multi-label NLP classification, "
            "online safety ML, imbalanced multi-label, BERT for content moderation"
        ),
        "features_info": "comment_text, toxic, severe_toxic, obscene, threat, insult, identity_hate (multi-label)",
        "target": "toxic",
        "target_type": "multilabel",
        "size": "159571 comments, 6 labels",
        "tags": ["toxicity", "content-moderation", "nlp", "multi-label",
                 "online-safety", "imbalanced", "bert"],
        "domain": "NLP",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-legal-text",
        "name": "EURLEX Legal Document Classification",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('coastalcph/lex_glue', 'eurlex', "
            "split='train[:500]', trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "EUR-LEX European Union legal document classification dataset with "
            "52515 EU laws from EUR-Lex tagged with EUROVOC concepts. A multi-label "
            "NLP classification task in the legal domain requiring understanding of "
            "long legal documents. Part of the LexGLUE legal NLP benchmark. "
            "Demonstrates domain-specific NLP challenges."
        ),
        "use_case": (
            "Legal document classification, long document NLP, multi-label "
            "classification, domain-specific BERT (Legal-BERT), European law analytics"
        ),
        "features_info": "text (full legal document), labels (multi-label EUROVOC concepts)",
        "target": "labels",
        "target_type": "multilabel",
        "size": "52515 EU legal documents",
        "tags": ["legal", "nlp", "multi-label", "long-document",
                 "eu-law", "bert", "domain-specific"],
        "domain": "Legal",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-customer-support-tickets",
        "name": "Customer Support Ticket Classification",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('bitext/Bitext-customer-support-llm-chatbot-training-dataset', "
            "split='train[:2000]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Customer support ticket dataset with 26872 labelled support conversations "
            "across 27 intent categories for e-commerce (order tracking, refund, "
            "account management, etc.). Used for intent classification, chatbot "
            "training, and customer service automation. Demonstrates real-world "
            "enterprise NLP applications."
        ),
        "use_case": (
            "Customer support intent classification, chatbot training, "
            "fine-grained NLP multiclass, enterprise NLP, BERT fine-tuning for support"
        ),
        "features_info": "instruction (customer message), intent (27 categories), response",
        "target": "intent",
        "target_type": "multiclass",
        "size": "26872 support conversations, 27 intents",
        "tags": ["customer-support", "intent", "nlp", "multiclass",
                 "chatbot", "enterprise", "e-commerce"],
        "domain": "NLP",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-product-reviews-multiclass",
        "name": "Amazon Multi-Domain Product Reviews",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('McAuley-Lab/Amazon-Reviews-2023', "
            "'raw_meta_All_Beauty', split='full[:1000]', trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Amazon product reviews dataset spanning multiple product categories "
            "with millions of reviews including star ratings, review text, helpful "
            "votes, and verified purchase status. Used for sentiment analysis, "
            "rating prediction, aspect-based sentiment analysis, and recommendation "
            "system research."
        ),
        "use_case": (
            "Rating prediction, aspect-based sentiment analysis, recommendation "
            "systems, regression on star ratings, multi-domain NLP generalization"
        ),
        "features_info": "reviewText, summary, overall (1-5 stars), verified, helpful votes, product category",
        "target": "overall",
        "target_type": "multiclass",
        "size": "Millions of reviews across categories",
        "tags": ["amazon", "reviews", "sentiment", "nlp", "multiclass",
                 "recommendation", "e-commerce", "rating"],
        "domain": "E-commerce",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-multilingual-sentiment",
        "name": "Multilingual Sentiment Analysis (5 Languages)",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('mteb/amazon_reviews_multi', 'en', "
            "split='train[:2000]')\n"
            "print(dataset)\n"
            "print(dataset[0])"
        ),
        "description": (
            "Multilingual Amazon product reviews dataset covering English, Japanese, "
            "German, French, and Chinese. Each review has a 1-5 star rating. "
            "Used for cross-lingual sentiment analysis and multilingual NLP model "
            "evaluation. Demonstrates how transformer models like mBERT and XLM-R "
            "handle multiple languages from a single model."
        ),
        "use_case": (
            "Multilingual sentiment analysis, cross-lingual NLP, mBERT/XLM-R, "
            "star rating prediction, 5-class classification"
        ),
        "features_info": "review_title, review_body, stars (1-5), language, product_category",
        "target": "stars",
        "target_type": "multiclass",
        "size": "210000 reviews across 5 languages",
        "tags": ["multilingual", "sentiment", "nlp", "amazon", "multiclass",
                 "cross-lingual", "xlm-r", "mbert"],
        "domain": "NLP",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "hf-abstractive-summarization",
        "name": "CNN/DailyMail News Summarization",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('abisee/cnn_dailymail', '3.0.0', "
            "split='train[:500]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "CNN/DailyMail news summarization dataset with 300k+ news articles "
            "paired with human-written bullet point summaries. The standard benchmark "
            "for abstractive text summarization. Used to evaluate and fine-tune "
            "sequence-to-sequence models like BART, T5, and Pegasus. Evaluated "
            "using ROUGE scores."
        ),
        "use_case": (
            "Abstractive summarization, seq2seq NLP, BART/T5 fine-tuning, "
            "ROUGE evaluation, long document summarization"
        ),
        "features_info": "article (full news text), highlights (bullet point summary), id",
        "target": "highlights",
        "target_type": "sequence_generation",
        "size": "311971 article-summary pairs",
        "tags": ["summarization", "nlp", "seq2seq", "bart", "t5",
                 "rouge", "news", "abstractive"],
        "domain": "NLP",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-named-entity-medical",
        "name": "Medical NER — Clinical Named Entity Recognition",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('ncats/BigBIO-drug-combo-extraction', "
            "split='train[:500]', trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Medical named entity recognition dataset for identifying drug names, "
            "diseases, symptoms, and procedures in clinical text. Part of the "
            "BigBIO biomedical NLP benchmark. Used for clinical information extraction, "
            "electronic health record (EHR) processing, and medical knowledge graph "
            "construction."
        ),
        "use_case": (
            "Medical NER, clinical information extraction, biomedical NLP, "
            "token classification, BioBERT fine-tuning, EHR processing"
        ),
        "features_info": "tokens (clinical text tokens), ner_tags (BIO tagging for medical entities)",
        "target": "ner_tags",
        "target_type": "sequence_labeling",
        "size": "500+ clinical documents",
        "tags": ["ner", "medical", "nlp", "token-classification",
                 "biobert", "clinical", "ehr", "information-extraction"],
        "domain": "Healthcare",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-stance-detection",
        "name": "SemEval Stance Detection Dataset",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('sem_eval_2016_task_6', "
            "split='train', trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0])"
        ),
        "description": (
            "SemEval-2016 Task 6 stance detection dataset with 4870 tweets about "
            "5 targets: Atheism, Climate Change, Feminist Movement, Hillary Clinton, "
            "and Legalization of Abortion. Each tweet is labelled as FAVOR, AGAINST, "
            "or NONE towards the target. Demonstrates multi-target stance classification "
            "and opinion mining."
        ),
        "use_case": (
            "Stance detection, opinion mining, NLP multiclass, political text analysis, "
            "target-dependent sentiment, debate analytics"
        ),
        "features_info": "tweet text, target (5 topics), stance (FAVOR/AGAINST/NONE)",
        "target": "stance",
        "target_type": "multiclass",
        "size": "4870 tweets, 5 targets",
        "tags": ["stance-detection", "opinion-mining", "nlp", "multiclass",
                 "political", "twitter", "semeval"],
        "domain": "NLP",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "hf-natural-language-inference",
        "name": "MultiNLI — Multi-Genre Natural Language Inference",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('multi_nli', split='train[:2000]')\n"
            "print(dataset)\n"
            "print(dataset[0])"
        ),
        "description": (
            "Multi-Genre Natural Language Inference corpus with 433k sentence pairs "
            "from 10 distinct genres (fiction, government reports, telephone speech, etc.). "
            "Each pair is labelled as entailment, contradiction, or neutral. "
            "Extends SNLI to cross-genre NLI and is used to evaluate how well "
            "NLU models generalise across domains."
        ),
        "use_case": (
            "Natural language inference, cross-genre NLU, BERT fine-tuning, "
            "textual entailment, sentence pair classification"
        ),
        "features_info": "premise, hypothesis, genre, label (entailment/contradiction/neutral)",
        "target": "label",
        "target_type": "multiclass",
        "size": "433k sentence pairs across 10 genres",
        "tags": ["nli", "entailment", "nlp", "multiclass", "bert",
                 "cross-genre", "sentence-pairs"],
        "domain": "NLP",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-code-generation",
        "name": "HumanEval Code Generation Benchmark",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('openai/openai_humaneval', split='test')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "HumanEval code generation benchmark with 164 Python programming problems "
            "created by OpenAI. Each problem includes a function signature, docstring, "
            "and unit tests. Used to evaluate LLM code generation capabilities. "
            "The standard benchmark for measuring functional correctness of "
            "AI-generated code using pass@k metric."
        ),
        "use_case": (
            "Code generation evaluation, LLM benchmarking, functional correctness "
            "assessment, pass@k metric, programming problem solving"
        ),
        "features_info": "task_id, prompt (function signature + docstring), canonical_solution, test (unit tests), entry_point",
        "target": "canonical_solution",
        "target_type": "sequence_generation",
        "size": "164 programming problems",
        "tags": ["code-generation", "llm", "benchmark", "python",
                 "programming", "pass-at-k", "humaneval"],
        "domain": "Software Engineering",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-question-generation",
        "name": "SQuAD 2.0 Reading Comprehension",
        "source": "huggingface",
        "category": "nlp",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('rajpurkar/squad_v2', split='train[:1000]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Stanford Question Answering Dataset 2.0 with 150k questions from Wikipedia. "
            "Unlike SQuAD 1.0, SQuAD 2.0 includes 50k unanswerable questions — the model "
            "must determine whether the context contains the answer. Standard benchmark "
            "for extractive question answering and reading comprehension evaluation "
            "of BERT-based models."
        ),
        "use_case": (
            "Extractive question answering, reading comprehension, BERT fine-tuning "
            "for QA, unanswerable question handling, span extraction"
        ),
        "features_info": "context (Wikipedia paragraph), question, answers (span + start position), is_impossible",
        "target": "answers",
        "target_type": "sequence_generation",
        "size": "150373 QA pairs from 505 Wikipedia articles",
        "tags": ["question-answering", "reading-comprehension", "nlp", "bert",
                 "squad", "extractive", "span-extraction"],
        "domain": "NLP",
        "difficulty": ["Hard"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 8: COMPUTER VISION — HUGGINGFACE (10)
    # =========================================================================
    {
        "id": "hf-brain-tumor-mri",
        "name": "Brain Tumor MRI Classification",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('Falah/Alzheimer_MRI', split='train[:200]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Brain MRI scan dataset for tumour classification into 4 categories: "
            "no tumour, glioma, meningioma, and pituitary tumour. Contains 7023 "
            "MRI images sourced from Figshare, SARTAJ, and Br35H datasets. "
            "A medical imaging benchmark for CNN and transfer learning using "
            "ResNet or VGG models pre-trained on ImageNet."
        ),
        "use_case": (
            "Medical image classification, brain tumour detection, transfer learning "
            "with ResNet/VGG, multiclass CV, healthcare deep learning"
        ),
        "features_info": "MRI scan images (244x244 or variable), label (no_tumor/glioma/meningioma/pituitary)",
        "target": "label",
        "target_type": "multiclass",
        "size": "7023 MRI images, 4 classes",
        "tags": ["brain-tumor", "mri", "medical-imaging", "cv",
                 "transfer-learning", "resnet", "healthcare", "deep-learning"],
        "domain": "Healthcare",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "hf-pneumonia-xray",
        "name": "Chest X-Ray Pneumonia Detection",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('keremberke/chest-xray-classification', "
            "'full', split='train[:200]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Chest X-ray pneumonia detection dataset with 5863 images of paediatric "
            "chest X-rays classified as normal or pneumonia (bacterial vs viral). "
            "Sourced from Guangzhou Women and Children's Medical Centre. Demonstrates "
            "binary medical image classification, data augmentation importance, and "
            "transfer learning from ImageNet to medical imaging."
        ),
        "use_case": (
            "Pneumonia detection, binary medical image classification, "
            "transfer learning, data augmentation for small medical datasets, CNN"
        ),
        "features_info": "chest X-ray images, label (NORMAL/PNEUMONIA)",
        "target": "label",
        "target_type": "binary",
        "size": "5863 X-ray images",
        "tags": ["pneumonia", "chest-xray", "medical-imaging", "cv",
                 "binary-classification", "transfer-learning", "healthcare"],
        "domain": "Healthcare",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-garbage-classification",
        "name": "Garbage and Waste Classification",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('garythung/trashnet', split='train[:200]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "TrashNet garbage classification dataset with 2527 images of waste "
            "across 6 categories: glass, paper, cardboard, plastic, metal, and trash. "
            "Images were taken against a white posterboard background under controlled "
            "lighting. Useful for environmental ML applications, recycling automation, "
            "and teaching basic CNN classification on real images."
        ),
        "use_case": (
            "Waste classification for recycling automation, environmental CV, "
            "multiclass CNN, transfer learning, sustainability ML"
        ),
        "features_info": "RGB images of individual waste items, label (glass/paper/cardboard/plastic/metal/trash)",
        "target": "label",
        "target_type": "multiclass",
        "size": "2527 images, 6 waste categories",
        "tags": ["garbage", "recycling", "cv", "multiclass",
                 "environmental", "sustainability", "cnn"],
        "domain": "Environmental",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "hf-traffic-signs",
        "name": "GTSRB German Traffic Sign Recognition",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('bazyl/GTSRB', split='train[:300]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "German Traffic Sign Recognition Benchmark (GTSRB) with 51839 images "
            "of 43 traffic sign classes in varying lighting, orientation, and weather "
            "conditions. A standard autonomous driving and computer vision benchmark. "
            "Images are real-world photographs with significant variation in quality, "
            "scale, and perspective."
        ),
        "use_case": (
            "Traffic sign recognition, autonomous driving CV, fine-grained "
            "multiclass classification, data augmentation for real-world variation, "
            "CNN with 43 classes"
        ),
        "features_info": "Variable-size traffic sign images (min 15x15 to max 222x193), 43 class labels",
        "target": "ClassId",
        "target_type": "multiclass",
        "size": "51839 images, 43 traffic sign classes",
        "tags": ["traffic-signs", "autonomous-driving", "cv", "multiclass",
                 "gtsrb", "real-world", "transportation"],
        "domain": "Transportation",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "hf-plant-village",
        "name": "PlantVillage Plant Disease Detection",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('plant_leaves', split='train[:200]', "
            "trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "PlantVillage plant disease dataset with 87000 images of 38 crop "
            "disease classes and healthy plants across 14 species including tomato, "
            "potato, corn, and apple. Used for precision agriculture and crop disease "
            "early detection. Demonstrates fine-grained classification for agricultural "
            "AI applications."
        ),
        "use_case": (
            "Plant disease detection, agricultural AI, fine-grained multiclass CV, "
            "transfer learning for domain-specific images, precision agriculture"
        ),
        "features_info": "Plant leaf images (RGB, 256x256), disease class label (38 classes across 14 crops)",
        "target": "label",
        "target_type": "multiclass",
        "size": "87000 images, 38 disease classes",
        "tags": ["plant-disease", "agriculture", "cv", "multiclass",
                 "transfer-learning", "precision-agriculture", "deep-learning"],
        "domain": "Agriculture",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-sign-language",
        "name": "Sign Language MNIST Hand Gesture",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('dataunification/sign_language_mnist', "
            "split='train[:500]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Sign Language MNIST dataset with 27455 training images of American "
            "Sign Language (ASL) hand gestures representing letters A-Z (excluding "
            "J and Z which require motion). Images are 28x28 grayscale similar to "
            "MNIST format. Used for accessibility AI, gesture recognition, and as "
            "a step up from MNIST for CV beginners."
        ),
        "use_case": (
            "ASL gesture recognition, accessibility AI, 24-class CV classification, "
            "CNN on grayscale images, comparison with MNIST difficulty"
        ),
        "features_info": "28x28 grayscale hand gesture images, label (24 ASL letter classes)",
        "target": "label",
        "target_type": "multiclass",
        "size": "27455 training, 7172 test images",
        "tags": ["sign-language", "asl", "cv", "multiclass",
                 "gesture-recognition", "accessibility", "mnist-format"],
        "domain": "Computer Vision",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-satellite-land-use",
        "name": "UC Merced Land Use Satellite Classification",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('Marceloxy/UCMerced_LandUse', split='train[:200]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "UC Merced Land Use dataset with 2100 aerial images from USGS National "
            "Map Urban Area Imagery, covering 21 land use categories including "
            "agricultural, airplane, beach, buildings, forest, and parking lot. "
            "A standard benchmark for remote sensing image classification and "
            "geospatial deep learning."
        ),
        "use_case": (
            "Remote sensing classification, geospatial ML, satellite imagery analysis, "
            "21-class multiclass CV, transfer learning for aerial images"
        ),
        "features_info": "256x256 RGB aerial imagery, 21 land use classes",
        "target": "label",
        "target_type": "multiclass",
        "size": "2100 aerial images, 21 land use categories",
        "tags": ["satellite", "remote-sensing", "cv", "multiclass",
                 "geospatial", "aerial", "land-use"],
        "domain": "Environmental",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-retinal-oct",
        "name": "Retinal OCT Medical Image Classification",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('keremberke/retinal-disease-classification', "
            "split='train[:200]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Retinal OCT (Optical Coherence Tomography) scan classification with "
            "84495 images across 4 classes: CNV, DME, DRUSEN, and NORMAL. "
            "Published in Cell journal (2018) with expert-validated labels from "
            "108312 total OCT images. Used for ophthalmic disease diagnosis, "
            "medical AI explainability, and CNN attention mechanisms."
        ),
        "use_case": (
            "Retinal disease diagnosis, medical imaging multiclass CV, "
            "explainable medical AI (Grad-CAM), transfer learning for OCT scans"
        ),
        "features_info": "Variable-size grayscale OCT scan images, 4 class labels (CNV/DME/DRUSEN/NORMAL)",
        "target": "label",
        "target_type": "multiclass",
        "size": "84495 OCT scans, 4 retinal classes",
        "tags": ["retinal", "oct", "medical-imaging", "cv", "multiclass",
                 "ophthalmology", "grad-cam", "healthcare"],
        "domain": "Healthcare",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-emotion-face",
        "name": "FER-2013 Facial Emotion Recognition",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('Tahahah/FER2013', split='train[:300]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Facial Emotion Recognition dataset with 35887 grayscale face images "
            "at 48x48 pixels across 7 emotion classes: angry, disgust, fear, happy, "
            "sad, surprise, and neutral. Created for the 2013 Kaggle emotion recognition "
            "challenge. Demonstrates the difficulty of human affect recognition — "
            "even humans disagree on ~65% of cases in this dataset."
        ),
        "use_case": (
            "Facial emotion recognition, 7-class CV classification, affective "
            "computing, CNN on grayscale face images, human-computer interaction"
        ),
        "features_info": "48x48 grayscale face images, 7 emotion labels (angry/disgust/fear/happy/sad/surprise/neutral)",
        "target": "label",
        "target_type": "multiclass",
        "size": "35887 face images, 7 emotion classes",
        "tags": ["emotion", "face", "cv", "multiclass", "affective-computing",
                 "grayscale", "fer2013"],
        "domain": "Computer Vision",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-document-layout",
        "name": "Document Layout Analysis (RVL-CDIP)",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('rvl_cdip', split='train[:200]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "RVL-CDIP document image classification dataset with 400000 grayscale "
            "document images across 16 categories including letter, memo, email, "
            "resume, scientific publication, invoice, and advertisement. Used for "
            "intelligent document processing and document understanding AI in "
            "enterprise settings."
        ),
        "use_case": (
            "Document classification, intelligent document processing, "
            "16-class CV classification, enterprise document AI, LayoutLM"
        ),
        "features_info": "Variable-size grayscale document images, 16 document type labels",
        "target": "label",
        "target_type": "multiclass",
        "size": "400000 document images, 16 categories",
        "tags": ["document", "cv", "multiclass", "document-understanding",
                 "enterprise", "layoutlm", "intelligent-processing"],
        "domain": "Computer Vision",
        "difficulty": ["Hard"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 9: RECOMMENDATION / UNSUPERVISED / ANOMALY / OTHER (10)
    # =========================================================================
    {
        "id": "openml-movielens-100k",
        "name": "MovieLens 100K Rating Dataset",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=25, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['rating'].value_counts())"
        ),
        "description": (
            "MovieLens 100K dataset with 100000 movie ratings (1-5 stars) from "
            "943 users on 1682 movies. The standard benchmark for collaborative "
            "filtering and recommendation system research. Contains user demographics "
            "and movie metadata. Used to teach matrix factorisation, SVD, and "
            "neural collaborative filtering."
        ),
        "use_case": (
            "Collaborative filtering, recommendation systems, matrix factorisation, "
            "SVD, neural collaborative filtering, rating prediction"
        ),
        "features_info": "user_id, item_id (movie), rating (1-5), timestamp, user demographics, movie genres",
        "target": "rating",
        "target_type": "multiclass",
        "size": "100000 ratings, 943 users, 1682 movies",
        "tags": ["recommendation", "collaborative-filtering", "ratings",
                 "svd", "matrix-factorisation", "movies", "user-item"],
        "domain": "Media",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-nsl-kdd",
        "name": "NSL-KDD Network Intrusion Detection",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=41672, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['label'].value_counts())"
        ),
        "description": (
            "NSL-KDD network intrusion detection dataset, an improved version of "
            "the KDD Cup 1999 dataset. Contains 125973 network connection records "
            "with 41 features describing TCP/IP connections. Classifies connections "
            "as normal or one of 4 attack types: DoS, Probe, R2L, U2R. "
            "The standard benchmark for network security ML."
        ),
        "use_case": (
            "Network intrusion detection, cybersecurity ML, multiclass classification, "
            "anomaly detection in network traffic, DoS attack detection"
        ),
        "features_info": (
            "41 features: duration, protocol_type, service, flag, src_bytes, dst_bytes, "
            "land, wrong_fragment, urgent, hot, num_failed_logins, logged_in, "
            "num_compromised, root_shell, su_attempted, num_root, num_file_creations, "
            "num_shells, num_access_files, is_host_login, is_guest_login, count, "
            "srv_count, serror_rate, srv_serror_rate, rerror_rate, srv_rerror_rate, "
            "same_srv_rate, diff_srv_rate, srv_diff_host_rate, dst_host_count, etc."
        ),
        "target": "label",
        "target_type": "multiclass",
        "size": "125973 rows x 42 features",
        "tags": ["network-intrusion", "cybersecurity", "anomaly-detection",
                 "multiclass", "dos", "network-security", "kdd"],
        "domain": "Cybersecurity",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "openml-ecg-heartbeat",
        "name": "ECG Heartbeat Arrhythmia Classification",
        "source": "openml",
        "category": "time-series",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=1114, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['target'].value_counts())"
        ),
        "description": (
            "MIT-BIH arrhythmia ECG heartbeat dataset with 109446 heartbeat samples "
            "from 48 half-hour ECG recordings. Each sample contains 187 time steps "
            "representing one heartbeat cycle. Classified into 5 arrhythmia types. "
            "Used for 1D signal classification, LSTM on medical time-series, and "
            "automated cardiac diagnosis."
        ),
        "use_case": (
            "ECG arrhythmia classification, 1D CNN on time-series signals, "
            "LSTM on medical data, automated cardiac diagnosis, multiclass medical"
        ),
        "features_info": "187 time-step ECG signal values per heartbeat + 1 label",
        "target": "target",
        "target_type": "multiclass",
        "size": "109446 heartbeat samples x 188 features",
        "tags": ["ecg", "arrhythmia", "healthcare", "time-series",
                 "1d-cnn", "lstm", "medical", "signal"],
        "domain": "Healthcare",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "openml-mall-customers",
        "name": "Mall Customer Segmentation",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43477, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df.dtypes)"
        ),
        "description": (
            "Mall customer segmentation dataset with 200 mall customers and their "
            "age, gender, annual income, and spending score. The most beginner-friendly "
            "clustering dataset — commonly used to introduce K-Means, the Elbow method, "
            "and customer segmentation concepts. RFM-style features make business "
            "interpretation intuitive."
        ),
        "use_case": (
            "Customer segmentation, K-Means clustering, Elbow method, "
            "unsupervised learning introduction, RFM analysis basics"
        ),
        "features_info": "CustomerID, Gender, Age, Annual_Income (k$), Spending_Score (1-100)",
        "target": "Spending_Score",
        "target_type": "continuous",
        "size": "200 rows x 5 features",
        "tags": ["clustering", "segmentation", "unsupervised", "kmeans",
                 "retail", "customer", "beginner"],
        "domain": "Retail",
        "difficulty": ["Easy"],
        "direct_load": True
    },
    {
        "id": "openml-country-clustering",
        "name": "Country Socioeconomic Clustering (HELP)",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43475, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df.dtypes)"
        ),
        "description": (
            "HELP International NGO dataset with socioeconomic and health indicators "
            "for 167 countries. Includes child mortality, exports, health spending, "
            "imports, income, inflation, life expectancy, fertility rate, and GDP. "
            "Used to identify countries in dire need of aid using clustering. "
            "Real-world humanitarian analytics use case."
        ),
        "use_case": (
            "Country clustering for humanitarian aid, K-Means on socioeconomic data, "
            "PCA for visualisation, hierarchical clustering, development economics ML"
        ),
        "features_info": (
            "9 features: child_mort (per 1000), exports (% GDP), health (% GDP), "
            "imports (% GDP), income (per capita), inflation, life_expec, "
            "total_fer (fertility rate), gdpp (GDP per capita)"
        ),
        "target": "country",
        "target_type": "multiclass",
        "size": "167 rows x 10 features",
        "tags": ["clustering", "socioeconomics", "humanitarian", "kmeans",
                 "pca", "development", "world-data"],
        "domain": "Socioeconomics",
        "difficulty": ["Easy", "Medium"],
        "direct_load": True
    },
    {
        "id": "openml-zomato-restaurants",
        "name": "Zomato Restaurant Ratings Prediction",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43550, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['rate'].describe())"
        ),
        "description": (
            "Zomato Bangalore restaurant dataset with 51717 restaurant records. "
            "Contains restaurant name, location, cuisines, cost for two, votes, "
            "and customer rating. Useful for hospitality analytics, rating prediction, "
            "and feature engineering on text-based cuisines and location data. "
            "A practical EDA and regression dataset."
        ),
        "use_case": (
            "Restaurant rating prediction, hospitality analytics, regression, "
            "text-based feature engineering (cuisines), location-based analysis"
        ),
        "features_info": (
            "17 features: url, address, name, online_order, book_table, rate, votes, "
            "phone, location, rest_type, dish_liked, cuisines, approx_cost (for two), "
            "reviews_list, menu_item, listed_in_type, listed_in_city"
        ),
        "target": "rate",
        "target_type": "continuous",
        "size": "51717 rows x 17 features",
        "tags": ["restaurant", "hospitality", "regression", "rating",
                 "food", "location", "zomato"],
        "domain": "Hospitality",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-black-friday",
        "name": "Black Friday Sales Purchase Analysis",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=41540, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Purchase'].describe())"
        ),
        "description": (
            "Black Friday retail sales dataset with 537577 purchase transactions "
            "from a retail company. Contains customer demographics, product categories, "
            "and purchase amounts. Used for purchase amount prediction, customer "
            "profiling, and retail analytics. Large dataset good for testing "
            "scalability of ML pipelines."
        ),
        "use_case": (
            "Purchase amount prediction, retail analytics, regression, "
            "customer profiling, large-scale feature engineering"
        ),
        "features_info": (
            "12 features: User_ID, Product_ID, Gender, Age, Occupation, "
            "City_Category, Stay_In_Current_City_Years, Marital_Status, "
            "Product_Category_1, Product_Category_2, Product_Category_3"
        ),
        "target": "Purchase",
        "target_type": "continuous",
        "size": "537577 rows x 12 features",
        "tags": ["retail", "sales", "regression", "black-friday",
                 "purchase", "customer-profiling", "large-scale"],
        "domain": "Retail",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-olympic-athletes",
        "name": "120 Years of Olympic Athletes History",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml(data_id=43458, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['Medal'].value_counts())"
        ),
        "description": (
            "120 years of Olympic Games athlete data from Athens 1896 to Rio 2016 "
            "with 271116 athlete-event records. Contains athlete age, height, weight, "
            "country, sport, event, and medal won. A rich dataset for sports analytics, "
            "medal prediction, historical trend analysis, and exploratory data analysis "
            "with temporal and categorical features."
        ),
        "use_case": (
            "Medal prediction, sports analytics, multiclass classification with imbalance, "
            "historical trend analysis, feature engineering on demographics"
        ),
        "features_info": (
            "15 features: ID, Name, Sex, Age, Height, Weight, Team, NOC (country code), "
            "Games, Year, Season, City, Sport, Event, Medal (Gold/Silver/Bronze/NA)"
        ),
        "target": "Medal",
        "target_type": "multiclass",
        "size": "271116 rows x 15 features",
        "tags": ["sports", "olympics", "multiclass", "imbalanced",
                 "historical", "athletics", "eda"],
        "domain": "Sports",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-human-activity-recognition",
        "name": "UCI HAR Human Activity Recognition",
        "source": "huggingface",
        "category": "tabular",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('qgyd2021/human_activity_recognition', "
            "split='train[:2000]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Human Activity Recognition dataset from UCI with 10299 smartphone "
            "sensor recordings. 561 features derived from accelerometer and gyroscope "
            "signals from 30 volunteers performing 6 activities: walking, walking "
            "upstairs, walking downstairs, sitting, standing, and laying. The classic "
            "IoT sensor classification benchmark."
        ),
        "use_case": (
            "Activity recognition, IoT sensor classification, multiclass classification, "
            "high-dimensional feature reduction (PCA), wearable health monitoring"
        ),
        "features_info": "561 statistical features from smartphone accelerometer and gyroscope (time/frequency domain)",
        "target": "activity",
        "target_type": "multiclass",
        "size": "10299 rows x 562 features",
        "tags": ["activity-recognition", "iot", "sensor", "multiclass",
                 "wearable", "accelerometer", "smartphone"],
        "domain": "IoT",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "openml-titanic-survival",
        "name": "Titanic Passenger Survival (Extended)",
        "source": "openml",
        "category": "tabular",
        "pip_install": "pip install scikit-learn pandas",
        "import_code": "from sklearn.datasets import fetch_openml\nimport pandas as pd",
        "load_code": (
            "data = fetch_openml('titanic', version=1, as_frame=True, parser='auto')\n"
            "df = data.frame\n"
            "print(df.shape)\n"
            "print(df.head())\n"
            "print(df['survived'].value_counts())"
        ),
        "description": (
            "Extended Titanic passenger survival dataset with 1309 passengers and "
            "additional features beyond the Seaborn version including cabin number, "
            "ticket number, and fare. The most famous binary classification benchmark "
            "in data science education. Demonstrates feature engineering (title from "
            "name, deck from cabin), missing value imputation, and survival analysis."
        ),
        "use_case": (
            "Survival prediction, binary classification, feature engineering, "
            "missing value imputation, teaching ML fundamentals"
        ),
        "features_info": (
            "13 features: pclass, survived, name, sex, age, sibsp, parch, ticket, "
            "fare, cabin, embarked, boat, body"
        ),
        "target": "survived",
        "target_type": "binary",
        "size": "1309 rows x 14 features",
        "tags": ["titanic", "survival", "binary-classification", "feature-engineering",
                 "missing-values", "beginner", "teaching"],
        "domain": "Transportation",
        "difficulty": ["Easy"],
        "direct_load": True
    },

    # =========================================================================
    # GROUP 10: AUDIO / GRAPH / DEEP LEARNING SPECIAL (5)
    # =========================================================================
    {
        "id": "hf-audio-emotion",
        "name": "RAVDESS Speech Emotion Recognition",
        "source": "huggingface",
        "category": "audio",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('narad/ravdess', split='train[:100]', "
            "trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "RAVDESS (Ryerson Audio-Visual Database of Emotional Speech and Song) "
            "with 1440 audio recordings from 24 professional actors. 8 emotion "
            "categories: neutral, calm, happy, sad, angry, fearful, disgust, surprised. "
            "The standard benchmark for Speech Emotion Recognition (SER) using "
            "MFCC features and deep learning."
        ),
        "use_case": (
            "Speech emotion recognition, audio multiclass classification, "
            "MFCC feature extraction, 1D CNN on audio, affective computing"
        ),
        "features_info": "Audio recordings (24.576 kHz WAV), 8 emotion classes, speech and song modalities",
        "target": "emotion",
        "target_type": "multiclass",
        "size": "1440 audio clips, 8 emotion classes",
        "tags": ["speech-emotion", "audio", "multiclass", "mfcc",
                 "ravdess", "affective-computing", "1d-cnn"],
        "domain": "Audio/Speech",
        "difficulty": ["Medium", "Hard"],
        "direct_load": True
    },
    {
        "id": "pyg-citeseer",
        "name": "CiteSeer Citation Graph Network",
        "source": "torch_geometric",
        "category": "graph",
        "pip_install": "pip install torch torch_geometric",
        "import_code": "from torch_geometric.datasets import Planetoid",
        "load_code": (
            "dataset = Planetoid(root='/tmp/CiteSeer', name='CiteSeer')\n"
            "data = dataset[0]\n"
            "print(f'Nodes: {data.num_nodes}, Edges: {data.num_edges}')\n"
            "print(f'Features: {data.x.shape}, Classes: {dataset.num_classes}')"
        ),
        "description": (
            "CiteSeer citation network with 3327 scientific publications and 4732 "
            "citation links. Each paper has a 3703-dimensional bag-of-words feature "
            "vector and belongs to one of 6 research areas: Agents, ML, IR, DB, HCI, AI. "
            "Alongside Cora, CiteSeer is the second standard GNN benchmark used in "
            "GCN, GAT, and GraphSAGE papers."
        ),
        "use_case": (
            "Graph node classification, GNN benchmarking, semi-supervised learning, "
            "GCN/GAT comparison, citation network analysis"
        ),
        "features_info": "3327 nodes (papers), 4732 edges (citations), 3703 BoW features per node, 6 class labels",
        "target": "research_area",
        "target_type": "multiclass",
        "size": "3327 nodes, 4732 edges",
        "tags": ["graph", "gnn", "node-classification", "citation-network",
                 "gcn", "gat", "semi-supervised", "benchmark"],
        "domain": "Academic",
        "difficulty": ["Medium"],
        "direct_load": True
    },
    {
        "id": "hf-mnist-fashion-extended",
        "name": "DeepFashion Clothing Attribute Recognition",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('detection-datasets/fashionpedia', "
            "split='train[:200]')\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "DeepFashion Fashionpedia dataset with fine-grained clothing attribute "
            "recognition across 27 apparel categories and 294 fine-grained attributes. "
            "Contains 48825 fashion images with segmentation masks and multi-label "
            "attribute annotations. Used for e-commerce product cataloguing, "
            "fashion recommendation, and instance segmentation."
        ),
        "use_case": (
            "Fashion attribute recognition, multi-label CV, instance segmentation, "
            "e-commerce product tagging, fine-grained classification"
        ),
        "features_info": "Fashion product images, 27 category labels, 294 fine-grained attribute annotations",
        "target": "category",
        "target_type": "multilabel",
        "size": "48825 fashion images",
        "tags": ["fashion", "cv", "multi-label", "e-commerce",
                 "segmentation", "attribute-recognition", "fine-grained"],
        "domain": "Retail",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-visual-question-answering",
        "name": "VQA Visual Question Answering",
        "source": "huggingface",
        "category": "cv",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('HuggingFaceM4/VQAv2', split='validation[:200]', "
            "trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "Visual Question Answering v2 dataset with 1.1M image-question pairs. "
            "Each sample contains an image, a natural language question about the image, "
            "and 10 human-provided answers. Requires both visual understanding and "
            "language comprehension. The standard multimodal AI benchmark for "
            "vision-language models."
        ),
        "use_case": (
            "Visual question answering, multimodal AI, vision-language models, "
            "BLIP/CLIP fine-tuning, image+text joint understanding"
        ),
        "features_info": "Image (RGB), question (text), multiple_choice_answer, answers (10 human responses)",
        "target": "multiple_choice_answer",
        "target_type": "multiclass",
        "size": "1.1M image-question pairs",
        "tags": ["vqa", "multimodal", "cv", "nlp", "vision-language",
                 "blip", "clip", "deep-learning"],
        "domain": "Computer Vision",
        "difficulty": ["Hard"],
        "direct_load": True
    },
    {
        "id": "hf-speech-to-text-librispeech-clean",
        "name": "LibriSpeech Clean 360h ASR Dataset",
        "source": "huggingface",
        "category": "audio",
        "pip_install": "pip install datasets",
        "import_code": "from datasets import load_dataset",
        "load_code": (
            "dataset = load_dataset('librispeech_asr', 'clean', "
            "split='train.360[:100]', trust_remote_code=True)\n"
            "print(dataset)\n"
            "print(dataset[0].keys())"
        ),
        "description": (
            "LibriSpeech clean 360-hour ASR corpus derived from LibriVox audiobooks. "
            "Larger split of the LibriSpeech benchmark providing 360 hours of clean "
            "read speech with transcripts. Used for fine-tuning Whisper and wav2vec 2.0 "
            "for custom ASR applications and comparing ASR model architectures."
        ),
        "use_case": (
            "Large-scale ASR fine-tuning, Whisper fine-tuning, wav2vec 2.0 evaluation, "
            "speech recognition benchmarking, audio transcription"
        ),
        "features_info": "16kHz mono audio clips with word-level transcripts, speaker IDs, chapter metadata",
        "target": "text",
        "target_type": "sequence_generation",
        "size": "360 hours of speech, 104014 utterances",
        "tags": ["asr", "speech", "audio", "librispeech", "whisper",
                 "wav2vec", "transcription", "large-scale"],
        "domain": "Audio/Speech",
        "difficulty": ["Hard"],
        "direct_load": True
    },
]


# =============================================================================
# MERGE WITH EXISTING CATALOG
# =============================================================================

def main():
    # Load existing catalog
    if not os.path.exists(CATALOG_INPUT):
        print(f"ERROR: {CATALOG_INPUT} not found. Place this script in the same folder.")
        return

    with open(CATALOG_INPUT, encoding="utf-8") as f:
        existing = json.load(f)

    existing_ids = {d["id"] for d in existing}
    print(f"Existing catalog: {len(existing)} datasets")
    print(f"New datasets to add: {len(NEW_DATASETS)}")
    print()

    # Validate every new entry has all required fields
    required = [
        "id", "name", "source", "category", "pip_install", "import_code",
        "load_code", "description", "use_case", "features_info", "target",
        "target_type", "size", "tags", "domain", "difficulty", "direct_load"
    ]
    valid_cats  = {"tabular", "nlp", "cv", "audio", "time-series", "graph"}
    valid_diffs = {"Easy", "Medium", "Hard"}

    errors   = []
    added    = []
    skipped  = []

    for d in NEW_DATASETS:
        # Skip if already exists
        if d["id"] in existing_ids:
            skipped.append(d["id"])
            continue

        # Check all fields present and non-empty
        entry_errors = []
        for f in required:
            if f not in d:
                entry_errors.append(f"MISSING field '{f}'")
            elif d[f] is None or d[f] == "" or d[f] == [] or d[f] == {}:
                entry_errors.append(f"EMPTY field '{f}'")

        # Check category
        if d.get("category") not in valid_cats:
            entry_errors.append(f"INVALID category '{d.get('category')}'")

        # Check difficulty values
        if not all(v in valid_diffs for v in d.get("difficulty", [])):
            entry_errors.append(f"INVALID difficulty values {d.get('difficulty')}")

        # Check direct_load is bool
        if not isinstance(d.get("direct_load"), bool):
            entry_errors.append("direct_load must be bool")

        if entry_errors:
            errors.append(f"  {d['id']}: {'; '.join(entry_errors)}")
        else:
            added.append(d)
            existing_ids.add(d["id"])

    # Report errors
    if errors:
        print("VALIDATION ERRORS (these entries were NOT added):")
        for e in errors:
            print(e)
        print()

    # Report skips
    if skipped:
        print(f"Skipped {len(skipped)} already-existing IDs:")
        for s in skipped:
            print(f"  {s}")
        print()

    # Merge
    merged = existing + added

    # Final duplicate check
    all_ids = [d["id"] for d in merged]
    from collections import Counter
    dupes = {k: v for k, v in Counter(all_ids).items() if v > 1}
    if dupes:
        print(f"WARNING: Duplicate IDs in merged catalog: {dupes}")

    # Write output
    with open(CATALOG_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # Summary
    from collections import Counter
    cats    = Counter(d["category"] for d in merged)
    domains = Counter(d["domain"] for d in merged)
    srcs    = Counter(d["source"] for d in merged)

    print("=" * 60)
    print(f"DONE — {CATALOG_OUTPUT} written")
    print(f"  Existing datasets : {len(existing)}")
    print(f"  New added         : {len(added)}")
    print(f"  Skipped (existed) : {len(skipped)}")
    print(f"  Errors skipped    : {len(errors)}")
    print(f"  TOTAL             : {len(merged)}")
    print()
    print("Category breakdown:")
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {k:20s}: {v}")
    print()
    print("Source breakdown:")
    for k, v in sorted(srcs.items(), key=lambda x: -x[1]):
        print(f"  {k:20s}: {v}")
    print()
    print("Domain coverage:")
    for k, v in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"  {k:30s}: {v}")
    print("=" * 60)
    print()
    print("NEXT STEPS:")
    print(f"  1. Rename {CATALOG_OUTPUT} → {CATALOG_INPUT}")
    print(f"  2. Run: python build_aiml_faiss.py")
    print(f"  3. Restart api_server.py")


if __name__ == "__main__":
    main()
