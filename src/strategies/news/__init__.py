"""
News sentiment strategies - OPTIONAL (requires paid APIs).

Cost: ~$110-140/month
- Twitter API: $100/month (Essential tier minimum)
- OpenAI/Anthropic: $10-20/month for LLM classification

Strategy (10% weight):
- Monitors Twitter for crypto, privacy, economic, and instability news
- LLM classifies news across 4 dimensions
- Generates signals based on aggregated sentiment

Set NEWS_MONITORING_ENABLED=false in .env to disable.
"""

from .strategy import NewsSentimentStrategy
from .twitter_client import TwitterClient
from .news_classifier import NewsClassifier
from .news_aggregator import NewsAggregator

__all__ = [
    'NewsSentimentStrategy',
    'TwitterClient',
    'NewsClassifier',
    'NewsAggregator',
]
