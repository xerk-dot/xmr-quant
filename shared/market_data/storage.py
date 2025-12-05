"""
Market data storage utilities.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..config import Config
from ..database import DuckDBClient
from ..monitoring.logger import get_logger
from .ccxt_client import CCXTClient

logger = get_logger(__name__)


class MarketDataStorage:
    """Utilities for storing and managing market data in DuckDB."""

    def __init__(self, db_client: Optional[DuckDBClient] = None):
        """
        Initialize market data storage.

        Args:
            db_client: DuckDB client instance (creates new if not provided)
        """
        self.db = db_client or DuckDBClient()
        self.ccxt = CCXTClient()

    def collect_daily_data(self, symbols: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Daily data collection: fetch latest quotes and update OHLCV for all symbols.
        This is the main method to call for regular data updates.

        Args:
            symbols: List of symbols (defaults to all supported: BTC, XMR, ZEC, LTC)

        Returns:
            Dictionary with counts of records stored
        """
        symbols = symbols or Config.SUPPORTED_SYMBOLS
        logger.info(f"Starting daily data collection for {symbols}")

        results = {"quotes": 0, "ohlcv": 0}

        # 1. Fetch and store latest quotes
        try:
            quotes = self.ccxt.get_latest_quotes(symbols)
            quotes_list = list(quotes.values())
            if quotes_list:
                results["quotes"] = self.db.insert_quotes_batch(quotes_list)
                logger.info(f"✓ Stored {results['quotes']} quotes")
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")

        # 2. Fetch and store OHLCV data for each symbol
        for symbol in symbols:
            try:
                # Get latest timestamp from database
                latest_ts = self.db.get_latest_timestamp(symbol, "ohlcv")

                if latest_ts:
                    # Incremental update: fetch from last timestamp to now
                    # CCXT expects timestamp in ms
                    since = int(latest_ts.timestamp() * 1000)
                    logger.info(f"Updating {symbol} OHLCV (since: {latest_ts})")
                else:
                    # Initial fetch: get all available historical data (last 5 years)
                    days_back = 1825  # 5 years
                    since = int((datetime.utcnow() - timedelta(days=days_back)).timestamp() * 1000)
                    logger.info(f"Initial {symbol} OHLCV fetch ({days_back} days)")

                ohlcv_list = self.ccxt.get_historical_ohlcv(symbol, timeframe="1h", since=since)

                if ohlcv_list:
                    count = self.db.insert_ohlcv_batch(ohlcv_list)
                    results["ohlcv"] += count
                    logger.info(f"✓ Stored {count} OHLCV records for {symbol}")

            except Exception as e:
                logger.error(f"Error fetching OHLCV for {symbol}: {e}")

        logger.info(f"Daily collection complete: {results}")
        return results

    def backfill_historical_data(
        self, symbols: Optional[List[str]] = None, days: int = 1825
    ) -> Dict[str, int]:
        """
        Backfill historical data for symbols.
        Use this for initial setup or to fill gaps.

        Args:
            symbols: List of symbols (defaults to all supported)
            days: Number of days to backfill

        Returns:
            Dictionary with counts per symbol
        """
        symbols = symbols or Config.SUPPORTED_SYMBOLS
        logger.info(f"Backfilling {days} days of historical data for {symbols}")

        results = {}
        for symbol in symbols:
            since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
            ohlcv_list = self.ccxt.get_historical_ohlcv(symbol, timeframe="1h", since=since)

            if ohlcv_list:
                count = self.db.insert_ohlcv_batch(ohlcv_list)
                results[symbol] = count
            else:
                results[symbol] = 0

        logger.info(f"Backfill complete: {results}")
        return results

    def get_price_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        Get price data for a symbol from the database.

        Args:
            symbol: Cryptocurrency symbol
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            Dictionary with quotes and ohlcv DataFrames
        """
        return {
            "quotes": self.db.get_quotes(symbol, start_date, end_date),
            "ohlcv": self.db.get_ohlcv(symbol, start_date, end_date),
        }

    def get_latest_prices(self, symbols: Optional[List[str]] = None) -> Dict:
        """
        Get latest prices for symbols from database.

        Args:
            symbols: List of symbols (defaults to all supported)

        Returns:
            Dictionary mapping symbol to latest price data
        """
        symbols = symbols or Config.SUPPORTED_SYMBOLS
        latest = {}

        for symbol in symbols:
            quote = self.db.get_latest_quote(symbol)
            if quote:
                latest[symbol] = quote

        return latest

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        return self.db.get_database_stats()

    def cleanup_old_data(self, days: Optional[int] = None) -> int:
        """
        Remove data older than specified days.

        Args:
            days: Number of days to retain (defaults to config)

        Returns:
            Number of records deleted
        """
        return self.db.clean_old_data(days)

    def close(self) -> None:
        """Close database connection."""
        self.db.close()
