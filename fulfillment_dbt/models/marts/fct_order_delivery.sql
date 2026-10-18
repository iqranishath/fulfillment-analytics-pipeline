with delivered_orders as (
    select *
    from {{ ref('stg_orders') }}
    where order_status = 'delivered'
),

latest_reviews as (
    select order_id, review_score
    from (
        select
            order_id,
            review_score,
            row_number() over (
                partition by order_id
                order by review_answered_at desc nulls last, review_created_at desc
            ) as review_rank
        from {{ ref('stg_reviews') }}
    ) ranked
    where review_rank = 1
),

customers as (
    select
        customer_id,
        customer_unique_id,
        state as customer_state
    from {{ ref('stg_customers') }}
),

seller_deadlines as (
    select
        order_id,
        max(seller_ship_deadline)         as seller_ship_deadline,
        count(distinct seller_id)         as seller_count,
        sum(price)                        as items_value,
        sum(freight_value)                as freight_value,
        sum(price) + sum(freight_value)   as order_value
    from {{ ref('stg_order_items') }}
    group by order_id
),

joined as (
    select
        o.order_id,
        o.customer_id,
        c.customer_unique_id,
        c.customer_state,
        o.purchased_at,
        date_trunc('month', o.purchased_at)::date        as purchase_month,
        o.shipped_to_carrier_at,
        s.seller_ship_deadline,
        s.seller_count,
        s.order_value,
        o.estimated_delivery_date,
        o.delivered_at,
        o.delivered_at::date                             as delivered_date,
        o.delivered_at::date > o.estimated_delivery_date as is_late,
        o.delivered_at::date - o.estimated_delivery_date as days_late,
        o.delivered_at::date - o.purchased_at::date      as delivery_days,
        o.shipped_to_carrier_at > s.seller_ship_deadline as seller_handoff_late,
        r.review_score,
        o.flag_missing_approval,
        o.flag_missing_carrier_date,
        o.flag_carrier_before_approval,
        o.flag_delivered_before_carrier
    from delivered_orders o
    left join customers c        on o.customer_id = c.customer_id
    left join latest_reviews r   on o.order_id = r.order_id
    left join seller_deadlines s on o.order_id = s.order_id
)

select
    *,
    case
        when not is_late                                          then 'on_time'
        when shipped_to_carrier_at is null
          or seller_ship_deadline is null
          or flag_delivered_before_carrier                        then 'unknown'
        when seller_handoff_late                                  then 'seller'
        else 'carrier'
    end as delay_cause
from joined