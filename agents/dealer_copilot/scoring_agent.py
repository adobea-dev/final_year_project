# agents/dealer_copilot/scoring_agent.py
# scoring agent: compute scores and optionally store them in public.dealer_scores

from __future__ import annotations

from typing import Any, Dict, Optional, List

import numpy as np
import pandas as pd
from sqlalchemy import text

from .data_agent import DataAgent
from config.settings import settings
from config.database import DatabaseConfig


_ALLOWED_RESOLUTIONS = {"daily", "weekly", "monthly", "bi_monthly"}


def _resolution_to_step(resolution: str) -> str:
    r = resolution.lower().strip()
    if r == "daily":
        return "1 day"
    if r == "weekly":
        return "1 week"
    if r == "monthly":
        return "1 month"
    if r == "bi_monthly":
        return "2 months"
    raise ValueError(f"resolution must be one of: {sorted(_ALLOWED_RESOLUTIONS)}")


def _get_dealer_scores_column_map() -> Dict[str, Optional[str]]:
    """
    dealer_scores table supports:
    - overall_score OR dealer_score
    - tier OR health_tier
    - score_change_vs_previous_period OR some score_change* column
    - created_at optional
    """
    engine = DatabaseConfig.get_postgres_engine()

    q = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'dealer_scores'
    """
    cols = pd.read_sql(q, engine)["column_name"].astype(str).tolist()
    cols_set = {c.lower() for c in cols}

    if "overall_score" in cols_set:
        score_col = "overall_score"
    elif "dealer_score" in cols_set:
        score_col = "dealer_score"
    else:
        raise RuntimeError("dealer_scores is missing overall_score or dealer_score.")

    if "tier" in cols_set:
        tier_col = "tier"
    elif "health_tier" in cols_set:
        tier_col = "health_tier"
    else:
        raise RuntimeError("dealer_scores is missing tier or health_tier.")

    if "score_change_vs_previous_period" in cols_set:
        delta_col: Optional[str] = "score_change_vs_previous_period"
    else:
        candidates = [c for c in cols if c.lower().startswith("score_change")]
        delta_col = candidates[0] if candidates else None

    created_at_col = "created_at" if "created_at" in cols_set else None

    return {
        "score_col": score_col,
        "tier_col": tier_col,
        "delta_col": delta_col,
        "created_at_col": created_at_col,
    }


def _assign_tier(score: float) -> str:
    for tier, (low, high) in settings.DEALER_TIERS.items():
        if low <= float(score) <= high:
            return tier
    return "Unassigned"


# -----------------------------
# Aggregated scoring path
# -----------------------------
def _compute_scores_from_metrics(
    country: Optional[str] = None,
    period_start_date: Optional[str] = None,
    period_end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Uses dealer_activity_metrics (already aggregated).
    """
    data_agent = DataAgent()

    sql = """
        SELECT
            m.dealer_id,
            m.period_start_date,
            m.period_end_date,
            d.dealership_name,
            d.country,

            COALESCE(m.sales_units, 0) AS sales_units,
            COALESCE(m.sales_growth, 0) AS sales_growth,
            COALESCE(m.inventory_update_count, 0) AS inventory_update_count,
            COALESCE(m.applications_count, 0) AS applications_count,
            COALESCE(m.leads_count, 0) AS leads_count

        FROM public.dealer_activity_metrics m
        JOIN public.dealers d
            ON d.dealer_id = m.dealer_id
    """

    filters: List[str] = []
    params: Dict[str, Any] = {}

    if country and country != "ALL":
        filters.append("d.country = %(country)s")
        params["country"] = country

    if period_start_date:
        filters.append("m.period_start_date >= %(period_start_date)s")
        params["period_start_date"] = period_start_date

    if period_end_date:
        filters.append("m.period_end_date <= %(period_end_date)s")
        params["period_end_date"] = period_end_date

    if filters:
        sql += " WHERE " + " AND ".join(filters)

    df = data_agent.run_sql(sql, params=params, limit=5000)
    if df.empty:
        return df

    for c in ["sales_units", "sales_growth", "inventory_update_count", "applications_count", "leads_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    group_cols = ["country", "period_start_date", "period_end_date"]

    def norm(col: str) -> pd.Series:
        mx = df.groupby(group_cols)[col].transform("max")
        return np.where(mx > 0, (df[col] / mx) * 100.0, 0.0)

    df["sales_score"] = norm("sales_growth")
    df["inventory_score"] = norm("inventory_update_count")
    df["applications_score"] = norm("applications_count")
    df["leads_score"] = norm("leads_count")

    df["overall_score"] = (
        df["sales_score"] * settings.SALES_GROWTH_WEIGHT
        + df["inventory_score"] * settings.INVENTORY_FREQ_WEIGHT
        + df["applications_score"] * settings.APPLICATIONS_WEIGHT
        + df["leads_score"] * settings.LEADS_WEIGHT
    )

    df["overall_score"] = df["overall_score"].clip(lower=0.0, upper=100.0)
    df["tier"] = df["overall_score"].apply(_assign_tier)

    df = df.sort_values(["dealer_id", "period_start_date", "period_end_date"])
    df["score_change_vs_previous_period"] = df.groupby("dealer_id")["overall_score"].diff().fillna(0.0)

    return df


# -----------------------------
# Raw tables scoring path
# -----------------------------
def _compute_scores_from_raw_tables(
    country: str,
    start_date: str,
    end_date: str,
    resolution: str = "monthly",
) -> pd.DataFrame:
    """
    Aggregates raw tables into period metrics.
    inventory_update_count = count(listings.date_posted in the period)
    Supports country='ALL'
    """
    if resolution not in _ALLOWED_RESOLUTIONS:
        raise ValueError(f"resolution must be one of: {sorted(_ALLOWED_RESOLUTIONS)}")

    step = _resolution_to_step(resolution)
    engine = DatabaseConfig.get_postgres_engine()

    sql = """
    WITH periods AS (
      SELECT
        gs::date AS period_start_date,
        LEAST((gs + (%(step)s)::interval - INTERVAL '1 day')::date, (%(end_date)s)::date) AS period_end_date
      FROM generate_series(
        (%(start_date)s)::timestamp,
        (%(end_date)s)::timestamp,
        (%(step)s)::interval
      ) AS gs
    ),
    dealer_base AS (
      SELECT dealer_id, country
      FROM public.dealers
      WHERE (%(country)s = 'ALL' OR country = %(country)s)
    ),
    leads_agg AS (
      SELECT
        d.dealer_id,
        p.period_start_date,
        p.period_end_date,
        COUNT(l.*)::int AS leads_count
      FROM dealer_base d
      CROSS JOIN periods p
      LEFT JOIN public.leads l
        ON l.dealer_id = d.dealer_id
       AND l.lead_date BETWEEN p.period_start_date AND p.period_end_date
      GROUP BY 1,2,3
    ),
    apps_agg AS (
      SELECT
        d.dealer_id,
        p.period_start_date,
        p.period_end_date,
        COUNT(a.*)::int AS applications_count
      FROM dealer_base d
      CROSS JOIN periods p
      LEFT JOIN public.applications a
        ON a.dealer_id = d.dealer_id
       AND a.lead_date BETWEEN p.period_start_date AND p.period_end_date
      GROUP BY 1,2,3
    ),
    sales_agg AS (
      SELECT
        d.dealer_id,
        p.period_start_date,
        p.period_end_date,
        COUNT(s.*)::int AS sales_units
      FROM dealer_base d
      CROSS JOIN periods p
      LEFT JOIN public.sales s
        ON s.dealer_id = d.dealer_id
       AND s.fulfillment_date BETWEEN p.period_start_date AND p.period_end_date
      GROUP BY 1,2,3
    ),
    listings_agg AS (
      SELECT
        d.dealer_id,
        p.period_start_date,
        p.period_end_date,
        COUNT(li.*)::int AS inventory_update_count
      FROM dealer_base d
      CROSS JOIN periods p
      LEFT JOIN public.listings li
        ON li.dealer_id = d.dealer_id
       AND li.date_posted BETWEEN p.period_start_date AND p.period_end_date
      GROUP BY 1,2,3
    )
    SELECT
      d.dealer_id,
      d.country,
      p.period_start_date,
      p.period_end_date,
      COALESCE(le.leads_count, 0) AS leads_count,
      COALESCE(ap.applications_count, 0) AS applications_count,
      COALESCE(sa.sales_units, 0) AS sales_units,
      COALESCE(li.inventory_update_count, 0) AS inventory_update_count
    FROM dealer_base d
    CROSS JOIN periods p
    LEFT JOIN leads_agg le
      ON le.dealer_id = d.dealer_id AND le.period_start_date = p.period_start_date AND le.period_end_date = p.period_end_date
    LEFT JOIN apps_agg ap
      ON ap.dealer_id = d.dealer_id AND ap.period_start_date = p.period_start_date AND ap.period_end_date = p.period_end_date
    LEFT JOIN sales_agg sa
      ON sa.dealer_id = d.dealer_id AND sa.period_start_date = p.period_start_date AND sa.period_end_date = p.period_end_date
    LEFT JOIN listings_agg li
      ON li.dealer_id = d.dealer_id AND li.period_start_date = p.period_start_date AND li.period_end_date = p.period_end_date
    ORDER BY d.dealer_id, p.period_start_date, p.period_end_date;
    """

    df = pd.read_sql(
        sql,
        engine,
        params={"country": country, "start_date": start_date, "end_date": end_date, "step": step},
    )

    if df.empty:
        return df

    # sales_growth: log growth reduces tiny-denominator explosions
    df = df.sort_values(["dealer_id", "period_start_date"])
    prev_sales = df.groupby("dealer_id")["sales_units"].shift(1).fillna(0)
    df["sales_growth"] = np.log((df["sales_units"] + 1) / (prev_sales + 1)) * 100.0

    group_cols = ["country", "period_start_date", "period_end_date"]

    def norm(col: str) -> pd.Series:
        mx = df.groupby(group_cols)[col].transform("max")
        return np.where(mx > 0, (df[col] / mx) * 100.0, 0.0)

    df["sales_score"] = norm("sales_growth")
    df["inventory_score"] = norm("inventory_update_count")
    df["applications_score"] = norm("applications_count")
    df["leads_score"] = norm("leads_count")

    df["overall_score"] = (
        df["sales_score"] * settings.SALES_GROWTH_WEIGHT
        + df["inventory_score"] * settings.INVENTORY_FREQ_WEIGHT
        + df["applications_score"] * settings.APPLICATIONS_WEIGHT
        + df["leads_score"] * settings.LEADS_WEIGHT
    )

    df["overall_score"] = df["overall_score"].clip(lower=0.0, upper=100.0)
    df["tier"] = df["overall_score"].apply(_assign_tier)
    df["score_change_vs_previous_period"] = df.groupby("dealer_id")["overall_score"].diff().fillna(0.0)

    return df


def _upsert_dealer_scores(df: pd.DataFrame) -> int:
    """
    UPSERT into public.dealer_scores
    Requires UNIQUE(dealer_id, period_start_date, period_end_date)
    """
    if df.empty:
        return 0

    col_map = _get_dealer_scores_column_map()
    score_col = col_map["score_col"]
    tier_col = col_map["tier_col"]
    delta_col = col_map["delta_col"]
    created_at_col = col_map["created_at_col"]

    engine = DatabaseConfig.get_postgres_engine()

    base_cols = ["dealer_id", "period_start_date", "period_end_date"]
    insert_cols = base_cols + [score_col, tier_col]
    if delta_col:
        insert_cols.append(delta_col)

    rows: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        item: Dict[str, Any] = {
            "dealer_id": r["dealer_id"],
            "period_start_date": r["period_start_date"],
            "period_end_date": r["period_end_date"],
            score_col: float(r["overall_score"]),
            tier_col: str(r["tier"]),
        }
        if delta_col:
            item[delta_col] = float(r["score_change_vs_previous_period"])
        rows.append(item)

    cols_sql = ", ".join(insert_cols)
    vals_sql = ", ".join([f":{c}" for c in insert_cols])

    update_sets = [
        f"{score_col} = EXCLUDED.{score_col}",
        f"{tier_col} = EXCLUDED.{tier_col}",
    ]
    if delta_col:
        update_sets.append(f"{delta_col} = EXCLUDED.{delta_col}")
    if created_at_col:
        update_sets.append(f"{created_at_col} = NOW()")

    upsert_sql = f"""
    INSERT INTO public.dealer_scores ({cols_sql})
    VALUES ({vals_sql})
    ON CONFLICT (dealer_id, period_start_date, period_end_date)
    DO UPDATE SET {", ".join(update_sets)}
    """

    with engine.begin() as conn:
        conn.execute(text(upsert_sql), rows)

    return len(rows)


# -----------------------------
# Public functions
# -----------------------------
def score_dealers(
    country: Optional[str] = None,
    period_start_date: Optional[str] = None,
    period_end_date: Optional[str] = None,
    top_n: int = 10,
    store: bool = True,
) -> Dict[str, Any]:
    """
    Aggregated path: dealer_activity_metrics
    """
    df = _compute_scores_from_metrics(country=country, period_start_date=period_start_date, period_end_date=period_end_date)

    if df.empty:
        return {
            "status": "no_data",
            "summary": "No dealer activity found for the given filters.",
            "filters_used": {"country": country, "period_start_date": period_start_date, "period_end_date": period_end_date},
            "stored_rows": 0,
            "top_dealers_latest_period": [],
        }

    stored_rows = _upsert_dealer_scores(df) if store else 0

    latest_start = df["period_start_date"].max()
    latest_end = df.loc[df["period_start_date"] == latest_start, "period_end_date"].max()

    latest_df = df[(df["period_start_date"] == latest_start) & (df["period_end_date"] == latest_end)].copy()
    latest_df = latest_df.sort_values("overall_score", ascending=False).head(int(top_n))

    return {
        "status": "ok",
        "summary": f"Computed {len(df)} dealer period-scores. Stored {stored_rows} rows into dealer_scores."
        if store else f"Computed {len(df)} dealer period-scores (store=False).",
        "filters_used": {"country": country, "period_start_date": period_start_date, "period_end_date": period_end_date},
        "stored_rows": stored_rows,
        "latest_period": {"period_start_date": str(latest_start), "period_end_date": str(latest_end)},
        "top_dealers_latest_period": latest_df[
            ["dealer_id", "dealership_name", "country", "period_start_date", "period_end_date", "overall_score", "tier", "score_change_vs_previous_period"]
        ].to_dict(orient="records"),
    }


def score_dealers_and_store(
    country: Optional[str] = None,
    period_start_date: Optional[str] = None,
    period_end_date: Optional[str] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    return score_dealers(country=country, period_start_date=period_start_date, period_end_date=period_end_date, top_n=top_n, store=True)


def score_dealers_by_date_range_and_store(
    country: str,
    start_date: str,
    end_date: str,
    resolution: str = "monthly",
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Robust path: raw tables. Supports country='ALL'.
    """
    df = _compute_scores_from_raw_tables(country=country, start_date=start_date, end_date=end_date, resolution=resolution)

    if df.empty:
        return {"status": "no_data", "country": country, "start_date": start_date, "end_date": end_date, "resolution": resolution}

    stored_rows = _upsert_dealer_scores(df)

    latest_start = df["period_start_date"].max()
    latest_end = df.loc[df["period_start_date"] == latest_start, "period_end_date"].max()

    latest_df = df[(df["period_start_date"] == latest_start) & (df["period_end_date"] == latest_end)].copy()
    latest_df = latest_df.sort_values("overall_score", ascending=False).head(int(top_n))

    return {
        "status": "ok",
        "country": country,
        "start_date": start_date,
        "end_date": end_date,
        "resolution": resolution,
        "stored_rows": stored_rows,
        "latest_period": {"period_start_date": str(latest_start), "period_end_date": str(latest_end)},
        "top_dealers_latest_period": latest_df[
            ["dealer_id", "country", "period_start_date", "period_end_date", "overall_score", "tier", "score_change_vs_previous_period"]
        ].to_dict(orient="records"),
    }


# ADK wrapper expected by agent.py
def score_dealers_tool(
    country: Optional[str] = None,
    period_start_date: Optional[str] = None,
    period_end_date: Optional[str] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    return score_dealers(country=country, period_start_date=period_start_date, period_end_date=period_end_date, top_n=top_n, store=True)
