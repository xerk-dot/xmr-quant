"""
Test script for darknet marketplace monitoring.

IMPORTANT SETUP REQUIREMENTS:
1. Install Tor Browser or Tor daemon
2. Start Tor (Tor Browser or `tor` command)
3. Configure marketplace addresses in marketplace_scraper.py
4. Install dependencies: pip install requests[socks] beautifulsoup4 aiohttp-socks

LEGAL DISCLAIMER:
This script scrapes only publicly available statistics from marketplace
stat pages for market research purposes. No illegal activity is facilitated.
"""

import asyncio
import logging
from datetime import datetime

from src.darknet.tor_client import TorClient
from src.darknet.marketplace_scraper import MarketplaceScraper
from src.darknet.darknet_adoption_strategy import DarknetAdoptionStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_tor_connection():
    """Test basic Tor connectivity."""
    print("=" * 70)
    print("TEST 1: Tor Connection")
    print("=" * 70)
    
    # Initialize Tor client
    # Port 9050 for system tor, 9150 for Tor Browser
    tor_client = TorClient(tor_proxy_host='127.0.0.1', tor_proxy_port=9050)
    
    print("\nAttempting to connect to Tor network...")
    print("(Make sure Tor is running: `tor` or Tor Browser)")
    
    connected = tor_client.connect()
    
    if connected:
        print("✅ Successfully connected to Tor network!")
        
        # Test connection details
        test_result = tor_client.test_connection()
        print(f"\nConnection Details:")
        print(f"  Using Tor: {test_result.get('using_tor')}")
        print(f"  Exit IP: {test_result.get('ip')}")
        print(f"  Timestamp: {test_result.get('timestamp')}")
        
        tor_client.disconnect()
        return True
    else:
        print("❌ Failed to connect to Tor network")
        print("\nTroubleshooting:")
        print("  1. Is Tor running? Try: `tor` or open Tor Browser")
        print("  2. Check proxy port (9050 for system tor, 9150 for Tor Browser)")
        print("  3. Install tor: `brew install tor` (macOS) or `apt install tor` (Linux)")
        return False


def test_marketplace_scraping():
    """Test marketplace scraping (requires valid onion addresses)."""
    print("\n" + "=" * 70)
    print("TEST 2: Marketplace Scraping")
    print("=" * 70)
    
    tor_client = TorClient()
    
    if not tor_client.connect():
        print("❌ Cannot proceed without Tor connection")
        return False
    
    try:
        scraper = MarketplaceScraper(tor_client)
        
        # Check configured marketplaces
        enabled_markets = [
            name for name, config in scraper.MARKETPLACES.items()
            if config.get('enabled', False)
        ]
        
        if not enabled_markets:
            print("\n⚠️  No marketplaces are enabled")
            print("\nTo enable marketplace scraping:")
            print("  1. Edit src/darknet/marketplace_scraper.py")
            print("  2. Add valid .onion addresses to MARKETPLACES dict")
            print("  3. Set 'enabled': True for each marketplace")
            print("\nNote: Marketplace addresses must be sourced from")
            print("      darknet directories like dark.fail or dread")
            return False
        
        print(f"\nEnabled marketplaces: {len(enabled_markets)}")
        for market in enabled_markets:
            print(f"  - {market}")
        
        print("\nScraping marketplaces (this may take a while)...")
        results = scraper.scrape_all_marketplaces(limit=3)
        
        if results:
            print(f"\n✅ Successfully scraped {len(results)} marketplace(s)")
            
            # Show results
            for result in results:
                print(f"\n{result['marketplace']}:")
                print(f"  BTC: {result.get('btc_percentage', 0):.1f}%")
                print(f"  XMR: {result.get('xmr_percentage', 0):.1f}%")
                print(f"  Method: {result.get('extraction_method', 'unknown')}")
            
            # Calculate aggregate
            aggregate = scraper.calculate_aggregate_stats(results)
            print(f"\n📊 Aggregate Statistics:")
            print(f"  XMR Adoption: {aggregate.get('xmr_percentage', 0):.1f}%")
            print(f"  BTC Dominance: {aggregate.get('btc_percentage', 0):.1f}%")
            print(f"  Confidence: {aggregate.get('confidence', 0):.2f}")
            print(f"  Trend: {aggregate.get('xmr_adoption_trend', 'unknown')}")
            
            return True
        else:
            print("❌ No data collected from marketplaces")
            print("\nPossible issues:")
            print("  - Invalid onion addresses")
            print("  - Marketplaces are offline")
            print("  - Stats page structure has changed")
            return False
            
    finally:
        tor_client.disconnect()


async def test_strategy():
    """Test the trading strategy based on adoption data."""
    print("\n" + "=" * 70)
    print("TEST 3: Trading Strategy")
    print("=" * 70)
    
    tor_client = TorClient()
    
    if not tor_client.connect():
        print("❌ Cannot proceed without Tor connection")
        return False
    
    try:
        scraper = MarketplaceScraper(tor_client)
        strategy = DarknetAdoptionStrategy(scraper)
        
        print("\nStrategy configuration:")
        print(f"  Bullish threshold: {strategy.params['bullish_threshold']}% XMR")
        print(f"  Bearish threshold: {strategy.params['bearish_threshold']}% XMR")
        print(f"  Min confidence: {strategy.params['min_confidence']}")
        
        # Update adoption data
        print("\nUpdating adoption data...")
        success = await strategy.update_adoption_data()
        
        if not success:
            print("❌ Failed to update adoption data")
            return False
        
        print("✅ Adoption data updated")
        
        # Get report
        report = strategy.get_adoption_report()
        
        if report['status'] == 'ok':
            print(f"\n📊 Adoption Report:")
            print(f"  XMR: {report['current_adoption']['xmr_percentage']:.1f}%")
            print(f"  BTC: {report['current_adoption']['btc_percentage']:.1f}%")
            print(f"  Trend: {report['current_adoption']['trend']}")
            print(f"  Signal Zone: {report['signal_status']['current_zone']}")
            print(f"  Data Confidence: {report['data_quality']['confidence']:.2f}")
            print(f"  Marketplaces: {report['data_quality']['marketplaces_count']}")
        
        # Generate trading signal
        import pandas as pd
        dummy_df = pd.DataFrame({'close': [100]})  # Dummy price data
        
        signal = strategy.generate_signal(dummy_df)
        
        if signal:
            print(f"\n💡 Trading Signal Generated:")
            print(f"  Type: {signal.signal_type.value.upper()}")
            print(f"  Strength: {signal.strength:.2%}")
            print(f"  Confidence: {signal.confidence:.2%}")
            print(f"  XMR Adoption: {signal.metadata['xmr_percentage']:.1f}%")
            print(f"  Trend: {signal.metadata['adoption_trend']}")
            return True
        else:
            print("\nℹ️  No signal generated (neutral zone or low confidence)")
            return True
            
    finally:
        tor_client.disconnect()


def print_setup_instructions():
    """Print setup instructions."""
    print("\n" + "=" * 70)
    print("SETUP INSTRUCTIONS")
    print("=" * 70)
    print("\n1. Install Tor:")
    print("   macOS: brew install tor")
    print("   Linux: apt install tor")
    print("   Windows: Download Tor Browser from torproject.org")
    
    print("\n2. Start Tor:")
    print("   System tor: tor")
    print("   Tor Browser: Just open the application")
    
    print("\n3. Install Python dependencies:")
    print("   pip install requests[socks] beautifulsoup4 aiohttp-socks")
    
    print("\n4. Configure marketplace addresses:")
    print("   Edit: src/darknet/marketplace_scraper.py")
    print("   Add valid .onion addresses and set enabled=True")
    
    print("\n5. Source marketplace addresses from:")
    print("   - dark.fail (Tor link directory)")
    print("   - Dread (darknet forum)")
    print("   - Other verified darknet directories")
    
    print("\nREMINDER: This is for market research only!")
    print("=" * 70)


async def main():
    """Run all tests."""
    print("\n🧅 Darknet Marketplace Monitoring Test Suite")
    print_setup_instructions()
    
    input("\nPress Enter to begin tests (make sure Tor is running)...")
    
    # Test 1: Tor connection
    if not test_tor_connection():
        print("\n❌ Tests aborted - fix Tor connection first")
        return
    
    # Test 2: Marketplace scraping
    print("\n⚠️  Marketplace scraping requires valid .onion addresses")
    choice = input("Have you configured marketplace addresses? (y/n): ")
    
    if choice.lower() == 'y':
        test_marketplace_scraping()
        await test_strategy()
    else:
        print("\nSkipping marketplace tests")
        print("Configure addresses in src/darknet/marketplace_scraper.py first")
    
    print("\n" + "=" * 70)
    print("Tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
