"""Compare the AI's answers with verified SQL and report a score.

python src/evaluate.py                    (with business definitions)
python src/evaluate.py --no-definitions   (without them)
"""
import csv
import os
import sys
import time
from datetime import date
from decimal import Decimal
from itertools import permutations

from dotenv import load_dotenv
from google import genai

import ask  # reuse the functions from ask.py

DELIVERED_ITEMS = """FROM staging.stg_order_items i
JOIN staging.stg_orders o ON i.order_id = o.order_id
WHERE o.order_status = 'delivered'"""

# (question, correct SQL). None means the data cannot answer it.
QUESTIONS = [
    ("What is the total revenue?",
     f"SELECT SUM(i.price) {DELIVERED_ITEMS}"),
    ("What is the late delivery rate?",
     """SELECT 100.0 * COUNT(*) FILTER (WHERE is_late) / COUNT(*)
        FROM staging.stg_orders
        WHERE order_status = 'delivered' AND NOT is_missing_delivery_date"""),
    ("How many orders are there for each order status?",
     "SELECT order_status, COUNT(*) FROM staging.stg_orders GROUP BY 1"),
    ("Show monthly revenue for 2017",
     f"""SELECT strftime(o.purchased_at, '%Y-%m'), SUM(i.price) {DELIVERED_ITEMS}
         AND year(o.purchased_at) = 2017 GROUP BY 1"""),
    ("How many delivered orders were purchased in 2018?",
     """SELECT COUNT(*) FROM staging.stg_orders
        WHERE order_status = 'delivered' AND year(purchased_at) = 2018"""),
    ("What are the top 5 product categories by revenue? Use English category names.",
     """SELECT t.product_category_name_english, SUM(i.price)
        FROM staging.stg_order_items i
        JOIN staging.stg_orders o ON i.order_id = o.order_id
        JOIN raw.products p ON i.product_id = p.product_id
        JOIN raw.category_translation t
          ON p.product_category_name = t.product_category_name
        WHERE o.order_status = 'delivered'
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5"""),
    ("Which 5 customer states have the highest late delivery rate? Show state and rate.",
     """SELECT c.customer_state,
               100.0 * COUNT(*) FILTER (WHERE o.is_late) / COUNT(*)
        FROM staging.stg_orders o
        JOIN raw.customers c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered' AND NOT o.is_missing_delivery_date
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5"""),
    ("What is the average review score across all reviews?",
     "SELECT AVG(review_score) FROM raw.order_reviews"),
    ("What is the total payment value for each payment type, across all orders?",
     "SELECT payment_type, SUM(payment_value) FROM raw.order_payments GROUP BY 1"),
    ("What is the total profit?", None),
]


def clean(value):
    """Make values comparable: round numbers, write month dates as YYYY-MM."""
    if isinstance(value, (int, float, Decimal)):
        return str(round(float(value), 2))
    if isinstance(value, date) and value.day == 1:
        return value.strftime("%Y-%m")
    return str(value)


def same_answer(expected, actual):
    """Ignore column names, column order, row order and extra columns."""
    if len(expected) != len(actual) or not expected:
        return expected == actual
    wanted = sorted(tuple(map(clean, row)) for row in expected)
    for columns in permutations(range(len(actual[0])), len(expected[0])):
        got = sorted(tuple(clean(row[c]) for c in columns) for row in actual)
        if got == wanted:
            return True
    return False


def main():
    load_dotenv(ask.ROOT / ".env")
    use_definitions = "--no-definitions" not in sys.argv
    metrics = "No definitions given."
    if use_definitions:
        metrics = (ask.ROOT / "metrics.yml").read_text(encoding="utf-8")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    client = genai.Client()
    con = ask.connect()
    schema = ask.get_schema(con)
    results = []

    for number, (question, correct_sql) in enumerate(QUESTIONS, start=1):
        sql, note = "", ""
        try:
            sql = ask.write_sql(client, model, question, schema, metrics)
        except Exception as error:  # API problem, such as a usage limit
            status, note = "NOT TESTED", str(error)
        else:
            if correct_sql is None:
                status = "PASS" if sql == "CANNOT_ANSWER" else "FAIL"
            elif sql == "CANNOT_ANSWER" or not ask.is_safe(con, sql):
                status = "FAIL"
            else:
                expected = con.execute(correct_sql).fetchall()
                try:
                    actual = con.execute(sql).fetchall()
                    status = "PASS" if same_answer(expected, actual) else "FAIL"
                except Exception as error:
                    status, note = "FAIL", str(error)
        print(f"{number:>2}. {status:<10} {question}")
        if note:
            print(f"    {note[:200]}")
        results.append([question, status, sql, note])
        time.sleep(6)  # slow down to respect free-tier limits

    passed = sum(r[1] == "PASS" for r in results)
    tested = sum(r[1] != "NOT TESTED" for r in results)
    label = "with" if use_definitions else "without"
    print(f"\nScore {label} definitions: {passed}/{tested} passed"
          f" ({len(results) - tested} not tested)")

    report = ask.ROOT / "tests" / f"results_{label}_definitions.csv"
    report.parent.mkdir(exist_ok=True)
    with open(report, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["question", "status", "ai_sql", "note"])
        writer.writerows(results)
    print(f"Details saved to {report}")


if __name__ == "__main__":
    main()