"""
Twitter API v2 client for fetching cryptocurrency and privacy-related news.

Monitors Twitter for breaking news across:
- Economic news (central banks, inflation, recession)
- Cryptocurrency news (Bitcoin, Monero, regulation)
- Privacy-oriented news (surveillance, encryption, data protection)
- Global instability (wars, sanctions, regulatory crackdowns)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


class TwitterClient:
    """
    Twitter API v2 client for fetching relevant news tweets.
    
    Uses bearer token authentication and supports:
    - Recent search (last 7 days)
    - Filtered stream (real-time)
    - User timeline
    """
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, bearer_token: str):
        """
        Initialize Twitter client.
        
        Args:
            bearer_token: Twitter API v2 Bearer Token
        """
        self.bearer_token = bearer_token
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Pre-configured search queries for different news categories
        self.queries = {
            'crypto_general': (
                '(Bitcoin OR BTC OR Monero OR XMR OR cryptocurrency OR crypto) '
                '(breaking OR news OR alert OR announces) '
                '-is:retweet -is:reply lang:en'
            ),
            'privacy_news': (
                '(privacy OR surveillance OR encryption OR anonymity OR "data protection") '
                '(breaking OR news OR alert OR law OR regulation) '
                '-is:retweet -is:reply lang:en'
            ),
            'economic_news': (
                '(Fed OR "Federal Reserve" OR "ECB" OR "central bank" OR inflation OR recession OR GDP) '
                '(breaking OR news OR alert OR announces OR decision) '
                '-is:retweet -is:reply lang:en'
            ),
            'instability_news': (
                '(war OR sanctions OR crisis OR "regulatory crackdown" OR ban OR shutdown) '
                '(crypto OR financial OR banking OR markets) '
                '-is:retweet -is:reply lang:en'
            ),
            'monero_specific': (
                '(Monero OR XMR OR $XMR) '
                '(news OR breaking OR alert OR listing OR delisting OR regulation) '
                '-is:retweet -is:reply lang:en'
            ),
        }
        
        # High-credibility accounts to monitor
        self.priority_accounts = [
            'CoinDesk', 'Cointelegraph', 'DecryptMedia', 'TheBlock__',
            'business', 'Reuters', 'FT', 'WSJ', 'nytimes',
            'federalreserve', 'SEC_News', 'SECGov',
            'edward_snowden', 'EFF', 'torproject'
        ]
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    'Authorization': f'Bearer {self.bearer_token}',
                    'Content-Type': 'application/json'
                }
            )
    
    async def disconnect(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def search_recent_tweets(
        self,
        query: str,
        max_results: int = 100,
        since_hours: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Search for recent tweets matching a query.
        
        Args:
            query: Twitter search query string
            max_results: Maximum number of results (10-100)
            since_hours: Only fetch tweets from last N hours
        
        Returns:
            List of tweet dictionaries with metadata
        """
        await self._ensure_session()
        
        # Calculate start time
        start_time = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat() + 'Z'
        
        params = {
            'query': query,
            'max_results': min(max_results, 100),
            'start_time': start_time,
            'tweet.fields': 'created_at,public_metrics,entities,author_id,context_annotations',
            'expansions': 'author_id',
            'user.fields': 'name,username,verified,public_metrics'
        }
        
        try:
            async with self.session.get(
                f'{self.BASE_URL}/tweets/search/recent',
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_tweets(data)
                elif response.status == 429:
                    logger.warning("Twitter API rate limit exceeded")
                    return []
                else:
                    error_text = await response.text()
                    logger.error(f"Twitter API error {response.status}: {error_text}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return []
    
    async def fetch_all_news(
        self,
        categories: Optional[List[str]] = None,
        since_hours: int = 2,
        max_per_category: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch news from all configured categories.
        
        Args:
            categories: List of category names to fetch (None = all)
            since_hours: Only fetch tweets from last N hours
            max_per_category: Max results per category
        
        Returns:
            Dictionary mapping category name to list of tweets
        """
        if categories is None:
            categories = list(self.queries.keys())
        
        results = {}
        
        # Fetch all categories in parallel
        tasks = []
        for category in categories:
            if category in self.queries:
                task = self.search_recent_tweets(
                    query=self.queries[category],
                    max_results=max_per_category,
                    since_hours=since_hours
                )
                tasks.append((category, task))
        
        # Wait for all fetches to complete
        for category, task in tasks:
            try:
                tweets = await task
                results[category] = tweets
                logger.info(f"Fetched {len(tweets)} tweets for category '{category}'")
            except Exception as e:
                logger.error(f"Error fetching category '{category}': {e}")
                results[category] = []
        
        return results
    
    def _parse_tweets(self, api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Twitter API response into standardized format.
        
        Args:
            api_response: Raw API response
        
        Returns:
            List of parsed tweet dictionaries
        """
        tweets = []
        
        if 'data' not in api_response:
            return tweets
        
        # Create user lookup
        users = {}
        if 'includes' in api_response and 'users' in api_response['includes']:
            for user in api_response['includes']['users']:
                users[user['id']] = user
        
        for tweet_data in api_response['data']:
            try:
                tweet = {
                    'id': tweet_data['id'],
                    'text': tweet_data['text'],
                    'created_at': datetime.fromisoformat(
                        tweet_data['created_at'].replace('Z', '+00:00')
                    ),
                    'url': f"https://twitter.com/i/web/status/{tweet_data['id']}",
                }
                
                # Add author info
                if 'author_id' in tweet_data and tweet_data['author_id'] in users:
                    user = users[tweet_data['author_id']]
                    tweet['author'] = {
                        'username': user['username'],
                        'name': user['name'],
                        'verified': user.get('verified', False),
                        'followers': user.get('public_metrics', {}).get('followers_count', 0)
                    }
                else:
                    tweet['author'] = {'username': 'unknown', 'name': 'unknown', 'verified': False}
                
                # Add engagement metrics
                if 'public_metrics' in tweet_data:
                    metrics = tweet_data['public_metrics']
                    tweet['engagement'] = {
                        'retweets': metrics.get('retweet_count', 0),
                        'likes': metrics.get('like_count', 0),
                        'replies': metrics.get('reply_count', 0),
                        'quotes': metrics.get('quote_count', 0)
                    }
                    # Calculate engagement score (weighted sum)
                    tweet['engagement_score'] = (
                        metrics.get('retweet_count', 0) * 3 +
                        metrics.get('like_count', 0) * 1 +
                        metrics.get('reply_count', 0) * 2 +
                        metrics.get('quote_count', 0) * 2
                    )
                else:
                    tweet['engagement_score'] = 0
                
                # Extract entities (hashtags, mentions, URLs)
                if 'entities' in tweet_data:
                    entities = tweet_data['entities']
                    tweet['hashtags'] = [
                        tag['tag'] for tag in entities.get('hashtags', [])
                    ]
                    tweet['mentions'] = [
                        mention['username'] for mention in entities.get('mentions', [])
                    ]
                    tweet['urls'] = [
                        url.get('expanded_url', url.get('url', ''))
                        for url in entities.get('urls', [])
                    ]
                else:
                    tweet['hashtags'] = []
                    tweet['mentions'] = []
                    tweet['urls'] = []
                
                # Extract context annotations (topics)
                if 'context_annotations' in tweet_data:
                    tweet['topics'] = [
                        annotation['domain']['name']
                        for annotation in tweet_data['context_annotations']
                        if 'domain' in annotation and 'name' in annotation['domain']
                    ]
                else:
                    tweet['topics'] = []
                
                # Check if from priority account
                if 'author' in tweet:
                    tweet['is_priority_source'] = (
                        tweet['author']['username'] in self.priority_accounts or
                        tweet['author'].get('verified', False)
                    )
                else:
                    tweet['is_priority_source'] = False
                
                tweets.append(tweet)
                
            except Exception as e:
                logger.warning(f"Error parsing tweet: {e}")
                continue
        
        return tweets
    
    async def get_user_timeline(
        self,
        username: str,
        max_results: int = 50,
        since_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent tweets from a specific user.
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum number of tweets
            since_hours: Only fetch tweets from last N hours
        
        Returns:
            List of tweet dictionaries
        """
        await self._ensure_session()
        
        # First, get user ID
        try:
            async with self.session.get(
                f'{self.BASE_URL}/users/by/username/{username}'
            ) as response:
                if response.status != 200:
                    logger.error(f"User {username} not found")
                    return []
                user_data = await response.json()
                user_id = user_data['data']['id']
        except Exception as e:
            logger.error(f"Error fetching user ID for {username}: {e}")
            return []
        
        # Fetch user timeline
        start_time = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat() + 'Z'
        
        params = {
            'max_results': min(max_results, 100),
            'start_time': start_time,
            'tweet.fields': 'created_at,public_metrics,entities',
            'exclude': 'retweets,replies'
        }
        
        try:
            async with self.session.get(
                f'{self.BASE_URL}/users/{user_id}/tweets',
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_tweets(data)
                else:
                    logger.error(f"Error fetching timeline for {username}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching user timeline: {e}")
            return []
    
    def add_custom_query(self, name: str, query: str):
        """
        Add a custom search query.
        
        Args:
            name: Name for the query category
            query: Twitter search query string
        """
        self.queries[name] = query
        logger.info(f"Added custom query '{name}': {query}")
    
    def remove_query(self, name: str):
        """Remove a search query by name."""
        if name in self.queries:
            del self.queries[name]
            logger.info(f"Removed query '{name}'")
