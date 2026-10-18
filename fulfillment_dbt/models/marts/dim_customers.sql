with orders as (
    select *
    from {{ ref('fct_order_delivery') }}
),

customer_summary as (
    select
        customer_unique_id,
        count(*)                    as order_count,
        min(purchased_at)           as first_order_at,
        max(purchased_at)           as last_order_at,
        sum(order_value)            as total_spend,
        round(avg(review_score), 2) as avg_review_score,
        bool_or(is_late)            as ever_late
    from orders
    group by customer_unique_id
),

first_orders as (
    select
        customer_unique_id,
        customer_state,
        is_late        as first_order_late,
        delay_cause    as first_order_delay_cause,
        delivery_days  as first_order_delivery_days,
        review_score   as first_order_review_score
    from (
        select
            *,
            row_number() over (
                partition by customer_unique_id
                order by purchased_at
            ) as order_rank
        from orders
    ) ranked
    where order_rank = 1
)

select
    s.customer_unique_id,
    f.customer_state,
    s.order_count,
    s.order_count > 1 as is_repeat_customer,
    s.first_order_at,
    s.last_order_at,
    s.total_spend,
    s.avg_review_score,
    s.ever_late,
    f.first_order_late,
    f.first_order_delay_cause,
    f.first_order_delivery_days,
    f.first_order_review_score
from customer_summary s
join first_orders f on s.customer_unique_id = f.customer_unique_id