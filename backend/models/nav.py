"""Pydantic models for the NAV calculation response."""
from typing import Optional
from pydantic import BaseModel, Field


class HoldingResult(BaseModel):
    name:             str
    isin:             str
    industry:         str
    quantity:         int
    pct_to_nav:       float
    trading_symbol:   str

    disclosed_price:  float
    prev_close:       Optional[float] = None
    live_price:       Optional[float] = None
    price_change_pct: Optional[float] = None
    nav_impact_pct:   float = 0.0
    status:           str   = "unpriced"   # "priced" | "unpriced"


class NAVResult(BaseModel):
    fund_id:            int
    fund_name:          str
    nav_date:           str
    portfolio_date:     str

    official_nav:       float
    estimated_nav:      float
    nav_change_abs:     float
    nav_change_pct:     float

    price_coverage_pct: float
    total_holdings:     int
    priced_count:       int
    unpriced_count:     int

    calculated_at:      str
    holdings:           list[HoldingResult] = Field(default_factory=list)
