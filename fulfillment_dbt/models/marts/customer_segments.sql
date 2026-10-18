with customers as (
    select *
    from {{ ref('dim_customers') }}
),

reference_date as (
    select max(last_order_at) as as_of_date
    from customers
),

scored as (
    select
        c.customer_unique_id,
        c.order_count,
        c.total_spend,
        c.last_order_at,
        (r.as_of_date::date - c.last_order_at::date)          as recency_days,
        ntile(4) over (order by c.last_order_at)              as recency_score,
        ntile(4) over (order by c.total_spend nulls first)    as monetary_score
    from customers c
    cross join reference_date r
)

select
    *,
    case
        when order_count >= 2                              then 'repeat'
        when recency_score >= 3 and monetary_score >= 3    then 'recent_high_value'
        when recency_score >= 3                            then 'recent_low_value'
        when monetary_score >= 3                           then 'lapsed_high_value'
        else 'lapsed_low_value'
    end as rfm_segment
from scored