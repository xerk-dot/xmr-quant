import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import logging
from .exchange_client import ExchangeClient
from config import config

logger = logging.getLogger(__name__)


class DataAggregator:
    def __init__(self, exchanges: Optional[List[str]] = None):
        self.exchanges = exchanges or ['binance', 'kraken']
        self.clients: Dict[str, ExchangeClient] = {}
        self._initialize_clients()

    def _initialize_clients(self):
        exchange_creds = config.exchange_credentials
        for exchange in self.exchanges:
            if exchange in exchange_creds:
                self.clients[exchange] = ExchangeClient(
                    exchange_name=exchange,
                    credentials=exchange_creds[exchange]
                )
            else:
                logger.warning(f"No credentials found for {exchange}, initializing without auth")
                self.clients[exchange] = ExchangeClient(exchange_name=exchange)

    async def connect_all(self):
        tasks = [client.connect() for client in self.clients.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Connected to all exchanges")

    async def disconnect_all(self):
        tasks = [client.disconnect() for client in self.clients.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Disconnected from all exchanges")

    async def fetch_aggregated_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        since: Optional[datetime] = None,
        limit: Optional[int] = 500
    ) -> pd.DataFrame:
        tasks = []
        for exchange_name, client in self.clients.items():
            tasks.append(
                self._fetch_with_exchange_name(
                    client.fetch_ohlcv(symbol, timeframe, since, limit),
                    exchange_name
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_dfs = []
        for result in results:
            if isinstance(result, pd.DataFrame):
                valid_dfs.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error fetching OHLCV data: {result}")

        if valid_dfs:
            aggregated_df = pd.concat(valid_dfs, ignore_index=True)
            aggregated_df = aggregated_df.sort_values('timestamp').reset_index(drop=True)
            return aggregated_df
        else:
            return pd.DataFrame()

    async def _fetch_with_exchange_name(self, coro, exchange_name: str):
        try:
            return await coro
        except Exception as e:
            logger.error(f"Error on {exchange_name}: {e}")
            raise

    async def fetch_best_bid_ask(self, symbol: str) -> Dict[str, Any]:
        tasks = []
        for exchange_name, client in self.clients.items():
            tasks.append(client.fetch_ticker(symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        best_bid = None
        best_ask = None
        best_bid_exchange = None
        best_ask_exchange = None

        for i, result in enumerate(results):
            if isinstance(result, dict):
                exchange = list(self.clients.keys())[i]

                if result.get('bid'):
                    if best_bid is None or result['bid'] > best_bid:
                        best_bid = result['bid']
                        best_bid_exchange = exchange

                if result.get('ask'):
                    if best_ask is None or result['ask'] < best_ask:
                        best_ask = result['ask']
                        best_ask_exchange = exchange

        return {
            'symbol': symbol,
            'best_bid': best_bid,
            'best_bid_exchange': best_bid_exchange,
            'best_ask': best_ask,
            'best_ask_exchange': best_ask_exchange,
            'spread': best_ask - best_bid if best_bid and best_ask else None,
            'timestamp': datetime.now()
        }

    async def fetch_aggregated_volume(self, symbol: str) -> Dict[str, float]:
        tasks = []
        for exchange_name, client in self.clients.items():
            tasks.append(client.fetch_ticker(symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        volume_by_exchange = {}
        total_volume = 0

        for i, result in enumerate(results):
            if isinstance(result, dict):
                exchange = list(self.clients.keys())[i]
                volume = result.get('volume', 0)
                volume_by_exchange[exchange] = volume
                total_volume += volume

        return {
            'symbol': symbol,
            'total_volume': total_volume,
            'volume_by_exchange': volume_by_exchange,
            'timestamp': datetime.now()
        }