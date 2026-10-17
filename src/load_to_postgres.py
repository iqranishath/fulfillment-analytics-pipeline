import json
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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
        clean.to_sql("orders", conn, schema="raw", if_exists="replace", index=False)
        rejected.to_sql("orders_rejected", conn, schema="raw", if_exists="replace", index=False)
        run_log.to_sql("pipeline_runs", conn, schema="raw", if_exists="append", index=False)


if __name__ == "__main__":
    orders = apply_rules(load_orders())
    clean, rejected = split_orders(orders)
    metrics = build_run_metrics(orders, clean, rejected)

    if metrics["rejection_rate"] > MAX_REJECTION_RATE:
        raise SystemExit("FAILED: rejection rate above limit, nothing loaded")

    load_to_postgres(get_engine(), clean, rejected, metrics)
    print(f"Loaded {len(clean)} clean and {len(rejected)} rejected orders into Postgres")