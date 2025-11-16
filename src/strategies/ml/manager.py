import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from .ml_strategy import XGBoostTradingStrategy
from .ml_models import XGBoostVolatilityPredictor, XGBoostSignalFilter, XGBoostExitOptimizer
from .base_strategy import Signal, SignalType

logger = logging.getLogger(__name__)


class MLModelManager:
    """Coordinates multiple XGBoost models for comprehensive trading intelligence"""

    def __init__(self, enable_all_models: bool = True):
        # Initialize all ML models
        self.regime_detector = XGBoostTradingStrategy()

        if enable_all_models:
            self.volatility_predictor = XGBoostVolatilityPredictor()
            self.signal_filter = XGBoostSignalFilter()
            self.exit_optimizer = XGBoostExitOptimizer()
        else:
            self.volatility_predictor = None
            self.signal_filter = None
            self.exit_optimizer = None

        self.last_regime = None
        self.last_volatility = None

    def analyze_market_state(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get comprehensive market analysis from all models"""
        analysis = {
            'timestamp': datetime.now(),
            'regime': None,
            'volatility_forecast': None,
            'market_risk': 'normal'
        }

        # 1. Detect current regime
        regime_result = self.regime_detector.predict_regime(df)
        if regime_result:
            analysis['regime'] = regime_result['regime']
            analysis['regime_confidence'] = regime_result['confidence']
            self.last_regime = regime_result['regime']

        # 2. Predict future volatility
        if self.volatility_predictor:
            vol_result = self.volatility_predictor.predict(df)
            if vol_result:
                analysis['volatility_forecast'] = vol_result['volatility_level']
                analysis['volatility_confidence'] = vol_result['confidence']
                self.last_volatility = vol_result['volatility_level']

                # Set market risk based on volatility
                if vol_result['volatility_level'] in ['high', 'extreme']:
                    analysis['market_risk'] = 'high'
                elif vol_result['volatility_level'] == 'low':
                    analysis['market_risk'] = 'low'

        return analysis

    def generate_enhanced_signal(self, df: pd.DataFrame, base_signal: Optional[Signal] = None) -> Optional[Signal]:
        """Generate signal with ML enhancement and filtering"""

        # Get market state analysis
        market_state = self.analyze_market_state(df)

        # 1. Generate base signal from regime detector
        if base_signal is None:
            base_signal = self.regime_detector.generate_signal(df)

        if base_signal is None:
            return None

        # 2. Filter signal quality
        enhanced_signal = self._enhance_signal_with_ml(base_signal, df, market_state)

        return enhanced_signal

    def _enhance_signal_with_ml(self, signal: Signal, df: pd.DataFrame, market_state: Dict[str, Any]) -> Optional[Signal]:
        """Enhance signal using ML models"""

        # Start with base signal
        enhanced_strength = signal.strength
        enhanced_confidence = signal.confidence

        # 1. Volatility-based position sizing adjustment
        if market_state.get('volatility_forecast'):
            vol_level = market_state['volatility_forecast']

            if vol_level == 'extreme':
                enhanced_strength *= 0.3  # Drastically reduce size
                logger.info("Extreme volatility detected - reducing position size")
            elif vol_level == 'high':
                enhanced_strength *= 0.6  # Reduce size
            elif vol_level == 'low':
                enhanced_strength *= 1.2  # Increase size (but cap at 1.0)

            enhanced_strength = min(enhanced_strength, 1.0)

        # 2. Signal quality filter
        if self.signal_filter:
            latest = df.iloc[-1]
            signal_context = {
                'volume_ratio': latest.get('volume_ratio', 1.0),
                'atr': latest.get('atr', 0.02),
                'adx': latest.get('adx', 25),
                'bb_pct': latest.get('bb_pct', 0.5),
                'trend_strength': latest.get('trend_strength', 0.02),
                'rsi': latest.get('rsi', 50),
                'macd': latest.get('macd', 0),
                'stoch_k': latest.get('stoch_k', 50)
            }

            signal_quality = self.signal_filter.evaluate_signal(df, signal_context)

            # If signal quality is poor, reject it
            if signal_quality < 0.4:
                logger.info(f"Signal rejected due to poor quality: {signal_quality:.2f}")
                return None

            # Adjust confidence based on signal quality
            enhanced_confidence *= signal_quality

        # 3. Regime-specific adjustments
        regime = market_state.get('regime')
        if regime == 'high_volatility':
            # In high volatility, be extra cautious
            enhanced_strength *= 0.5
            enhanced_confidence *= 0.7
        elif regime == 'ranging' and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
            # In ranging market, mean reversion signals are more reliable
            enhanced_confidence *= 1.1

        # Final quality check
        if enhanced_confidence < 0.3 or enhanced_strength < 0.2:
            logger.info("Signal rejected after ML enhancement - insufficient confidence/strength")
            return None

        # Create enhanced signal
        enhanced_signal = Signal(
            signal_type=signal.signal_type,
            strength=enhanced_strength,
            confidence=enhanced_confidence,
            strategy_name="MLEnhanced",
            timestamp=signal.timestamp,
            metadata={
                **signal.metadata,
                'original_strength': signal.strength,
                'original_confidence': signal.confidence,
                'market_regime': regime,
                'volatility_forecast': market_state.get('volatility_forecast'),
                'ml_enhanced': True
            }
        )

        return enhanced_signal

    def should_exit_position(self, position_context: Dict[str, Any]) -> str:
        """Determine if position should be exited using ML"""

        if self.exit_optimizer is None:
            return "hold"

        # Add regime context to position analysis
        position_context['current_regime'] = self.last_regime
        position_context['volatility_forecast'] = self.last_volatility

        exit_signal = self.exit_optimizer.should_exit(position_context)

        # Override with regime-specific logic
        if self.last_regime == 'high_volatility':
            # In high vol, exit quickly on any profit
            if position_context.get('unrealized_pnl_pct', 0) > 0.5:
                return "exit_profit"

        return exit_signal

    def get_position_sizing_multiplier(self, base_size: float) -> float:
        """Adjust position size based on ML predictions"""
        multiplier = 1.0

        # Volatility-based sizing
        if self.last_volatility == 'extreme':
            multiplier *= 0.3
        elif self.last_volatility == 'high':
            multiplier *= 0.6
        elif self.last_volatility == 'low':
            multiplier *= 1.2

        # Regime-based sizing
        if self.last_regime == 'high_volatility':
            multiplier *= 0.5
        elif self.last_regime == 'trending_up' or self.last_regime == 'trending_down':
            multiplier *= 1.1  # Slightly larger positions in trending markets

        return min(multiplier, 2.0)  # Cap at 2x base size

    def train_all_models(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train all ML models with new data"""
        results = {}

        # Train regime detector
        regime_result = self.regime_detector.train_model(df)
        results['regime_detector'] = regime_result

        # Train volatility predictor
        if self.volatility_predictor:
            vol_result = self.volatility_predictor.train_model(df)
            results['volatility_predictor'] = vol_result

        # Note: Signal filter and exit optimizer need specific training data
        # which would come from actual trading history, not just price data

        logger.info(f"ML model training results: {results}")
        return results

    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all ML models"""
        status = {
            'regime_detector': self.regime_detector.model is not None,
            'volatility_predictor': self.volatility_predictor.model is not None if self.volatility_predictor else False,
            'signal_filter': self.signal_filter.model is not None if self.signal_filter else False,
            'exit_optimizer': self.exit_optimizer.model is not None if self.exit_optimizer else False,
            'last_regime': self.last_regime,
            'last_volatility': self.last_volatility
        }
        return status

    def retrain_if_needed(self, df: pd.DataFrame) -> Dict[str, bool]:
        """Check and retrain models if necessary"""
        retrain_results = {}

        # Check regime detector
        if self.regime_detector.should_retrain():
            logger.info("Retraining regime detector...")
            result = self.regime_detector.train_model(df)
            retrain_results['regime_detector'] = result.get('success', False)

        # Check volatility predictor
        # (Add similar retraining logic for other models)

        return retrain_results