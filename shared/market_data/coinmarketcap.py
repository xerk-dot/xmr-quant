"""
CoinMarketCap API client for fetching cryptocurrency market data.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

from ..config import Config


class CoinMarketCapClient:
    """Client for interacting with CoinMarketCap API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CoinMarketCap client.

        Args:
            api_key: CoinMarketCap API key (defaults to config)
        """
        self.api_key = api_key or Config.COINMARKETCAP_API_KEY
        self.base_url = Config.COINMARKETCAP_BASE_URL
        self.session = requests.Session()
        self.session.headers.update(
            {"X-CMC_PRO_API_KEY": self.api_key, "Accept": "application/json"}
        )

        # Rate limiting
        self.last_request_time = 0.0
        self.min_request_interval = 1.0  # seconds between requests

    def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)

        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the CoinMarketCap API.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            API response data

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        self._rate_limit()

        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if data.get("status", {}).get("error_code") != 0:
            error_message = data.get("status", {}).get("error_message", "Unknown error")
            raise Exception(f"CoinMarketCap API error: {error_message}")

        return data  # type: ignore[return-value]

    def get_latest_quotes(self, symbols: Optional[List[str]] = None) -> Dict:
        """
        Get latest price quotes for specified cryptocurrencies.

        Args:
            symbols: List of cryptocurrency symbols (defaults to config supported symbols)

        Returns:
            Dictionary with quote data for each symbol
        """
        if symbols is None:
            symbols = Config.SUPPORTED_SYMBOLS

        params = {"symbol": ",".join(symbols), "convert": "USD"}

        data = self._make_request("cryptocurrency/quotes/latest", params)

        # Extract and format the data
        quotes = {}
        for symbol in symbols:
            if symbol in data.get("data", {}):
                coin_data = data["data"][symbol]
                quote = coin_data.get("quote", {}).get("USD", {})

                quotes[symbol] = {
                    "symbol": symbol,
                    "name": coin_data.get("name"),
                    "price": quote.get("price"),
                    "volume_24h": quote.get("volume_24h"),
                    "volume_change_24h": quote.get("volume_change_24h"),
                    "percent_change_1h": quote.get("percent_change_1h"),
                    "percent_change_24h": quote.get("percent_change_24h"),
                    "percent_change_7d": quote.get("percent_change_7d"),
                    "market_cap": quote.get("market_cap"),
                    "market_cap_dominance": quote.get("market_cap_dominance"),
                    "last_updated": quote.get("last_updated"),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return quotes

    def get_historical_quotes(
        self,
        symbol: str,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
        count: int = 10,
        interval: str = "1d",
    ) -> List[Dict]:
        """
        Get historical price quotes for a cryptocurrency.

        Args:
            symbol: Cryptocurrency symbol
            time_start: Start time (ISO 8601 format)
            time_end: End time (ISO 8601 format)
            count: Number of data points to return
            interval: Time interval (1d, hourly, 5m, etc.)

        Returns:
            List of historical quote data
        """
        params = {"symbol": symbol, "count": count, "interval": interval, "convert": "USD"}

        if time_start:
            params["time_start"] = time_start
        if time_end:
            params["time_end"] = time_end

        data = self._make_request("cryptocurrency/quotes/historical", params)

        # Extract and format historical data
        quotes = []
        if symbol in data.get("data", {}):
            for quote_data in data["data"][symbol].get("quotes", []):
                quote = quote_data.get("quote", {}).get("USD", {})
                quotes.append(
                    {
                        "symbol": symbol,
                        "timestamp": quote_data.get("timestamp"),
                        "price": quote.get("price"),
                        "volume_24h": quote.get("volume_24h"),
                        "market_cap": quote.get("market_cap"),
                    }
                )

        return quotes

    def get_metadata(self, symbols: Optional[List[str]] = None) -> Dict:
        """
        Get metadata for cryptocurrencies.

        Args:
            symbols: List of cryptocurrency symbols

        Returns:
            Dictionary with metadata for each symbol
        """
        if symbols is None:
            symbols = Config.SUPPORTED_SYMBOLS

        params = {"symbol": ",".join(symbols)}

        data = self._make_request("cryptocurrency/info", params)

        # Extract metadata
        metadata = {}
        for symbol in symbols:
            if symbol in data.get("data", {}):
                coin_data = data["data"][symbol]
                metadata[symbol] = {
                    "symbol": symbol,
                    "name": coin_data.get("name"),
                    "description": coin_data.get("description"),
                    "logo": coin_data.get("logo"),
                    "website": coin_data.get("urls", {}).get("website", []),
                    "technical_doc": coin_data.get("urls", {}).get("technical_doc", []),
                    "twitter": coin_data.get("urls", {}).get("twitter", []),
                    "reddit": coin_data.get("urls", {}).get("reddit", []),
                }

        return metadata
