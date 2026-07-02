import re
import gzip
import csv
import logging
import urllib.request
from io import BytesIO, StringIO
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from config import settings
from database import db_dependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

EQUITY_SEGMENTS = {"NSE_EQ", "BSE_EQ", "NSE_SM", "BSE_SM"}
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")


def _check_secret(x_admin_secret: str = Header(...)):
    if x_admin_secret != settings.admin_secret:
        raise HTTPException(401, "Invalid admin secret.")


@router.post("/load-instruments")
def load_instruments(
    db=Depends(db_dependency),
    _=Depends(_check_secret),
):
    
    url = settings.instrument_master_url
    logger.info("Downloading instrument master from %s", url)

    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            compressed = r.read()
    except Exception as e:
        raise HTTPException(502, f"Failed to download instrument master: {e}")

    logger.info("Downloaded %.1f MB, decompressing...", len(compressed) / 1_048_576)

    try:
        with gzip.GzipFile(fileobj=BytesIO(compressed)) as gz:
            csv_text = gz.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(500, f"Failed to decompress: {e}")

    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames or "instrument_key" not in reader.fieldnames:
        raise HTTPException(500, "instrument_key column not found in CSV.")

    col = {c.strip().lower(): c.strip() for c in reader.fieldnames}
    def get(row, name):
        return str(row.get(col.get(name.lower(), name), "")).strip()

    rows = []
    loaded_at = datetime.now(tz=timezone.utc).isoformat()

    for row in reader:
        key = get(row, "instrument_key")
        if not key or "|" not in key:
            continue
        segment, isin = key.split("|", 1)
        segment, isin = segment.upper(), isin.upper()
        if segment not in EQUITY_SEGMENTS:
            continue
        if not ISIN_RE.match(isin):
            continue
        sym = get(row, "tradingsymbol") or get(row, "trading_symbol")
        rows.append((isin, key, sym, get(row, "exchange").upper(), segment,
                     get(row, "name"), loaded_at))

    if not rows:
        raise HTTPException(500, "No equity instruments found in CSV.")

    logger.info("Inserting %d equity instruments into instrument_master...", len(rows))
    with db.cursor() as cur:
        cur.execute("DELETE FROM instrument_master")
        cur.executemany(
            """INSERT INTO instrument_master
               (isin, instrument_key, trading_symbol, exchange, segment, name, loaded_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            rows,
        )
    db.commit()
    logger.info("Instrument master loaded: %d rows", len(rows))

    return {
        "status":  "ok",
        "loaded":  len(rows),
        "message": "Instrument master loaded successfully.",
    }
