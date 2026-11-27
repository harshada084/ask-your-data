"""Type a question in English. Gemini writes SQL, DuckDB runs it."""
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from google import genai

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "olist.duckdb"


def connect():
    # read_only: data cannot be changed
    # enable_external_access False: SQL cannot open other files, such as .env
    return duckdb.connect(
        str(DB_PATH), read_only=True, config={"enable_external_access": False}
    )


def get_schema(con):
    """List table and column names. No data rows are sent to the AI."""
    rows = con.execute("""
        SELECT table_schema, table_name,
               string_agg(column_name || ' ' || data_type, ', ' ORDER BY ordinal_position)
        FROM information_schema.columns
        WHERE table_schema IN ('raw', 'staging')
        GROUP BY table_schema, table_name
        ORDER BY table_schema, table_name
    """).fetchall()
    return "\n".join(f"{s}.{t}: {cols}" for s, t, cols in rows)


def write_sql(client, model, question, schema, metrics):
    prompt = f"""You write DuckDB SQL for the Olist e-commerce database.

Tables:
{schema}

Business definitions (always follow these):
{metrics}

Rules:
- Return only one SELECT query, with no explanation and no markdown.
- Prefer staging tables when they have the needed columns.
- If the data cannot answer the question, return exactly: CANNOT_ANSWER

Question: {question}"""
    reply = client.interactions.create(model=model, input=prompt)
    text = (reply.output_text or "").strip()
    # remove code fences if the AI adds them
    return text.replace("```sql", "").replace("```", "").strip()


def is_safe(con, sql):
    """Allow exactly one SELECT statement."""
    try:
        statements = con.extract_statements(sql)
    except duckdb.Error:
        return False
    return len(statements) == 1 and statements[0].type == duckdb.StatementType.SELECT


def main():
    load_dotenv(ROOT / ".env")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY not found. Check your .env file.")
    metrics_file = ROOT / "metrics.yml"
    if not metrics_file.exists():
        raise SystemExit("metrics.yml not found in the main project folder.")

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    client = genai.Client()
    con = connect()
    schema = get_schema(con)
    metrics = metrics_file.read_text(encoding="utf-8")

    while True:
        question = input("\nAsk your data (or type exit): ").strip()
        if question.lower() == "exit":
            break
        if not question:
            continue
        try:
            sql = write_sql(client, model, question, schema, metrics)
            if sql == "CANNOT_ANSWER":
                print("This data cannot answer that question.")
                continue
            print(f"\nSQL written by AI:\n{sql}\n")
            if not is_safe(con, sql):
                print("Blocked: only a single SELECT query is allowed.")
                continue
            print(con.sql(sql))
        except Exception as error:  # keep the app running after a failure
            print(f"Something went wrong: {error}")


if __name__ == "__main__":
    main()