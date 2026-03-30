import streamlit as st
import matplotlib.pyplot as plt
import requests
import pandas as pd
import time
import os
from datetime import datetime, timezone

API_BASE = os.environ.get("API_BASE", "http://localhost:9000/api/v1")
_SERVER_BASE = API_BASE.replace("/api/v1", "")
BILLING_BASE = f"{_SERVER_BASE.rstrip('/')}/billing/v1"

st.set_page_config(
    page_title="Qwen Question Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "last_health_check" not in st.session_state:
    st.session_state.last_health_check = 0
if "pending_job_id" not in st.session_state:
    st.session_state.pending_job_id = None
if "pending_poll_url" not in st.session_state:
    st.session_state.pending_poll_url = None
if "job_start_ts" not in st.session_state:
    st.session_state.job_start_ts = None
if "org_id" not in st.session_state:
    st.session_state.org_id = ""

is_generating = st.session_state.pending_job_id is not None


def request_headers() -> dict:
    """Headers for API calls — includes X-Org-Id when set (metering / org context)."""
    oid = (st.session_state.get("org_id") or "").strip()
    return {"X-Org-Id": oid} if oid else {}


def render_usage_dashboard():
    """Usage & billing explorer (GET /billing/v1/*)."""
    st.title("📊 Usage & billing")
    st.caption(
        "Per-organization token usage and call counts from the gisul billing API. "
        "Set **Organization ID** in the sidebar (same as `X-Org-Id`). "
        "Server must have `MONGODB_URI` and database `aaptor_model` on the cluster."
    )

    qorg = (st.session_state.get("org_id") or "").strip()
    if not qorg:
        st.warning(
            "Enter an **Organization ID** in the sidebar (e.g. `ORG002`) to load org-specific tabs. "
            "The **All orgs (admin)** tab still works without it."
        )
    else:
        st.success(f"Reporting for organization **`{qorg}`**")

    default_period = datetime.now(timezone.utc).strftime("%Y-%m")
    period = st.text_input("Billing period (YYYY-MM)", value=default_period, key="dash_period")

    tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs(
        ["Current period", "By route", "Monthly history", "Recent logs", "All orgs (admin)"]
    )

    def _safe_get(url: str, params=None):
        try:
            r = requests.get(url, params=params or {}, timeout=45)
            return r.status_code, r.json() if r.content else {}, r.text
        except Exception as ex:
            return -1, {}, str(ex)

    with tab_a:
        if not qorg:
            st.warning("Set **Organization ID** in the sidebar (or above) to load usage.")
        else:
            code, data, raw = _safe_get(f"{BILLING_BASE}/orgs/{qorg}/usage/current")
            if code != 200:
                st.error(f"Could not load current usage (HTTP {code}). {raw[:800]}")
            else:
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Total tokens", f"{data.get('total_tokens', 0):,}")
                with m2:
                    st.metric("Calls", data.get("call_count", 0))
                with m3:
                    st.metric("Prompt tokens", f"{data.get('prompt_tokens', 0):,}")
                with m4:
                    st.metric("Completion tokens", f"{data.get('completion_tokens', 0):,}")
                st.caption(f"Billing period: **{data.get('billing_period', period)}**")
                avg = data.get("avg_latency_ms")
                if avg is not None:
                    st.metric("Avg latency (ms)", f"{float(avg):.1f}")
                with st.expander("Raw JSON"):
                    st.json(data)

    with tab_b:
        if not qorg:
            st.warning("Organization ID required.")
        else:
            code, data, raw = _safe_get(
                f"{BILLING_BASE}/orgs/{qorg}/usage/by-route",
                params={"period": period},
            )
            if code != 200:
                st.error(f"HTTP {code}: {raw[:800]}")
            else:
                routes = data.get("routes") or []
                if not routes:
                    st.info("No usage rows for this org/period yet.")
                else:
                    rows = []
                    for row in routes:
                        rid = row.get("_id") or row.get("route")
                        rows.append(
                            {
                                "route": rid,
                                "total_tokens": row.get("total_tokens", 0),
                                "call_count": row.get("call_count", 0),
                                "cache_hits": row.get("cache_hits", 0),
                                "avg_latency_ms": row.get("avg_latency_ms"),
                            }
                        )
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    try:
                        chart_df = pd.DataFrame(rows).head(20)
                        if not chart_df.empty and chart_df["total_tokens"].sum() > 0:
                            st.bar_chart(chart_df.set_index("route")["total_tokens"])
                    except Exception:
                        pass
                with st.expander("Raw JSON"):
                    st.json(data)

    with tab_c:
        if not qorg:
            st.warning("Organization ID required.")
        else:
            code, data, raw = _safe_get(f"{BILLING_BASE}/orgs/{qorg}/usage/history")
            if code != 200:
                st.error(f"HTTP {code}: {raw[:800]}")
            else:
                hist = data.get("history") or []
                if not hist:
                    st.info("No history yet.")
                else:
                    df = pd.DataFrame(
                        [
                            {
                                "month": h.get("_id"),
                                "total_tokens": h.get("total_tokens", 0),
                                "call_count": h.get("call_count", 0),
                            }
                            for h in hist
                        ]
                    )
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    try:
                        st.line_chart(df.set_index("month")["total_tokens"])
                    except Exception:
                        pass
                with st.expander("Raw JSON"):
                    st.json(data)

    with tab_d:
        if not qorg:
            st.warning("Organization ID required.")
        else:
            page = st.number_input("Page", min_value=1, max_value=500, value=1, step=1, key="logs_page")
            ps = st.selectbox("Page size", [25, 50, 100, 200], index=1, key="logs_ps")
            code, data, raw = _safe_get(
                f"{BILLING_BASE}/orgs/{qorg}/usage/logs",
                params={"period": period, "page": int(page), "page_size": int(ps)},
            )
            if code != 200:
                st.error(f"HTTP {code}: {raw[:800]}")
            else:
                logs = data.get("logs") or []
                if not logs:
                    st.info("No log rows for this page/period.")
                else:
                    flat = []
                    for row in logs:
                        flat.append(
                            {
                                "created_at": row.get("created_at"),
                                "route": row.get("route"),
                                "total_tokens": row.get("total_tokens"),
                                "status": row.get("status"),
                                "cache_hit": row.get("cache_hit"),
                                "latency_ms": row.get("latency_ms"),
                                "job_id": row.get("job_id"),
                            }
                        )
                    st.dataframe(pd.DataFrame(flat), use_container_width=True, hide_index=True)
                with st.expander("Raw JSON"):
                    st.json(data)

    with tab_e:
        st.caption("Aggregated usage across **all** orgs for the selected period (operator view).")
        code, data, raw = _safe_get(f"{BILLING_BASE}/admin/usage", params={"period": period})
        if code != 200:
            st.error(f"HTTP {code}: {raw[:800]}")
        else:
            orgs = data.get("orgs") or []
            if not orgs:
                st.info("No usage in this period yet.")
            else:
                rows = []
                for row in orgs:
                    rows.append(
                        {
                            "org_id": row.get("_id"),
                            "total_tokens": row.get("total_tokens", 0),
                            "call_count": row.get("call_count", 0),
                        }
                    )
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
                try:
                    st.bar_chart(df.set_index("org_id")["total_tokens"].head(30))
                except Exception:
                    pass
            with st.expander("Raw JSON"):
                st.json(data)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ App")
    view_mode = st.radio(
        "View",
        ["generator", "usage"],
        format_func=lambda x: "🧠 Question generator" if x == "generator" else "📊 Usage & billing",
    )
    st.text_input(
        "Organization ID (X-Org-Id)",
        key="org_id",
        placeholder="e.g. ORG002 — leave empty for unattributed",
        help="Sent on every generation request for per-org metering. Match `orgId` in MongoDB.",
    )
    st.divider()
    st.header("⚙️ Server Controls")

    _health_cooldown = 10
    _now = time.time()
    _since_last = _now - st.session_state.last_health_check
    _health_disabled = _since_last < _health_cooldown
    _health_label = (
        f"🔍 Check Server Health ({int(_health_cooldown - _since_last)}s)"
        if _since_last < _health_cooldown
        else "🔍 Check Server Health"
    )

    if st.button(_health_label, use_container_width=True,
                 disabled=_health_disabled or is_generating, key="health_btn"):
        st.session_state.last_health_check = time.time()
        try:
            r = requests.get(f"{_SERVER_BASE}/health", timeout=5)
            h = r.json()
            if h.get("status") == "healthy":
                st.success("Server is healthy ✅")
                col_a, col_b = st.columns(2)
                with col_a:
                    model_ok = h.get("model_loaded", False)
                    st.metric("Model", "Loaded ✅" if model_ok else "Not loaded ❌")
                with col_b:
                    mem = h.get("memory_gb", 0)
                    st.metric("GPU Memory", f"{round(mem, 2)} GB" if mem and mem > 0 else "N/A")
                col_c, col_d = st.columns(2)
                with col_c:
                    st.metric("Active Jobs", h.get("active_jobs", 0))
                with col_d:
                    st.metric("Jobs in Store", h.get("total_jobs_in_store", 0))
                qs = h.get("queue_sizes", {})
                stuck = {k: v for k, v in qs.items() if v > 0}
                if stuck:
                    st.warning(f"⚠️ Stuck queue items: {stuck}")
                else:
                    st.caption("All queues empty ✅")
            else:
                st.warning("Server responded but may not be fully ready.")
        except Exception as e:
            st.error(f"Cannot reach server at `{_SERVER_BASE}`: {e}")

    st.divider()

    st.subheader("🗑️ Cache")
    use_cache = st.toggle("Use Cache", value=True,
                          help="Uncheck to bypass cache and always regenerate fresh questions.")

    if st.button("🧹 Clear Cache", use_container_width=True, type="secondary", disabled=is_generating):
        try:
            r = requests.post(f"{API_BASE}/clear-cache", timeout=10)
            st.success(f"✅ {r.json().get('message', 'Cache cleared')}")
        except Exception as e:
            st.error(f"Failed to clear cache: {e}")

    st.divider()

    if st.button("📊 View Stats", use_container_width=True, key="stats_btn", disabled=is_generating):
        try:
            r = requests.get(f"{_SERVER_BASE}/stats", timeout=5)
            s = r.json()
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.metric("Total Requests", s.get("total_requests", 0))
                st.metric("Cache Hit Rate", f"{s.get('cache_hit_rate_percent', 0)}%")
            with col_s2:
                st.metric("Errors", s.get("errors", 0))
                st.metric("Avg Batch Size", s.get("avg_batch_size", 0))
            by_ep = s.get("requests_by_endpoint", {})
            if by_ep:
                st.caption("Requests by endpoint: " + ", ".join(f"{k}: {v}" for k, v in by_ep.items()))
        except Exception as e:
            st.error(f"Could not fetch stats: {e}")

if view_mode == "usage":
    render_usage_dashboard()
    st.stop()

st.title("🧠 Qwen Question Generator")

# ─────────────────────────────────────────────
# ENDPOINT SELECTOR
# ─────────────────────────────────────────────
ENDPOINTS = [
    "generate-topics",
    "generate-mcq",
    "generate-subjective",
    "generate-coding",
    "generate-sql",
    "generate-aiml",
    "generate-aiml-library",
    "generate-dsa-question",
]

ENDPOINT_LABELS = {
    "generate-topics":       "📋 Generate Topics",
    "generate-mcq":          "✅ Multiple Choice (MCQ)",
    "generate-subjective":   "✍️  Subjective Questions",
    "generate-coding":       "💻 Coding Problems",
    "generate-sql":          "🗄️  SQL Problems",
    "generate-aiml":         "🤖 AI/ML Synthetic Problems",
    "generate-aiml-library": "📚 AI/ML Library Dataset Problems",
    "generate-dsa-question": "🔢 DSA Question (FAISS RAG)",
}

endpoint = st.selectbox(
    "Choose Endpoint",
    ENDPOINTS,
    format_func=lambda x: ENDPOINT_LABELS[x],
)

st.divider()

# ─────────────────────────────────────────────
# INPUTS
# ─────────────────────────────────────────────
needs_topic_fields  = endpoint in ("generate-mcq", "generate-subjective",
                                   "generate-coding", "generate-sql",
                                   "generate-aiml", "generate-aiml-library",
                                   "generate-dsa-question")
needs_topics_fields = endpoint == "generate-topics"
needs_language      = endpoint == "generate-coding"
needs_db_type       = endpoint == "generate-sql"
needs_audience      = endpoint in ("generate-mcq", "generate-subjective")
needs_concepts      = endpoint in ("generate-aiml-library", "generate-dsa-question")
needs_dsa_languages = endpoint == "generate-dsa-question"

st.subheader("🔧 Request Parameters")

col1, col2, col3 = st.columns(3)
with col1:
    if endpoint not in ("generate-aiml", "generate-aiml-library", "generate-dsa-question"):
        num_questions = st.number_input(
            "Number of Questions / Items",
            min_value=1, max_value=20, value=3,
            help="How many items to generate in a single request."
        )
    else:
        num_questions = 1

if needs_topics_fields:
    col1b, col2b = st.columns(2)
    with col1b:
        assessment_title = st.text_input("Assessment Title", "Python Developer Assessment")
        job_designation  = st.text_input("Job Designation", "Software Developer")
        skills           = st.text_input("Skills (comma separated)", "Python, FastAPI, SQL")
    with col2b:
        experience_min = st.number_input("Min Experience (yrs)", 0, 30, 1)
        experience_max = st.number_input("Max Experience (yrs)", 0, 30, 3)

if needs_topic_fields:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        topic = st.text_input("Topic", "Arrays and Hash Maps" if endpoint == "generate-dsa-question" else "Python list slicing")
    with col_t2:
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])

if needs_audience:
    target_audience = st.text_input("Target Audience", "Mid-level Software Developers")

if needs_language:
    language = st.selectbox("Language", ["Python", "JavaScript", "Java", "C++", "Go", "TypeScript"])

if needs_db_type:
    database_type = st.selectbox("Database Type", ["PostgreSQL", "MySQL", "SQLite", "MS SQL Server"])

if endpoint in ("generate-coding", "generate-sql"):
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        job_role = st.text_input("Job Role", "Software Engineer")
    with col_r2:
        experience_years = st.selectbox(
            "Experience Level",
            ["0-1 (Fresher)", "1-3 (Junior)", "3-5 (Mid-level)", "5-8 (Senior)", "8+ (Staff/Principal)"],
            index=2,
        )

if needs_concepts:
    concepts_input = st.text_input(
        "Concepts (comma separated)",
        "binary search, two pointers" if endpoint == "generate-dsa-question" else "classification, imbalanced data",
        help="Concepts to match against the dataset catalog using semantic search"
    )

if needs_dsa_languages:
    dsa_languages = st.multiselect(
        "Starter Code Languages",
        ["python", "java", "javascript", "typescript", "kotlin", "go", "rust", "cpp", "csharp", "c"],
        default=["python", "java", "javascript"],
        help="Which languages to include in starter code"
    )

st.divider()

# ─────────────────────────────────────────────
# PAYLOAD BUILDER
# ─────────────────────────────────────────────
def build_payload() -> dict:
    base = {"num_questions": int(num_questions), "use_cache": use_cache}

    if endpoint == "generate-topics":
        base.update({
            "assessment_title": assessment_title,
            "job_designation":  job_designation,
            "skills":           [s.strip() for s in skills.split(",") if s.strip()],
            "experience_min":   int(experience_min),
            "experience_max":   int(experience_max),
            "num_topics":       int(num_questions),
        })
    elif endpoint == "generate-mcq":
        base.update({"topic": topic, "difficulty": difficulty, "target_audience": target_audience})
    elif endpoint == "generate-subjective":
        base.update({"topic": topic, "difficulty": difficulty, "target_audience": target_audience})
    elif endpoint == "generate-coding":
        base.update({"topic": topic, "difficulty": difficulty, "language": language,
                     "job_role": job_role, "experience_years": experience_years})
    elif endpoint == "generate-sql":
        base.update({"topic": topic, "difficulty": difficulty, "database_type": database_type,
                     "job_role": job_role, "experience_years": experience_years})
    elif endpoint == "generate-aiml":
        base = {"use_cache": use_cache, "topic": topic, "difficulty": difficulty}
    elif endpoint == "generate-aiml-library":
        concepts_list = [c.strip() for c in concepts_input.split(",") if c.strip()]
        base = {
            "use_cache":  use_cache,
            "topic":      topic,
            "difficulty": difficulty,
            "concepts":   concepts_list,
        }
    elif endpoint == "generate-dsa-question":
        concepts_list = [c.strip() for c in concepts_input.split(",") if c.strip()]
        base = {
            "topic":      topic,
            "difficulty": difficulty,
            "concepts":   concepts_list,
            "languages":  dsa_languages,
        }
    return base


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────
def show_metadata(data: dict):
    cols = st.columns(3)
    with cols[0]:
        st.metric("⏱ Generation Time", f"{round(data.get('generation_time_seconds', 0), 2)}s")
    with cols[1]:
        st.metric("📦 Batch Size", data.get("batch_size", 1))
    with cols[2]:
        st.metric("🗃 Cache Hit", "Yes" if data.get("cache_hit") else "No")


def render_mcq_question(q: dict, index: int):
    st.markdown(f"#### Question {index}")
    st.write(q.get("question", "*(no question text)*"))
    for opt in q.get("options", []):
        label, text = opt.get("label", "?"), opt.get("text", "")
        if opt.get("isCorrect"):
            st.markdown(f"**{label}. ✅ {text}**")
        else:
            st.write(f"{label}. {text}")
    if q.get("explanation"):
        with st.expander("💡 Explanation"):
            st.info(q["explanation"])
    c1, c2 = st.columns(2)
    with c1: st.caption(f"Difficulty: `{q.get('difficulty', '—')}`")
    with c2: st.caption(f"Bloom Level: `{q.get('bloomLevel', '—')}`")


def render_subjective_question(q: dict, index: int):
    st.markdown(f"#### Question {index}")
    st.write(q.get("question", "*(no question text)*"))
    if q.get("expectedAnswer"):
        with st.expander("📝 Expected Answer"):
            st.success(q["expectedAnswer"])
    if q.get("gradingCriteria"):
        with st.expander("📏 Grading Criteria"):
            for c in q["gradingCriteria"]: st.write(f"• {c}")
    c1, c2 = st.columns(2)
    with c1: st.caption(f"Difficulty: `{q.get('difficulty', '—')}`")
    with c2: st.caption(f"Bloom Level: `{q.get('bloomLevel', '—')}`")


def render_coding_problem(p: dict, index: int):
    st.markdown(f"#### Problem {index}")
    st.markdown("**Problem Statement**")
    st.write(p.get("problemStatement", ""))
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Input Format**"); st.write(p.get("inputFormat", ""))
    with col_b:
        st.markdown("**Output Format**"); st.write(p.get("outputFormat", ""))
    if p.get("constraints"):
        with st.expander("📐 Constraints"):
            for c in p["constraints"]: st.write(f"• {c}")
    if p.get("examples"):
        with st.expander(f"📖 Examples ({len(p['examples'])})"):
            for ex in p["examples"]:
                st.write(f"**Input:** `{ex.get('input', '')}`")
                st.write(f"**Output:** `{ex.get('output', '')}`")
                if "explanation" in ex: st.caption(ex["explanation"])
                st.divider()
    if p.get("starterCode"):
        lang_map = {"Python": "python", "JavaScript": "javascript", "Java": "java",
                    "C++": "cpp", "Go": "go", "TypeScript": "typescript"}
        with st.expander("🖊 Starter Code"):
            st.code(p["starterCode"], language=lang_map.get(p.get("language", "Python"), "python"))
    if p.get("testCases"):
        with st.expander(f"🧪 Test Cases ({len(p['testCases'])})"):
            try:
                st.dataframe(pd.DataFrame(p["testCases"]), use_container_width=True)
            except Exception:
                st.json(p["testCases"])
    if p.get("expectedComplexity"):
        st.caption(f"Expected Complexity: `{p['expectedComplexity']}`")
    if p.get("hints"):
        with st.expander("💡 Hints"):
            for idx, h in enumerate(p["hints"], 1): st.write(f"Hint {idx}: {h}")
    st.caption(f"Difficulty: `{p.get('difficulty', '—')}`")


def render_sql_problem(p: dict, index: int):
    st.markdown(f"#### SQL Problem {index}")
    st.write(p.get("problemStatement", ""))
    if p.get("schema"):
        with st.expander("🗂 Schema"):
            for table in p["schema"].get("tables", []):
                st.markdown(f"**Table: `{table.get('name', '?')}`**")
                try:
                    st.dataframe(pd.DataFrame(table.get("columns", [])), use_container_width=True)
                except Exception:
                    st.json(table.get("columns", []))
    if p.get("expectedQuery"):
        with st.expander("✅ Expected Query"):
            st.code(p["expectedQuery"], language="sql")
    if p.get("explanation"):
        with st.expander("💡 Explanation"):
            st.info(p["explanation"])
    if p.get("alternativeApproach"):
        with st.expander("⚠️ Alternative Approach & Why It's Worse"):
            st.write(p["alternativeApproach"])
    if p.get("concepts_tested"):
        st.caption(f"Concepts tested: {', '.join(p['concepts_tested'])}")
    st.caption(f"Difficulty: `{p.get('difficulty', '—')}`")


def render_aiml_problem(p: dict, index: int):
    st.markdown(f"#### AI/ML Problem {index}")
    st.write(p.get("problemStatement", ""))

    # Dataset strategy badge
    strategy = p.get("dataset_strategy", "")
    if strategy:
        badge_map = {
            "library":           "📚 Library Dataset",
            "synthetic":         "🔧 Synthetic Dataset",
            "synthetic_fallback":"🔧 Synthetic Fallback",
        }
        st.caption(f"Dataset strategy: **{badge_map.get(strategy, strategy)}**")

    if p.get("tasks"):
        with st.expander("📋 Tasks", expanded=True):
            for t in p["tasks"]:
                st.write(f"• {t}")

    if p.get("dataset"):
        dataset = p["dataset"]
        with st.expander("📊 Dataset Details", expanded=True):
            st.write(f"**Description:** {dataset.get('description', '')}")

            # ── Library dataset: show full load code AND execute it live ──────
            if dataset.get("direct_load") and dataset.get("load_code"):
                import_code = dataset.get("import_code", "")
                load_code   = dataset["load_code"]
                pip_install = dataset.get("pip_install", "")

                # Build the full runnable code block to show
                combined = f"{import_code}\n\n{load_code}" if import_code else load_code
                st.markdown("**Load Code (run in notebook):**")
                st.code(combined, language="python")
                st.info("✅ This dataset loads directly from the library — no download needed.")

                # ── Live preview: execute load_code and render DataFrame ──────
                preview_key = f"df_preview_{index}_{dataset.get('catalog_id', 'ds')}"
                if preview_key not in st.session_state:
                    st.session_state[preview_key] = None   # not yet loaded
                    st.session_state[preview_key + "_err"] = None

                col_load, _ = st.columns([1, 3])
                with col_load:
                    load_btn = st.button(
                        "▶ Load & Preview Dataset",
                        key=f"load_btn_{index}_{dataset.get('catalog_id', 'ds')}",
                        type="primary",
                        use_container_width=True,
                    )

                if load_btn:
                    with st.spinner("Loading dataset from library…"):
                        try:
                            # Standard imports always available in any library dataset
                            exec_globals = {
                                "pd": pd,
                                "plt": plt,
                            }
                            # Inject source-specific imports
                            source = dataset.get("source", "").lower()
                            if source == "seaborn":
                                import seaborn as _sns
                                exec_globals["sns"] = _sns
                            elif source in ("sklearn", "openml"):
                                import sklearn.datasets as _skds
                                from sklearn.datasets import (
                                    load_iris, load_breast_cancer, load_diabetes,
                                    load_wine, load_digits, fetch_california_housing,
                                    fetch_20newsgroups, fetch_olivetti_faces,
                                    make_classification, make_regression,
                                    make_blobs, make_moons, make_circles,
                                    fetch_openml,
                                )
                                import numpy as _np
                                exec_globals.update({
                                    "load_iris": load_iris,
                                    "load_breast_cancer": load_breast_cancer,
                                    "load_diabetes": load_diabetes,
                                    "load_wine": load_wine,
                                    "load_digits": load_digits,
                                    "fetch_california_housing": fetch_california_housing,
                                    "fetch_20newsgroups": fetch_20newsgroups,
                                    "fetch_olivetti_faces": fetch_olivetti_faces,
                                    "make_classification": make_classification,
                                    "make_regression": make_regression,
                                    "make_blobs": make_blobs,
                                    "make_moons": make_moons,
                                    "make_circles": make_circles,
                                    "fetch_openml": fetch_openml,
                                    "np": _np,
                                })
                            elif source == "statsmodels":
                                import statsmodels.api as _sm
                                exec_globals["sm"] = _sm
                            elif source == "keras":
                                try:
                                    from tensorflow import keras as _keras
                                    exec_globals["keras"] = _keras
                                except ImportError:
                                    import keras as _keras
                                    exec_globals["keras"] = _keras
                            elif source == "nltk":
                                import nltk as _nltk
                                exec_globals["nltk"] = _nltk
                            elif source == "huggingface":
                                from datasets import load_dataset as _ld
                                exec_globals["load_dataset"] = _ld
                            elif source == "torch_geometric":
                                import torch as _torch
                                exec_globals["torch"] = _torch

                            # Run import_code first (e.g. "import seaborn as sns")
                            if import_code.strip():
                                exec(import_code, exec_globals)

                            # Run load_code — suppress print() output visually
                            import io, contextlib
                            _buf = io.StringIO()
                            with contextlib.redirect_stdout(_buf):
                                exec(load_code, exec_globals)

                            # Find the DataFrame — look for 'df' first, then any DataFrame
                            loaded_df = None
                            if "df" in exec_globals and isinstance(exec_globals["df"], pd.DataFrame):
                                loaded_df = exec_globals["df"]
                            else:
                                for _v in exec_globals.values():
                                    if isinstance(_v, pd.DataFrame):
                                        loaded_df = _v
                                        break

                            if loaded_df is not None:
                                st.session_state[preview_key] = loaded_df
                                st.session_state[preview_key + "_err"] = None
                            else:
                                st.session_state[preview_key + "_err"] = (
                                    "load_code ran successfully but no DataFrame (df) was found. "
                                    "Copy the load code into your notebook to use manually."
                                )
                        except Exception as _e:
                            st.session_state[preview_key + "_err"] = str(_e)

                # Show loaded DataFrame or error
                _loaded = st.session_state.get(preview_key)
                _err    = st.session_state.get(preview_key + "_err")

                if _err:
                    st.warning(f"⚠️ Could not load in frontend: {_err}")
                    st.caption("Use the load code above in your Jupyter notebook instead.")
                elif _loaded is not None:
                    st.success(f"✅ Loaded — {_loaded.shape[0]} rows × {_loaded.shape[1]} columns")
                    st.markdown("**Preview (first 10 rows):**")
                    st.dataframe(_loaded.head(10), use_container_width=True)

                    # Stats / missing / target: use subheaders — nested st.expander is not allowed
                    st.markdown("##### 📈 Dataset Statistics")
                    st.dataframe(_loaded.describe(include="all"), use_container_width=True)

                    _missing = _loaded.isnull().sum()
                    _missing = _missing[_missing > 0]
                    if not _missing.empty:
                        st.markdown(f"##### ⚠️ Missing Values ({_missing.sum()} total)")
                        st.dataframe(
                            _missing.rename("missing_count").to_frame(),
                            use_container_width=True,
                        )
                    else:
                        st.caption("✅ No missing values detected.")

                    target_col = dataset.get("target", "")
                    if target_col and target_col in _loaded.columns:
                        st.markdown(f"##### 🎯 Target Distribution — `{target_col}`")
                        _vc = _loaded[target_col].value_counts()
                        st.bar_chart(_vc)

                    # Download button
                    _csv = _loaded.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download Dataset as CSV",
                        data=_csv,
                        file_name=f"{dataset.get('catalog_id', 'dataset')}.csv",
                        mime="text/csv",
                        key=f"dl_live_{index}_{dataset.get('catalog_id', 'ds')}",
                    )

            # ── Metadata columns ─────────────────────────────────────────────
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Source:** `{dataset.get('source', '—')}`")
                st.write(f"**Target:** `{dataset.get('target', '—')}`")
                st.write(f"**Target Type:** `{dataset.get('target_type', '—')}`")
                st.write(f"**Size:** `{dataset.get('size', '—')}`")
            with c2:
                if dataset.get("class_distribution"):
                    st.write("**Class Distribution:**")
                    _cd = dataset["class_distribution"]
                    _labels = list(_cd.keys())
                    _values = list(_cd.values())
                    _colors = ["#4CAF50", "#F44336", "#2196F3", "#FF9800", "#9C27B0"]
                    _fig, _ax = plt.subplots(figsize=(3, 3), facecolor="none")
                    _ax.pie(
                        _values, labels=_labels,
                        colors=_colors[:len(_labels)],
                        autopct="%1.0f%%", startangle=90,
                        textprops={"color": "white", "fontsize": 11}
                    )
                    _ax.set_facecolor("none")
                    st.pyplot(_fig, use_container_width=True)
                    plt.close(_fig)

            if dataset.get("features"):
                st.write(f"**Features ({len(dataset['features'])}):** {', '.join(f'`{f}`' for f in dataset['features'])}")
            if dataset.get("features_info"):
                st.write(f"**Features Info:** {dataset['features_info']}")
            if dataset.get("feature_types"):
                st.write("**Feature Types:**")
                st.json(dataset["feature_types"])

            # ── Synthetic dataset rows (non-library) ─────────────────────────
            data_rows = dataset.get("data", [])
            if data_rows:
                st.write(f"**Dataset ({len(data_rows)} rows):**")
                try:
                    df = pd.DataFrame(data_rows)
                    st.dataframe(df, use_container_width=True)
                except Exception:
                    st.json(data_rows[:5])
            elif not dataset.get("direct_load"):
                st.warning("No dataset rows generated.")

    # Starter code (for library endpoint)
    if p.get("starter_code"):
        with st.expander("🖊 Starter Code"):
            sc = p["starter_code"]
            if isinstance(sc, dict):
                py_code = sc.get("python3", sc.get("python", ""))
                if py_code:
                    st.code(py_code, language="python")
            else:
                st.code(str(sc), language="python")

    if p.get("preprocessing_requirements"):
        with st.expander("⚙️ Preprocessing Requirements"):
            for r in p["preprocessing_requirements"]:
                st.write(f"• {r}")
    if p.get("expectedApproach"):
        with st.expander("🧪 Expected Approach"):
            st.write(p["expectedApproach"])
    if p.get("evaluationCriteria"):
        with st.expander("📏 Evaluation Criteria"):
            for c in p["evaluationCriteria"]:
                st.write(f"• {c}")
    st.caption(f"Difficulty: `{p.get('difficulty', '—')}`")

    # Download CSV for synthetic datasets
    data_rows = p.get("dataset", {}).get("data", [])
    if data_rows:
        try:
            csv_data = pd.DataFrame(data_rows).to_csv(index=False)
            st.download_button(
                label="⬇️ Download Dataset as CSV",
                data=csv_data,
                file_name=f"aiml_dataset_{index}.csv",
                mime="text/csv",
                key=f"csv_download_{index}"
            )
        except Exception as e:
            st.caption(f"Could not build CSV download: {e}")


def render_dsa_question(p: dict, index: int):
    st.markdown(f"#### DSA Problem {index}")

    # Reworded badge
    if p.get("reworded"):
        st.caption(f"🔄 Reworded from: `{p.get('original_title', '')}`")

    st.markdown("**Problem Statement**")
    st.write(p.get("description", ""))

    # Tags
    if p.get("tags"):
        st.caption(f"Tags: {', '.join(f'`{t}`' for t in p['tags'])}")

    # Example images (for graph/tree problems)
    if p.get("example_images"):
        with st.expander("🖼️ Problem Images", expanded=True):
            for img_url in p["example_images"]:
                st.image(img_url, use_container_width=True)

    # Examples with text
    if p.get("examples"):
        with st.expander(f"📖 Examples ({len(p['examples'])})"):
            for ex in p["examples"]:
                st.write(f"**Example {ex.get('example_num', '')}:**")
                st.code(ex.get("example_text", ""), language="text")
                st.divider()

    # Function signature
    if p.get("function_signature"):
        fn = p["function_signature"]
        with st.expander("🔧 Function Signature"):
            params = ", ".join(f"{x.get('name')}: {x.get('type')}" for x in fn.get("parameters", []))
            sig = f"def {fn.get('name')}({params}) -> {fn.get('return_type', 'Any')}"
            st.code(sig, language="python")

    # Public test cases
    if p.get("public_testcases"):
        with st.expander(f"🧪 Public Test Cases ({len(p['public_testcases'])}) — visible to candidate"):
            for i, t in enumerate(p["public_testcases"], 1):
                st.write(f"**Case {i}:** `{t.get('input_raw', '')}`")
                st.write(f"**Expected:** `{t.get('expected_output', '')}`")
                st.divider()

    # Hidden test cases count only
    if p.get("hidden_testcases"):
        st.info(f"🔒 {len(p['hidden_testcases'])} hidden test cases (edge cases — not visible to candidate)")

    # Starter code by language
    if p.get("starter_code"):
        sc = p["starter_code"]
        if isinstance(sc, dict) and sc:
            with st.expander(f"🖊 Starter Code ({len(sc)} languages)"):
                lang_tabs = st.tabs(list(sc.keys()))
                for tab, (lang, code) in zip(lang_tabs, sc.items()):
                    with tab:
                        lang_map = {
                            "python": "python", "java": "java",
                            "javascript": "javascript", "typescript": "typescript",
                            "kotlin": "kotlin", "go": "go", "rust": "rust",
                            "cpp": "cpp", "csharp": "csharp", "c": "c"
                        }
                        st.code(code, language=lang_map.get(lang, "text"))

    c1, c2 = st.columns(2)
    with c1: st.caption(f"Difficulty: `{p.get('difficulty', '—')}`")
    with c2: st.caption(f"AI Generated: {'✅' if p.get('ai_generated') else '—'}")


def render_topic(t: dict, index: int):
    label = t.get("label", t) if isinstance(t, dict) else str(t)
    qtype = t.get("questionType", "") if isinstance(t, dict) else ""
    diff  = t.get("difficulty", "")   if isinstance(t, dict) else ""
    judge = t.get("canUseJudge0", None) if isinstance(t, dict) else None
    cols = st.columns([3, 2, 2, 1])
    with cols[0]: st.write(f"**{index}.** {label}")
    with cols[1]: st.caption(f"Type: `{qtype}`" if qtype else "")
    with cols[2]: st.caption(f"Difficulty: `{diff}`" if diff else "")
    with cols[3]:
        if judge is not None: st.caption("Judge0 ✅" if judge else "")


# ─────────────────────────────────────────────
# GENERATE BUTTON
# ─────────────────────────────────────────────
if st.button("🚀 Generate", type="primary", use_container_width=True, disabled=is_generating):
    payload = build_payload()
    url = f"{API_BASE}/{endpoint}"

    with st.expander("📨 Request Payload", expanded=False):
        st.json(payload)

    try:
        resp = requests.post(url, json=payload, headers=request_headers(), timeout=180)

        if resp.status_code != 200:
            st.error(f"❌ Server returned HTTP {resp.status_code}")
            try:
                err_body = resp.json()
                detail = err_body.get("detail")
                if isinstance(detail, list):
                    for item in detail:
                        field = " → ".join(str(x) for x in item.get("loc", []))
                        st.error(f"Validation error on `{field}`: {item.get('msg', '')}")
                elif detail:
                    st.error(str(detail))
                else:
                    st.json(err_body)
            except Exception:
                st.text(resp.text[:500])
            st.stop()

        data = resp.json()

        if "job_id" in data:
            st.session_state.pending_job_id = data["job_id"]
            st.session_state.pending_poll_url = f"{API_BASE}/job/{data['job_id']}"
            st.session_state.job_start_ts = time.time()
            st.session_state.last_response = None
            st.rerun()
        else:
            st.session_state.last_response = data
            st.session_state.pending_job_id = None
            st.rerun()

    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to server at `{_SERVER_BASE}`. Is it running?")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

# ─────────────────────────────────────────────
# JOB POLLING
# ─────────────────────────────────────────────
if st.session_state.pending_job_id:
    elapsed = int(time.time() - (st.session_state.job_start_ts or time.time()))

    _messages = [
        "🧠 Thinking deeply...",
        "✍️ Crafting questions...",
        "🔍 Validating output...",
        "⚙️ Almost there...",
        "📦 Packaging results...",
    ]
    _msg = _messages[(elapsed // 5) % len(_messages)]
    _progress = min(0.9, elapsed / 120)
    st.progress(_progress, text=f"{_msg}  •  {elapsed}s elapsed")

    try:
        poll_resp = requests.get(
            st.session_state.pending_poll_url, headers=request_headers(), timeout=60
        )
        poll_data = poll_resp.json()

        if poll_data.get("status") == "complete":
            st.progress(1.0, text="✅ Done!")
            result = poll_data.get("result") or poll_data
            st.session_state.last_response = result
            st.session_state.pending_job_id = None
            st.session_state.pending_poll_url = None
            st.session_state.job_start_ts = None
            st.rerun()

        elif poll_data.get("status") in ("failed", "error"):
            st.error(f"❌ Generation failed: {poll_data.get('error', 'Unknown error')}")
            st.session_state.pending_job_id = None
            st.session_state.pending_poll_url = None
            st.session_state.job_start_ts = None

        else:
            time.sleep(3)
            st.rerun()

    except requests.exceptions.Timeout:
        time.sleep(3)
        st.rerun()

    except Exception as e:
        st.warning(f"Polling hiccup, retrying… ({e})")
        time.sleep(3)
        st.rerun()


# ─────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────
data = st.session_state.get("last_response")

if data:
    st.divider()
    st.header("📄 Generated Output")

    if "topics" in data:
        topics_list = data["topics"]
        st.subheader(f"📋 Generated Topics ({len(topics_list)})")
        for i, t in enumerate(topics_list, 1):
            render_topic(t, i)

    elif "questions" in data:
        questions_list = data["questions"]
        st.subheader(f"✅ Questions ({len(questions_list)})")
        for i, q in enumerate(questions_list, 1):
            with st.container(border=True):
                if "options" in q:
                    render_mcq_question(q, i)
                else:
                    render_subjective_question(q, i)

    elif "coding_problems" in data:
        problems = data["coding_problems"]
        st.subheader(f"💻 Coding Problems ({len(problems)})")
        for i, p in enumerate(problems, 1):
            with st.container(border=True):
                render_coding_problem(p, i)

    elif "sql_problems" in data:
        problems = data["sql_problems"]
        st.subheader(f"🗄️ SQL Problems ({len(problems)})")
        for i, p in enumerate(problems, 1):
            with st.container(border=True):
                render_sql_problem(p, i)

    elif "aiml_problems" in data:
        problems = data["aiml_problems"]
        # Detect which AIML endpoint was used
        is_library = any(p.get("dataset_strategy") == "library" for p in problems)
        label = "📚 AI/ML Library Problems" if is_library else "🤖 AI/ML Problems"
        st.subheader(f"{label} ({len(problems)})")
        for i, p in enumerate(problems, 1):
            with st.container(border=True):
                render_aiml_problem(p, i)

    # DSA question — direct response (not job-based)
    elif "public_testcases" in data and "starter_code" in data:
        st.subheader("🔢 DSA Question")
        with st.container(border=True):
            render_dsa_question(data, 1)

    elif "dataset" in data and "problemStatement" in data:
        st.subheader("🤖 AI/ML Problem")
        with st.container(border=True):
            render_aiml_problem(data, 1)

    elif "options" in data and "question" in data:
        st.subheader("✅ MCQ Question")
        with st.container(border=True):
            render_mcq_question(data, 1)

    elif "expectedAnswer" in data and "question" in data:
        st.subheader("✍️ Subjective Question")
        with st.container(border=True):
            render_subjective_question(data, 1)

    elif "schema" in data and "problemStatement" in data:
        st.subheader("🗄️ SQL Problem")
        with st.container(border=True):
            render_sql_problem(data, 1)

    elif "inputFormat" in data and "problemStatement" in data:
        st.subheader("💻 Coding Problem")
        with st.container(border=True):
            render_coding_problem(data, 1)

    else:
        st.warning("Unrecognised response shape — showing raw JSON.")
        st.json(data)

    st.divider()
    st.subheader("📊 Response Metadata")
    show_metadata(data)

    st.divider()
    import json as _json
    st.download_button(
        label="⬇️ Download as JSON",
        data=_json.dumps(data, indent=2),
        file_name="generated_output.json",
        mime="application/json",
    )