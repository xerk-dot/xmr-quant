#!/usr/bin/env python3
"""
Setup and initialize the market data database.
Fetches initial data for all supported cryptocurrencies.
"""

import os
import sys

# Add project root to sys.path to allow imports from shared
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)


def main():
    print("=" * 60)
    print("XMR QUANT - DATABASE SETUP")
    print("=" * 60)

    # Initialize storage (creates database automatically)
    print("\n📦 Initializing database...")
    from shared.market_data.storage import MarketDataStorage

    storage = MarketDataStorage()
    print("✓ Database created at:", storage.db.db_path)

    # Collect initial data
    print("\n📊 Fetching initial data for BTC, XMR, ZEC, LTC...")
    print("This may take a minute...\n")

    results = storage.collect_daily_data()

    print("\n✓ Setup complete!")
    print(f"  - Quotes stored: {results['quotes']}")
    print(f"  - OHLCV records: {results['ohlcv']}")

    # Show stats
    stats = storage.get_stats()
    print("\n📈 Database Statistics:")
    print(f"  - Total quotes: {stats['quotes_count']:,}")
    print(f"  - Total OHLCV: {stats['ohlcv_count']:,}")
    print(f"  - Symbols: {', '.join(stats['symbols_quotes'])}")

    storage.close()
    print("\n" + "=" * 60)
    print("✓ Database ready to use!")
    print("=" * 60)


if __name__ == "__main__":
    main()
