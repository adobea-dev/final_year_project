# agents/data_agent.py
#data_agent.py is just a Python helpers that the agent.py imports and uses
# agents/data_agent.py
# agents/dealer_copilot/data_agent.py
from __future__ import annotations

import io
import re
from typing import Any, Dict, Optional, Set, Literal, List

import pandas as pd
from sqlalchemy.engine import Engine

from config.database import DatabaseConfig


class DataAgent:
    """
    Runs read-only analytics queries against the Postgres dealer_ai database.

    Safety features:
    - Read-only enforcement (blocks writes and unsafe patterns).
    - Allowlist of tables (only approved tables can be queried).
    - Hard LIMIT enforcement (clamped).
    """

    # Allowlisted tables (from your screenshot)
    ALLOWED_TABLES: Set[str] = {
        "account_managers",
        "applications",
        "dealer_activity_metrics",
        "dealer_scores",
        "dealers",
        "leads",
        "listings",
        "sales",
    }

    # Keywords that should never appear in a read-only query
    FORBIDDEN_KEYWORDS: Set[str] = {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "truncate",
        "grant",
        "revoke",
        "copy",
        "call",
        "execute",
        "do",
    }

    # Patterns that are risky even if query looks like SELECT
    FORBIDDEN_PATTERNS = [
        re.compile(r"\bselect\b\s+\binto\b", re.IGNORECASE),  # SELECT INTO creates a table
        re.compile(r"\bfor\b\s+\bupdate\b", re.IGNORECASE),  # row locks
        re.compile(r"\bfor\b\s+\bshare\b", re.IGNORECASE),   # row locks
        re.compile(r";\s*\S", re.IGNORECASE),                # multi-statement
        re.compile(r"--", re.IGNORECASE),                    # comments
        re.compile(r"/\*", re.IGNORECASE),                   # comments
    ]

    def __init__(self) -> None:
        self.engine: Engine = DatabaseConfig.get_postgres_engine()

    @staticmethod
    def _strip_trailing_semicolons(sql: str) -> str:
        s = sql.strip()
        while s.endswith(";"):
            s = s[:-1].rstrip()
        return s

    @staticmethod
    def _strip_string_literals(sql: str) -> str:
        """
        Replace single-quoted strings so scanning for keywords/patterns
        is not confused by harmless text inside strings.
        """
        return re.sub(r"'(?:''|[^'])*'", "''", sql)

    @staticmethod
    def _extract_cte_names(sql: str) -> Set[str]:
        """
        If query starts with WITH, collect CTE names so we do not mistake them as real tables.
        Example: WITH t AS (...) SELECT * FROM t;
        """
        s = sql.strip()
        if not s.lower().startswith("with"):
            return set()

        lower = s.lower()
        m = re.search(r"\bselect\b", lower)
        cutoff = m.start() if m else len(s)
        prefix = s[:cutoff]

        names: Set[str] = set()
        for name in re.findall(r"\b([a-zA-Z_]\w*)\s+as\s*\(", prefix, flags=re.IGNORECASE):
            names.add(name.lower())
        return names

    @staticmethod
    def _extract_table_names(sql: str) -> Set[str]:
        """
        Extract table names used after FROM or JOIN.
        Handles schema.table by taking the last part.
        Skips subqueries like FROM (SELECT ...).
        """
        s = DataAgent._strip_string_literals(sql)
        found: Set[str] = set()

        for m in re.finditer(r"\b(from|join)\b\s+([a-zA-Z0-9_\.\"']+)", s, flags=re.IGNORECASE):
            tok = m.group(2).strip().rstrip(",")

            if tok.startswith("("):  # subquery
                continue

            tok = tok.replace('"', "").replace("'", "")
            if "." in tok:
                tok = tok.split(".")[-1]

            found.add(tok.lower())

        return found

    def _validate_readonly_sql(self, sql: str) -> str:
        sql_clean = self._strip_trailing_semicolons(sql)
        sql_lower = sql_clean.lower().strip()

        # Allow SELECT and WITH (CTE)
        if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
            raise ValueError("Only SELECT or WITH queries are allowed.")

        # Strip strings before scanning for patterns and keywords (reduces false positives)
        sql_no_strings = self._strip_string_literals(sql_clean)
        sql_no_strings_lower = sql_no_strings.lower()

        # Block dangerous patterns
        for pat in self.FORBIDDEN_PATTERNS:
            if pat.search(sql_no_strings):
                raise ValueError("Query rejected: unsafe pattern detected.")

        # Block forbidden keywords anywhere
        for kw in self.FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", sql_no_strings_lower):
                raise ValueError(f"Query rejected: forbidden keyword '{kw}' detected.")

        # Enforce allowlist of tables
        ctes = self._extract_cte_names(sql_clean)
        tables = self._extract_table_names(sql_clean)
        tables = {t for t in tables if t not in ctes}

        # Queries like SELECT 1 have no tables
        unknown = tables - {t.lower() for t in self.ALLOWED_TABLES}
        if unknown:
            raise ValueError(
                f"Query rejected: table(s) not allowed: {sorted(unknown)}. "
                f"Allowed tables: {sorted(self.ALLOWED_TABLES)}"
            )

        return sql_clean

    def run_sql(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = 500,
    ) -> pd.DataFrame:
        """
        Execute a read-only SQL query on Postgres and return a pandas DataFrame.
        LIMIT is always enforced (clamped 1..5000). If limit=None, defaults to 500.
        """
        sql_safe = self._validate_readonly_sql(sql)

        lim = 500 if limit is None else int(limit)
        lim = max(1, min(lim, 5000))

        wrapped_sql = f"SELECT * FROM ({sql_safe}) AS subq LIMIT {lim}"

        with self.engine.connect() as conn:
            df = pd.read_sql(wrapped_sql, conn, params=params)

        return df

    def run_sql_as_dicts(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = 500,
    ) -> Dict[str, Any]:
        """
        Helper for tools: run a query and return JSON-serialisable output.
        """
        df = self.run_sql(sql=sql, params=params, limit=limit)
        return {
            "row_count": int(len(df)),
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
        }


# -------------------------------------------------------------------
# ADK tool functions (agent.py imports these)
# -------------------------------------------------------------------

def ask_db(sql: str, limit: int = 500) -> Dict[str, Any]:
    """
    Tool: execute a read-only SQL query on Postgres and return JSON results.
    The model generates the SQL, this tool validates and runs it safely.
    """
    agent = DataAgent()
    return agent.run_sql_as_dicts(sql=sql, limit=limit)


def plot_db(
    sql: str,
    x: str,
    y: str,
    chart_type: str = "bar",
    title: Optional[str] = None,
    limit: int = 500,
    tool_context=None,
) -> Dict[str, Any]:
    """
    Tool: run a query and produce a matplotlib chart saved as an ADK artifact.

    Args:
      sql: SELECT/WITH query (validated and executed safely)
      x: column name for x-axis
      y: column name for y-axis
      chart_type: bar | line | scatter
      title: optional title
      tool_context: provided by ADK for saving artifacts
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import google.genai.types as types

    agent = DataAgent()
    df = agent.run_sql(sql=sql, limit=limit)

    if x not in df.columns or y not in df.columns:
        return {"status": "error", "message": f"Columns not found. Available: {list(df.columns)}"}

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    ct = chart_type.lower().strip()
    if ct == "bar":
        ax.bar(df[x], df[y])
    elif ct == "line":
        ax.plot(df[x], df[y])
    elif ct == "scatter":
        ax.scatter(df[x], df[y])
    else:
        return {"status": "error", "message": "chart_type must be bar, line, or scatter"}

    ax.set_xlabel(x)
    ax.set_ylabel(y)
    if title:
        ax.set_title(title)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)

    filename = "dealer_copilot_chart.png"
    if tool_context is not None:
        part = types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")
        tool_context.save_artifact(filename, part)
        return {"status": "ok", "artifact_filename": filename, "row_count": int(len(df))}

    return {
        "status": "ok",
        "message": "Chart created but tool_context was not provided, so it was not saved as an artifact.",
        "row_count": int(len(df)),
    }


# -------------------------------------------------------------------
# Structured tools (reduces need for the model to write SQL)
# -------------------------------------------------------------------

Metric = Literal[
    "leads_count",
    "applications_count",
    "sales_units",
    "inventory_update_count",
    "sales_growth",
]

_ALLOWED_METRICS: Set[str] = {
    "leads_count",
    "applications_count",
    "sales_units",
    "inventory_update_count",
    "sales_growth",
}


def count_dealers(country: Optional[str] = None) -> Dict[str, Any]:
    """
    Tool: count dealers (optionally filter by country) without requiring model-written SQL.
    """
    agent = DataAgent()
    sql = "SELECT COUNT(*) AS total_dealers FROM dealers"
    params: Dict[str, Any] = {}
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
    """
    Tool: get top dealers by a selected metric from dealer_activity_metrics.
    Model only supplies metric name + optional filters; tool writes safe SQL.
    """
    if metric not in _ALLOWED_METRICS:
        raise ValueError(f"metric must be one of: {sorted(_ALLOWED_METRICS)}")

    agent = DataAgent()
    params: Dict[str, Any] = {}
    where: List[str] = []

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
