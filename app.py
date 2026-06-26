import streamlit as st
import anthropic
import json
import re

st.set_page_config(
    page_title="AI SQL Query Builder",
    page_icon="🗄️",
    layout="wide"
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 2rem; font-weight: 700; margin-bottom: 0; }
    .main-sub { color: #888; font-size: 0.95rem; margin-top: 0; }
    .complexity-simple { display:inline-block; background:#e6f4ea; color:#1e7e34;
        border-radius:20px; padding:2px 14px; font-size:0.8rem; font-weight:600; }
    .complexity-moderate { display:inline-block; background:#fff8e1; color:#b26a00;
        border-radius:20px; padding:2px 14px; font-size:0.8rem; font-weight:600; }
    .complexity-complex { display:inline-block; background:#fce8e6; color:#c62828;
        border-radius:20px; padding:2px 14px; font-size:0.8rem; font-weight:600; }
    .history-item { background:#f8f9fa; border-radius:8px; padding:0.6rem 0.9rem;
        margin-bottom:0.5rem; font-size:0.82rem; cursor:pointer;
        border:1px solid #eee; color:#333; }
    .history-item:hover { border-color:#aaa; }
    .info-box { background:#f0f7ff; border:1px solid #bbdefb; border-radius:8px;
        padding:0.75rem 1rem; color:#1565c0; font-size:0.88rem; margin-bottom:1rem; }
    .explanation-box { background:#f8f9fa; border-left:3px solid #3b5bdb;
        padding:0.9rem 1.1rem; border-radius:0 8px 8px 0; font-size:0.92rem;
        line-height:1.7; color:#333; }
    div[data-testid="stCodeBlock"] { border-radius:8px; }
</style>
""", unsafe_allow_html=True)

SAMPLE_SCHEMA = """-- E-commerce database schema

CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) UNIQUE NOT NULL,
    country     VARCHAR(60),
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    category    VARCHAR(80),
    price       NUMERIC(10,2) NOT NULL,
    stock_qty   INTEGER DEFAULT 0
);

CREATE TABLE orders (
    id            SERIAL PRIMARY KEY,
    customer_id   INTEGER REFERENCES customers(id),
    created_at    TIMESTAMP DEFAULT NOW(),
    status        VARCHAR(30) DEFAULT 'pending'
);

CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER REFERENCES orders(id),
    product_id  INTEGER REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    unit_price  NUMERIC(10,2) NOT NULL
);
"""

SAMPLE_QUESTIONS = [
    "Top 10 customers by total revenue this year",
    "Monthly revenue for the last 6 months",
    "Products with low stock (less than 10 units)",
    "Orders placed today with customer names",
    "Average order value by country",
]

DIALECTS = ["PostgreSQL", "MySQL", "SQLite", "BigQuery", "SQL Server"]

# ── Session state ─────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "result" not in st.session_state:
    st.session_state.result = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "builder"


def get_complexity(sql: str) -> str:
    sql_upper = sql.upper()
    score = 0
    for keyword in ["JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL JOIN"]:
        score += sql_upper.count(keyword)
    if "SUBQUERY" in sql_upper or "WITH " in sql_upper or "EXISTS" in sql_upper:
        score += 2
    if "HAVING" in sql_upper or "GROUP BY" in sql_upper:
        score += 1
    if score == 0:
        return "Simple"
    elif score <= 2:
        return "Moderate"
    return "Complex"


def complexity_badge(level: str) -> str:
    css = {"Simple": "complexity-simple", "Moderate": "complexity-moderate", "Complex": "complexity-complex"}
    return f'<span class="{css[level]}">{level}</span>'


def build_query(question: str, schema: str, dialect: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    system = f"""You are an expert {dialect} SQL writer.
Given a database schema and a plain-English question, return ONLY valid JSON — no markdown, no explanation outside JSON.

JSON schema:
{{
  "sql": "the complete SQL query as a string",
  "explanation": "plain-English explanation of what the query does and why, 2-4 sentences",
  "warnings": "any caveats, performance notes, or null"
}}

Rules:
- Write clean, readable SQL with aliases and formatting.
- Prefer CTEs over nested subqueries for readability.
- Always qualify column names with table aliases when joining.
- If the question is ambiguous, pick the most reasonable interpretation.
- Dialect: {dialect}. Use dialect-specific functions/syntax where appropriate.
"""
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system,
        messages=[{
            "role": "user",
            "content": f"Schema:\n{schema}\n\nQuestion: {question}"
        }]
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())


def fix_query(broken_sql: str, error_msg: str, schema: str, dialect: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    system = f"""You are an expert {dialect} SQL debugger.
Given broken SQL and an optional error message, return ONLY valid JSON — no markdown.

JSON schema:
{{
  "sql": "the corrected SQL query",
  "explanation": "what was wrong and what you fixed, 2-3 sentences",
  "warnings": "any additional notes or null"
}}

Dialect: {dialect}
"""
    context = f"Schema:\n{schema}\n\nBroken SQL:\n{broken_sql}"
    if error_msg.strip():
        context += f"\n\nError message:\n{error_msg}"

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": context}]
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input("Anthropic API Key", type="password",
                             help="Get yours at console.anthropic.com")
    dialect = st.selectbox("SQL Dialect", DIALECTS)
    st.divider()

    st.markdown("### 📋 Schema")
    schema = st.text_area("Paste your CREATE TABLE statements",
                           value=SAMPLE_SCHEMA, height=340,
                           help="The AI will write queries specifically for your tables.")
    st.divider()

    if st.session_state.history:
        st.markdown("### 🕐 History")
        for i, h in enumerate(reversed(st.session_state.history[-10:])):
            if st.button(f"↩ {h['question'][:45]}…" if len(h['question']) > 45 else f"↩ {h['question']}",
                         key=f"hist_{i}", use_container_width=True):
                st.session_state.result = h
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🗄️ AI SQL Query Builder</p>', unsafe_allow_html=True)
st.markdown('<p class="main-sub">Describe what you want in plain English — get production-ready SQL instantly.</p>', unsafe_allow_html=True)
st.divider()

if not api_key:
    st.markdown("""<div class="info-box">ℹ️ Add your Anthropic API key in the sidebar to start generating queries.</div>""",
                unsafe_allow_html=True)

tab_builder, tab_fixer = st.tabs(["✨ Query Builder", "🔧 Fix My SQL"])

# ── TAB 1: Builder ────────────────────────────────────────────────────────────
with tab_builder:
    st.markdown("**Try an example:**")
    example_cols = st.columns(len(SAMPLE_QUESTIONS))
    for i, q in enumerate(SAMPLE_QUESTIONS):
        if example_cols[i].button(q, key=f"ex_{i}", use_container_width=True):
            st.session_state.prefill = q

    question = st.text_area(
        "What do you want to query?",
        value=st.session_state.get("prefill", ""),
        placeholder="e.g. Show me the top 10 customers by total revenue this year",
        height=90,
        label_visibility="collapsed"
    )
    if "prefill" in st.session_state:
        del st.session_state.prefill

    generate = st.button("⚡ Generate SQL", type="primary",
                          disabled=not api_key or not question.strip(),
                          use_container_width=False)

    if generate and question.strip() and api_key:
        with st.spinner("Writing your query…"):
            try:
                result = build_query(question.strip(), schema, dialect, api_key)
                result["question"] = question.strip()
                result["dialect"] = dialect
                st.session_state.result = result
                if not any(h["question"] == question.strip() for h in st.session_state.history):
                    st.session_state.history.append(result)
            except json.JSONDecodeError:
                st.error("Unexpected response from Claude. Try rephrasing your question.")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state.result and st.session_state.result.get("sql"):
        r = st.session_state.result
        complexity = get_complexity(r["sql"])

        st.divider()
        c1, c2 = st.columns([6, 1])
        c1.markdown(f"**Generated {r.get('dialect', dialect)} Query** &nbsp; {complexity_badge(complexity)}",
                    unsafe_allow_html=True)

        st.code(r["sql"], language="sql")

        if r.get("explanation"):
            st.markdown(f'<div class="explanation-box">💡 {r["explanation"]}</div>',
                        unsafe_allow_html=True)

        if r.get("warnings"):
            st.warning(f"⚠️ {r['warnings']}")

        st.download_button(
            "⬇️ Download .sql",
            data=r["sql"],
            file_name="query.sql",
            mime="text/plain"
        )

# ── TAB 2: SQL Fixer ──────────────────────────────────────────────────────────
with tab_fixer:
    st.markdown("Paste broken SQL and an optional error message — Claude will fix and explain it.")

    broken_sql = st.text_area("Broken SQL", height=180,
                               placeholder="SELECT cusomer_id, SUM(totl) FORM orders GRUP BY cusomer_id")
    error_msg = st.text_area("Error message (optional)", height=80,
                              placeholder="ERROR: column 'totl' does not exist")

    fix_btn = st.button("🔧 Fix SQL", type="primary",
                         disabled=not api_key or not broken_sql.strip())

    if fix_btn and broken_sql.strip() and api_key:
        with st.spinner("Debugging your query…"):
            try:
                fixed = fix_query(broken_sql.strip(), error_msg, schema, dialect, api_key)
                st.divider()
                st.markdown("**Fixed Query**")
                st.code(fixed["sql"], language="sql")
                if fixed.get("explanation"):
                    st.markdown(f'<div class="explanation-box">🔍 {fixed["explanation"]}</div>',
                                unsafe_allow_html=True)
                if fixed.get("warnings"):
                    st.warning(f"⚠️ {fixed['warnings']}")
                st.download_button("⬇️ Download fixed .sql", data=fixed["sql"],
                                   file_name="fixed_query.sql", mime="text/plain")
            except json.JSONDecodeError:
                st.error("Unexpected response. Try again.")
            except Exception as e:
                st.error(f"Error: {e}")
