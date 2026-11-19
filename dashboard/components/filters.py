"""
Sidebar filters and shared data caching for the Streamlit dashboard.
"""

from typing import Any
import pandas as pd
import streamlit as st
from src.utils.io import get_duckdb_connection


@st.cache_data(ttl=3600)
def load_filter_options() -> dict[str, list[Any]]:
    """Load distinct filter values from DuckDB."""
    con = get_duckdb_connection(read_only=True)
    years = [int(r[0]) for r in con.execute("SELECT DISTINCT policy_year FROM dim_policy ORDER BY policy_year").fetchall()]
    plan_types = [r[0] for r in con.execute("SELECT DISTINCT plan_type FROM dim_policy ORDER BY plan_type").fetchall()]
    regions = [r[0] for r in con.execute("SELECT DISTINCT region FROM dim_member ORDER BY region").fetchall()]
    channels = [r[0] for r in con.execute("SELECT DISTINCT sales_channel FROM dim_policy ORDER BY sales_channel").fetchall()]
    con.close()
    return {
        "years": ["All"] + years,
        "plan_types": ["All"] + plan_types,
        "regions": ["All"] + regions,
        "channels": ["All"] + channels,
    }


def render_sidebar_filters() -> dict[str, Any]:
    """Render sidebar filters and return selected values."""
    st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.sidebar.title("MediSure Analytics")
    st.sidebar.caption("Portfolio Underwriting & Operations Intelligence")

    options = load_filter_options()

    selected_year = st.sidebar.selectbox("Policy Year Cohort", options["years"], index=0)
    selected_plan_type = st.sidebar.selectbox("Plan Type", options["plan_types"], index=0)
    selected_region = st.sidebar.selectbox("Geographic Region", options["regions"], index=0)
    selected_channel = st.sidebar.selectbox("Sales Channel", options["channels"], index=0)

    st.sidebar.markdown("---")
    st.sidebar.caption("MediSure Health Insurance Platform v1.0")

    return {
        "year": selected_year,
        "plan_type": selected_plan_type,
        "region": selected_region,
        "channel": selected_channel,
    }


def get_filter_where_clause(filters: dict[str, Any], table_alias_policy: str = "p", table_alias_member: str = "m") -> str:
    """Build dynamic SQL WHERE clause based on sidebar filters."""
    clauses = ["1=1"]
    if filters["year"] != "All":
        clauses.append(f"{table_alias_policy}.policy_year = {filters['year']}")
    if filters["plan_type"] != "All":
        clauses.append(f"{table_alias_policy}.plan_type = '{filters['plan_type']}'")
    if filters["region"] != "All":
        clauses.append(f"{table_alias_member}.region = '{filters['region']}'")
    if filters["channel"] != "All":
        clauses.append(f"{table_alias_policy}.sales_channel = '{filters['channel']}'")
    return " AND ".join(clauses)

