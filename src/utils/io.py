"""
I/O helpers for Parquet, CSV, and DuckDB interactions.
Leverages DuckDB's built-in Parquet engine for high performance and compatibility.
"""

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.utils.config import get_path


def get_duckdb_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Return a connection to the local warehouse DuckDB instance."""
    db_path = get_path("duckdb_file")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(database=str(db_path), read_only=read_only)


def save_parquet(df: pd.DataFrame, path: Path | str, **kwargs: Any) -> Path:
    """Save DataFrame as parquet file using DuckDB native parquet engine."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    abs_path_str = str(p.resolve()).replace("\\", "/")
    con = duckdb.connect()
    con.register("df_to_save", df)
    con.execute(f"COPY df_to_save TO '{abs_path_str}' (FORMAT PARQUET)")
    con.close()
    return p


def read_parquet(path: Path | str, **kwargs: Any) -> pd.DataFrame:
    """Read parquet file into DataFrame using DuckDB native parquet engine."""
    p = Path(path)
    abs_path_str = str(p.resolve()).replace("\\", "/")
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM '{abs_path_str}'").df()
    con.close()
    return df


def save_csv(df: pd.DataFrame, path: Path | str, **kwargs: Any) -> Path:
    """Save DataFrame as CSV ensuring parent directory exists."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, **kwargs)
    return p


def read_csv(path: Path | str, **kwargs: Any) -> pd.DataFrame:
    """Read CSV file into DataFrame."""
    return pd.read_csv(Path(path), **kwargs)
