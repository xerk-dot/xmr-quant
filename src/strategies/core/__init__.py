"""
Core trading strategies - REQUIRED.

These strategies form the foundation of the bot:
- BTCCorrelationStrategy (40% weight) - Primary edge, exploits BTC-XMR lag
- TrendFollowingStrategy (12.5% weight) - EMA crossovers with ADX confirmation
- MeanReversionStrategy (12.5% weight) - RSI + Bollinger Bands in ranging markets
"""

from .btc_correlation import BTCCorrelationStrategy
from .trend_following import TrendFollowingStrategy, MeanReversionStrategy

__all__ = [
    'BTCCorrelationStrategy',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
]

