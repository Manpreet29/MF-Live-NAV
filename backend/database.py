"""
database.py — PostgreSQL (Supabase) connection management and schema.

Key differences from the old SQLite version:
  - Placeholder: SQLite uses ?  →  PostgreSQL uses %s
  - AUTOINCREMENT  →  SERIAL
  - datetime('now','localtime')  →  NOW()
  - executescript()  →  separate execute() calls in a transaction
  - Row access: psycopg2 RealDictCursor returns dict-like rows
    so code that does row["column"] works unchanged.
"""

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras

from config import settings

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# DDL                                                                  #
# ------------------------------------------------------------------ #

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS funds (
        id             SERIAL PRIMARY KEY,
        name           TEXT    NOT NULL,
        official_nav   REAL    NOT NULL,
        nav_date       TEXT    NOT NULL,
        portfolio_date TEXT    NOT NULL DEFAULT '',
        total_holdings INTEGER NOT NULL DEFAULT 0,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS holdings (
        id                 SERIAL PRIMARY KEY,
        fund_id            INTEGER NOT NULL REFERENCES funds(id) ON DELETE CASCADE,
        name               TEXT    NOT NULL,
        isin               TEXT    NOT NULL,
        industry           TEXT    NOT NULL DEFAULT '',
        quantity           BIGINT  NOT NULL,
        market_value_lacs  REAL    NOT NULL,
        disclosed_price    REAL    NOT NULL,
        pct_to_nav         REAL    NOT NULL,
        trading_symbol     TEXT    NOT NULL DEFAULT ''
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_holdings_fund_id ON holdings(fund_id)",
    "CREATE INDEX IF NOT EXISTS idx_holdings_isin    ON holdings(isin)",
    """
    CREATE TABLE IF NOT EXISTS instrument_master (
        id             SERIAL PRIMARY KEY,
        isin           TEXT NOT NULL,
        instrument_key TEXT NOT NULL,
        trading_symbol TEXT,
        exchange       TEXT,
        segment        TEXT,
        name           TEXT,
        loaded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_im_isin ON instrument_master(isin)",
]


# ------------------------------------------------------------------ #
# Connection factory                                                   #
# ------------------------------------------------------------------ #

def get_connection() -> psycopg2.extensions.connection:
    """
    Open a new PostgreSQL connection.
    RealDictCursor makes rows behave like dicts (row["column"]).
    """
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add it to your .env file or Render environment variables."
        )
    conn = psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=10,
    )
    return conn


@contextmanager
def get_db() -> Generator:
    """Context manager that yields a connection and guarantees close."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def db_dependency() -> Generator:
    """FastAPI dependency — yields connection, closes after request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# Schema init                                                          #
# ------------------------------------------------------------------ #

def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    logger.info("Initialising PostgreSQL schema...")
    with get_db() as conn:
        with conn.cursor() as cur:
            for stmt in _TABLES:
                cur.execute(stmt)
        conn.commit()
    logger.info("Database schema ready.")


def instrument_master_count() -> int:
    """Return number of rows in instrument_master (0 = not loaded)."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM instrument_master")
                row = cur.fetchone()
                return row["c"] if row else 0
    except Exception:
        return 0
