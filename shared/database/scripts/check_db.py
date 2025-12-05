import logging
import os
import sys

# Add project root to sys.path to allow imports from shared
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

from shared.market_data.storage import MarketDataStorage  # noqa: E402

# Configure logging to suppress debug output
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

storage = MarketDataStorage()
stats = storage.get_stats()

print("\n" + "=" * 40)
print("DATABASE STATS")
print("=" * 40)
print(f"Quotes count: {stats['quotes_count']}")
print(f"OHLCV count:  {stats['ohlcv_count']}")
print(f"Symbols:      {stats['symbols_ohlcv']}")
print("=" * 40 + "\n")
