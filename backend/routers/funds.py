"""
Fund CRUD endpoints (PostgreSQL version)

POST   /api/funds                  Create fund + upload holdings
GET    /api/funds                  List all tracked funds
GET    /api/funds/{id}             Get one fund with its holdings
DELETE /api/funds/{id}             Remove fund and all its holdings
PATCH  /api/funds/{id}             Update fund name / nav / date
POST   /api/funds/{id}/holdings    Re-upload holdings for existing fund
"""
import logging
import psycopg2.extensions
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from models.fund import FundCreate, FundUpdate, FundSummary
from services.holdings_parser import parse_holdings, HoldingsParseError
from services.isin_mapper import resolve_symbols, ISINMapperError
from database import db_dependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/funds", tags=["Funds"])

MAX_FILE = 10 * 1024 * 1024  # 10 MB


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _fund_or_404(db, fund_id: int):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM funds WHERE id = %s", (fund_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, f"Fund {fund_id} not found.")
    return row


def _save_holdings(db, fund_id: int, holdings, symbol_map: dict):
    with db.cursor() as cur:
        cur.execute("DELETE FROM holdings WHERE fund_id = %s", (fund_id,))
        rows = [
            (fund_id, h.name, h.isin, h.industry, h.quantity,
             h.market_value_lacs, h.disclosed_price, h.pct_to_nav,
             symbol_map.get(h.isin, ""))
            for h in holdings
        ]
        cur.executemany(
            """INSERT INTO holdings
               (fund_id, name, isin, industry, quantity,
                market_value_lacs, disclosed_price, pct_to_nav, trading_symbol)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            rows,
        )
        cur.execute(
            "UPDATE funds SET total_holdings=%s, updated_at=NOW() WHERE id=%s",
            (len(rows), fund_id),
        )


def _validate_file(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, "No file provided.")
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, f"Only .xlsx files accepted.")


# ------------------------------------------------------------------ #
# POST /api/funds                                                      #
# ------------------------------------------------------------------ #

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_fund(
    file:         UploadFile = File(...),
    name:         str        = Form(...),
    official_nav: float      = Form(..., gt=0),
    nav_date:     str        = Form(...),
    db = Depends(db_dependency),
):
    req = FundCreate(name=name, official_nav=official_nav, nav_date=nav_date)
    _validate_file(file)
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE:
        raise HTTPException(400, "File too large (max 10 MB).")

    try:
        holdings, portfolio_date = parse_holdings(file_bytes)
    except HoldingsParseError as e:
        raise HTTPException(400, str(e))

    try:
        symbol_map = resolve_symbols([h.isin for h in holdings])
    except ISINMapperError as e:
        raise HTTPException(503, str(e))

    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO funds (name, official_nav, nav_date, portfolio_date, total_holdings)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (req.name, req.official_nav, req.nav_date, portfolio_date, len(holdings)),
        )
        fund_id = cur.fetchone()["id"]

    _save_holdings(db, fund_id, holdings, symbol_map)
    db.commit()

    logger.info("Created fund id=%d '%s' with %d holdings", fund_id, req.name, len(holdings))
    return {"id": fund_id, "name": req.name, "total_holdings": len(holdings)}


# ------------------------------------------------------------------ #
# GET /api/funds                                                       #
# ------------------------------------------------------------------ #

@router.get("", response_model=list[FundSummary])
def list_funds(db = Depends(db_dependency)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM funds ORDER BY created_at DESC")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------ #
# GET /api/funds/{id}                                                  #
# ------------------------------------------------------------------ #

@router.get("/{fund_id}")
def get_fund(fund_id: int, db = Depends(db_dependency)):
    fund = _fund_or_404(db, fund_id)
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM holdings WHERE fund_id=%s ORDER BY pct_to_nav DESC",
            (fund_id,),
        )
        holdings = cur.fetchall()
    return {**dict(fund), "holdings": [dict(h) for h in holdings]}


# ------------------------------------------------------------------ #
# DELETE /api/funds/{id}                                               #
# ------------------------------------------------------------------ #

@router.delete("/{fund_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fund(fund_id: int, db = Depends(db_dependency)):
    _fund_or_404(db, fund_id)
    with db.cursor() as cur:
        cur.execute("DELETE FROM funds WHERE id=%s", (fund_id,))
    db.commit()
    logger.info("Deleted fund id=%d", fund_id)


# ------------------------------------------------------------------ #
# PATCH /api/funds/{id}                                                #
# ------------------------------------------------------------------ #

@router.patch("/{fund_id}", response_model=FundSummary)
def update_fund(fund_id: int, body: FundUpdate, db = Depends(db_dependency)):
    _fund_or_404(db, fund_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update.")

    set_clause = ", ".join(f"{k}=%s" for k in updates)
    set_clause += ", updated_at=NOW()"
    with db.cursor() as cur:
        cur.execute(
            f"UPDATE funds SET {set_clause} WHERE id=%s",
            [*updates.values(), fund_id],
        )
    db.commit()
    return dict(_fund_or_404(db, fund_id))


# ------------------------------------------------------------------ #
# POST /api/funds/{id}/holdings                                        #
# ------------------------------------------------------------------ #

@router.post("/{fund_id}/holdings")
async def reupload_holdings(
    fund_id: int,
    file: UploadFile = File(...),
    db = Depends(db_dependency),
):
    _fund_or_404(db, fund_id)
    _validate_file(file)
    file_bytes = await file.read()

    try:
        holdings, portfolio_date = parse_holdings(file_bytes)
    except HoldingsParseError as e:
        raise HTTPException(400, str(e))

    try:
        symbol_map = resolve_symbols([h.isin for h in holdings])
    except ISINMapperError as e:
        raise HTTPException(503, str(e))

    _save_holdings(db, fund_id, holdings, symbol_map)
    with db.cursor() as cur:
        cur.execute(
            "UPDATE funds SET portfolio_date=%s, updated_at=NOW() WHERE id=%s",
            (portfolio_date, fund_id),
        )
    db.commit()
    logger.info("Re-uploaded holdings for fund id=%d: %d rows", fund_id, len(holdings))
    return {"fund_id": fund_id, "total_holdings": len(holdings), "portfolio_date": portfolio_date}
