import duckdb

con = duckdb.connect("db/olist.duckdb", read_only=True)

print(con.sql("""
    SELECT
        ROUND(SUM(i.price), 2) AS revenue,
        COUNT(DISTINCT o.order_id) AS orders,
        ROUND(SUM(i.price) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
    FROM staging.stg_order_items i
    JOIN staging.stg_orders o ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
"""))