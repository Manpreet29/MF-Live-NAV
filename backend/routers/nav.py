"""
routers/nav.py — NAV calculation endpoints (PostgreSQL version)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from database import db_dependency, instrument_master_count
from services.price_fetcher import fetch_prices
from services.nav_calculator import calculate_nav
from models.nav import NAVResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["NAV"])


@router.get("/nav/{fund_id}", response_model=NAVResult)
async def get_nav(fund_id: int, db=Depends(db_dependency)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM funds WHERE id=%s", (fund_id,))
        fund = cur.fetchone()
    if not fund:
        raise HTTPException(404, f"Fund {fund_id} not found.")

    with db.cursor() as cur:
        cur.execute("SELECT * FROM holdings WHERE fund_id=%s", (fund_id,))
        holdings = cur.fetchall()
    if not holdings:
        raise HTTPException(400, f"Fund {fund_id} has no holdings.")

    holdings_list = [dict(h) for h in holdings]
    symbols       = [h["trading_symbol"] for h in holdings_list if h["trading_symbol"]]
    prices        = await fetch_prices(symbols)

    return calculate_nav(
        fund_id=fund_id,
        fund_name=fund["name"],
        official_nav=fund["official_nav"],
        nav_date=str(fund["nav_date"]),
        portfolio_date=fund["portfolio_date"],
        holdings_db=holdings_list,
        prices=prices,
    )


@router.get("/nav/all/batch")
async def get_all_nav(db=Depends(db_dependency)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM funds ORDER BY id")
        funds = cur.fetchall()
    if not funds:
        return []

    all_symbols: set[str] = set()
    fund_holdings: dict[int, list[dict]] = {}

    for fund in funds:
        with db.cursor() as cur:
            cur.execute("SELECT * FROM holdings WHERE fund_id=%s", (fund["id"],))
            rows = [dict(h) for h in cur.fetchall()]
        fund_holdings[fund["id"]] = rows
        for h in rows:
            if h["trading_symbol"]:
                all_symbols.add(h["trading_symbol"])

    prices = await fetch_prices(list(all_symbols))

    results = []
    for fund in funds:
        fid = fund["id"]
        holdings_list = fund_holdings.get(fid, [])
        if not holdings_list:
            continue
        results.append(calculate_nav(
            fund_id=fid,
            fund_name=fund["name"],
            official_nav=fund["official_nav"],
            nav_date=str(fund["nav_date"]),
            portfolio_date=fund["portfolio_date"],
            holdings_db=holdings_list,
            prices=prices,
        ))
    return results


@router.get("/health")
def health():
    """
    Health check — tests DB connection and returns status.
    Returns 200 even if DB is down, so the error is visible in the response body.
    """
    from config import settings

    # Check DB
    db_status  = "ok"
    db_error   = None
    im_count   = 0
    fund_count = 0

    if not settings.database_url:
        db_status = "error"
        db_error  = "DATABASE_URL environment variable is not set."
    else:
        try:
            from database import get_db
            with get_db() as db:
                with db.cursor() as cur:
                    cur.execute("SELECT COUNT(*) AS c FROM instrument_master")
                    im_count = cur.fetchone()["c"]
                    cur.execute("SELECT COUNT(*) AS c FROM funds")
                    fund_count = cur.fetchone()["c"]
        except Exception as e:
            db_status = "error"
            db_error  = str(e)

    return {
        "status":                   "ok" if db_status == "ok" else "degraded",
        "database":                 db_status,
        "database_error":           db_error,
        "instrument_master_loaded": im_count > 0,
        "instrument_master_count":  im_count,
        "tracked_funds":            fund_count,
        "database_url_set":         bool(settings.database_url),
    }