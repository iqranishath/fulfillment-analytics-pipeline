select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date::timestamp as seller_ship_deadline,
    price,
    freight_value
from {{ source('raw', 'order_items') }}