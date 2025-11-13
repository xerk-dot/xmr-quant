"""
Darknet adoption trading strategy.

Generates trading signals based on Monero adoption rates in darknet markets.

Thesis:
- Higher XMR adoption on darknet = increased privacy demand = bullish for XMR
- Trend changes in adoption indicate shifting privacy preferences
- This is a unique, underutilized signal not available from traditional sources

Signal Logic:
- XMR adoption >60%: Bullish (high privacy demand)
- XMR adoption increasing trend: Additional bullish signal
- BTC dominance >80%: Bearish for XMR
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from src.signals.base_strategy import BaseStrategy, Signal, SignalType
from .marketplace_scraper import MarketplaceScraper

logger = logging.getLogger(__name__)


class DarknetAdoptionStrategy(BaseStrategy):
    """
    Trading strategy based on darknet marketplace crypto adoption rates.
    
    Monitors XMR vs BTC usage as privacy demand indicator.
    """
    
    def __init__(
        self,
        marketplace_scraper: MarketplaceScraper,
        bullish_threshold: float = 60.0,  # XMR% for bullish signal
        bearish_threshold: float = 35.0,  # XMR% for bearish signal
        min_confidence: float = 0.5,      # Minimum data confidence
        update_interval_hours: int = 24,  # How often to scrape
        params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize darknet adoption strategy.
        
        Args:
            marketplace_scraper: MarketplaceScraper instance
            bullish_threshold: XMR adoption % above which signal is bullish
            bearish_threshold: XMR adoption % below which signal is bearish
            min_confidence: Minimum confidence to generate signal
            update_interval_hours: Hours between scraping updates
            params: Additional strategy parameters
        """
        default_params = {
            'bullish_threshold': bullish_threshold,
            'bearish_threshold': bearish_threshold,
            'min_confidence': min_confidence,
            'update_interval_hours': update_interval_hours,
            'trend_weight': 0.3,  # Weight for trend component
            'level_weight': 0.7,  # Weight for absolute adoption level
        }
        
        if params:
            default_params.update(params)
        
        super().__init__("DarknetAdoption", default_params)
        
        self.marketplace_scraper = marketplace_scraper
        self.last_scrape_time: Optional[datetime] = None
        self.cached_stats: Optional[Dict] = None
        self.adoption_history: list = []
    
    async def update_adoption_data(self) -> bool:
        """
        Scrape darknet marketplaces for latest adoption data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Scraping darknet marketplaces for adoption data...")
            
            # Scrape top 10 marketplaces
            results = self.marketplace_scraper.scrape_all_marketplaces(limit=10)
            
            if not results:
                logger.warning("No marketplace data collected")
                return False
            
            # Calculate aggregate statistics
            stats = self.marketplace_scraper.calculate_aggregate_stats(results)
            
            if stats['status'] != 'success':
                logger.error(f"Failed to calculate stats: {stats.get('message')}")
                return False
            
            # Cache results
            self.cached_stats = stats
            self.last_scrape_time = datetime.now()
            
            # Add to history
            self.adoption_history.append({
                'timestamp': self.last_scrape_time,
                'xmr_percentage': stats['xmr_percentage'],
                'btc_percentage': stats['btc_percentage'],
                'confidence': stats['confidence']
            })
            
            # Keep only last 30 data points
            if len(self.adoption_history) > 30:
                self.adoption_history = self.adoption_history[-30:]
            
            logger.info(
                f"Darknet adoption updated: "
                f"XMR={stats['xmr_percentage']:.1f}%, "
                f"BTC={stats['btc_percentage']:.1f}%, "
                f"Confidence={stats['confidence']:.2f}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating adoption data: {e}")
            return False
    
    def needs_update(self) -> bool:
        """Check if adoption data needs to be updated."""
        if not self.last_scrape_time:
            return True
        
        hours_since_update = (datetime.now() - self.last_scrape_time).total_seconds() / 3600
        return hours_since_update >= self.params['update_interval_hours']
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        """
        Generate trading signal based on darknet adoption data.
        
        Args:
            df: Price data (not used directly, but required by interface)
            
        Returns:
            Signal or None
        """
        # Check if we have data
        if not self.cached_stats:
            logger.debug("No darknet adoption data available")
            return None
        
        # Check confidence threshold
        confidence = self.cached_stats.get('confidence', 0)
        if confidence < self.params['min_confidence']:
            logger.debug(f"Confidence too low: {confidence:.2f}")
            return None
        
        # Get adoption metrics
        xmr_pct = self.cached_stats.get('xmr_percentage', 0)
        btc_pct = self.cached_stats.get('btc_percentage', 0)
        trend = self.cached_stats.get('xmr_adoption_trend', 'stable')
        
        # Determine signal type based on adoption level
        signal_type = SignalType.HOLD
        
        if xmr_pct >= self.params['bullish_threshold']:
            signal_type = SignalType.BUY
        elif xmr_pct <= self.params['bearish_threshold']:
            signal_type = SignalType.SELL
        else:
            # In neutral zone - use trend as tiebreaker
            if trend == 'increasing':
                signal_type = SignalType.BUY
            elif trend == 'decreasing':
                signal_type = SignalType.SELL
        
        # Calculate signal strength
        strength = self.calculate_signal_strength(df)
        
        # Calculate confidence (combination of data confidence and signal clarity)
        signal_confidence = self.calculate_confidence(df)
        
        if signal_type == SignalType.HOLD:
            return None  # Don't generate hold signals
        
        return Signal(
            signal_type=signal_type,
            strength=strength,
            confidence=signal_confidence,
            strategy_name=self.name,
            timestamp=pd.Timestamp.now(),
            metadata={
                'xmr_percentage': xmr_pct,
                'btc_percentage': btc_pct,
                'adoption_trend': trend,
                'data_confidence': confidence,
                'marketplaces_count': self.cached_stats.get('marketplaces_count', 0),
                'last_scrape': self.last_scrape_time.isoformat() if self.last_scrape_time else None
            }
        )
    
    def validate_signal(self, signal: Signal, df: pd.DataFrame) -> bool:
        """
        Validate that signal is still relevant.
        
        Args:
            signal: Signal to validate
            df: Current market data
            
        Returns:
            True if signal is valid, False otherwise
        """
        if not signal.metadata:
            return False
        
        # Check data freshness
        last_scrape_str = signal.metadata.get('last_scrape')
        if last_scrape_str:
            try:
                last_scrape = datetime.fromisoformat(last_scrape_str)
                hours_old = (datetime.now() - last_scrape).total_seconds() / 3600
                
                # Signal expires after 48 hours
                if hours_old > 48:
                    logger.debug("Signal expired (data too old)")
                    return False
            except:
                pass
        
        # Check confidence
        data_confidence = signal.metadata.get('data_confidence', 0)
        if data_confidence < self.params['min_confidence']:
            return False
        
        return True
    
    def calculate_signal_strength(self, df: pd.DataFrame) -> float:
        """
        Calculate signal strength based on adoption metrics.
        
        Higher strength when:
        - XMR adoption is very high or very low (clear signal)
        - Trend is strong and consistent
        - Multiple marketplaces agree
        """
        if not self.cached_stats:
            return 0.0
        
        xmr_pct = self.cached_stats.get('xmr_percentage', 50)
        trend = self.cached_stats.get('xmr_adoption_trend', 'stable')
        
        # Component 1: Adoption level strength
        # Distance from neutral (50%)
        distance_from_neutral = abs(xmr_pct - 50) / 50
        level_strength = min(distance_from_neutral, 1.0)
        
        # Component 2: Trend strength
        trend_strength = {
            'increasing': 0.8 if xmr_pct > 50 else 0.3,
            'decreasing': 0.8 if xmr_pct < 50 else 0.3,
            'stable': 0.5,
            'insufficient_data': 0.3
        }.get(trend, 0.5)
        
        # Combine components
        level_weight = self.params['level_weight']
        trend_weight = self.params['trend_weight']
        
        strength = (
            level_strength * level_weight +
            trend_strength * trend_weight
        )
        
        return min(strength, 1.0)
    
    def calculate_confidence(self, df: pd.DataFrame) -> float:
        """
        Calculate signal confidence.
        
        Based on:
        - Data confidence (marketplace sample size, consistency)
        - Historical consistency
        - Signal clarity
        """
        if not self.cached_stats:
            return 0.0
        
        # Component 1: Data collection confidence
        data_confidence = self.cached_stats.get('confidence', 0)
        
        # Component 2: Historical consistency
        hist_confidence = self._calculate_historical_consistency()
        
        # Component 3: Signal clarity (how far from neutral zone)
        xmr_pct = self.cached_stats.get('xmr_percentage', 50)
        bullish_thresh = self.params['bullish_threshold']
        bearish_thresh = self.params['bearish_threshold']
        
        if xmr_pct >= bullish_thresh:
            # Above bullish threshold
            clarity = min((xmr_pct - bullish_thresh) / (100 - bullish_thresh), 1.0)
        elif xmr_pct <= bearish_thresh:
            # Below bearish threshold
            clarity = min((bearish_thresh - xmr_pct) / bearish_thresh, 1.0)
        else:
            # In neutral zone
            clarity = 0.3
        
        # Weighted combination
        overall_confidence = (
            data_confidence * 0.5 +
            hist_confidence * 0.3 +
            clarity * 0.2
        )
        
        return overall_confidence
    
    def _calculate_historical_consistency(self) -> float:
        """Calculate consistency of adoption data over time."""
        if len(self.adoption_history) < 3:
            return 0.5  # Neutral if insufficient history
        
        # Check if recent trend is consistent
        recent_xmr = [h['xmr_percentage'] for h in self.adoption_history[-5:]]
        
        if len(recent_xmr) < 2:
            return 0.5
        
        # Calculate variance
        import statistics
        std_dev = statistics.stdev(recent_xmr)
        
        # Lower variance = higher consistency
        # Assume std_dev > 10 is high variance
        consistency = max(0, 1 - (std_dev / 20))
        
        return consistency
    
    def get_adoption_report(self) -> Dict[str, Any]:
        """
        Generate detailed adoption report.
        
        Returns:
            Dict with adoption metrics and analysis
        """
        if not self.cached_stats:
            return {
                'status': 'no_data',
                'message': 'No darknet adoption data available'
            }
        
        return {
            'status': 'ok',
            'timestamp': self.last_scrape_time,
            'current_adoption': {
                'xmr_percentage': self.cached_stats.get('xmr_percentage'),
                'btc_percentage': self.cached_stats.get('btc_percentage'),
                'trend': self.cached_stats.get('xmr_adoption_trend')
            },
            'signal_status': {
                'bullish_threshold': self.params['bullish_threshold'],
                'bearish_threshold': self.params['bearish_threshold'],
                'current_zone': self._get_current_zone()
            },
            'data_quality': {
                'confidence': self.cached_stats.get('confidence'),
                'marketplaces_count': self.cached_stats.get('marketplaces_count'),
                'marketplaces': self.cached_stats.get('marketplaces_included', [])
            },
            'history': {
                'data_points': len(self.adoption_history),
                'recent_trend': self._calculate_recent_trend()
            }
        }
    
    def _get_current_zone(self) -> str:
        """Determine which signal zone we're currently in."""
        if not self.cached_stats:
            return 'unknown'
        
        xmr_pct = self.cached_stats.get('xmr_percentage', 50)
        
        if xmr_pct >= self.params['bullish_threshold']:
            return 'bullish'
        elif xmr_pct <= self.params['bearish_threshold']:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_recent_trend(self) -> str:
        """Calculate trend over recent history."""
        if len(self.adoption_history) < 3:
            return 'insufficient_data'
        
        recent = self.adoption_history[-3:]
        xmr_values = [h['xmr_percentage'] for h in recent]
        
        # Simple linear trend
        if xmr_values[-1] > xmr_values[0] + 3:
            return 'increasing'
        elif xmr_values[-1] < xmr_values[0] - 3:
            return 'decreasing'
        else:
            return 'stable'

