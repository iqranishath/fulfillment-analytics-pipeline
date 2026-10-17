import json
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

from validate_orders import (
    PROJECT_ROOT,
    RAW_DATA,  # NEW
    MAX_REJECTION_RATE,
    load_orders,
    apply_rules,
    split_orders,
    build_run_metrics,
)

load_dotenv(PROJECT_ROOT / ".env")

# NEW: supporting tables, loaded as-is and checked later by dbt tests
EXTRA_TABLES = {
    "order_items": "olist_order_items_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
}


def get_engine():
    """Build a database connection from the settings in .env."""
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    db = os.environ["POSTGRES_DB"]
    return create_engine(f"postgresql+psycopg2://{user}:{password}@localhost:5433/{db}")


# NEW
def load_extra_tables():
    """Read the supporting CSVs into a dictionary of DataFrames."""
    return {name: pd.read_csv(RAW_DATA / file) for name, file in EXTRA_TABLES.items()}


def replace_table_contents(df, table, conn):
    """Empty and refill a raw table, keeping the table (and views built on it) in place."""
    if inspect(conn).has_table(table, schema="raw"):
        conn.execute(text(f"TRUNCATE TABLE raw.{table}"))
        df.to_sql(table, conn, schema="raw", if_exists="append", index=False)
    else:
        df.to_sql(table, conn, schema="raw", if_exists="replace", index=False)


def load_to_postgres(engine, clean, rejected, metrics, extra_tables):  # CHANGED: extra_tables
    """Write all tables and the run log in one transaction."""
    run_log = pd.DataFrame([{
        "run_at": metrics["run_at"],
        "rows_read": metrics["rows_read"],
        "rows_clean": metrics["rows_clean"],
        "rows_rejected": metrics["rows_rejected"],
        "rejection_rate": metrics["rejection_rate"],
        "flag_counts": json.dumps(metrics["flag_counts"]),
    }])

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        replace_table_contents(clean, "orders", conn)
        replace_table_contents(rejected, "orders_rejected", conn)
        for name, df in extra_tables.items():  # NEW
            replace_table_contents(df, name, conn)
        run_log.to_sql("pipeline_runs", conn, schema="raw", if_exists="append", index=False)


if __name__ == "__main__":
    orders = apply_rules(load_orders())
    clean, rejected = split_orders(orders)
    metrics = build_run_metrics(orders, clean, rejected)

    if metrics["rejection_rate"] > MAX_REJECTION_RATE:
        raise SystemExit("FAILED: rejection rate above limit, nothing loaded")

    extra_tables = load_extra_tables()  # NEW
    load_to_postgres(get_engine(), clean, rejected, metrics, extra_tables)

    print(f"Loaded {len(clean)} clean and {len(rejected)} rejected orders into Postgres")
    for name, df in extra_tables.items():  # NEW
        print(f"Loaded {len(df)} rows into raw.{name}")