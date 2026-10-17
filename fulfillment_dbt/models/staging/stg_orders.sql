select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp            as purchased_at,
    order_approved_at                   as approved_at,
    order_delivered_carrier_date        as shipped_to_carrier_at,
    order_delivered_customer_date       as delivered_at,
    order_estimated_delivery_date::date as estimated_delivery_date,
    flag_missing_approval,
    flag_missing_carrier_date,
    flag_canceled_but_delivered,
    flag_carrier_before_approval,
    flag_delivered_before_carrier
from {{ source('raw', 'orders') }}