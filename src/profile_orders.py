from pathlib import Path
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = PROJECT_ROOT / "data" / "raw"

orders = pd.read_csv(RAW_DATA / "olist_orders_dataset.csv")

print(orders.shape)
print(orders["order_status"].value_counts())
print(orders.isna().sum())


# Count missing values per status, like a pivot table

date_cols = [
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
]

print(orders[date_cols].isna().groupby(orders["order_status"]).sum())

# Convert date columns from text to real datetimes

ts_cols = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]
for col in ts_cols:
    orders[col] = pd.to_datetime(orders[col])

# Timestamp sequence checks: each step should happen after the previous one
approved_before_purchase = orders["order_approved_at"] < orders["order_purchase_timestamp"]
carrier_before_approval = orders["order_delivered_carrier_date"] < orders["order_approved_at"]
delivered_before_carrier = orders["order_delivered_customer_date"] < orders["order_delivered_carrier_date"]

print("Approved before purchase:", approved_before_purchase.sum())
print("Carrier handoff before approval:", carrier_before_approval.sum())
print("Delivered before carrier handoff:", delivered_before_carrier.sum())

# Duplicate check

print("Duplicate order_ids:", orders["order_id"].duplicated().sum())

# How far apart are approval and carrier handoff in the broken rows?
gap = orders["order_approved_at"] - orders["order_delivered_carrier_date"]
print(gap[carrier_before_approval].describe())

