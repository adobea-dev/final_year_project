from __future__ import annotations

from pathlib import Path
import uuid
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXTRACT_DIR = PROJECT_ROOT / "data" / "synth" / "autochek_synth_dataset_extracted"
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

# Use your prepared listings as templates for required listing columns
LISTING_TEMPLATE_PATH = PROJECT_ROOT / "data" / "staged" / "listings_prepared.csv"

# Use existing dealers snapshot as the “population”
DEALERS_PATH = EXTRACT_DIR / "dealers.csv"
ACCOUNT_MANAGERS_PATH = EXTRACT_DIR / "account_managers.csv"  # keep if you already have it

# Time setup (monthly)
START_DATE = "2023-01-01"
END_DATE = "2023-08-31"

# Tier proportions per country
TIER_SPLIT = {
    "Platinum": 0.05,
    "Gold": 0.10,
    "Silver": 0.25,
    "Bronze": 0.60,
}

# Tier intensity. These drive raw event counts per month. "strength level" you use when generating synthetic data. It controls how many leads, applications, sales, and listings a dealer produces per period.
# You can tune these, but keep the ordering.
TIER_LEVELS = {
    "Bronze":   {"leads_mu": 6,  "apps_rate": 0.20, "sales_rate": 0.35, "listings_mu": 2},
    "Silver":   {"leads_mu": 18, "apps_rate": 0.28, "sales_rate": 0.40, "listings_mu": 6},
    "Gold":     {"leads_mu": 40, "apps_rate": 0.35, "sales_rate": 0.45, "listings_mu": 14},
    "Platinum": {"leads_mu": 250, "apps_rate": 0.70, "sales_rate": 0.80, "listings_mu": 100},

}

LEAD_SOURCES = ["web", "referral", "social", "marketplace"]
LEAD_CHANNELS = ["organic", "paid", "direct"]
APP_SOURCES = ["bank_partner", "autochek_form", "branch"]
PRODUCT_STATUS = ["submitted", "approved", "rejected"]
BANKS = ["Bank A", "Bank B", "Bank C"]
PRODUCT_CLASSES = ["car_loan", "personal_loan"]

RNG = np.random.default_rng(42)


def month_periods(start_date: str, end_date: str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    starts = pd.date_range(start_date, end_date, freq="MS")
    periods = []
    for s in starts:
        e = (s + pd.offsets.MonthEnd(1)).normalize()
        if e > pd.to_datetime(end_date):
            e = pd.to_datetime(end_date)
        periods.append((s, e))
    return periods


def random_dates_in_period(n: int, start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    if n <= 0:
        return []
    span = (end - start).days
    offsets = RNG.integers(0, max(span + 1, 1), size=n)
    return [start + pd.Timedelta(days=int(o)) for o in offsets]


def assign_tiers(dealers_df: pd.DataFrame) -> pd.DataFrame:
    dealers_df = dealers_df.copy()

    # Ensure countries exist
    countries = sorted(dealers_df["country"].dropna().unique().tolist())

    tier_map = {}
    for c in countries:
        ids = dealers_df.loc[dealers_df["country"] == c, "dealer_id"].dropna().unique().tolist()
        RNG.shuffle(ids)
        n = len(ids)
        if n == 0:
            continue

        # Compute counts for each tier
        platinum_n = max(1, int(round(TIER_SPLIT["Platinum"] * n)))
        gold_n = max(1, int(round(TIER_SPLIT["Gold"] * n)))
        silver_n = max(1, int(round(TIER_SPLIT["Silver"] * n)))
        bronze_n = n - (platinum_n + gold_n + silver_n)
        if bronze_n < 0:
            bronze_n = 0

        tiers = (["Platinum"] * platinum_n +
                 ["Gold"] * gold_n +
                 ["Silver"] * silver_n +
                 ["Bronze"] * bronze_n)
        tiers = tiers[:n]

        for did, t in zip(ids, tiers):
            tier_map[did] = t

    dealers_df["synthetic_tier"] = dealers_df["dealer_id"].map(tier_map).fillna("Bronze")
    return dealers_df


def main() -> None:
    if not DEALERS_PATH.exists():
        raise FileNotFoundError(f"Missing {DEALERS_PATH}. Run your existing extract first or place dealers.csv there.")

    if not LISTING_TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Missing {LISTING_TEMPLATE_PATH}. Run prepare_kaggle_listings.py first.")

    dealers = pd.read_csv(DEALERS_PATH)
    dealers = dealers.dropna(subset=["dealer_id", "country"])
    dealers = assign_tiers(dealers)

    listing_template = pd.read_csv(LISTING_TEMPLATE_PATH)
    # Use templates only for non-key fields
    template_cols = [c for c in listing_template.columns if c not in {"listing_id", "country", "dealer_id", "date_posted"}]

    periods = month_periods(START_DATE, END_DATE)

    leads_rows = []
    apps_rows = []
    sales_rows = []
    listings_rows = []
    metrics_rows = []

    # Track sales per dealer per period for growth
    prev_sales_units = {}

    for (p_start, p_end) in periods:
        for _, drow in dealers.iterrows():
            dealer_id = drow["dealer_id"]
            country = drow["country"]
            dealer_name = drow.get("dealership_name", drow.get("dealer_name", str(dealer_id)))
            tier = drow["synthetic_tier"]
            cfg = TIER_LEVELS[tier]

            # Generate raw counts
            leads_count = int(RNG.poisson(cfg["leads_mu"]))
            apps_count = int(RNG.binomial(leads_count, cfg["apps_rate"])) if leads_count > 0 else 0
            sales_units = int(RNG.binomial(apps_count, cfg["sales_rate"])) if apps_count > 0 else 0
            listings_count = int(RNG.poisson(cfg["listings_mu"]))

            # Build lead events
            for dt in random_dates_in_period(leads_count, p_start, p_end):
                leads_rows.append({
                    "lead_id": str(uuid.uuid4()),
                    "country": country,
                    "lead_date": dt.date(),
                    "lead_source": RNG.choice(LEAD_SOURCES),
                    "lead_channel": RNG.choice(LEAD_CHANNELS),
                    "dealer_id": dealer_id,
                    "dealer_name": dealer_name,
                    "linked_loanid": ""  # optional
                })

            # Build application events
            for dt in random_dates_in_period(apps_count, p_start, p_end):
                apps_rows.append({
                    "loanid": str(uuid.uuid4()),
                    "country": country,
                    "lead_date": dt.date(),  # your applications table uses lead_date
                    "source": RNG.choice(APP_SOURCES),
                    "dealer_id": dealer_id,
                    "dealer_name": dealer_name,
                    "product_status": RNG.choice(PRODUCT_STATUS),
                })

            # Build sales events
            for dt in random_dates_in_period(sales_units, p_start, p_end):
                sales_rows.append({
                    "transaction_id": str(uuid.uuid4()),
                    "country": country,
                    "fulfillment_date": dt.date(),
                    "gmv_in_dollars": float(RNG.integers(6000, 14000)),
                    "product_classification": RNG.choice(PRODUCT_CLASSES),
                    "lead_source": RNG.choice(LEAD_SOURCES),
                    "loan_id": "",  # optional
                    "financing_bank": RNG.choice(BANKS),
                    "dealer_source_name": dealer_name,
                    "dealer_id": dealer_id,
                })

            # Build listing postings (inventory updates)
            if listings_count > 0:
                sampled = listing_template.sample(n=listings_count, replace=True, random_state=int(RNG.integers(0, 10_000)))
                dates = random_dates_in_period(listings_count, p_start, p_end)
                for i, (_, tmpl) in enumerate(sampled.iterrows()):
                    row = {
                        "listing_id": str(uuid.uuid4()),
                        "country": country,
                        "dealer_id": dealer_id,
                        "date_posted": dates[i].date(),
                    }
                    for c in template_cols:
                        row[c] = tmpl.get(c)
                    listings_rows.append(row)

            # Compute sales_growth using previous period sales_units
            prev = prev_sales_units.get(dealer_id, None)
            if prev is None or prev <= 0:
                sales_growth = 0.0
            else:
                sales_growth = ((sales_units - prev) / prev) * 100.0
            prev_sales_units[dealer_id] = sales_units

            # Metrics row (this matches what scoring_agent expects)
            metrics_rows.append({
                "dealer_id": dealer_id,
                "country": country,
                "period_start_date": p_start.date(),
                "period_end_date": p_end.date(),
                "sales_units": sales_units,
                "sales_growth": float(sales_growth),
                "inventory_update_count": listings_count,
                "applications_count": apps_count,
                "leads_count": leads_count,
            })

    # Write outputs
    pd.DataFrame(leads_rows).to_csv(EXTRACT_DIR / "leads.csv", index=False)
    pd.DataFrame(apps_rows).to_csv(EXTRACT_DIR / "applications.csv", index=False)
    pd.DataFrame(sales_rows).to_csv(EXTRACT_DIR / "sales.csv", index=False)
    pd.DataFrame(listings_rows).to_csv(EXTRACT_DIR / "raw_listings_kaggle_schema.csv", index=False)
    pd.DataFrame(metrics_rows).to_csv(EXTRACT_DIR / "dealer_activity_metrics.csv", index=False)

    print("Generated tier-diverse synthetic events and metrics.")
    print("Wrote to:", EXTRACT_DIR)


if __name__ == "__main__":
    main()
