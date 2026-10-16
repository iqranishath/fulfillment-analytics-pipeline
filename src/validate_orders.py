import json
from datetime import datetime
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"
MAX_REJECTION_RATE = 0.001  # fail the run if more than 1% of rows are rejected

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


#
def split_orders(orders):
    """Separate rejected rows from clean rows."""
    rejected_mask = orders["rejection_reason"].notna()
    clean = orders[~rejected_mask]
    rejected = orders[rejected_mask]
    return clean, rejected


#
def build_run_metrics(orders, clean, rejected):
    """Summarise this run: row counts, rejection rate and flag counts."""
    flag_cols = [col for col in orders.columns if col.startswith("flag_")]
    return {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "rows_read": len(orders),
        "rows_clean": len(clean),
        "rows_rejected": len(rejected),
        "rejection_rate": round(len(rejected) / len(orders), 5),
        "flag_counts": {col: int(orders[col].sum()) for col in flag_cols},
    }


#
def write_outputs(clean, rejected, metrics, passed):
    """Always write rejected rows and metrics; write clean data only if the run passed."""
    PROCESSED_DATA.mkdir(parents=True, exist_ok=True)
    rejected.to_csv(PROCESSED_DATA / "orders_rejected.csv", index=False)
    with open(PROCESSED_DATA / "run_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    if passed:
        clean.to_csv(PROCESSED_DATA / "orders_clean.csv", index=False)


# the main block now splits, writes and checks the threshold
if __name__ == "__main__":
    orders = apply_rules(load_orders())
    clean, rejected = split_orders(orders)
    metrics = build_run_metrics(orders, clean, rejected)

    passed = metrics["rejection_rate"] <= MAX_REJECTION_RATE
    write_outputs(clean, rejected, metrics, passed)

    print(json.dumps(metrics, indent=2))

    if not passed:
        raise SystemExit(
            f"FAILED: rejection rate {metrics['rejection_rate']:.2%} "
            f"exceeds limit {MAX_REJECTION_RATE:.2%}"
        )
    print("PASSED: clean data written")