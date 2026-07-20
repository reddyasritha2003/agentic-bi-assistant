import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import re
import os

from groq import Groq
from dotenv import load_dotenv

client = Groq(
    api_key="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"
)
st.set_page_config(
    page_title="Agentic BI Assistant Pro",
    layout="wide"
)

if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# Load CSV Files into SQLite
# -----------------------------
def load_csvs_to_db(uploaded_files):

    conn = sqlite3.connect("business.db")
    cursor = conn.cursor()

    # Remove old tables
    cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    """)

    tables = cursor.fetchall()

    for table in tables:
        cursor.execute(
            f"DROP TABLE IF EXISTS '{table[0]}'"
        )

    conn.commit()

    loaded_tables = []

    for uploaded_file in uploaded_files:

        try:
            df = pd.read_csv(
                uploaded_file,
                encoding="utf-8"
            )

        except:

            uploaded_file.seek(0)

            df = pd.read_csv(
                uploaded_file,
                encoding="latin1"
            )

        # Clean column names
        df.columns = (
            df.columns
            .str.strip()
            .str.replace(" ", "_", regex=False)
            .str.replace("-", "_", regex=False)
            .str.replace("/", "_", regex=False)
            .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
        )

        table_name = (
            uploaded_file.name
            .replace(".csv", "")
            .replace(" ", "_")
            .replace("-", "_")
        )

        df.to_sql(
            table_name,
            conn,
            if_exists="replace",
            index=False
        )

        loaded_tables.append(table_name)

    conn.close()

    return loaded_tables
    # -----------------------------
# Schema Discovery
# -----------------------------
def get_schema():

    conn = sqlite3.connect("business.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    """)

    tables = cursor.fetchall()

    schema = ""

    for table in tables:

        table_name = table[0]

        cursor.execute(
            f"PRAGMA table_info('{table_name}')"
        )

        columns = cursor.fetchall()

        schema += f"\nTABLE: {table_name}\n"

        for col in columns:

            schema += (
                f"{col[1]} ({col[2]})\n"
            )

    conn.close()

    return schema
    # -----------------------------
# SQL Cleaner
# -----------------------------
def clean_sql(sql):

    sql = re.sub(
        r"```sql|```",
        "",
        sql,
        flags=re.IGNORECASE
    )

    lines = sql.split("\n")

    sql_lines = []

    start = False

    for line in lines:

        if (
            line.strip().upper().startswith("SELECT")
            or line.strip().upper().startswith("WITH")
        ):
            start = True

        if start:
            sql_lines.append(line)

    return "\n".join(sql_lines).strip()
    # -----------------------------
# Generate SQL
# -----------------------------
def generate_sql(question):

    schema = get_schema()

    prompt = f"""
You are an expert SQLite analyst.

Database Schema:

{schema}

Rules:
1. Return ONLY SQLite SQL.
2. Start directly with SELECT.
3. No markdown.
4. No explanation.
5. Use ONLY tables shown.
6. Use ONLY columns shown.
7. Never invent column names.
8. Use exact column names from schema.

Question:
{question}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return clean_sql(
        response.choices[0].message.content
    )
# Execute SQL
# -----------------------------
def run_sql(sql):

    conn = sqlite3.connect(
        "business.db"
    )

    df = pd.read_sql_query(
        sql,
        conn
    )

    conn.close()

    return df
    # -----------------------------
# Fix SQL (Self-Healing)
# -----------------------------
def fix_sql(
    question,
    bad_sql,
    error
):

    schema = get_schema()

    prompt = f"""
You are an expert SQLite developer.

Database Schema:
{schema}

Question:
{question}

Bad SQL:
{bad_sql}

Error:
{error}

Rules:
1. Return ONLY corrected SQLite SQL.
2. Start directly with SELECT.
3. No explanation.
4. No markdown.

Correct SQL:
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return clean_sql(
        response.choices[0].message.content
    )
    # -----------------------------
# Business Insights
# -----------------------------
def generate_insight(
    question,
    data
):

    prompt = f"""
You are a Senior Business Analyst.

Question:
{question}

Result:
{data}

Provide:
1. Executive Summary
2. Key Findings
3. Trends
4. Recommendations
5. Next Actions

Keep it concise and business-focused.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3
    )

    return response.choices[0].message.content
    # -----------------------------
# UI
# -----------------------------
st.title("🤖 Agentic BI Assistant Pro")

# Sidebar
with st.sidebar:

    st.header("📊 Database Schema")

    schema = get_schema()

    if schema.strip():
        st.text(schema)
    else:
        st.write(
            "No tables loaded. Upload a CSV file."
        )

    st.divider()

    st.header("🕒 Query History")

    if len(st.session_state.history) == 0:
        st.write("No questions asked yet")
    else:
        for q in st.session_state.history[-10:]:
            st.write(f"• {q}")

# Upload Files
uploaded_files = st.file_uploader(
    "Upload CSV Files",
    type=["csv"],
    accept_multiple_files=True
)

# Clear Database
if st.button("🗑 Clear Database"):

    conn = sqlite3.connect("business.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    """)

    tables = cursor.fetchall()

    for table in tables:
        cursor.execute(
            f"DROP TABLE IF EXISTS '{table[0]}'"
        )

    conn.commit()
    conn.close()

    st.success("Database Cleared")
    st.rerun()
    # -----------------------------
# Load Uploaded Files
# -----------------------------
loaded_tables = []

if uploaded_files:

    try:

        loaded_tables = load_csvs_to_db(
            uploaded_files
        )

        st.success(
            f"Loaded Tables: {', '.join(loaded_tables)}"
        )

        # Data Preview
        table_name = loaded_tables[0]

        conn = sqlite3.connect(
            "business.db"
        )

        preview_df = pd.read_sql_query(
            f"SELECT * FROM '{table_name}' LIMIT 10",
            conn
        )

        conn.close()

        st.subheader(
            "📄 Data Preview"
        )

        st.dataframe(
            preview_df,
            use_container_width=True
        )

        col1, col2, col3 = st.columns(3)

        conn = sqlite3.connect(
            "business.db"
        )

        total_rows = 0

        for table in loaded_tables:

            count_df = pd.read_sql_query(
                f"SELECT COUNT(*) AS cnt FROM '{table}'",
                conn
            )

            total_rows += int(
                count_df["cnt"][0]
            )

        conn.close()

        col1.metric(
            "Tables",
            len(loaded_tables)
        )

        col2.metric(
            "Rows",
            total_rows
        )

        col3.metric(
            "Questions Asked",
            len(st.session_state.history)
        )

        with st.expander(
            "Suggested Questions"
        ):

            st.write("""
• Show first 10 rows
• Show total sales by category
• Show profit by region
• Show monthly sales trend
• Top 10 customers by sales
• Top 10 products by profit
• Most profitable category
• Average discount by segment
""")

    except Exception as e:

        st.error(
            f"Upload Error: {str(e)}"
        )
        # -----------------------------
# Question Input
# -----------------------------
question = st.text_input(
    "Ask a business question"
)

# -----------------------------
# Analyze
# -----------------------------
if st.button("Analyze"):

    if not question:

        st.warning(
            "Please enter a question."
        )

    else:

        try:

            st.session_state.history.append(
                question
            )

            sql = generate_sql(
                question
            )

            st.subheader(
                "Generated SQL"
            )

            sql = st.text_area(
                "SQL Editor",
                sql,
                height=150
            )

            try:

                df = run_sql(sql)

            except Exception as e:

                corrected_sql = fix_sql(
                    question,
                    sql,
                    str(e)
                )

                st.warning(
                    "SQL corrected automatically"
                )

                st.code(
                    corrected_sql
                )

                df = run_sql(
                    corrected_sql
                )

            st.subheader(
                "Results"
            )

            st.dataframe(
                df,
                use_container_width=True
            )

            # Download Results
            csv_data = df.to_csv(
                index=False
            )

            st.download_button(
                "📥 Download Results",
                csv_data,
                "results.csv",
                "text/csv"
            )

            chart_type = st.selectbox(
                "📊 Select Chart Type",
                [
                    "Auto",
                    "Bar",
                    "Line",
                    "Pie",
                    "Scatter"
                ]
            )

            # Visualization
            try:

                if len(df.columns) >= 2:

                    x_col = df.columns[0]
                    y_col = df.columns[1]

                    if pd.api.types.is_numeric_dtype(
                        df[y_col]
                    ):

                        if chart_type == "Bar":

                            fig = px.bar(
                                df.head(20),
                                x=x_col,
                                y=y_col,
                                title=f"{y_col} by {x_col}",
                                text_auto=True
                            )

                        elif chart_type == "Line":

                            fig = px.line(
                                df,
                                x=x_col,
                                y=y_col,
                                markers=True,
                                title=f"{y_col} Trend"
                            )

                        elif chart_type == "Pie":

                            fig = px.pie(
                                df,
                                names=x_col,
                                values=y_col,
                                title=f"{y_col} Distribution"
                            )

                        elif chart_type == "Scatter":

                            fig = px.scatter(
                                df,
                                x=x_col,
                                y=y_col,
                                title=f"{x_col} vs {y_col}"
                            )

                        else:

                            fig = px.bar(
                                df.head(20),
                                x=y_col,
                                y=x_col,
                                orientation="h",
                                text_auto=True,
                                title=f"{y_col} by {x_col}"
                            )

                        st.plotly_chart(
                            fig,
                            use_container_width=True
                        )

            except Exception as e:

                st.warning(
                    f"Chart Error: {str(e)}"
                )

            insight = generate_insight(
                question,
                df.head(50).to_string()
            )

            st.subheader(
                "Business Insight"
            )

            st.write(
                insight
            )

        except Exception as e:

            st.error(
                f"Error: {str(e)}"
            )
