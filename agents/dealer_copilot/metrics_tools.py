#The model only chooses a metric name and filters, it does not need to write SQL.
from __future__ import annotations
from typing import Any, Dict, Optional, Literal

from .data_agent import DataAgent

Metric = Literal[
    "leads_count",
    "applications_count",
    "sales_units",
    "inventory_update_count",
    "sales_growth",
]

ALLOWED_METRICS = {
    "leads_count",
    "applications_count",
    "sales_units",
    "inventory_update_count",
    "sales_growth",
}

def count_dealers(country: Optional[str] = None) -> Dict[str, Any]:
    agent = DataAgent()
    sql = "SELECT COUNT(*) AS total_dealers FROM dealers"
    params = {}
    if country:
        sql += " WHERE country = %(country)s"
        params["country"] = country
    return agent.run_sql_as_dicts(sql=sql, params=params, limit=10)

def top_dealers_by_metric(
    metric: Metric,
    country: Optional[str] = None,
    top_n: int = 5,
    period_start_date: Optional[str] = None,
    period_end_date: Optional[str] = None,
) -> Dict[str, Any]:
    if metric not in ALLOWED_METRICS:
        raise ValueError(f"metric must be one of: {sorted(ALLOWED_METRICS)}")

    agent = DataAgent()
    params: Dict[str, Any] = {}
    where = []

    if country:
        where.append("d.country = %(country)s")
        params["country"] = country
    if period_start_date:
        where.append("m.period_start_date >= %(period_start_date)s")
        params["period_start_date"] = period_start_date
    if period_end_date:
        where.append("m.period_end_date <= %(period_end_date)s")
        params["period_end_date"] = period_end_date

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
    SELECT
        m.dealer_id,
        d.dealership_name,
        d.country,
        SUM(COALESCE(m.{metric}, 0)) AS metric_value
    FROM dealer_activity_metrics m
    JOIN dealers d ON d.dealer_id = m.dealer_id
    {where_sql}
    GROUP BY m.dealer_id, d.dealership_name, d.country
    ORDER BY metric_value DESC
    LIMIT {int(top_n)}
    """
    return agent.run_sql_as_dicts(sql=sql, params=params, limit=5000)
