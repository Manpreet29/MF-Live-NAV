"""
Resolves ISINs to NSE trading symbols via the PostgreSQL instrument master.
Priority: NSE_EQ > NSE_SM > BSE_EQ > BSE_SM
"""
import logging
from database import get_db, instrument_master_count

logger = logging.getLogger(__name__)

_SQL = """
    SELECT trading_symbol
    FROM   instrument_master
    WHERE  isin = %s
      AND  segment IN ('NSE_EQ','NSE_SM','BSE_EQ','BSE_SM')
    ORDER BY CASE segment
        WHEN 'NSE_EQ' THEN 1 WHEN 'NSE_SM' THEN 2
        WHEN 'BSE_EQ' THEN 3 ELSE 4 END
    LIMIT 1
"""


class ISINMapperError(Exception):
    pass


def resolve_symbols(isins: list[str]) -> dict[str, str]:
    """
    Returns dict of ISIN -> trading_symbol (empty string if not found).
    Raises ISINMapperError if instrument master is empty.
    """
    if instrument_master_count() == 0:
        raise ISINMapperError(
            "Instrument master is empty. "
            "Call POST /api/admin/load-instruments to load it."
        )

    result: dict[str, str] = {}
    unique = list(dict.fromkeys(isins))

    with get_db() as db:
        with db.cursor() as cur:
            for isin in unique:
                cur.execute(_SQL, (isin,))
                row = cur.fetchone()
                result[isin] = row["trading_symbol"] if row and row["trading_symbol"] else ""

    found = sum(1 for v in result.values() if v)
    logger.info("ISIN mapping: %d/%d resolved", found, len(unique))
    return result
