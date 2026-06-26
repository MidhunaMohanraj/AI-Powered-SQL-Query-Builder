# 🗄️ AI SQL Query Builder

> Type a question in plain English → get production-ready SQL instantly. Supports PostgreSQL, MySQL, SQLite, BigQuery, and SQL Server.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-ff4b4b) ![Claude](https://img.shields.io/badge/AI-Claude%20claude-sonnet-4-6-blueviolet)

---

## Features

- 💬 **Plain-English → SQL** — describe what you want, get a working query
- 🔧 **SQL Fixer tab** — paste broken SQL + error message, get it corrected and explained
- 📋 **Schema-aware** — paste your own `CREATE TABLE` statements for accurate queries
- 🏷️ **Complexity badge** — Simple / Moderate / Complex rating on every query
- 🕐 **Query history** — last 10 queries saved in the sidebar for the session
- ⬇️ **Export** — download any query as a `.sql` file
- 🎯 **5 example prompts** — works out of the box with a sample e-commerce schema

---

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/sql-query-builder.git
cd sql-query-builder
pip install -r requirements.txt
streamlit run app.py
```

Add your Anthropic API key in the sidebar. Get one free at [console.anthropic.com](https://console.anthropic.com).

---

## How it works

```
User types question + pastes schema
           │
           ▼
Claude claude-sonnet-4-6 (system prompt: expert SQL writer for chosen dialect)
           │
           ▼
Structured JSON → { sql, explanation, warnings }
           │
           ▼
Streamlit renders syntax-highlighted query + explanation
```

The system prompt is dialect-aware — switching from PostgreSQL to BigQuery changes functions like `DATE_TRUNC`, `ILIKE`, and interval syntax automatically.

---

## Project structure

```
sql-query-builder/
├── app.py            # Streamlit app (builder + fixer tabs)
├── requirements.txt
└── README.md
```

---

## Sample prompts to try

- *"Top 10 customers by total revenue this year"*
- *"Monthly revenue for the last 6 months"*
- *"Products with low stock (less than 10 units)"*
- *"Average order value by country"*
- *"Orders placed today with customer names"*

---

## Tech stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| AI | Anthropic Claude claude-sonnet-4-6 |
| SQL parsing | Python stdlib + regex |

---

## License

MIT
