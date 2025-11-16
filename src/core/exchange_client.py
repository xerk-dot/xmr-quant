import ccxt
import asyncio
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from .base import DataSource

logger = logging.getLogger(__name__)


class ExchangeClient(DataSource):
    def __init__(self, exchange_name: str, credentials: Optional[Dict[str, str]] = None):
        self.exchange_name = exchange_name
        self.credentials = credentials or {}
        self.exchange = None
        self._initialize_exchange()

    def _initialize_exchange(self):
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange = exchange_class({
            **self.credentials,
            'enableRateLimit': True,
            'timeout': 30000,
        })

    async def connect(self) -> None:
        try:
            await self.exchange.load_markets()
            logger.info(f"Connected to {self.exchange_name}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.exchange_name}: {e}")
            raise

    async def disconnect(self) -> None:
        if self.exchange:
            await self.exchange.close()
            logger.info(f"Disconnected from {self.exchange_name}")

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        since: Optional[datetime] = None,
        limit: Optional[int] = 500
    ) -> pd.DataFrame:
        try:
            since_ms = int(since.timestamp() * 1000) if since else None
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since_ms,
                limit=limit
            )

            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df['timeframe'] = timeframe
            df['exchange'] = self.exchange_name

            return df

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            raise

    async def fetch_order_book(
        self,
        symbol: str,
        limit: Optional[int] = 20
    ) -> Dict[str, Any]:
        try:
            order_book = await self.exchange.fetch_order_book(symbol, limit)
            return {
                'bids': order_book['bids'],
                'asks': order_book['asks'],
                'timestamp': order_book['timestamp'],
                'datetime': order_book['datetime'],
                'symbol': symbol,
                'exchange': self.exchange_name
            }
        except Exception as e:
            logger.error(f"Failed to fetch order book: {e}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'exchange': self.exchange_name,
                'timestamp': ticker['timestamp'],
                'datetime': ticker['datetime'],
                'high': ticker['high'],
                'low': ticker['low'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'close': ticker['close'],
                'volume': ticker['baseVolume'],
                'quote_volume': ticker['quoteVolume']
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticker: {e}")
            raise

    async def fetch_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        try:
            since_ms = int(since.timestamp() * 1000) if since else None
            trades = await self.exchange.fetch_trades(symbol, since_ms, limit)

            return [
                {
                    'id': trade['id'],
                    'timestamp': trade['timestamp'],
                    'datetime': trade['datetime'],
                    'symbol': symbol,
                    'type': trade['type'],
                    'side': trade['side'],
                    'price': trade['price'],
                    'amount': trade['amount'],
                    'cost': trade['cost'],
                    'exchange': self.exchange_name
                }
                for trade in trades
            ]
        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            raise