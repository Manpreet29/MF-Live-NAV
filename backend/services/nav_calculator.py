"""
NAV estimation engine using the Previous-Close method.

Formula:
  For each holding i with a live price AND prev_close:
    price_change(i) = (live_price(i) - prev_close(i)) / prev_close(i)
    nav_impact(i)   = (pct_to_nav(i) / 100) * price_change(i)

  total_change    = sum(nav_impact)        [priced holdings only]
  estimated_nav   = official_nav * (1 + total_change)

"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from models.nav import HoldingResult, NAVResult
from services.price_fetcher import PriceData

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30))


def calculate_nav(
    fund_id:        int,
    fund_name:      str,
    official_nav:   float,
    nav_date:       str,
    portfolio_date: str,
    holdings_db:    list[dict],           # rows from DB holdings table
    prices:         dict[str, PriceData], # symbol -> PriceData
) -> NAVResult:
    results         = []
    total_change_pp = 0.0
    pct_all         = 0.0
    pct_priced      = 0.0
    priced          = 0
    unpriced        = 0

    for h in holdings_db:
        sym        = h["trading_symbol"] or ""
        pd         = prices.get(sym) if sym else None
        live_price  = pd.current    if pd else None
        prev_close  = pd.prev_close if pd else None

        # Use prev_close as base; fallback to disclosed_price
        base = prev_close if prev_close else None

        chg_pct    = None
        impact_pct = 0.0
        status     = "unpriced"

        if live_price is not None and base is not None and base > 0:
            chg_pct    = round((live_price - base) / base * 100, 4)
            impact_pct = round((h["pct_to_nav"] / 100) * chg_pct, 6)
            status     = "priced"

        results.append(HoldingResult(
            name=h["name"], isin=h["isin"], industry=h["industry"],
            quantity=h["quantity"], pct_to_nav=h["pct_to_nav"],
            trading_symbol=sym,
            disclosed_price=h["disclosed_price"],
            prev_close=prev_close,
            live_price=live_price,
            price_change_pct=chg_pct,
            nav_impact_pct=impact_pct,
            status=status,
        ))

        pct_all += h["pct_to_nav"]
        if status == "priced":
            total_change_pp += impact_pct
            pct_priced      += h["pct_to_nav"]
            priced          += 1
        else:
            unpriced += 1

    estimated_nav = round(official_nav * (1 + total_change_pp / 100), 4)
    nav_change_abs = round(estimated_nav - official_nav, 4)
    nav_change_pct = round(total_change_pp, 4)

    coverage = round(pct_priced / pct_all * 100, 2) if pct_all > 0 else 0.0

    # Sort: priced first by pct_to_nav desc
    results.sort(key=lambda x: (x.status != "priced", -x.pct_to_nav))

    logger.info(
        "Fund %d '%s': est_nav=%.4f change=%+.4f%% coverage=%.1f%% priced=%d unpriced=%d",
        fund_id, fund_name, estimated_nav, nav_change_pct, coverage, priced, unpriced,
    )

    return NAVResult(
        fund_id=fund_id, fund_name=fund_name,
        nav_date=nav_date, portfolio_date=portfolio_date,
        official_nav=round(official_nav, 4),
        estimated_nav=estimated_nav,
        nav_change_abs=nav_change_abs,
        nav_change_pct=nav_change_pct,
        price_coverage_pct=coverage,
        total_holdings=len(results),
        priced_count=priced, unpriced_count=unpriced,
        calculated_at=datetime.now(tz=IST).isoformat(timespec="seconds"),
        holdings=results,
    )
