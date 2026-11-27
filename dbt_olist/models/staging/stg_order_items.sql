-- One row per item inside an order
select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    cast(price as decimal(12, 2))          as price,
    cast(freight_value as decimal(12, 2))  as freight_value
from {{ source('raw', 'order_items') }}
