"""Load the Olist CSV files into one DuckDB database and run basic checks."""
from pathlib import Path

import duckdb

# Build paths from this file's location, so the script works from any folder
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "db" / "olist.duckdb"

# table name -> CSV file name
TABLES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# Each query counts problem rows
CHECKS = {
    "Duplicate order IDs": """
        SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM raw.orders
    """,
    "Delivered orders with no delivery date": """
        SELECT COUNT(*) FROM raw.orders
        WHERE order_status = 'delivered'
          AND order_delivered_customer_date IS NULL
    """,
    "Order items with no matching order": """
        SELECT COUNT(*) FROM raw.order_items i
        LEFT JOIN raw.orders o ON i.order_id = o.order_id
        WHERE o.order_id IS NULL
    """,
}


def main():
    # Stop early with a clear message if any file is missing
    missing = [f for f in TABLES.values() if not (RAW_DIR / f).exists()]
    if missing:
        raise SystemExit("Missing files in data/raw:\n  " + "\n  ".join(missing))

    DB_PATH.parent.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    # 'raw' schema holds untouched source data
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    print("Loading tables")
    for table, filename in TABLES.items():
        # CREATE OR REPLACE makes the script safe to run again
        con.execute(
            f"CREATE OR REPLACE TABLE raw.{table} AS "
            "SELECT * FROM read_csv_auto(?, header=true)",
            [str(RAW_DIR / filename)],
        )
        rows = con.execute(f"SELECT COUNT(*) FROM raw.{table}").fetchone()[0]
        print(f"  raw.{table:<22} {rows:>10,} rows")

    print("\nData quality checks")
    for name, query in CHECKS.items():
        count = con.execute(query).fetchone()[0]
        print(f"  {name:<42} {count:,}")

    con.close()
    print(f"\nDone. Database saved to {DB_PATH}")


if __name__ == "__main__":
    main()
