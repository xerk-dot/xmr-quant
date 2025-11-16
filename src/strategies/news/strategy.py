"""
News sentiment trading strategy.

Generates trading signals based on aggregated news sentiment
from Twitter monitoring and LLM classification.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd

from src.signals.base_strategy import BaseStrategy, Signal
from .news_aggregator import NewsAggregator

logger = logging.getLogger(__name__)


class NewsSentimentStrategy(BaseStrategy):
    """
    Trading strategy based on news sentiment analysis.
    
    Generates signals when:
    - Privacy-related news creates bullish sentiment for XMR
    - Instability news increases demand for privacy coins
    - Regulatory news impacts crypto markets
    - Economic news affects risk appetite
    """
    
    def __init__(
        self,
        news_aggregator: NewsAggregator,
        min_sentiment_threshold: float = 30,
        significant_news_min: int = 2,
        privacy_boost_multiplier: float = 1.5,
        instability_boost_multiplier: float = 1.2,
        max_signal_age_hours: int = 4
    ):
        """
        Initialize news sentiment strategy.
        
        Args:
            news_aggregator: NewsAggregator instance
            min_sentiment_threshold: Minimum sentiment strength to generate signal
            significant_news_min: Minimum significant news items required
            privacy_boost_multiplier: Boost for privacy-related news
            instability_boost_multiplier: Boost for instability news
            max_signal_age_hours: Maximum age of news to consider
        """
        super().__init__(name="NewsSentiment")
        
        self.news_aggregator = news_aggregator
        self.min_sentiment_threshold = min_sentiment_threshold
        self.significant_news_min = significant_news_min
        self.privacy_boost = privacy_boost_multiplier
        self.instability_boost = instability_boost_multiplier
        self.max_signal_age_hours = max_signal_age_hours
        
        # Cache latest sentiment
        self.latest_sentiment: Optional[Dict[str, Any]] = None
        self.last_update: Optional[datetime] = None
        
        logger.info(f"NewsSentimentStrategy initialized (threshold={min_sentiment_threshold})")
    
    async def update_sentiment(self):
        """
        Fetch and update latest news sentiment.
        
        Should be called periodically (e.g., every 30 minutes).
        """
        try:
            logger.info("Updating news sentiment...")
            
            # Fetch and aggregate news
            sentiment = await self.news_aggregator.update_and_aggregate(
                since_hours=self.max_signal_age_hours
            )
            
            self.latest_sentiment = sentiment
            self.last_update = datetime.utcnow()
            
            logger.info(
                f"News sentiment updated: {sentiment['overall_sentiment']:.1f}, "
                f"actionable: {sentiment['is_actionable']}, "
                f"significant: {sentiment['significant_news_count']}"
            )
            
        except Exception as e:
            logger.error(f"Error updating news sentiment: {e}")
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        """
        Generate trading signal based on latest news sentiment.
        
        Args:
            df: OHLCV dataframe (not used directly, but required by interface)
        
        Returns:
            Signal object or None
        """
        # Check if we have recent sentiment
        if self.latest_sentiment is None:
            logger.debug("No sentiment data available")
            return None
        
        # Check if sentiment is recent enough
        age_hours = (datetime.utcnow() - self.last_update).total_seconds() / 3600
        if age_hours > self.max_signal_age_hours:
            logger.debug(f"Sentiment data too old ({age_hours:.1f}h)")
            return None
        
        sentiment = self.latest_sentiment
        
        # Check if actionable
        if not sentiment['is_actionable']:
            logger.debug("Sentiment not actionable")
            return None
        
        # Check minimum thresholds
        if abs(sentiment['overall_sentiment']) < self.min_sentiment_threshold:
            logger.debug(f"Sentiment below threshold: {sentiment['overall_sentiment']:.1f}")
            return None
        
        if sentiment['significant_news_count'] < self.significant_news_min:
            logger.debug(f"Not enough significant news: {sentiment['significant_news_count']}")
            return None
        
        # Generate signal
        signal_type = 'buy' if sentiment['overall_sentiment'] > 0 else 'sell'
        
        # Calculate signal strength (0-1)
        base_strength = abs(sentiment['overall_sentiment']) / 100
        
        # Apply boosts for privacy and instability
        privacy_factor = 1.0 + (sentiment['avg_privacy_score'] / 100) * (self.privacy_boost - 1.0)
        instability_factor = 1.0 + (sentiment['avg_instability_score'] / 100) * (self.instability_boost - 1.0)
        
        # Only boost bullish signals (privacy concerns = bullish for XMR)
        if signal_type == 'buy':
            strength = base_strength * privacy_factor * instability_factor
        else:
            strength = base_strength
        
        # Clamp to [0, 1]
        strength = max(0.0, min(1.0, strength))
        
        # Calculate confidence based on:
        # - Number of significant news items
        # - Average confidence from classifier
        # - Consensus in sentiment
        significant_ratio = min(1.0, sentiment['significant_news_count'] / 5)
        
        # Check sentiment consensus (are most items agreeing?)
        total_directional = sentiment['bullish_count'] + sentiment['bearish_count']
        if total_directional > 0:
            if signal_type == 'buy':
                consensus = sentiment['bullish_count'] / total_directional
            else:
                consensus = sentiment['bearish_count'] / total_directional
        else:
            consensus = 0.5
        
        confidence = (significant_ratio + consensus) / 2
        
        # Metadata for signal
        metadata = {
            'overall_sentiment': sentiment['overall_sentiment'],
            'sentiment_strength': sentiment['sentiment_strength'],
            'significant_news_count': sentiment['significant_news_count'],
            'bullish_count': sentiment['bullish_count'],
            'bearish_count': sentiment['bearish_count'],
            'avg_privacy_score': sentiment['avg_privacy_score'],
            'avg_instability_score': sentiment['avg_instability_score'],
            'avg_crypto_score': sentiment['avg_crypto_score'],
            'avg_economic_score': sentiment['avg_economic_score'],
            'top_topics': sentiment['top_topics'][:5],
            'top_news': sentiment['top_news_summaries'][:3],
            'sentiment_age_hours': age_hours
        }
        
        signal = Signal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            strategy_name=self.name,
            metadata=metadata
        )
        
        logger.info(
            f"Generated {signal_type.upper()} signal: "
            f"strength={strength:.3f}, confidence={confidence:.3f}, "
            f"sentiment={sentiment['overall_sentiment']:.1f}"
        )
        
        return signal
    
    def get_sentiment_summary(self) -> Dict[str, Any]:
        """
        Get summary of current news sentiment.
        
        Returns:
            Dictionary with sentiment summary
        """
        if self.latest_sentiment is None:
            return {
                'status': 'no_data',
                'message': 'No sentiment data available'
            }
        
        age_hours = (datetime.utcnow() - self.last_update).total_seconds() / 3600
        
        return {
            'status': 'ok',
            'overall_sentiment': self.latest_sentiment['overall_sentiment'],
            'sentiment_strength': self.latest_sentiment['sentiment_strength'],
            'is_actionable': self.latest_sentiment['is_actionable'],
            'significant_news_count': self.latest_sentiment['significant_news_count'],
            'bullish_count': self.latest_sentiment['bullish_count'],
            'bearish_count': self.latest_sentiment['bearish_count'],
            'neutral_count': self.latest_sentiment['neutral_count'],
            'avg_privacy_score': self.latest_sentiment['avg_privacy_score'],
            'avg_instability_score': self.latest_sentiment['avg_instability_score'],
            'top_topics': self.latest_sentiment['top_topics'][:5],
            'top_news_summaries': self.latest_sentiment['top_news_summaries'][:3],
            'age_hours': age_hours,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    def get_detailed_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed breakdown of news categories and sentiment.
        
        Returns:
            Detailed analysis dictionary
        """
        if self.latest_sentiment is None:
            return {'status': 'no_data'}
        
        sentiment = self.latest_sentiment
        
        # Categorize news impact
        categories = {
            'privacy_focused': sentiment['avg_privacy_score'] >= 60,
            'instability_focused': sentiment['avg_instability_score'] >= 60,
            'crypto_focused': sentiment['avg_crypto_score'] >= 60,
            'economic_focused': sentiment['avg_economic_score'] >= 60
        }
        
        # Determine primary driver
        scores = {
            'privacy': sentiment['avg_privacy_score'],
            'instability': sentiment['avg_instability_score'],
            'crypto': sentiment['avg_crypto_score'],
            'economic': sentiment['avg_economic_score']
        }
        primary_driver = max(scores, key=scores.get)
        
        # Sentiment direction
        if sentiment['overall_sentiment'] > 30:
            direction = 'bullish'
        elif sentiment['overall_sentiment'] < -30:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        # Get trend
        trend = self.news_aggregator.get_sentiment_trend(hours=24)
        
        return {
            'status': 'ok',
            'overall_sentiment': sentiment['overall_sentiment'],
            'direction': direction,
            'is_actionable': sentiment['is_actionable'],
            'primary_driver': primary_driver,
            'categories': categories,
            'category_scores': scores,
            'sentiment_counts': {
                'bullish': sentiment['bullish_count'],
                'bearish': sentiment['bearish_count'],
                'neutral': sentiment['neutral_count'],
                'total': sentiment['total_news_items'],
                'significant': sentiment['significant_news_count']
            },
            'trend_24h': trend,
            'top_topics': sentiment['top_topics'][:10],
            'window_hours': sentiment['window_hours']
        }
