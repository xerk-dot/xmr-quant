"""
Kraken exchange API client for trading operations.
"""

from typing import Any, Dict, List, Literal, Optional

import krakenex

from ..config import Config


class KrakenClient:
    """Client for interacting with Kraken exchange API."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Kraken client.

        Args:
            api_key: Kraken API key (defaults to config)
            api_secret: Kraken API secret (defaults to config)
        """
        self.api = krakenex.API()
        self.api.key = api_key or Config.KRAKEN_API_KEY
        self.api.secret = api_secret or Config.KRAKEN_API_SECRET

    def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance for all assets.

        Returns:
            Dictionary with asset balances
        """
        response = self.api.query_private("Balance")  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        return response.get("result", {})  # type: ignore[return-value]

    def get_ticker(self, pair: str) -> Dict[str, Any]:
        """
        Get ticker information for a trading pair.

        Args:
            pair: Trading pair (e.g., 'XMRUSD')

        Returns:
            Ticker data
        """
        response = self.api.query_public("Ticker", {"pair": pair})  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        result = response.get("result", {})

        # Kraken returns data with the pair as key
        if pair in result:
            ticker_data = result[pair]
            return {
                "pair": pair,
                "ask": float(ticker_data["a"][0]),
                "bid": float(ticker_data["b"][0]),
                "last": float(ticker_data["c"][0]),
                "volume": float(ticker_data["v"][1]),
                "vwap": float(ticker_data["p"][1]),
                "trades": int(ticker_data["t"][1]),
                "low": float(ticker_data["l"][1]),
                "high": float(ticker_data["h"][1]),
                "open": float(ticker_data["o"]),
            }

        return {}

    def get_ohlc(
        self, pair: str, interval: int = 1, since: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get OHLC (candlestick) data for a trading pair.

        Args:
            pair: Trading pair (e.g., 'XMRUSD')
            interval: Time interval in minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
            since: Return data since given timestamp

        Returns:
            List of OHLC data
        """
        params = {"pair": pair, "interval": interval}
        if since:
            params["since"] = since

        response = self.api.query_public("OHLC", params)  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        result = response.get("result", {})

        # Extract OHLC data
        ohlc_data = []
        if pair in result:
            for candle in result[pair]:
                ohlc_data.append(
                    {
                        "timestamp": int(candle[0]),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "vwap": float(candle[5]),
                        "volume": float(candle[6]),
                        "count": int(candle[7]),
                    }
                )

        return ohlc_data

    def place_market_order(
        self, pair: str, side: Literal["buy", "sell"], volume: float, validate: bool = False
    ) -> Dict[str, Any]:
        """
        Place a market order.

        Args:
            pair: Trading pair (e.g., 'XMRUSD')
            side: Order side ('buy' or 'sell')
            volume: Order volume
            validate: If True, only validate the order without placing it

        Returns:
            Order response
        """
        params: Dict[str, Any] = {
            "pair": pair,
            "type": side,
            "ordertype": "market",
            "volume": str(volume),
        }

        if validate:
            params["validate"] = "true"

        response = self.api.query_private("AddOrder", params)  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        return response.get("result", {})  # type: ignore[return-value]

    def place_limit_order(
        self,
        pair: str,
        side: Literal["buy", "sell"],
        volume: float,
        price: float,
        validate: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a limit order.

        Args:
            pair: Trading pair (e.g., 'XMRUSD')
            side: Order side ('buy' or 'sell')
            volume: Order volume
            price: Limit price
            validate: If True, only validate the order without placing it

        Returns:
            Order response
        """
        params: Dict[str, Any] = {
            "pair": pair,
            "type": side,
            "ordertype": "limit",
            "volume": str(volume),
            "price": str(price),
        }

        if validate:
            params["validate"] = "true"

        response = self.api.query_private("AddOrder", params)  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        return response.get("result", {})  # type: ignore[return-value]

    def cancel_order(self, txid: str) -> Dict[str, Any]:
        """
        Cancel an open order.

        Args:
            txid: Transaction ID of the order to cancel

        Returns:
            Cancellation response
        """
        response = self.api.query_private("CancelOrder", {"txid": txid})  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        return response.get("result", {})  # type: ignore[return-value]

    def get_open_orders(self) -> Dict[str, Any]:
        """
        Get all open orders.

        Returns:
            Dictionary of open orders
        """
        response = self.api.query_private("OpenOrders")  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        return response.get("result", {}).get("open", {})  # type: ignore[return-value]

    def get_closed_orders(
        self, start: Optional[int] = None, end: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get closed orders.

        Args:
            start: Starting timestamp
            end: Ending timestamp

        Returns:
            Dictionary of closed orders
        """
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        response = self.api.query_private("ClosedOrders", params)  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        return response.get("result", {}).get("closed", {})  # type: ignore[return-value]

    def get_trades_history(
        self, start: Optional[int] = None, end: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get trade history.

        Args:
            start: Starting timestamp
            end: Ending timestamp

        Returns:
            Dictionary of trades
        """
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        response = self.api.query_private("TradesHistory", params)  # type: ignore[no-any-return]

        if response.get("error"):
            raise Exception(f"Kraken API error: {response['error']}")

        return response.get("result", {}).get("trades", {})  # type: ignore[return-value]
