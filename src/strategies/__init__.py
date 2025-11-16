"""
Trading strategies module.

Organized into:
- core/         - Required strategies (BTC correlation, trend, mean reversion)
- ml/           - ML-based strategies (optional but recommended)
- news/         - News sentiment strategies (optional, requires APIs)
- experimental/ - Experimental strategies (darknet monitoring)
"""

from .base import BaseStrategy, Signal, SignalType
from .aggregator import SignalAggregator

# Core strategies (REQUIRED)
from .core.btc_correlation import BTCCorrelationStrategy
from .core.trend_following import TrendFollowingStrategy, MeanReversionStrategy

__all__ = [
    # Base classes
    'BaseStrategy',
    'Signal',
    'SignalType',
    'SignalAggregator',
    
    # Core strategies
    'BTCCorrelationStrategy',
    'TrendFollowingStrategy',
    'MeanReversionStrategy',
]

# Optional strategies (imported only if dependencies available)
def get_ml_strategies():
    """Get ML strategies if available."""
    try:
        from .ml.xgboost_strategy import XGBoostTradingStrategy
        from .ml.manager import MLModelManager
        return {'XGBoostTradingStrategy': XGBoostTradingStrategy, 'MLModelManager': MLModelManager}
    except ImportError as e:
        return {}

def get_news_strategies():
    """Get news strategies if available."""
    try:
        from .news.strategy import NewsSentimentStrategy
        return {'NewsSentimentStrategy': NewsSentimentStrategy}
    except ImportError:
        return {}

def get_experimental_strategies():
    """Get experimental strategies if available."""
    try:
        from .experimental.darknet.strategy import DarknetAdoptionStrategy
        return {'DarknetAdoptionStrategy': DarknetAdoptionStrategy}
    except ImportError:
        return {}

