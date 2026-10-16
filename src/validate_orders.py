from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = PROJECT_ROOT / "data" / "raw"

TIMESTAMP_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def load_orders():
    """Read the raw orders CSV and convert date columns to datetimes."""
    orders = pd.read_csv(RAW_DATA / "olist_orders_dataset.csv")
    for col in TIMESTAMP_COLS:
        orders[col] = pd.to_datetime(orders[col])
    return orders


def apply_rules(orders):
    """Add a rejection_reason column and one True/False column per flag rule."""
    delivered = orders["order_status"] == "delivered"
    canceled = orders["order_status"] == "canceled"

    # Rejection rule: can't calculate SLA without a delivery date
    orders["rejection_reason"] = None
    missing_delivery = delivered & orders["order_delivered_customer_date"].isna()
    orders.loc[missing_delivery, "rejection_reason"] = "delivered_missing_delivery_date"

    # Flag rules: row is usable but suspicious
    orders["flag_missing_approval"] = delivered & orders["order_approved_at"].isna()
    orders["flag_missing_carrier_date"] = delivered & orders["order_delivered_carrier_date"].isna()
    orders["flag_canceled_but_delivered"] = canceled & orders["order_delivered_customer_date"].notna()
    orders["flag_carrier_before_approval"] = (
        orders["order_delivered_carrier_date"] < orders["order_approved_at"]
    )
    orders["flag_delivered_before_carrier"] = (
        orders["order_delivered_customer_date"] < orders["order_delivered_carrier_date"]
    )
    return orders


if __name__ == "__main__":
    orders = apply_rules(load_orders())

    print("Rejected:", orders["rejection_reason"].notna().sum())

    flag_cols = [col for col in orders.columns if col.startswith("flag_")]
    print(orders[flag_cols].sum())