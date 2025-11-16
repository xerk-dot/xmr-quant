"""
Machine Learning strategies - OPTIONAL (but recommended).

These strategies use XGBoost models for:
- Regime detection (25% weight) - Market classification and signal filtering
- Volatility prediction - Position sizing adjustments
- Signal quality filtering - Reduces false signals

Models auto-train on first run (takes 1-2 hours).
"""

from .xgboost_strategy import XGBoostTradingStrategy
from .manager import MLModelManager
from .models import (
    XGBoostVolatilityPredictor,
    XGBoostSignalFilter,
    XGBoostExitOptimizer
)

__all__ = [
    'XGBoostTradingStrategy',
    'MLModelManager',
    'XGBoostVolatilityPredictor',
    'XGBoostSignalFilter',
    'XGBoostExitOptimizer',
]

