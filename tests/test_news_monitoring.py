"""
Test script for news monitoring system.

Tests Twitter client, LLM classification, and sentiment aggregation.
Run with: python test_news_monitoring.py
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from src.news.twitter_client import TwitterClient
from src.news.news_classifier import NewsClassifier
from src.news.news_aggregator import NewsAggregator
from src.news.news_sentiment_strategy import NewsSentimentStrategy

# Load environment variables
load_dotenv()


async def test_twitter_client():
    """Test Twitter API connection and news fetching."""
    print("\n" + "="*60)
    print("Testing Twitter Client")
    print("="*60)
    
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
    if not bearer_token:
        print("❌ TWITTER_BEARER_TOKEN not set in .env")
        return None
    
    client = TwitterClient(bearer_token)
    
    # Test fetching crypto news
    print("\n📡 Fetching recent crypto news (last 2 hours)...")
    try:
        news = await client.search_recent_tweets(
            query=client.queries['crypto_general'],
            max_results=10,
            since_hours=2
        )
        
        print(f"✅ Found {len(news)} tweets")
        
        if news:
            print("\n📰 Sample tweet:")
            tweet = news[0]
            print(f"  Author: {tweet['author']['username']} "
                  f"({'verified' if tweet['author'].get('verified') else 'unverified'})")
            print(f"  Text: {tweet['text'][:150]}...")
            print(f"  Engagement: {tweet['engagement_score']}")
            print(f"  Priority source: {tweet['is_priority_source']}")
        
        return client
        
    except Exception as e:
        print(f"❌ Error fetching tweets: {e}")
        return None


async def test_news_classifier(sample_text: str = None):
    """Test LLM classification."""
    print("\n" + "="*60)
    print("Testing News Classifier")
    print("="*60)
    
    provider = os.getenv('NEWS_LLM_PROVIDER', 'openai')
    
    if provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
    elif provider == 'anthropic':
        api_key = os.getenv('ANTHROPIC_API_KEY')
    else:
        print(f"❌ Unknown provider: {provider}")
        return None
    
    if not api_key:
        print(f"❌ API key for {provider} not set in .env")
        return None
    
    classifier = NewsClassifier(provider=provider, api_key=api_key)
    
    # Test with sample news
    if sample_text is None:
        sample_text = (
            "BREAKING: Federal Reserve announces emergency rate hike of 0.75% "
            "citing persistent inflation concerns. Markets tumble on news."
        )
    
    print(f"\n🔍 Classifying sample news with {provider}...")
    print(f"Text: {sample_text[:100]}...")
    
    try:
        result = await classifier.classify_news(
            sample_text,
            metadata={
                'author': {'name': 'Reuters', 'verified': True},
                'created_at': datetime.utcnow(),
                'is_priority_source': True
            }
        )
        
        print("\n✅ Classification results:")
        print(f"  Economic Score: {result['economic_score']:.1f}/100")
        print(f"  Crypto Score: {result['crypto_score']:.1f}/100")
        print(f"  Privacy Score: {result['privacy_score']:.1f}/100")
        print(f"  Instability Score: {result['instability_score']:.1f}/100")
        print(f"  Sentiment: {result['sentiment'].upper()}")
        print(f"  Confidence: {result['confidence']:.1f}/100")
        print(f"  Overall Relevance: {result['overall_relevance']:.1f}/100")
        print(f"  Is Significant: {result['is_significant']}")
        print(f"  Summary: {result['summary']}")
        print(f"  Key Entities: {', '.join(result['key_entities'][:5])}")
        
        return classifier
        
    except Exception as e:
        print(f"❌ Error classifying news: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_news_aggregator(twitter_client, news_classifier):
    """Test news aggregation and sentiment calculation."""
    print("\n" + "="*60)
    print("Testing News Aggregator")
    print("="*60)
    
    if not twitter_client or not news_classifier:
        print("⚠️  Skipping (dependencies not initialized)")
        return None
    
    aggregator = NewsAggregator(
        twitter_client=twitter_client,
        news_classifier=news_classifier,
        aggregation_window_hours=2
    )
    
    print("\n📊 Fetching, classifying, and aggregating news...")
    print("(This may take 30-60 seconds due to LLM API calls)")
    
    try:
        sentiment = await aggregator.update_and_aggregate(since_hours=2)
        
        print("\n✅ Aggregated sentiment:")
        print(f"  Overall Sentiment: {sentiment['overall_sentiment']:.1f} "
              f"({'bullish' if sentiment['overall_sentiment'] > 0 else 'bearish'})")
        print(f"  Sentiment Strength: {sentiment['sentiment_strength']:.1f}")
        print(f"  Is Actionable: {sentiment['is_actionable']}")
        print(f"  Total News Items: {sentiment['total_news_items']}")
        print(f"  Significant News: {sentiment['significant_news_count']}")
        print(f"  Bullish: {sentiment['bullish_count']}, "
              f"Bearish: {sentiment['bearish_count']}, "
              f"Neutral: {sentiment['neutral_count']}")
        
        print("\n📈 Category Scores:")
        print(f"  Economic: {sentiment['avg_economic_score']:.1f}")
        print(f"  Crypto: {sentiment['avg_crypto_score']:.1f}")
        print(f"  Privacy: {sentiment['avg_privacy_score']:.1f}")
        print(f"  Instability: {sentiment['avg_instability_score']:.1f}")
        
        if sentiment['top_topics']:
            print(f"\n🏷️  Top Topics: {', '.join(sentiment['top_topics'][:5])}")
        
        if sentiment['top_news_summaries']:
            print("\n📰 Top News Items:")
            for i, news in enumerate(sentiment['top_news_summaries'][:3], 1):
                print(f"  {i}. [{news['sentiment'].upper()}] {news['summary']}")
                print(f"     Relevance: {news['relevance']:.1f}")
        
        return aggregator
        
    except Exception as e:
        print(f"❌ Error aggregating news: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_sentiment_strategy(aggregator):
    """Test trading signal generation from news sentiment."""
    print("\n" + "="*60)
    print("Testing News Sentiment Strategy")
    print("="*60)
    
    if not aggregator:
        print("⚠️  Skipping (aggregator not initialized)")
        return None
    
    strategy = NewsSentimentStrategy(
        news_aggregator=aggregator,
        min_sentiment_threshold=30,
        significant_news_min=2
    )
    
    # Update sentiment
    print("\n🔄 Updating strategy sentiment...")
    await strategy.update_sentiment()
    
    # Get summary
    summary = strategy.get_sentiment_summary()
    
    print(f"\n✅ Strategy Status: {summary['status']}")
    if summary['status'] == 'ok':
        print(f"  Overall Sentiment: {summary['overall_sentiment']:.1f}")
        print(f"  Is Actionable: {summary['is_actionable']}")
        print(f"  Significant News Count: {summary['significant_news_count']}")
        print(f"  Age: {summary['age_hours']:.2f} hours")
    
    # Try to generate signal
    print("\n🎯 Attempting to generate trading signal...")
    
    import pandas as pd
    import numpy as np
    
    # Dummy price data (not used by news strategy, but required by interface)
    df = pd.DataFrame({
        'close': np.random.rand(100) * 100 + 150
    })
    
    signal = strategy.generate_signal(df)
    
    if signal:
        print("\n✅ Signal Generated!")
        print(f"  Type: {signal.signal_type.upper()}")
        print(f"  Strength: {signal.strength:.3f}")
        print(f"  Confidence: {signal.confidence:.3f}")
        print(f"  Strategy: {signal.strategy_name}")
        
        meta = signal.metadata
        print(f"\n  Signal Details:")
        print(f"    Overall Sentiment: {meta['overall_sentiment']:.1f}")
        print(f"    Significant News: {meta['significant_news_count']}")
        print(f"    Privacy Score: {meta['avg_privacy_score']:.1f}")
        print(f"    Instability Score: {meta['avg_instability_score']:.1f}")
        
        if meta['top_news']:
            print(f"\n  Top Contributing News:")
            for i, news in enumerate(meta['top_news'][:2], 1):
                print(f"    {i}. {news['summary']}")
    else:
        print("\n⚪ No signal generated (sentiment not strong enough or not actionable)")
    
    # Get detailed breakdown
    breakdown = strategy.get_detailed_breakdown()
    if breakdown['status'] == 'ok':
        print(f"\n📊 Sentiment Breakdown:")
        print(f"  Direction: {breakdown['direction'].upper()}")
        print(f"  Primary Driver: {breakdown['primary_driver']}")
        print(f"  24h Trend: {breakdown['trend_24h']['trend']}")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("NEWS MONITORING SYSTEM TEST")
    print("="*60)
    print("\nThis script tests the complete news monitoring pipeline:")
    print("1. Twitter API connection and news fetching")
    print("2. LLM-based classification (4 dimensions)")
    print("3. News aggregation and sentiment calculation")
    print("4. Trading signal generation")
    print("\nMake sure you have configured .env with:")
    print("  - TWITTER_BEARER_TOKEN")
    print("  - OPENAI_API_KEY or ANTHROPIC_API_KEY")
    print("  - NEWS_LLM_PROVIDER (openai or anthropic)")
    
    try:
        # Test Twitter client
        twitter_client = await test_twitter_client()
        
        # Test news classifier
        news_classifier = await test_news_classifier()
        
        # Test aggregator (this will fetch and classify multiple items)
        aggregator = await test_news_aggregator(twitter_client, news_classifier)
        
        # Test strategy
        await test_sentiment_strategy(aggregator)
        
        # Cleanup
        if twitter_client:
            await twitter_client.disconnect()
        if news_classifier:
            await news_classifier.disconnect()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        print("\nNext steps:")
        print("1. Review the classification results")
        print("2. Adjust thresholds if needed")
        print("3. Enable NEWS_MONITORING_ENABLED=true in .env")
        print("4. Run the main bot with: python run_bot.py --mode paper")
        print("\nSee docs/NEWS_MONITORING_GUIDE.md for detailed documentation.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

