"""
NAV calculation endpoints (PostgreSQL version)

GET /api/nav/{fund_id}    Calculate live NAV for one fund
GET /api/nav/all/batch    Calculate live NAV for all funds
GET /api/health           Server + instrument master status
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
        raise HTTPException(400, f"Fund {fund_id} has no holdings. Upload a statement first.")

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
def health(db=Depends(db_dependency)):
    count = instrument_master_count()
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM funds")
        fund_count = cur.fetchone()["c"]
    return {
        "status":                   "ok",
        "instrument_master_loaded": count > 0,
        "instrument_master_count":  count,
        "tracked_funds":            fund_count,
    }
