"""
LLM-based news classifier for multi-dimensional analysis.

Classifies news items across 4 dimensions:
1. Economic Relevance (0-100): Central bank policy, inflation, recession signals
2. Crypto Relevance (0-100): Bitcoin, Monero, blockchain regulation
3. Privacy Relevance (0-100): Surveillance, encryption, data protection
4. Instability Relevance (0-100): Wars, sanctions, regulatory crackdowns

Supports both OpenAI (GPT-4) and Anthropic (Claude) as LLM providers.
"""

import logging
import json
from typing import Dict, Any, Optional, Literal
from datetime import datetime
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


class NewsClassifier:
    """
    LLM-based classifier for news relevance and sentiment analysis.
    
    Uses structured prompts to classify news across multiple dimensions
    and generate sentiment scores for privacy coin trading.
    """
    
    def __init__(
        self,
        provider: Literal['openai', 'anthropic'] = 'openai',
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize news classifier.
        
        Args:
            provider: LLM provider ('openai' or 'anthropic')
            api_key: API key for the LLM provider
            model: Model name (auto-selects if None)
        """
        self.provider = provider
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Auto-select model based on provider
        if model is None:
            if provider == 'openai':
                self.model = 'gpt-4o-mini'  # Cost-effective, fast
            elif provider == 'anthropic':
                self.model = 'claude-3-haiku-20240307'  # Fast, cost-effective
            else:
                raise ValueError(f"Unknown provider: {provider}")
        else:
            self.model = model
        
        # API endpoints
        self.endpoints = {
            'openai': 'https://api.openai.com/v1/chat/completions',
            'anthropic': 'https://api.anthropic.com/v1/messages'
        }
        
        logger.info(f"Initialized NewsClassifier with {provider} ({self.model})")
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists with proper headers."""
        if self.session is None or self.session.closed:
            headers = {}
            
            if self.provider == 'openai':
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
            elif self.provider == 'anthropic':
                headers = {
                    'x-api-key': self.api_key,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json'
                }
            
            self.session = aiohttp.ClientSession(headers=headers)
    
    async def disconnect(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _build_classification_prompt(self, news_text: str, metadata: Dict[str, Any]) -> str:
        """
        Build the classification prompt for LLM.
        
        Args:
            news_text: The news text to classify
            metadata: Additional metadata (author, source, etc.)
        
        Returns:
            Formatted prompt string
        """
        author_info = metadata.get('author', {})
        author = author_info.get('name', 'Unknown')
        verified = author_info.get('verified', False)
        
        prompt = f"""Analyze the following news item and classify it across multiple dimensions for cryptocurrency trading (specifically privacy coins like Monero/XMR).

NEWS TEXT: "{news_text}"
SOURCE: {author} {"(Verified)" if verified else ""}
TIMESTAMP: {metadata.get('created_at', 'Unknown')}

Please provide scores (0-100) for each dimension:

1. ECONOMIC RELEVANCE (0-100):
   - How relevant is this to economic/monetary policy?
   - Consider: Central bank decisions, inflation data, recession signals, GDP, employment
   - High scores: Fed announcements, inflation reports, major economic policy changes
   - Low scores: Unrelated topics, entertainment, sports

2. CRYPTOCURRENCY RELEVANCE (0-100):
   - How relevant is this to cryptocurrency markets?
   - Consider: Bitcoin price, crypto regulation, exchange news, blockchain developments
   - High scores: Major exchange listings/delistings, regulatory actions, BTC price moves >5%
   - Low scores: Vague mentions, unrelated financial news

3. PRIVACY RELEVANCE (0-100):
   - How relevant is this to privacy, surveillance, and anonymity?
   - Consider: Privacy regulations, surveillance news, encryption laws, data breaches
   - High scores: Privacy coin regulations, surveillance expansions, encryption debates
   - Low scores: General tech news, non-privacy crypto topics

4. INSTABILITY RELEVANCE (0-100):
   - How relevant is this to global financial/political instability?
   - Consider: Wars, sanctions, banking crises, regulatory crackdowns, political unrest
   - High scores: War escalations, bank failures, major sanctions, crypto bans
   - Low scores: Minor policy changes, routine announcements

5. SENTIMENT FOR PRIVACY COINS (bullish/bearish/neutral):
   - Would this news likely increase demand for privacy coins like Monero?
   - Bullish: Increased surveillance, privacy concerns, banking restrictions, capital controls
   - Bearish: Privacy coin bans, exchange delistings, negative regulation
   - Neutral: General market news without specific privacy implications

6. CONFIDENCE (0-100):
   - How confident are you in your analysis?
   - Consider: Clarity of news, source credibility, specificity of information

7. KEY ENTITIES (list):
   - Extract 3-5 key entities mentioned (people, organizations, currencies, countries)

8. BRIEF SUMMARY (1 sentence):
   - Summarize the key point of this news

Respond ONLY with valid JSON in this exact format:
{{
  "economic_score": <0-100>,
  "crypto_score": <0-100>,
  "privacy_score": <0-100>,
  "instability_score": <0-100>,
  "sentiment": "<bullish|bearish|neutral>",
  "confidence": <0-100>,
  "key_entities": ["entity1", "entity2", "entity3"],
  "summary": "<brief summary>",
  "reasoning": "<brief explanation of scores>"
}}"""
        
        return prompt
    
    async def classify_news(
        self,
        news_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify a single news item using LLM.
        
        Args:
            news_text: The news text to classify
            metadata: Optional metadata about the news item
        
        Returns:
            Classification results dictionary
        """
        if metadata is None:
            metadata = {}
        
        await self._ensure_session()
        
        prompt = self._build_classification_prompt(news_text, metadata)
        
        try:
            if self.provider == 'openai':
                result = await self._call_openai(prompt)
            elif self.provider == 'anthropic':
                result = await self._call_anthropic(prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
            
            # Parse and validate result
            parsed = self._parse_classification(result)
            
            # Calculate overall relevance score
            parsed['overall_relevance'] = self._calculate_overall_relevance(parsed)
            
            # Determine if news is significant
            parsed['is_significant'] = self._is_significant(parsed, metadata)
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error classifying news: {e}")
            return self._get_default_classification()
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are an expert financial analyst specializing in cryptocurrency markets and privacy coins. Respond only with valid JSON.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.3,  # Lower temperature for more consistent scoring
            'max_tokens': 500
        }
        
        async with self.session.post(
            self.endpoints['openai'],
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"OpenAI API error: {error_text}")
            
            data = await response.json()
            return data['choices'][0]['message']['content']
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        payload = {
            'model': self.model,
            'max_tokens': 500,
            'temperature': 0.3,
            'system': 'You are an expert financial analyst specializing in cryptocurrency markets and privacy coins. Respond only with valid JSON.',
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        async with self.session.post(
            self.endpoints['anthropic'],
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Anthropic API error: {error_text}")
            
            data = await response.json()
            return data['content'][0]['text']
    
    def _parse_classification(self, llm_response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured classification.
        
        Args:
            llm_response: Raw LLM response text
        
        Returns:
            Parsed classification dictionary
        """
        try:
            # Try to find JSON in the response
            # Sometimes LLMs add markdown code blocks
            response = llm_response.strip()
            
            if '```json' in response:
                # Extract JSON from markdown code block
                start = response.find('```json') + 7
                end = response.find('```', start)
                response = response[start:end].strip()
            elif '```' in response:
                # Extract from generic code block
                start = response.find('```') + 3
                end = response.find('```', start)
                response = response[start:end].strip()
            
            # Parse JSON
            result = json.loads(response)
            
            # Validate and clamp scores
            result['economic_score'] = max(0, min(100, float(result.get('economic_score', 0))))
            result['crypto_score'] = max(0, min(100, float(result.get('crypto_score', 0))))
            result['privacy_score'] = max(0, min(100, float(result.get('privacy_score', 0))))
            result['instability_score'] = max(0, min(100, float(result.get('instability_score', 0))))
            result['confidence'] = max(0, min(100, float(result.get('confidence', 50))))
            
            # Validate sentiment
            sentiment = result.get('sentiment', 'neutral').lower()
            if sentiment not in ['bullish', 'bearish', 'neutral']:
                result['sentiment'] = 'neutral'
            else:
                result['sentiment'] = sentiment
            
            # Ensure key_entities is a list
            if 'key_entities' not in result or not isinstance(result['key_entities'], list):
                result['key_entities'] = []
            
            # Ensure summary exists
            if 'summary' not in result:
                result['summary'] = 'No summary provided'
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.debug(f"Raw response: {llm_response}")
            return self._get_default_classification()
    
    def _calculate_overall_relevance(self, classification: Dict[str, Any]) -> float:
        """
        Calculate overall relevance score from individual dimensions.
        
        Privacy and instability get higher weight for privacy coin trading.
        
        Args:
            classification: Classification dictionary
        
        Returns:
            Overall relevance score (0-100)
        """
        weights = {
            'economic': 0.20,
            'crypto': 0.30,
            'privacy': 0.35,  # Highest weight for privacy coins
            'instability': 0.15
        }
        
        score = (
            classification.get('economic_score', 0) * weights['economic'] +
            classification.get('crypto_score', 0) * weights['crypto'] +
            classification.get('privacy_score', 0) * weights['privacy'] +
            classification.get('instability_score', 0) * weights['instability']
        )
        
        # Boost by confidence
        confidence_factor = classification.get('confidence', 50) / 100
        
        return score * confidence_factor
    
    def _is_significant(
        self,
        classification: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Determine if news is significant enough to act on.
        
        Args:
            classification: Classification results
            metadata: News metadata
        
        Returns:
            True if news is significant
        """
        # High overall relevance
        if classification['overall_relevance'] >= 60:
            return True
        
        # High privacy or instability score
        if classification.get('privacy_score', 0) >= 70:
            return True
        if classification.get('instability_score', 0) >= 70:
            return True
        
        # Strong sentiment from credible source
        if classification.get('sentiment') in ['bullish', 'bearish']:
            if metadata.get('is_priority_source', False):
                if classification['overall_relevance'] >= 40:
                    return True
        
        # High engagement
        if metadata.get('engagement_score', 0) >= 1000:
            if classification['overall_relevance'] >= 50:
                return True
        
        return False
    
    def _get_default_classification(self) -> Dict[str, Any]:
        """Get default classification for errors."""
        return {
            'economic_score': 0,
            'crypto_score': 0,
            'privacy_score': 0,
            'instability_score': 0,
            'sentiment': 'neutral',
            'confidence': 0,
            'overall_relevance': 0,
            'key_entities': [],
            'summary': 'Classification failed',
            'reasoning': 'Error during classification',
            'is_significant': False
        }
    
    async def classify_batch(
        self,
        news_items: list[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> list[Dict[str, Any]]:
        """
        Classify multiple news items concurrently.
        
        Args:
            news_items: List of news items (each with 'text' and optional metadata)
            max_concurrent: Maximum concurrent API calls
        
        Returns:
            List of classification results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def classify_with_semaphore(item):
            async with semaphore:
                text = item.get('text', '')
                metadata = {k: v for k, v in item.items() if k != 'text'}
                classification = await self.classify_news(text, metadata)
                
                # Merge classification with original item
                return {**item, **classification}
        
        tasks = [classify_with_semaphore(item) for item in news_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error classifying item {i}: {result}")
                # Add default classification
                valid_results.append({**news_items[i], **self._get_default_classification()})
            else:
                valid_results.append(result)
        
        return valid_results
