"""Browser screen for the Ask Your Data analyst."""
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import ask  # reuse the tested functions from src/ask.py

load_dotenv(ROOT / ".env")

st.set_page_config(page_title="Ask Your Data")
st.title("Ask Your Data")
st.caption("Olist e-commerce data, 2016-2018. Amounts are in Brazilian reais (R$).")

if not os.getenv("GEMINI_API_KEY"):
    st.error("GEMINI_API_KEY not found. Check your .env file.")
    st.stop()


def show_result(df):
    if df.empty:
        st.info("No matching data found.")
        return
    # one single value: show it as a big number
    if df.shape == (1, 1):
        value = df.iloc[0, 0]
        if isinstance(value, float):
            value = f"{value:,.2f}"
        st.metric("Result", str(value))
        return
    # show dates without the 00:00:00 time
    table = df.copy()
    for column in table.columns:
        if is_datetime64_any_dtype(table[column]):
            values = table[column].dropna()
            if (values == values.dt.normalize()).all():
                table[column] = table[column].dt.date
    st.dataframe(table, hide_index=True)
    # chart when there is a label (or date) column followed by a number column
    if len(df) > 1 and df.shape[1] == 2:
        chart = df.set_axis(["label", "value"], axis=1)
        names = {"x_label": str(df.columns[0]), "y_label": str(df.columns[1])}
        if is_numeric_dtype(chart["value"]):
            if is_datetime64_any_dtype(chart["label"]):
                st.line_chart(chart, x="label", y="value", **names)
            elif not is_numeric_dtype(chart["label"]):
                st.bar_chart(chart, x="label", y="value", sort=False, **names)


with st.form("question_form"):
    question = st.text_input("Your question", placeholder="What is the total revenue?")
    clicked = st.form_submit_button("Ask")

if clicked and question.strip():
    con = None
    try:
        con = ask.connect()
        metrics = (ROOT / "metrics.yml").read_text(encoding="utf-8")
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        with st.spinner("Working..."):
            client = genai.Client()
            sql = ask.write_sql(client, model, question, ask.get_schema(con), metrics)
        if sql == "CANNOT_ANSWER":
            st.warning("This data cannot answer that question.")
        elif not ask.is_safe(con, sql):
            st.error("Blocked: only a single SELECT query is allowed.")
            st.code(sql, language="sql")
        else:
            # show at most 1,000 rows
            show_result(con.sql(sql).limit(1000).df())
            with st.expander("Show SQL"):
                st.code(sql, language="sql")
    except Exception as error:
        st.error(f"Something went wrong: {error}")
    finally:
        if con is not None:
            con.close()