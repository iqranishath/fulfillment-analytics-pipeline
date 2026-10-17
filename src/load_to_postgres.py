import json
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

from validate_orders import (
    PROJECT_ROOT,
    MAX_REJECTION_RATE,
    load_orders,
    apply_rules,
    split_orders,
    build_run_metrics,
)

load_dotenv(PROJECT_ROOT / ".env")


def get_engine():
    """Build a database connection from the settings in .env."""
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    db = os.environ["POSTGRES_DB"]
    return create_engine(f"postgresql+psycopg2://{user}:{password}@localhost:5433/{db}")

def replace_table_contents(df, table, conn):
    """Empty and refill a raw table, keeping the table (and views built on it) in place."""
    if inspect(conn).has_table(table, schema="raw"):
        conn.execute(text(f"TRUNCATE TABLE raw.{table}"))
        df.to_sql(table, conn, schema="raw", if_exists="append", index=False)
    else:
        df.to_sql(table, conn, schema="raw", if_exists="replace", index=False)


def load_to_postgres(engine, clean, rejected, metrics):
    """Write clean rows, rejected rows and the run log in one transaction."""
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
        run_log.to_sql("pipeline_runs", conn, schema="raw", if_exists="append", index=False)


if __name__ == "__main__":
    orders = apply_rules(load_orders())
    clean, rejected = split_orders(orders)
    metrics = build_run_metrics(orders, clean, rejected)

    if metrics["rejection_rate"] > MAX_REJECTION_RATE:
        raise SystemExit("FAILED: rejection rate above limit, nothing loaded")

    load_to_postgres(get_engine(), clean, rejected, metrics)
    print(f"Loaded {len(clean)} clean and {len(rejected)} rejected orders into Postgres")