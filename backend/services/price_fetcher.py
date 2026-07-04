"""
Fetches live prices from Yahoo Finance (free, no API key needed).

Optimised for speed:
- MAX_CONCURRENT increased to 25 for faster batch fetching
- Deduplicates symbols across funds before fetching
- Returns both current price and previous close
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

# Higher concurrency = faster total fetch time
# 25 concurrent requests for 191 unique symbols = ~8 seconds instead of ~30
MAX_CONCURRENT = 25


@dataclass
class PriceData:
    current:    Optional[float]
    prev_close: Optional[float]


async def fetch_prices(symbols: list[str]) -> dict[str, PriceData]:
    """
    Fetch prices for a list of NSE trading symbols.
    Automatically deduplicates — safe to call with overlapping symbol lists.
    Returns dict of symbol -> PriceData(current, prev_close).
    """
    unique = list(dict.fromkeys(s for s in symbols if s))
    if not unique:
        return {}

    tickers = [s + ".NS" for s in unique]
    logger.info("Fetching prices for %d unique symbols", len(tickers))

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
    Fetch current price and yesterday's close for one Yahoo Finance ticker.

    prev_close is extracted from closes[-2] (second-to-last daily close)
    NOT from chartPreviousClose which points 5 trading days back.
    """
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(ticker)
        + "?interval=1d&range=5d"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())

        result = data.get("chart", {}).get("result")
        if not result:
            return PriceData(None, None)

        meta   = result[0].get("meta", {})
        quotes = result[0].get("indicators", {}).get("quote", [{}])
        closes = [c for c in (quotes[0].get("close", []) if quotes else []) if c is not None]

        current    = meta.get("regularMarketPrice")
        prev_close = None

        if len(closes) >= 2:
            prev_close = round(float(closes[-2]), 4)
        elif len(closes) == 1:
            raw = meta.get("chartPreviousClose") or meta.get("previousClose")
            if raw is not None:
                prev_close = round(float(raw), 4)

        if current is not None:
            current = round(float(current), 4)

        return PriceData(current, prev_close)

    except urllib.error.HTTPError as e:
        if e.code != 404:
            logger.debug("Yahoo HTTP %s for %s", e.code, ticker)
        return PriceData(None, None)
    except Exception as e:
        logger.debug("Yahoo fetch error for %s: %s", ticker, e)
        return PriceData(None, None)