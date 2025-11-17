"""
Market Data Collector for Market Cycle Analysis
Collects XMR and BTC historical data for market cycle indicator calculations
"""

import logging
import time
from datetime import datetime, timedelta

import ccxt
import pandas as pd

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """Collects and manages market data for multiple assets"""

    def __init__(self, exchange_id: str = "binance"):
        """
        Initialize data collector

        Args:
            exchange_id: CCXT exchange ID (default: binance)
        """
        self.exchange = getattr(ccxt, exchange_id)(
            {"enableRateLimit": True, "options": {"defaultType": "spot"}}
        )
        self.exchange_id = exchange_id

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: datetime | None = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol

        Args:
            symbol: Trading pair (e.g., 'XMR/USDT', 'BTC/USDT')
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            since: Start date (default: 1000 periods ago)
            limit: Number of candles to fetch (max depends on exchange)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            logger.info(f"Fetching {symbol} data ({timeframe})...")

            if since is None:
                # Calculate 'since' based on limit and timeframe
                since = self._calculate_since(timeframe, limit)

            since_ms = int(since.timestamp() * 1000)

            # Fetch data
            ohlcv = self.exchange.fetch_ohlcv(
                symbol, timeframe=timeframe, since=since_ms, limit=limit
            )

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            logger.info(f"✓ Fetched {len(df)} candles for {symbol}")
            logger.info(f"  Date range: {df.index[0]} to {df.index[-1]}")

            return df

        except Exception as e:
            logger.error(f"Failed to fetch {symbol} data: {e}")
            return pd.DataFrame()

    def fetch_historical_data(
        self, symbol: str, timeframe: str = "1h", days: int = 365, batch_size: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch historical data by making multiple paginated requests

        Args:
            symbol: Trading pair
            timeframe: Timeframe
            days: Number of days to fetch
            batch_size: Candles per request

        Returns:
            DataFrame with historical data
        """
        logger.info(f"Fetching {days} days of {symbol} data...")

        all_data = []
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        current_time = start_time

        while current_time < end_time:
            try:
                df_batch = self.fetch_ohlcv(
                    symbol, timeframe=timeframe, since=current_time, limit=batch_size
                )

                if df_batch.empty:
                    break

                all_data.append(df_batch)

                # Update current_time to last timestamp + 1 period
                current_time = df_batch.index[-1] + pd.Timedelta(timeframe)

                # Rate limiting
                time.sleep(self.exchange.rateLimit / 1000)

                if current_time >= end_time:
                    break

            except Exception as e:
                logger.error(f"Error fetching batch: {e}")
                break

        if not all_data:
            return pd.DataFrame()

        # Combine all batches
        df = pd.concat(all_data)
        df = df[~df.index.duplicated(keep="first")]  # Remove duplicates
        df.sort_index(inplace=True)

        logger.info(f"✓ Fetched total of {len(df)} candles")

        return df

    def fetch_market_cycle_data(
        self,
        xmr_symbol: str = "XMR/USDT",
        btc_symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        days: int = 730,  # 2 years for cycle indicators
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch data for both XMR and BTC for market cycle analysis

        Args:
            xmr_symbol: XMR trading pair
            btc_symbol: BTC trading pair
            timeframe: Timeframe
            days: Number of days of history

        Returns:
            Dictionary with 'xmr' and 'btc' DataFrames
        """
        logger.info("=" * 60)
        logger.info("Fetching Market Cycle Data")
        logger.info("=" * 60)

        # Fetch XMR data
        xmr_df = self.fetch_historical_data(xmr_symbol, timeframe, days)

        # Fetch BTC data
        btc_df = self.fetch_historical_data(btc_symbol, timeframe, days)

        # Align timeframes (in case of missing data)
        if not xmr_df.empty and not btc_df.empty:
            # Find common time range
            start_date = max(xmr_df.index[0], btc_df.index[0])
            end_date = min(xmr_df.index[-1], btc_df.index[-1])

            xmr_df = xmr_df.loc[start_date:end_date]
            btc_df = btc_df.loc[start_date:end_date]

            # Reindex to ensure alignment
            common_index = xmr_df.index.union(btc_df.index)
            xmr_df = xmr_df.reindex(common_index, method="ffill")
            btc_df = btc_df.reindex(common_index, method="ffill")

            logger.info("=" * 60)
            logger.info(f"✓ Data aligned: {len(xmr_df)} periods")
            logger.info(f"  Date range: {xmr_df.index[0]} to {xmr_df.index[-1]}")
            logger.info("=" * 60)

        return {"xmr": xmr_df, "btc": btc_df}

    def _calculate_since(self, timeframe: str, limit: int) -> datetime:
        """Calculate 'since' timestamp based on timeframe and limit"""

        # Parse timeframe
        timeframe_minutes = {
            "1m": 1,
            "3m": 3,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "2h": 120,
            "4h": 240,
            "6h": 360,
            "12h": 720,
            "1d": 1440,
            "3d": 4320,
            "1w": 10080,
        }

        minutes = timeframe_minutes.get(timeframe, 60)
        total_minutes = minutes * limit

        since = datetime.now() - timedelta(minutes=total_minutes)

        return since

    def save_data(self, df: pd.DataFrame, filename: str, directory: str = "data/historical"):
        """Save DataFrame to CSV"""
        import os

        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)

        df.to_csv(filepath)
        logger.info(f"✓ Saved data to {filepath}")

    def load_data(self, filename: str, directory: str = "data/historical") -> pd.DataFrame:
        """Load DataFrame from CSV"""
        import os

        filepath = os.path.join(directory, filename)

        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filepath}")
            return pd.DataFrame()

        df = pd.read_csv(filepath, index_col="timestamp", parse_dates=True)
        logger.info(f"✓ Loaded data from {filepath} ({len(df)} rows)")

        return df


def collect_and_save_market_data(timeframe: str = "1h", days: int = 730, exchange: str = "binance"):
    """
    Convenience function to collect and save market data

    Args:
        timeframe: Candle timeframe
        days: Days of history
        exchange: Exchange ID
    """
    collector = MarketDataCollector(exchange)

    data = collector.fetch_market_cycle_data(timeframe=timeframe, days=days)

    if not data["xmr"].empty:
        collector.save_data(data["xmr"], f"xmr_usdt_{timeframe}_{days}d.csv")

    if not data["btc"].empty:
        collector.save_data(data["btc"], f"btc_usdt_{timeframe}_{days}d.csv")

    return data


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    print("\n" + "=" * 60)
    print("Market Data Collector for Market Cycle Analysis")
    print("=" * 60 + "\n")

    # Collect 2 years of hourly data
    data = collect_and_save_market_data(timeframe="1h", days=730, exchange="binance")

    print("\n✓ Data collection complete!\n")
