"""
Darknet adoption monitoring strategy - EXPERIMENTAL / UNRELIABLE.

⚠️ WARNING: This strategy is:
- Experimental and unproven
- Requires Tor and manual .onion address maintenance
- Addresses change frequently
- Sites go offline regularly
- May provide minimal edge

Current Status: All .onion addresses are FAKE placeholders.

To enable:
1. Install Tor (brew install tor / apt install tor)
2. Get real .onion addresses from dark.fail
3. Edit marketplace_scraper.py MARKETPLACES dict
4. Set DARKNET_MONITORING_ENABLED=true in .env

Recommendation: Skip this unless you're experienced with Tor and darknet research.
"""

from .strategy import DarknetAdoptionStrategy
from .tor_client import TorClient
from .marketplace_scraper import MarketplaceScraper

__all__ = [
    'DarknetAdoptionStrategy',
    'TorClient',
    'MarketplaceScraper',
]
