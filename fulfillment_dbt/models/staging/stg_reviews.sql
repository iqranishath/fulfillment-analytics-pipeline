select
    review_id || '-' || order_id         as review_key,
    review_id,
    order_id,
    review_score,
    review_creation_date::timestamp    as review_created_at,
    review_answer_timestamp::timestamp as review_answered_at
from {{ source('raw', 'reviews') }}