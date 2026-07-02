"""
services/price_fetcher.py
--------------------------
Fetches live prices from Yahoo Finance (free, no API key needed).

IMPORTANT — how prev_close is extracted:
  Yahoo's meta.chartPreviousClose = close BEFORE the chart range starts.
  With range=5d, that's ~5 trading days ago — NOT yesterday.

  The correct yesterday's close is extracted from the historical data array:
    closes = result["indicators"]["quote"][0]["close"]
    prev_close = closes[-2]   # second-to-last = yesterday
    current    = closes[-1]   # last = today's latest close / live price

  During market hours, regularMarketPrice is the live tick price, which
  is more current than closes[-1]. We use it when available.
"""
import asyncio
import json
import logging
import urllib.request
import urllib.parse
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

MAX_CONCURRENT = 10


@dataclass
class PriceData:
    current:    Optional[float]  # live/today's price (regularMarketPrice)
    prev_close: Optional[float]  # yesterday's official closing price


async def fetch_prices(symbols: list[str]) -> dict[str, PriceData]:
    """
    Fetch prices for a list of NSE trading symbols.
    Returns dict of symbol -> PriceData(current, prev_close).
    """
    unique = list(dict.fromkeys(s for s in symbols if s))
    if not unique:
        return {}

    tickers = [s + ".NS" for s in unique]
    logger.info("Fetching prices for %d symbols via Yahoo Finance", len(tickers))

    ticker_data = await _fetch_all(tickers)

    result: dict[str, PriceData] = {}
    for sym in unique:
        ticker = sym + ".NS"
        result[sym] = ticker_data.get(ticker, PriceData(None, None))

    priced = sum(1 for v in result.values() if v.current is not None)
    logger.info("Prices received: %d/%d", priced, len(unique))
    return result


async def _fetch_all(tickers: list[str]) -> dict[str, PriceData]:
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results: dict[str, PriceData] = {}

    async def one(ticker: str):
        async with sem:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _fetch_one, ticker)
            results[ticker] = data

    await asyncio.gather(*[one(t) for t in tickers])
    return results


def _fetch_one(ticker: str) -> PriceData:
    """
    Fetch one ticker using Yahoo Finance v8/chart with range=5d.

    Extracts:
      current    = meta.regularMarketPrice  (live tick during market hours,
                   or last closing price after hours)
      prev_close = closes[-2]               (second-to-last daily close
                   = yesterday's official close)

    Why closes[-2] and not chartPreviousClose:
      chartPreviousClose is the close BEFORE the chart range starts.
      With range=5d it points ~5 trading days back, not yesterday.
      The closes array contains one entry per trading day in the range,
      so closes[-2] is always yesterday's close regardless of range.
    """
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(ticker)
        + "?interval=1d&range=5d"
    )
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        result = data.get("chart", {}).get("result")
        if not result:
            logger.debug("No chart result for %s", ticker)
            return PriceData(None, None)

        meta   = result[0].get("meta", {})
        quotes = result[0].get("indicators", {}).get("quote", [{}])
        closes = quotes[0].get("close", []) if quotes else []

        # Remove None values that Yahoo sometimes inserts for incomplete days
        closes = [c for c in closes if c is not None]

        # --- current price ---
        # regularMarketPrice = live tick during market hours
        # Falls back to last close if market is closed
        current = meta.get("regularMarketPrice")
        if current is not None:
            current = round(float(current), 4)

        # --- previous close ---
        # closes[-1] = today's close (or latest intraday close)
        # closes[-2] = yesterday's official close  ← THIS IS WHAT WE WANT
        prev_close = None
        if len(closes) >= 2:
            prev_close = round(float(closes[-2]), 4)
        elif len(closes) == 1:
            # Only one day of data — use chartPreviousClose as fallback
            raw = meta.get("chartPreviousClose") or meta.get("previousClose")
            if raw is not None:
                prev_close = round(float(raw), 4)

        logger.debug(
            "%s -> current=%.2f  prev_close=%s  (from %d closes in range)",
            ticker,
            current or 0,
            f"{prev_close:.2f}" if prev_close else "None",
            len(closes),
        )
        return PriceData(current, prev_close)

    except urllib.error.HTTPError as e:
        if e.code != 404:
            logger.debug("Yahoo HTTP %s for %s", e.code, ticker)
        return PriceData(None, None)
    except Exception as e:
        logger.debug("Yahoo fetch error for %s: %s", ticker, e)
        return PriceData(None, None)


def _get_symbol_from_db(instrument_key: str) -> Optional[str]:
    """Fallback: look up trading_symbol from SQLite by instrument_key."""
    try:
        from database import get_db
        with get_db() as db:
            row = db.execute(
                "SELECT trading_symbol FROM instrument_master "
                "WHERE instrument_key = ? LIMIT 1",
                (instrument_key,)
            ).fetchone()
            return row["trading_symbol"] if row else None
    except Exception as e:
        logger.warning("DB lookup failed for %s: %s", instrument_key, e)
        return None