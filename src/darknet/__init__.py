"""
Darknet marketplace monitoring module.

Tracks cryptocurrency adoption rates (BTC vs XMR) on darknet marketplaces
as a sentiment indicator for privacy coin demand.

LEGAL DISCLAIMER:
This module is for market research and analysis purposes only.
It scrapes only publicly available statistics (similar to analyzing
exchange volumes or on-chain metrics). DO NOT use for illegal purposes.
"""

from .tor_client import TorClient
from .marketplace_scraper import MarketplaceScraper
from .darknet_adoption_strategy import DarknetAdoptionStrategy

__all__ = [
    'TorClient',
    'MarketplaceScraper',
    'DarknetAdoptionStrategy'
]

