with delivered_orders as (
    select *
    from {{ ref('stg_orders') }}
    where order_status = 'delivered'
)

select
    order_id,
    customer_id,
    purchased_at,
    date_trunc('month', purchased_at)::date        as purchase_month,
    estimated_delivery_date,
    delivered_at,
    delivered_at::date                             as delivered_date,
    delivered_at::date > estimated_delivery_date   as is_late,
    delivered_at::date - estimated_delivery_date   as days_late,
    delivered_at::date - purchased_at::date        as delivery_days,
    flag_missing_approval,
    flag_missing_carrier_date,
    flag_carrier_before_approval,
    flag_delivered_before_carrier
from delivered_orders