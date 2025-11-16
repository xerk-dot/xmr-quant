"""
Core bot functionality - REQUIRED components.

This module contains the essential components needed to run the trading bot:
- Data aggregation from exchanges
- Feature engineering (technical indicators)
- Exchange client interface
"""

from .data_aggregator import DataAggregator
from .exchange_client import ExchangeClient
from .feature_engineering import FeatureEngineer
from .base import DataSource

__all__ = [
    'DataAggregator',
    'ExchangeClient',
    'FeatureEngineer',
    'DataSource',
]

