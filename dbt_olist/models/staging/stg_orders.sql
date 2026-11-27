-- One row per order, with clear column names and delivery flags
select
    order_id,
    customer_id,
    order_status,
    cast(order_purchase_timestamp as timestamp)       as purchased_at,
    cast(order_delivered_customer_date as timestamp)  as delivered_at,
    cast(order_estimated_delivery_date as date)       as estimated_delivery_date,

    -- flag the data quality issue instead of deleting rows
    (order_status = 'delivered'
        and order_delivered_customer_date is null)    as is_missing_delivery_date,

    -- empty (null) when there is no delivery date
    date_diff('day',
        cast(order_purchase_timestamp as timestamp),
        cast(order_delivered_customer_date as timestamp)) as delivery_days,

    cast(order_delivered_customer_date as date)
        > cast(order_estimated_delivery_date as date) as is_late
from {{ source('raw', 'orders') }}
