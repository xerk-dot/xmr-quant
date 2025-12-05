#!/usr/bin/env python3
"""
Backfill historical hourly data for all supported cryptocurrencies.
Fetches 5 years of hourly OHLCV data for BTC, LTC, XMR, and ZEC.
"""

import os
import sys

# Add project root to sys.path to allow imports from shared
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)


def main():
    print("=" * 60)
    print("XMR QUANT - BACKFILL HOURLY DATA (5 YEARS)")
    print("=" * 60)

    from shared.config import Config
    from shared.market_data.storage import MarketDataStorage

    storage = MarketDataStorage()
    print(f"✓ Connected to database: {storage.db.db_path}")

    symbols = Config.SUPPORTED_SYMBOLS  # BTC, XMR, ZEC, LTC
    print(f"\n📊 Fetching 5 years of hourly data for: {', '.join(symbols)}")
    print("⚠️  This may take several minutes...\n")

    # Backfill 5 years (1825 days) of hourly data
    results = storage.backfill_historical_data(symbols=symbols, days=1825)

    print("\n✓ Backfill complete!")
    for symbol, count in results.items():
        print(f"  - {symbol}: {count:,} records")

    # Show final stats
    stats = storage.get_stats()
    print("\n📈 Database Statistics:")
    print(f"  - Total quotes: {stats['quotes_count']:,}")
    print(f"  - Total OHLCV: {stats['ohlcv_count']:,}")
    print(f"  - Symbols (OHLCV): {', '.join(stats['symbols_ohlcv'])}")
    print(f"  - Symbols (Quotes): {', '.join(stats['symbols_quotes'])}")

    storage.close()
    print("\n" + "=" * 60)
    print("✓ Database ready with 5 years of hourly data!")
    print("=" * 60)


if __name__ == "__main__":
    main()
