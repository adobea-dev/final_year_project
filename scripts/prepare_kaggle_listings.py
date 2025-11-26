import sys
from pathlib import Path
import uuid
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.database import DatabaseConfig  # noqa

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "kaggle_listings.csv"
OUT_PATH = PROJECT_ROOT / "data" / "staged" / "listings_prepared.csv"

AUTOCHEK_COUNTRIES = ["GH", "NG", "KE", "UG"]
CITY_MAP = {
    "GH": ["Accra", "Kumasi", "Tema", "Takoradi", "Tamale"],
    "NG": ["Lagos", "Abuja", "Port Harcourt", "Kano", "Ibadan"],
    "KE": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"],
    "UG": ["Kampala", "Entebbe", "Jinja", "Gulu", "Mbarara"],
}

def main():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing raw Kaggle CSV at {RAW_PATH}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW_PATH)

    # Clean Price
    df["Price"] = pd.to_numeric(df["Price"].astype(str).str.replace(",", "").str.strip(), errors="coerce")

    # Parse DatePosted
    df["DatePosted"] = pd.to_datetime(df["DatePosted"], errors="coerce").dt.date

    # Create listing_id
    df["listing_id"] = [str(uuid.uuid4()) for _ in range(len(df))]

    # Assign a country per row (you can bias this later)
    rng = np.random.default_rng(42)
    df["country"] = rng.choice(AUTOCHEK_COUNTRIES, size=len(df), replace=True)

    # Replace location with Autochek-like cities per assigned country
    def make_location(row):
        return rng.choice(CITY_MAP[row["country"]])
    df["Location"] = df.apply(make_location, axis=1)

    # Pull eligible dealer_ids from Postgres
    engine = DatabaseConfig.get_postgres_engine()
    dealers = pd.read_sql(
        """
        SELECT dealer_id, country
        FROM dealers
        WHERE has_listings = true
        """,
        engine
    )

    # Assign dealer_id based on assigned country
    # For each country, we pick from eligible dealers in that country
    def assign_dealer_id(row):
        pool = dealers[dealers["country"] == row["country"]]["dealer_id"].values
        if len(pool) == 0:
            return None
        return pool[int(rng.integers(0, len(pool)))]

    df["dealer_id"] = df.apply(assign_dealer_id, axis=1)

    # Keep only rows that successfully got a dealer_id (avoids FK errors)
    df = df[df["dealer_id"].notna()].copy()

    # Rename Kaggle columns to match your listings table
    prepared = df.rename(columns={
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
    })

    # Final columns that match Postgres listings table
    prepared = prepared[
        ["listing_id", "country", "dealer_id", "date_posted", "title", "seller_type", "price",
         "car_make", "car_model", "car_variant", "condition", "year_manufactured",
         "transmission", "engine_capacity", "body_type", "location", "warranty",
         "mileage", "colour_type", "colour", "description"]
    ].copy()

    prepared.to_csv(OUT_PATH, index=False)
    print(f"Saved prepared listings to: {OUT_PATH} with {len(prepared)} rows")

if __name__ == "__main__":
    main()
