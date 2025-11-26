from __future__ import annotations

import sys
from pathlib import Path
import zipfile
import uuid
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.database import DatabaseConfig  # noqa: E402


ZIP_PATH = PROJECT_ROOT / "data" / "synth" / "autochek_synth_dataset.zip"
EXTRACT_DIR = PROJECT_ROOT / "data" / "synth" / "autochek_synth_dataset_extracted"

RESET_TABLES_BEFORE_LOAD = True

REQUIRED_FILES = [
    "account_managers.csv",
    "dealers.csv",
    "raw_listings_kaggle_schema.csv",
    "leads.csv",
    "applications.csv",
    "sales.csv",
    "dealer_activity_metrics.csv",
]


def extracted_ready() -> bool:
    return EXTRACT_DIR.exists() and all((EXTRACT_DIR / f).exists() for f in REQUIRED_FILES)


def ensure_extracted() -> None:
    if extracted_ready():
        return

    if not ZIP_PATH.exists():
        missing = [f for f in REQUIRED_FILES if not (EXTRACT_DIR / f).exists()]
        raise FileNotFoundError(
            "Zip not found and extracted CSVs are incomplete.\n"
            f"Zip expected at: {ZIP_PATH}\n"
            f"Extracted dir: {EXTRACT_DIR}\n"
            f"Missing CSVs: {missing}"
        )

    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(EXTRACT_DIR)

    if not extracted_ready():
        missing = [f for f in REQUIRED_FILES if not (EXTRACT_DIR / f).exists()]
        raise FileNotFoundError(f"Extracted but still missing CSVs: {missing}")


def read_csv(filename: str) -> pd.DataFrame:
    path = EXTRACT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")
    return pd.read_csv(path)


def reset_tables(engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            TRUNCATE TABLE
                dealer_activity_metrics,
                sales,
                applications,
                leads,
                listings,
                dealers,
                account_managers
            RESTART IDENTITY CASCADE;
            """
        )


def get_table_schema(engine, table_name: str) -> pd.DataFrame:
    q = """
    SELECT
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = %(t)s
    ORDER BY ordinal_position
    """
    return pd.read_sql(q, engine, params={"t": table_name})


def align_df_to_table(engine, table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    schema = get_table_schema(engine, table_name)
    if schema.empty:
        raise RuntimeError(f"Table not found in Postgres (public.{table_name}).")

    df = df.copy()

    # 1) Drop columns that are not in the DB table
    table_cols = schema["column_name"].tolist()
    extra = [c for c in df.columns if c not in table_cols]
    if extra:
        df = df.drop(columns=extra)

    # 2) Check required columns (NOT NULL + no default) exist in df
    required = schema[(schema["is_nullable"] == "NO") & (schema["column_default"].isna())]["column_name"].tolist()
    missing_required = [c for c in required if c not in df.columns]
    if missing_required:
        raise ValueError(
            f"{table_name}: missing required columns required by Postgres: {missing_required}\n"
            f"DF columns: {list(df.columns)}"
        )

    # 3) Cast types based on Postgres column data_type
    dtype_map = dict(zip(schema["column_name"], schema["data_type"]))

    for col in df.columns:
        t = dtype_map.get(col)

        if t in ("integer", "bigint", "smallint"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

            # If required, fill missing with 0 (common for count fields)
            if col in required:
                df[col] = df[col].fillna(0)

            df[col] = df[col].astype("Int64")  # nullable int

        elif t in ("numeric", "double precision", "real", "decimal"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if col in required:
                df[col] = df[col].fillna(0.0)

        elif t == "date":
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

        elif "timestamp" in str(t):
            df[col] = pd.to_datetime(df[col], errors="coerce")

        elif t == "boolean":
            # normalize common bool strings/numbers
            df[col] = df[col].map(
                lambda x: True if str(x).strip().lower() in ("true", "t", "1", "yes", "y") else
                          False if str(x).strip().lower() in ("false", "f", "0", "no", "n") else
                          None
            )

        elif t == "uuid":
            # generate UUIDs only if this uuid column is required and has nulls
            if col in required:
                mask = df[col].isna()
                if mask.any():
                    df.loc[mask, col] = [str(uuid.uuid4()) for _ in range(mask.sum())]

        # else: text/varchar, leave as-is

    # 4) Hard check: required columns cannot be null now
    for col in required:
        if col in df.columns and df[col].isna().any():
            bad = df[df[col].isna()].head(5)
            raise ValueError(
                f"{table_name}: required column '{col}' still has NULLs after cleaning.\n"
                f"Sample bad rows:\n{bad}"
            )

    # 5) Insert only columns that exist in DB table, in DB order
    insert_cols = [c for c in table_cols if c in df.columns]
    return df[insert_cols].copy()


def fix_dealers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    return df.rename(columns={"DF_Category": "df_category", "Dealer_Class": "dealer_class"})


def fix_listings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "listing_id" not in df.columns:
        df["listing_id"] = [str(uuid.uuid4()) for _ in range(len(df))]

    if "DatePosted" in df.columns:
        df["DatePosted"] = pd.to_datetime(df["DatePosted"], errors="coerce").dt.date

    df = df.rename(
        columns={
            "DatePosted": "date_posted",
            "Title": "title",
            "Seller Type": "seller_type",
            "Price": "price",
            "Car Make": "car_make",
            "Car Model": "car_model",
            "Car Variant": "car_variant",
            "Condition": "condition",
            "Year Manufactured": "year_manufactured",
            "Transmission": "transmission",
            "Engine Capacity": "engine_capacity",
            "Body Type": "body_type",
            "Location": "location",
            "Warranty": "warranty",
            "Mileage": "mileage",
            "Colour Type": "colour_type",
            "Colour": "colour",
            "Description": "description",
        }
    )

    if "price" in df.columns:
        df["price"] = (
            df["price"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    return df


def fix_leads(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "lead_date" in df.columns:
        df["lead_date"] = pd.to_datetime(df["lead_date"], errors="coerce").dt.date
    return df


def fix_applications(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "lead_date" in df.columns:
        df["lead_date"] = pd.to_datetime(df["lead_date"], errors="coerce").dt.date
    return df


def fix_sales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "fulfillment_date" in df.columns:
        df["fulfillment_date"] = pd.to_datetime(df["fulfillment_date"], errors="coerce").dt.date
    if "gmv_in_dollars" in df.columns:
        df["gmv_in_dollars"] = pd.to_numeric(df["gmv_in_dollars"], errors="coerce").fillna(0.0)
    return df


def fix_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "period_start_date" in df.columns:
        df["period_start_date"] = pd.to_datetime(df["period_start_date"], errors="coerce").dt.date
    if "period_end_date" in df.columns:
        df["period_end_date"] = pd.to_datetime(df["period_end_date"], errors="coerce").dt.date

    # Counts should always be integers
    for c in ["active_listings", "applications_count", "sales_count", "leads_count"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    if "gmv_total" in df.columns:
        df["gmv_total"] = pd.to_numeric(df["gmv_total"], errors="coerce").fillna(0.0)

    df = df.drop_duplicates(subset=["dealer_id", "country", "period_start_date", "period_end_date"])

    return df


def load_table(engine, table_name: str, df: pd.DataFrame, chunksize: int = 1000, method: str | None = "multi") -> None:
    print(f"\nLoading {table_name} ...")
    df2 = align_df_to_table(engine, table_name, df)
    print(f"{table_name}: inserting {len(df2)} rows, {len(df2.columns)} cols")

    df2.to_sql(table_name, engine, if_exists="append", index=False, method=method, chunksize=chunksize)

    with engine.connect() as conn:
        n = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table_name}").scalar()
    print(f"{table_name}: done, total rows now = {n}")


def main() -> None:
    ensure_extracted()
    engine = DatabaseConfig.get_postgres_engine()

    if RESET_TABLES_BEFORE_LOAD:
        reset_tables(engine)

    ams = read_csv("account_managers.csv")
    dealers = fix_dealers(read_csv("dealers.csv"))
    listings = fix_listings(read_csv("raw_listings_kaggle_schema.csv"))
    leads = fix_leads(read_csv("leads.csv"))
    applications = fix_applications(read_csv("applications.csv"))
    sales = fix_sales(read_csv("sales.csv"))
    metrics = fix_metrics(read_csv("dealer_activity_metrics.csv"))

    # Load in FK-safe order
    load_table(engine, "account_managers", ams, chunksize=1000)
    load_table(engine, "dealers", dealers, chunksize=1000)
    load_table(engine, "listings", listings, chunksize=500)
    load_table(engine, "leads", leads, chunksize=1000)
    load_table(engine, "applications", applications, chunksize=1000)
    load_table(engine, "sales", sales, chunksize=1000)
    load_table(engine, "dealer_activity_metrics", metrics, chunksize=500)

    print("\nAll tables loaded successfully.")


if __name__ == "__main__":
    main()
