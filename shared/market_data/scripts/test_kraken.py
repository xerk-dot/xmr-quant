#!/usr/bin/env python3
"""Test CCXT connection to Kraken."""

import ccxt

try:
    print("Testing Kraken connection...")
    exchange = ccxt.kraken({"enableRateLimit": True})

    # Try to load markets
    print("Loading markets...")
    markets = exchange.load_markets()
    print(f"✓ Successfully loaded {len(markets)} markets")

    # Try to fetch a ticker
    print("\nFetching BTC/USD ticker...")
    ticker = exchange.fetch_ticker("BTC/USD")
    print(f"✓ BTC/USD price: ${ticker['last']:,.2f}")

    # Try to fetch OHLCV
    print("\nFetching recent OHLCV data...")
    ohlcv = exchange.fetch_ohlcv("BTC/USD", "1h", limit=5)
    print(f"✓ Fetched {len(ohlcv)} candles")

    print("\n✓ All tests passed! Kraken API is working.")

except Exception as e:
    print(f"\n✗ Error: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback

    traceback.print_exc()
