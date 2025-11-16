"""
News aggregation and sentiment analysis engine.

Coordinates news fetching from Twitter, classification via LLM,
and aggregates sentiment across time windows for trading signals.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from .twitter_client import TwitterClient
from .news_classifier import NewsClassifier

logger = logging.getLogger(__name__)


class NewsAggregator:
    """
    Aggregates news from multiple sources and generates sentiment scores.
    
    Workflow:
    1. Fetch news from Twitter across multiple categories
    2. Classify each news item using LLM (4 dimensions + sentiment)
    3. Aggregate sentiment over time window
    4. Generate actionable trading signals
    """
    
    def __init__(
        self,
        twitter_client: TwitterClient,
        news_classifier: NewsClassifier,
        aggregation_window_hours: int = 2
    ):
        """
        Initialize news aggregator.
        
        Args:
            twitter_client: Twitter API client
            news_classifier: LLM-based news classifier
            aggregation_window_hours: Time window for aggregating news
        """
        self.twitter_client = twitter_client
        self.news_classifier = news_classifier
        self.aggregation_window_hours = aggregation_window_hours
        
        # Cache for classified news (to avoid re-processing)
        self.classified_news_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expiry_hours = 24
        
        # Historical sentiment tracking
        self.sentiment_history: List[Dict[str, Any]] = []
        self.max_history_items = 100
        
        logger.info(f"NewsAggregator initialized with {aggregation_window_hours}h window")
    
    async def fetch_and_classify_news(
        self,
        since_hours: int = 2,
        max_per_category: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from Twitter and classify using LLM.
        
        Args:
            since_hours: Fetch news from last N hours
            max_per_category: Max tweets per category
        
        Returns:
            List of classified news items
        """
        logger.info(f"Fetching news from last {since_hours} hours...")
        
        # Fetch from all categories
        news_by_category = await self.twitter_client.fetch_all_news(
            since_hours=since_hours,
            max_per_category=max_per_category
        )
        
        # Flatten and deduplicate
        all_news = []
        seen_ids = set()
        
        for category, news_items in news_by_category.items():
            for item in news_items:
                item_id = item['id']
                
                # Skip if already processed
                if item_id in seen_ids:
                    continue
                
                # Check cache
                if item_id in self.classified_news_cache:
                    cached = self.classified_news_cache[item_id]
                    # Check if cache is still valid
                    if (datetime.utcnow() - cached['cached_at']).total_seconds() < self.cache_expiry_hours * 3600:
                        all_news.append(cached['data'])
                        seen_ids.add(item_id)
                        continue
                
                # Add category to item
                item['category'] = category
                all_news.append(item)
                seen_ids.add(item_id)
        
        logger.info(f"Found {len(all_news)} unique news items")
        
        # Classify uncached items
        uncached_items = [
            item for item in all_news
            if item['id'] not in self.classified_news_cache
        ]
        
        if uncached_items:
            logger.info(f"Classifying {len(uncached_items)} new items...")
            classified = await self.news_classifier.classify_batch(
                uncached_items,
                max_concurrent=5
            )
            
            # Update cache
            for item in classified:
                self.classified_news_cache[item['id']] = {
                    'data': item,
                    'cached_at': datetime.utcnow()
                }
            
            # Merge with cached items
            cached_items = [
                self.classified_news_cache[item['id']]['data']
                for item in all_news
                if item['id'] in self.classified_news_cache
                and item['id'] not in [i['id'] for i in classified]
            ]
            
            all_news = classified + cached_items
        else:
            logger.info("All items found in cache")
            all_news = [
                self.classified_news_cache[item['id']]['data']
                for item in all_news
            ]
        
        # Clean old cache entries
        self._clean_cache()
        
        return all_news
    
    def aggregate_sentiment(
        self,
        classified_news: List[Dict[str, Any]],
        window_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Aggregate sentiment from classified news items.
        
        Args:
            classified_news: List of classified news items
            window_hours: Time window (None = use default)
        
        Returns:
            Aggregated sentiment dictionary
        """
        if window_hours is None:
            window_hours = self.aggregation_window_hours
        
        cutoff_time = datetime.utcnow() - timedelta(hours=window_hours)
        
        # Filter news within time window
        recent_news = [
            item for item in classified_news
            if item['created_at'] >= cutoff_time
        ]
        
        if not recent_news:
            return self._get_empty_sentiment()
        
        logger.info(f"Aggregating sentiment from {len(recent_news)} items")
        
        # Count by sentiment
        sentiment_counts = defaultdict(int)
        for item in recent_news:
            sentiment_counts[item.get('sentiment', 'neutral')] += 1
        
        # Filter significant news
        significant_news = [
            item for item in recent_news
            if item.get('is_significant', False)
        ]
        
        # Calculate average scores
        avg_scores = {
            'economic': sum(item.get('economic_score', 0) for item in recent_news) / len(recent_news),
            'crypto': sum(item.get('crypto_score', 0) for item in recent_news) / len(recent_news),
            'privacy': sum(item.get('privacy_score', 0) for item in recent_news) / len(recent_news),
            'instability': sum(item.get('instability_score', 0) for item in recent_news) / len(recent_news)
        }
        
        # Calculate overall sentiment score (-100 to +100)
        overall_sentiment = self._calculate_overall_sentiment(
            recent_news,
            significant_news,
            avg_scores
        )
        
        # Extract top topics/entities
        top_topics = self._extract_top_topics(recent_news)
        
        # Determine if sentiment is actionable
        is_actionable = self._is_actionable(
            overall_sentiment,
            significant_news,
            avg_scores
        )
        
        # Get top news summaries
        top_news = sorted(
            significant_news,
            key=lambda x: x.get('overall_relevance', 0),
            reverse=True
        )[:5]
        
        aggregated = {
            'timestamp': datetime.utcnow(),
            'window_hours': window_hours,
            'total_news_items': len(recent_news),
            'significant_news_count': len(significant_news),
            'bullish_count': sentiment_counts['bullish'],
            'bearish_count': sentiment_counts['bearish'],
            'neutral_count': sentiment_counts['neutral'],
            'avg_economic_score': avg_scores['economic'],
            'avg_crypto_score': avg_scores['crypto'],
            'avg_privacy_score': avg_scores['privacy'],
            'avg_instability_score': avg_scores['instability'],
            'overall_sentiment': overall_sentiment,
            'sentiment_strength': abs(overall_sentiment),
            'is_actionable': is_actionable,
            'top_topics': top_topics,
            'top_news_summaries': [
                {
                    'text': item['text'][:200],
                    'summary': item.get('summary', ''),
                    'sentiment': item.get('sentiment', 'neutral'),
                    'relevance': item.get('overall_relevance', 0)
                }
                for item in top_news
            ]
        }
        
        # Add to history
        self.sentiment_history.append(aggregated)
        if len(self.sentiment_history) > self.max_history_items:
            self.sentiment_history = self.sentiment_history[-self.max_history_items:]
        
        return aggregated
    
    def _calculate_overall_sentiment(
        self,
        all_news: List[Dict[str, Any]],
        significant_news: List[Dict[str, Any]],
        avg_scores: Dict[str, float]
    ) -> float:
        """
        Calculate overall sentiment score (-100 to +100).
        
        Privacy and instability news get boosted for privacy coins.
        
        Args:
            all_news: All news items
            significant_news: Filtered significant news
            avg_scores: Average category scores
        
        Returns:
            Sentiment score (-100 to +100)
        """
        if not all_news:
            return 0.0
        
        # Count weighted sentiment
        sentiment_value = {
            'bullish': 1.0,
            'neutral': 0.0,
            'bearish': -1.0
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for item in all_news:
            sentiment = item.get('sentiment', 'neutral')
            confidence = item.get('confidence', 50) / 100
            relevance = item.get('overall_relevance', 0) / 100
            
            # Base weight
            weight = confidence * relevance
            
            # Boost for significant news
            if item.get('is_significant', False):
                weight *= 1.5
            
            # Boost for high privacy or instability scores (bullish for XMR)
            privacy_boost = 1.0 + (item.get('privacy_score', 0) / 100) * 0.5
            instability_boost = 1.0 + (item.get('instability_score', 0) / 100) * 0.3
            
            # Apply sentiment value with boosts
            sentiment_val = sentiment_value[sentiment]
            if sentiment == 'bullish':
                sentiment_val *= privacy_boost * instability_boost
            elif sentiment == 'bearish':
                # Bearish news is worse with privacy concerns (e.g., delisting)
                sentiment_val *= (2.0 - privacy_boost * 0.5)
            
            total_score += sentiment_val * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize to -100 to +100
        normalized_score = (total_score / total_weight) * 100
        
        return max(-100, min(100, normalized_score))
    
    def _extract_top_topics(self, news_items: List[Dict[str, Any]]) -> List[str]:
        """Extract most common topics/entities from news."""
        topic_counts = defaultdict(int)
        
        for item in news_items:
            # Count key entities
            for entity in item.get('key_entities', []):
                topic_counts[entity] += 1
            
            # Count hashtags
            for hashtag in item.get('hashtags', []):
                topic_counts[hashtag] += 1
        
        # Sort by frequency
        sorted_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [topic for topic, count in sorted_topics[:10]]
    
    def _is_actionable(
        self,
        overall_sentiment: float,
        significant_news: List[Dict[str, Any]],
        avg_scores: Dict[str, float]
    ) -> bool:
        """
        Determine if sentiment is strong enough to act on.
        
        Args:
            overall_sentiment: Overall sentiment score
            significant_news: List of significant news
            avg_scores: Average category scores
        
        Returns:
            True if sentiment is actionable
        """
        # Need minimum sentiment strength
        if abs(overall_sentiment) < 30:
            return False
        
        # Need minimum significant news items
        if len(significant_news) < 2:
            return False
        
        # High privacy or instability scores
        if avg_scores['privacy'] >= 60 or avg_scores['instability'] >= 60:
            return True
        
        # Strong crypto relevance with strong sentiment
        if avg_scores['crypto'] >= 70 and abs(overall_sentiment) >= 50:
            return True
        
        return False
    
    def _get_empty_sentiment(self) -> Dict[str, Any]:
        """Get empty sentiment dict when no news available."""
        return {
            'timestamp': datetime.utcnow(),
            'window_hours': self.aggregation_window_hours,
            'total_news_items': 0,
            'significant_news_count': 0,
            'bullish_count': 0,
            'bearish_count': 0,
            'neutral_count': 0,
            'avg_economic_score': 0.0,
            'avg_crypto_score': 0.0,
            'avg_privacy_score': 0.0,
            'avg_instability_score': 0.0,
            'overall_sentiment': 0.0,
            'sentiment_strength': 0.0,
            'is_actionable': False,
            'top_topics': [],
            'top_news_summaries': []
        }
    
    def _clean_cache(self):
        """Remove old entries from cache."""
        cutoff = datetime.utcnow() - timedelta(hours=self.cache_expiry_hours)
        
        expired_ids = [
            item_id for item_id, data in self.classified_news_cache.items()
            if data['cached_at'] < cutoff
        ]
        
        for item_id in expired_ids:
            del self.classified_news_cache[item_id]
        
        if expired_ids:
            logger.info(f"Cleaned {len(expired_ids)} expired cache entries")
    
    async def update_and_aggregate(
        self,
        since_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Convenience method: fetch, classify, and aggregate in one call.
        
        Args:
            since_hours: Hours to look back (None = use window size)
        
        Returns:
            Aggregated sentiment dictionary
        """
        if since_hours is None:
            since_hours = self.aggregation_window_hours
        
        # Fetch and classify
        classified_news = await self.fetch_and_classify_news(since_hours=since_hours)
        
        # Aggregate sentiment
        sentiment = self.aggregate_sentiment(classified_news)
        
        return sentiment
    
    def get_sentiment_trend(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analyze sentiment trend over recent history.
        
        Args:
            hours: Hours to analyze
        
        Returns:
            Trend analysis dictionary
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        recent_sentiments = [
            s for s in self.sentiment_history
            if s['timestamp'] >= cutoff
        ]
        
        if not recent_sentiments:
            return {
                'trend': 'unknown',
                'average_sentiment': 0.0,
                'sentiment_change': 0.0,
                'data_points': 0
            }
        
        sentiments = [s['overall_sentiment'] for s in recent_sentiments]
        
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        # Calculate trend
        if len(sentiments) >= 2:
            sentiment_change = sentiments[-1] - sentiments[0]
            if sentiment_change > 10:
                trend = 'improving'
            elif sentiment_change < -10:
                trend = 'deteriorating'
            else:
                trend = 'stable'
        else:
            sentiment_change = 0.0
            trend = 'stable'
        
        return {
            'trend': trend,
            'average_sentiment': avg_sentiment,
            'sentiment_change': sentiment_change,
            'data_points': len(sentiments),
            'latest_sentiment': sentiments[-1] if sentiments else 0.0
        }
