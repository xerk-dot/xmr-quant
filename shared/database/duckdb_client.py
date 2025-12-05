"""
DuckDB client for market data storage.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd

from ..config import Config
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class DuckDBClient:
    """Client for interacting with DuckDB market data database."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DuckDB client.

        Args:
            db_path: Path to DuckDB database file (defaults to config)
        """
        self.db_path = db_path or Config.DATABASE_PATH
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self._ensure_database()

    def _ensure_database(self) -> None:
        """Ensure database and tables exist."""
        self.conn = duckdb.connect(self.db_path)
        self._create_tables()
        logger.info(f"Connected to DuckDB at {self.db_path}")

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        # Create sequences for IDs
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_quotes_id")
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_ohlcv_id")

        # Quotes table for real-time price data
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_quotes_id'),
                symbol VARCHAR NOT NULL,
                name VARCHAR,
                timestamp TIMESTAMP NOT NULL,
                price DOUBLE,
                volume_24h DOUBLE,
                volume_change_24h DOUBLE,
                percent_change_1h DOUBLE,
                percent_change_24h DOUBLE,
                percent_change_7d DOUBLE,
                market_cap DOUBLE,
                market_cap_dominance DOUBLE,
                last_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create index on symbol and timestamp for fast queries
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_quotes_symbol_timestamp
            ON quotes(symbol, timestamp)
        """
        )

        # OHLCV table for historical candlestick data
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_ohlcv_id'),
                symbol VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                market_cap DOUBLE,
                interval VARCHAR DEFAULT '1d',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp, interval)
            )
        """
        )

        # Create index on symbol and timestamp
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timestamp
            ON ohlcv(symbol, timestamp)
        """
        )

        logger.info("Database tables created/verified")

    def insert_quote(self, quote_data: Dict[str, Any]) -> None:
        """
        Insert a single quote into the database.

        Args:
            quote_data: Quote data dictionary from CCXT
        """
        self.conn.execute(
            """
            INSERT INTO quotes (
                symbol, name, timestamp, price, volume_24h, volume_change_24h,
                percent_change_1h, percent_change_24h, percent_change_7d,
                market_cap, market_cap_dominance, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                quote_data.get("symbol"),
                quote_data.get("name"),
                quote_data.get("timestamp"),
                quote_data.get("price"),
                quote_data.get("volume_24h"),
                quote_data.get("volume_change_24h"),
                quote_data.get("percent_change_1h"),
                quote_data.get("percent_change_24h"),
                quote_data.get("percent_change_7d"),
                quote_data.get("market_cap"),
                quote_data.get("market_cap_dominance"),
                quote_data.get("last_updated"),
            ],
        )
        logger.debug(f"Inserted quote for {quote_data.get('symbol')}")

    def insert_quotes_batch(self, quotes: List[Dict[str, Any]]) -> int:
        """
        Insert multiple quotes into the database.

        Args:
            quotes: List of quote data dictionaries

        Returns:
            Number of quotes inserted
        """
        if not quotes:
            return 0

        df = pd.DataFrame(quotes)
        df = df[
            [
                "symbol",
                "name",
                "timestamp",
                "price",
                "volume_24h",
                "volume_change_24h",
                "percent_change_1h",
                "percent_change_24h",
                "percent_change_7d",
                "market_cap",
                "market_cap_dominance",
                "last_updated",
            ]
        ]

        self.conn.execute(
            """
            INSERT INTO quotes (
                symbol, name, timestamp, price, volume_24h, volume_change_24h,
                percent_change_1h, percent_change_24h, percent_change_7d,
                market_cap, market_cap_dominance, last_updated
            ) SELECT * FROM df
            """
        )
        count = len(quotes)
        logger.info(f"Inserted {count} quotes")
        return count

    def insert_ohlcv(self, ohlcv_data: Dict[str, Any]) -> None:
        """
        Insert OHLCV data into the database.

        Args:
            ohlcv_data: OHLCV data dictionary
        """
        try:
            self.conn.execute(
                """
                INSERT INTO ohlcv (
                    symbol, timestamp, open, high, low, close, volume, market_cap, interval
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol, timestamp, interval) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    market_cap = EXCLUDED.market_cap
            """,
                [
                    ohlcv_data.get("symbol"),
                    ohlcv_data.get("timestamp"),
                    ohlcv_data.get("open"),
                    ohlcv_data.get("high"),
                    ohlcv_data.get("low"),
                    ohlcv_data.get("close"),
                    ohlcv_data.get("volume"),
                    ohlcv_data.get("market_cap"),
                    ohlcv_data.get("interval", "1d"),
                ],
            )
            logger.debug(f"Inserted OHLCV for {ohlcv_data.get('symbol')}")
        except Exception as e:
            logger.error(f"Error inserting OHLCV: {e}")

    def insert_ohlcv_batch(self, ohlcv_list: List[Dict[str, Any]]) -> int:
        """
        Insert multiple OHLCV records into the database.

        Args:
            ohlcv_list: List of OHLCV data dictionaries

        Returns:
            Number of records inserted/updated
        """
        if not ohlcv_list:
            return 0

        count = 0
        for ohlcv_data in ohlcv_list:
            try:
                self.insert_ohlcv(ohlcv_data)
                count += 1
            except Exception as e:
                logger.error(f"Error inserting OHLCV batch item: {e}")

        logger.info(f"Inserted/updated {count} OHLCV records")
        return count

    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest quote for a symbol.

        Args:
            symbol: Cryptocurrency symbol

        Returns:
            Latest quote data or None
        """
        result = self.conn.execute(
            """
            SELECT * FROM quotes
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            [symbol],
        ).fetchone()

        if result:
            columns = [desc[0] for desc in self.conn.description]
            return dict(zip(columns, result))
        return None

    def get_quotes(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Get quotes from the database.

        Args:
            symbol: Filter by symbol (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of records (optional)

        Returns:
            DataFrame with quote data
        """
        query = "SELECT * FROM quotes WHERE 1=1"
        params: List[Any] = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += f" LIMIT {limit}"

        return self.conn.execute(query, params).df()

    def get_ohlcv(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Get OHLCV data from the database.

        Args:
            symbol: Filter by symbol (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            interval: Candlestick interval (default: 1d)

        Returns:
            DataFrame with OHLCV data
        """
        query = "SELECT * FROM ohlcv WHERE interval = ?"
        params: List[Any] = [interval]

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp ASC"

        return self.conn.execute(query, params).df()

    def get_latest_timestamp(self, symbol: str, table: str = "quotes") -> Optional[datetime]:
        """
        Get the latest timestamp for a symbol in a table.

        Args:
            symbol: Cryptocurrency symbol
            table: Table name ('quotes' or 'ohlcv')

        Returns:
            Latest timestamp or None
        """
        result = self.conn.execute(
            f"""
            SELECT MAX(timestamp) as max_timestamp
            FROM {table}
            WHERE symbol = ?
        """,
            [symbol],
        ).fetchone()

        if result and result[0]:
            return result[0]
        return None

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        quotes_count = self.conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        ohlcv_count = self.conn.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0]

        symbols_quotes = self.conn.execute(
            "SELECT DISTINCT symbol FROM quotes ORDER BY symbol"
        ).fetchall()
        symbols_ohlcv = self.conn.execute(
            "SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol"
        ).fetchall()

        date_range_quotes = self.conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM quotes"
        ).fetchone()
        date_range_ohlcv = self.conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM ohlcv"
        ).fetchone()

        return {
            "database_path": self.db_path,
            "quotes_count": quotes_count,
            "ohlcv_count": ohlcv_count,
            "symbols_quotes": [s[0] for s in symbols_quotes],
            "symbols_ohlcv": [s[0] for s in symbols_ohlcv],
            "quotes_date_range": {
                "start": date_range_quotes[0],
                "end": date_range_quotes[1],
            }
            if date_range_quotes[0]
            else None,
            "ohlcv_date_range": {
                "start": date_range_ohlcv[0],
                "end": date_range_ohlcv[1],
            }
            if date_range_ohlcv[0]
            else None,
        }

    def clean_old_data(self, days: Optional[int] = None) -> int:
        """
        Remove data older than specified days.

        Args:
            days: Number of days to retain (defaults to config)

        Returns:
            Number of records deleted
        """
        days = days or Config.DATA_RETENTION_DAYS
        cutoff_date = datetime.now() - pd.Timedelta(days=days)

        deleted_quotes = self.conn.execute(
            "DELETE FROM quotes WHERE timestamp < ?", [cutoff_date]
        ).fetchone()
        deleted_ohlcv = self.conn.execute(
            "DELETE FROM ohlcv WHERE timestamp < ?", [cutoff_date]
        ).fetchone()

        total_deleted = (deleted_quotes[0] if deleted_quotes else 0) + (
            deleted_ohlcv[0] if deleted_ohlcv else 0
        )
        logger.info(f"Deleted {total_deleted} old records (older than {days} days)")
        return total_deleted

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
