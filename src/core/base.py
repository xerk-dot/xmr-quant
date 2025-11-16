from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd


class DataSource(ABC):
    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    async def fetch_order_book(
        self,
        symbol: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        pass


class MarketData:
    def __init__(
        self,
        timestamp: datetime,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        symbol: str,
        timeframe: str,
        exchange: Optional[str] = None
    ):
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = exchange

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "exchange": self.exchange
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketData":
        return cls(**data)