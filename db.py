import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

CSV_TABLE_MAP = {
    "universities.csv": "universities",
    "admission_criteria.csv": "admission_criteria",
    "scholarship_rules.csv": "scholarship_rules",
    "eligibility_logs.csv": "eligibility_logs",
    "tuition_logs.csv": "tuition_logs",
    "inquiries.csv": "inquiries",
}
JSON_TABLE_MAP = {
    "users.json": "users",
    "agencies.json": "agencies",
}

def get_database_url():
    # Local fallback: read .streamlit/secrets.toml very simply.
    # In Streamlit Cloud, this is configured in App settings > Secrets.
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url

    secrets_path = BASE / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        for line in secrets_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    raise RuntimeError("DATABASE_URL was not found. Add it to .streamlit/secrets.toml or environment variables.")

def engine():
    return create_engine(get_database_url(), pool_pre_ping=True)

def clean_df(df):
    return df.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "")

def table_exists(table):
    with engine().connect() as conn:
        return conn.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table}).scalar() is not None

def create_tables_from_seed(refresh=False):
    eng = engine()

    for filename, table in CSV_TABLE_MAP.items():
        path = DATA / filename
        if not path.exists():
            continue
        if table_exists(table) and not refresh:
            print(f"Skipped existing table: {table}")
            continue
        df = pd.read_csv(path, keep_default_na=False).fillna("")
        clean_df(df).to_sql(table, eng, if_exists="replace", index=False)
        print(f"Uploaded CSV seed to Supabase: {table}")

    for filename, table in JSON_TABLE_MAP.items():
        path = DATA / filename
        if not path.exists():
            continue
        if table_exists(table) and not refresh:
            print(f"Skipped existing table: {table}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        df = pd.DataFrame(data)
        clean_df(df).to_sql(table, eng, if_exists="replace", index=False)
        print(f"Uploaded JSON seed to Supabase: {table}")

if __name__ == "__main__":
    create_tables_from_seed(refresh=False)
    print("Supabase database is ready.")
