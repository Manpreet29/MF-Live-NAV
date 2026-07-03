"""
scripts/load_instrument_master.py
----------------------------------
Downloads the Upstox instrument master CSV and indexes it into PostgreSQL.

Run once after deployment (from your local machine pointing at Supabase):
    cd backend
    python scripts/load_instrument_master.py

Re-run monthly to pick up newly listed stocks.
"""
import re, sys, os, gzip, csv, logging
import urllib.request
from io import BytesIO, StringIO
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from database import init_db, get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

EQUITY_SEGMENTS = {"NSE_EQ", "BSE_EQ", "NSE_SM", "BSE_SM"}
ISIN_RE         = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")


def download() -> bytes:
    url = settings.instrument_master_url
    logger.info("Downloading from %s", url)
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    logger.info("Downloaded %.1f MB compressed", len(data) / 1_048_576)
    return data


def decompress(data: bytes) -> str:
    with gzip.GzipFile(fileobj=BytesIO(data)) as gz:
        raw = gz.read()
    logger.info("Decompressed to %.1f MB", len(raw) / 1_048_576)
    return raw.decode("utf-8", errors="replace")


def load(csv_text: str) -> int:
    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames or "instrument_key" not in reader.fieldnames:
        raise ValueError("'instrument_key' column not found in CSV.")

    col = {c.strip().lower(): c.strip() for c in reader.fieldnames}
    def get(row, name):
        return str(row.get(col.get(name.lower(), name), "")).strip()

    rows = []
    loaded_at = datetime.now(tz=timezone.utc).isoformat()
    skipped = 0

    for row in reader:
        key = get(row, "instrument_key")
        if not key or "|" not in key:
            continue
        segment, isin = key.split("|", 1)
        segment, isin = segment.upper(), isin.upper()

        if segment not in EQUITY_SEGMENTS:
            skipped += 1
            continue
        if not ISIN_RE.match(isin):
            continue

        sym = get(row, "tradingsymbol") or get(row, "trading_symbol")
        rows.append((isin, key, sym, get(row, "exchange").upper(),
                     segment, get(row, "name"), loaded_at))

    logger.info("Equity rows: %d  (skipped non-equity: %d)", len(rows), skipped)

    if not rows:
        raise ValueError("No equity instruments found.")

    # Insert in batches of 1000 to avoid timeouts
    BATCH = 1000
    with get_db() as db:
        with db.cursor() as cur:
            cur.execute("DELETE FROM instrument_master")
        db.commit()
        logger.info("Cleared old instrument master. Inserting %d rows in batches...", len(rows))

        for i in range(0, len(rows), BATCH):
            batch = rows[i:i + BATCH]
            with db.cursor() as cur:
                cur.executemany(
                    """INSERT INTO instrument_master
                       (isin, instrument_key, trading_symbol, exchange, segment, name, loaded_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    batch,
                )
            db.commit()
            logger.info("  Inserted rows %d-%d...", i + 1, min(i + BATCH, len(rows)))

    logger.info("Done. Inserted %d rows total.", len(rows))
    return len(rows)


def verify():
    checks = {
        "INE090A01021": "ICICI Bank",
        "INE040A01034": "HDFC Bank",
        "INE585B01010": "Maruti Suzuki",
        "INE002A01018": "Reliance Industries",
        "INE009A01021": "Infosys",
    }
    with get_db() as db:
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM instrument_master")
            total = cur.fetchone()["c"]
        logger.info("Total rows in instrument_master: %d", total)
        logger.info("--- Spot check ---")
        for isin, name in checks.items():
            with db.cursor() as cur:
                cur.execute(
                    """SELECT trading_symbol, segment FROM instrument_master
                       WHERE isin=%s AND segment IN ('NSE_EQ','NSE_SM','BSE_EQ','BSE_SM')
                       ORDER BY CASE segment WHEN 'NSE_EQ' THEN 1 WHEN 'NSE_SM' THEN 2
                                             WHEN 'BSE_EQ' THEN 3 ELSE 4 END LIMIT 1""",
                    (isin,)
                )
                row = cur.fetchone()
            if row:
                logger.info("  %-14s %-22s -> %s [%s]",
                            isin, name, row["trading_symbol"], row["segment"])
            else:
                logger.warning("  %-14s %-22s -> NOT FOUND", isin, name)


def main():
    logger.info("=== Instrument Master Loader ===")
    init_db()
    compressed = download()
    csv_text   = decompress(compressed)
    count      = load(csv_text)
    verify()
    logger.info("=== Done. Loaded %d instruments. ===", count)


if __name__ == "__main__":
    main()