"""
CCXT client for fetching cryptocurrency market data.
"""

from datetime import datetime
from typing import Dict, List, Optional

import ccxt
from ccxt.base.errors import NetworkError, RateLimitExceeded

from ..config import Config
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class CCXTClient:
    """Client for interacting with exchanges via CCXT."""

    def __init__(self, exchange_id: str = "kraken"):
        """
        Initialize CCXT client.

        Args:
            exchange_id: Exchange ID (default: kraken)
        """
        self.exchange_id = exchange_id

        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class(
            {
                "apiKey": Config.KRAKEN_API_KEY if exchange_id == "kraken" else "",
                "secret": Config.KRAKEN_API_SECRET if exchange_id == "kraken" else "",
                "enableRateLimit": True,
            }
        )

    def get_latest_quotes(self, symbols: Optional[List[str]] = None) -> Dict:
        """
        Get latest price quotes for specified cryptocurrencies.

        Args:
            symbols: List of cryptocurrency symbols (e.g., ["BTC", "XMR"])

        Returns:
            Dictionary with quote data for each symbol
        """
        if symbols is None:
            symbols = Config.SUPPORTED_SYMBOLS

        # Map symbols to exchange format (e.g., BTC -> BTC/USD)
        # Note: This assumes USD pairs for now
        pairs = [f"{s}/USD" for s in symbols]

        try:
            tickers = self.exchange.fetch_tickers(pairs)

            quotes = {}
            for pair, ticker in tickers.items():
                symbol = pair.split("/")[0]

                quotes[symbol] = {
                    "symbol": symbol,
                    "name": symbol,  # CCXT ticker doesn't always have full name
                    "price": ticker.get("last"),
                    "volume_24h": ticker.get("baseVolume"),  # Volume in base currency
                    "volume_change_24h": None,  # Not typically available in simple ticker
                    "percent_change_1h": None,
                    "percent_change_24h": ticker.get("percentage"),
                    "percent_change_7d": None,
                    "market_cap": None,  # Not typically available in ticker
                    "market_cap_dominance": None,
                    "last_updated": ticker.get("datetime"),
                    "timestamp": datetime.utcnow().isoformat(),
                }

            return quotes

        except (NetworkError, RateLimitExceeded) as e:
            logger.error(f"CCXT network/rate limit error: {e}")
            return {}
        except Exception as e:
            logger.error(f"CCXT error fetching quotes: {e}")
            return {}

    def get_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        since: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get historical OHLCV data with automatic pagination.

        Args:
            symbol: Cryptocurrency symbol
            timeframe: Timeframe (default: 1d)
            since: Timestamp in ms (optional)
            limit: Number of candles (optional)

        Returns:
            List of OHLCV data dictionaries
        """
        pair = f"{symbol}/USD"
        all_data = []

        try:
            # If no limit specified and we have a 'since' timestamp, fetch all data with pagination
            if since is not None and limit is None:
                # Fetch in chunks (most exchanges limit to 500-1000 candles per request)
                batch_limit = 720  # Safe limit for most exchanges (30 days of hourly data)
                current_since = since

                while True:
                    logger.info(
                        f"Fetching {symbol} OHLCV batch from {datetime.fromtimestamp(current_since/1000)}"
                    )
                    ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, current_since, batch_limit)

                    if not ohlcv:
                        break

                    # Format the data
                    for candle in ohlcv:
                        ts, open_price, high_price, low_price, close_price, vol = candle
                        all_data.append(
                            {
                                "symbol": symbol,
                                "timestamp": datetime.fromtimestamp(ts / 1000).isoformat(),
                                "open": open_price,
                                "high": high_price,
                                "low": low_price,
                                "close": close_price,
                                "volume": vol,
                                "market_cap": 0,
                                "interval": timeframe,
                            }
                        )

                    # If we got fewer candles than requested, we've reached the end
                    if len(ohlcv) < batch_limit:
                        break

                    # Update 'since' to the timestamp of the last candle + 1ms
                    current_since = ohlcv[-1][0] + 1

                    # Safety check: if we've reached current time, stop
                    if current_since >= datetime.utcnow().timestamp() * 1000:
                        break

                logger.info(f"Fetched total of {len(all_data)} candles for {symbol}")
                return all_data

            else:
                # Single request for limited data
                ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, since, limit)

                for candle in ohlcv:
                    ts, open_price, high_price, low_price, close_price, vol = candle
                    all_data.append(
                        {
                            "symbol": symbol,
                            "timestamp": datetime.fromtimestamp(ts / 1000).isoformat(),
                            "open": open_price,
                            "high": high_price,
                            "low": low_price,
                            "close": close_price,
                            "volume": vol,
                            "market_cap": 0,
                            "interval": timeframe,
                        }
                    )

                return all_data

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return all_data if all_data else []
