"""
BTC-XMR Correlation Lag Strategy

Exploits the observed lag between BTC and XMR price movements.
XMR typically follows BTC with a 6-24 hour delay, providing a leading indicator.

Key Insights from CLAUDE.md:
- XMR often lags BTC movements by hours/days
- Lower liquidity means slower price discovery
- Retail-heavy market = delayed reaction to BTC moves
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from .base_strategy import BaseStrategy, Signal, SignalType
import logging

logger = logging.getLogger(__name__)


class BTCCorrelationStrategy(BaseStrategy):
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            # BTC movement thresholds
            'btc_move_threshold': 0.03,  # 3% move in BTC triggers signal
            'strong_btc_move': 0.05,     # 5% move = high confidence
            
            # Time windows for detecting BTC moves
            'short_window_hours': 4,     # Short-term moves
            'medium_window_hours': 12,   # Medium-term moves
            'long_window_hours': 24,     # Longer-term trend
            
            # Expected lag parameters
            'expected_lag_hours': 8,     # Average observed lag
            'max_lag_hours': 24,         # Max time to wait for XMR follow
            
            # Correlation parameters
            'min_correlation': 0.6,      # Minimum required correlation
            'lookback_days': 14,         # Days for correlation calculation
            
            # Volume confirmation
            'volume_multiplier': 1.3,    # BTC volume should be elevated
            
            # Signal decay
            'signal_half_life_hours': 6, # Signal strength decays over time
        }
        if params:
            default_params.update(params)
        super().__init__("BTCCorrelation", default_params)
        
        self.btc_data = None
        self.last_btc_signal = None
        self.last_btc_signal_time = None
        self.correlation_history = []
        
    def set_btc_data(self, btc_df: pd.DataFrame):
        """Set BTC price data for comparison"""
        self.btc_data = btc_df.copy()
        
    def calculate_correlation(self, xmr_df: pd.DataFrame, btc_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate rolling correlation and optimal lag between BTC and XMR"""
        if len(xmr_df) < 24 or len(btc_df) < 24:
            return {'correlation': 0.0, 'optimal_lag': 0}
        
        # Align dataframes by timestamp
        xmr_returns = xmr_df.set_index('timestamp')['close'].pct_change()
        btc_returns = btc_df.set_index('timestamp')['close'].pct_change()
        
        # Find optimal lag (in hours) by testing different lags
        max_correlation = 0
        optimal_lag = 0
        
        for lag in range(0, 25):  # Test 0-24 hour lags
            try:
                if lag == 0:
                    corr = xmr_returns.corr(btc_returns)
                else:
                    # Shift XMR returns forward to test if it lags BTC
                    shifted_xmr = xmr_returns.shift(-lag)
                    corr = shifted_xmr.corr(btc_returns)
                
                if not np.isnan(corr) and abs(corr) > abs(max_correlation):
                    max_correlation = corr
                    optimal_lag = lag
            except Exception as e:
                logger.debug(f"Error calculating lag {lag}: {e}")
                continue
        
        return {
            'correlation': max_correlation,
            'optimal_lag': optimal_lag
        }
    
    def detect_btc_move(self, btc_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Detect significant BTC price movements"""
        if len(btc_df) < 24:
            return None
        
        latest_price = btc_df['close'].iloc[-1]
        
        moves = {}
        for window_name, hours in [
            ('short', self.params['short_window_hours']),
            ('medium', self.params['medium_window_hours']),
            ('long', self.params['long_window_hours'])
        ]:
            if len(btc_df) >= hours:
                past_price = btc_df['close'].iloc[-hours]
                pct_change = (latest_price - past_price) / past_price
                moves[window_name] = {
                    'pct_change': pct_change,
                    'hours': hours,
                    'significant': abs(pct_change) >= self.params['btc_move_threshold']
                }
        
        # Check if any window shows significant move
        significant_moves = [m for m in moves.values() if m['significant']]
        
        if not significant_moves:
            return None
        
        # Get the strongest move
        strongest = max(significant_moves, key=lambda x: abs(x['pct_change']))
        
        # Volume confirmation
        latest_volume = btc_df['volume'].iloc[-1]
        avg_volume = btc_df['volume'].tail(24).mean()
        volume_confirmed = latest_volume > avg_volume * self.params['volume_multiplier']
        
        return {
            'direction': 'up' if strongest['pct_change'] > 0 else 'down',
            'magnitude': abs(strongest['pct_change']),
            'window': strongest['hours'],
            'volume_confirmed': volume_confirmed,
            'all_moves': moves,
            'timestamp': datetime.now()
        }
    
    def calculate_signal_decay(self) -> float:
        """Calculate how much the signal has decayed since BTC move"""
        if not self.last_btc_signal_time:
            return 0.0
        
        hours_elapsed = (datetime.now() - self.last_btc_signal_time).total_seconds() / 3600
        
        # Exponential decay with half-life
        half_life = self.params['signal_half_life_hours']
        decay_factor = np.exp(-np.log(2) * hours_elapsed / half_life)
        
        # Signal expires after max_lag_hours
        if hours_elapsed > self.params['max_lag_hours']:
            return 0.0
        
        return decay_factor
    
    def generate_signal(self, xmr_df: pd.DataFrame) -> Optional[Signal]:
        """Generate XMR trading signal based on BTC movements"""
        if self.btc_data is None or len(self.btc_data) < 24:
            logger.warning("BTC data not available for correlation strategy")
            return None
        
        if len(xmr_df) < 24:
            return None
        
        # Calculate correlation
        corr_stats = self.calculate_correlation(xmr_df, self.btc_data)
        
        if abs(corr_stats['correlation']) < self.params['min_correlation']:
            logger.debug(f"Correlation too low: {corr_stats['correlation']:.2f}")
            return None
        
        # Detect BTC move
        btc_move = self.detect_btc_move(self.btc_data)
        
        if btc_move and btc_move['magnitude'] >= self.params['btc_move_threshold']:
            # New BTC signal detected
            self.last_btc_signal = btc_move
            self.last_btc_signal_time = btc_move['timestamp']
            
            logger.info(f"BTC {btc_move['direction']} move detected: {btc_move['magnitude']:.2%} "
                       f"over {btc_move['window']}h, volume_confirmed={btc_move['volume_confirmed']}")
        
        # Check if we have an active BTC signal to follow
        if not self.last_btc_signal:
            return None
        
        decay_factor = self.calculate_signal_decay()
        
        if decay_factor < 0.1:  # Signal too old
            logger.debug("BTC signal expired")
            self.last_btc_signal = None
            self.last_btc_signal_time = None
            return None
        
        # Check if XMR has already moved (signal may be late)
        xmr_latest = xmr_df['close'].iloc[-1]
        xmr_past = xmr_df['close'].iloc[-4]  # 4 hours ago
        xmr_move = (xmr_latest - xmr_past) / xmr_past
        
        # If XMR already moved significantly in BTC's direction, we might be late
        same_direction = (
            (self.last_btc_signal['direction'] == 'up' and xmr_move > 0.02) or
            (self.last_btc_signal['direction'] == 'down' and xmr_move < -0.02)
        )
        
        if same_direction:
            logger.debug("XMR already moved - signal may be late")
            # Reduce confidence but don't eliminate signal
            lateness_penalty = 0.5
        else:
            lateness_penalty = 1.0
        
        # Generate signal
        signal_type = SignalType.BUY if self.last_btc_signal['direction'] == 'up' else SignalType.SELL
        
        strength = self.calculate_signal_strength(xmr_df)
        confidence = self.calculate_confidence(xmr_df) * decay_factor * lateness_penalty
        
        return Signal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            strategy_name=self.name,
            timestamp=pd.Timestamp.now(),
            metadata={
                'btc_move': self.last_btc_signal['magnitude'],
                'btc_direction': self.last_btc_signal['direction'],
                'btc_window_hours': self.last_btc_signal['window'],
                'correlation': corr_stats['correlation'],
                'optimal_lag': corr_stats['optimal_lag'],
                'decay_factor': decay_factor,
                'hours_since_btc_move': (datetime.now() - self.last_btc_signal_time).total_seconds() / 3600,
                'volume_confirmed': self.last_btc_signal['volume_confirmed'],
                'lateness_penalty': lateness_penalty,
                'xmr_move_4h': xmr_move
            }
        )
    
    def validate_signal(self, signal: Signal, df: pd.DataFrame) -> bool:
        """Validate that signal is still relevant"""
        if not signal.metadata:
            return False
        
        # Check correlation is still good
        if abs(signal.metadata.get('correlation', 0)) < self.params['min_correlation']:
            return False
        
        # Check signal hasn't expired
        hours_since = signal.metadata.get('hours_since_btc_move', 0)
        if hours_since > self.params['max_lag_hours']:
            return False
        
        # Check XMR hasn't moved too much already
        lateness_penalty = signal.metadata.get('lateness_penalty', 1.0)
        if lateness_penalty < 0.3:
            return False
        
        return True
    
    def calculate_signal_strength(self, xmr_df: pd.DataFrame) -> float:
        """Calculate signal strength based on BTC move magnitude and confirmation"""
        if not self.last_btc_signal:
            return 0.0
        
        # Magnitude component (0 to 1)
        magnitude = self.last_btc_signal['magnitude']
        magnitude_score = min(magnitude / self.params['strong_btc_move'], 1.0)
        
        # Volume confirmation component
        volume_score = 1.0 if self.last_btc_signal['volume_confirmed'] else 0.6
        
        # Multi-window confirmation (stronger if multiple timeframes agree)
        moves = self.last_btc_signal.get('all_moves', {})
        direction = self.last_btc_signal['direction']
        agreeing_windows = sum(
            1 for move in moves.values()
            if (direction == 'up' and move['pct_change'] > 0) or
               (direction == 'down' and move['pct_change'] < 0)
        )
        multi_window_score = agreeing_windows / len(moves) if moves else 0.5
        
        # Combined strength
        strength = (
            magnitude_score * 0.5 +
            volume_score * 0.3 +
            multi_window_score * 0.2
        )
        
        return min(strength, 1.0)
    
    def calculate_confidence(self, xmr_df: pd.DataFrame) -> float:
        """Calculate confidence based on historical correlation and market conditions"""
        if self.btc_data is None or len(self.btc_data) < 24:
            return 0.0
        
        # Correlation strength
        corr_stats = self.calculate_correlation(xmr_df, self.btc_data)
        correlation_confidence = abs(corr_stats['correlation'])
        
        # Lag consistency (if optimal lag matches our expected lag, higher confidence)
        expected_lag = self.params['expected_lag_hours']
        actual_lag = corr_stats['optimal_lag']
        lag_diff = abs(expected_lag - actual_lag)
        lag_confidence = max(0, 1 - lag_diff / 12)  # Penalty for lag difference
        
        # Market conditions (prefer lower XMR volatility for cleaner signal)
        latest = xmr_df.iloc[-1]
        atr = latest.get('atr', 0)
        volatility_confidence = 1 - min(atr / latest['close'] * 50, 1.0)
        
        # Check if XMR and BTC are currently aligned in trend
        xmr_trend = xmr_df['close'].iloc[-1] > xmr_df['close'].iloc[-24]
        btc_trend = self.btc_data['close'].iloc[-1] > self.btc_data['close'].iloc[-24]
        trend_aligned = xmr_trend == btc_trend
        alignment_confidence = 1.0 if trend_aligned else 0.7
        
        # Combined confidence
        confidence = (
            correlation_confidence * 0.4 +
            lag_confidence * 0.2 +
            volatility_confidence * 0.2 +
            alignment_confidence * 0.2
        )
        
        return min(confidence, 1.0)
    
    def get_correlation_report(self, xmr_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate a detailed correlation report for analysis"""
        if self.btc_data is None:
            return {}
        
        corr_stats = self.calculate_correlation(xmr_df, self.btc_data)
        btc_move = self.detect_btc_move(self.btc_data)
        
        return {
            'correlation': corr_stats['correlation'],
            'optimal_lag_hours': corr_stats['optimal_lag'],
            'current_btc_move': btc_move,
            'active_signal': self.last_btc_signal,
            'signal_age_hours': (datetime.now() - self.last_btc_signal_time).total_seconds() / 3600 
                if self.last_btc_signal_time else None,
            'signal_decay': self.calculate_signal_decay(),
            'timestamp': datetime.now()
        }

