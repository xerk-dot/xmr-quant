"""
Darknet marketplace scraper for cryptocurrency adoption metrics.

Scrapes public statistics pages from darknet marketplaces to determine
the percentage of transactions using Bitcoin vs Monero.

LEGAL & ETHICAL DISCLAIMER:
- This module scrapes ONLY publicly available statistics pages
- NO personal data, transactions, or listings are collected
- Purpose: Market sentiment analysis for cryptocurrency trading
- Similar to analyzing exchange volumes or on-chain metrics
- DO NOT use for illegal purposes

This is analogous to analyzing:
- Coinbase BTC/XMR volume ratios
- On-chain transaction counts
- Exchange listing preferences
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup
import json

from .tor_client import TorClient

logger = logging.getLogger(__name__)


class MarketplaceScraper:
    """
    Scrapes darknet marketplace statistics to gauge crypto adoption.
    
    Focus: Payment method preferences (BTC vs XMR) as market sentiment indicator.
    """
    
    # Known marketplace onion addresses (these change frequently)
    # NOTE: These are EXAMPLE placeholders. Real onions must be sourced from
    # darknet directories like dark.fail or similar verification services.
    MARKETPLACES = {
        'Example Market 1': {
            'onion': 'examplemarket1xxxxxxxxxxxxxxxxxxxxxxxxx.onion',
            'stats_path': '/stats',
            'enabled': False  # Disabled by default for safety
        },
        'Example Market 2': {
            'onion': 'examplemarket2xxxxxxxxxxxxxxxxxxxxxxxxx.onion',
            'stats_path': '/statistics',
            'enabled': False
        },
        # Add real marketplaces here with valid onion addresses
    }
    
    def __init__(self, tor_client: TorClient):
        """
        Initialize marketplace scraper.
        
        Args:
            tor_client: Connected TorClient instance
        """
        self.tor_client = tor_client
        self.scrape_history: List[Dict] = []
        
    def scrape_marketplace_stats(self, marketplace_name: str) -> Optional[Dict[str, Any]]:
        """
        Scrape statistics from a single marketplace.
        
        Args:
            marketplace_name: Name of marketplace to scrape
            
        Returns:
            Dict with cryptocurrency adoption stats or None if failed
        """
        if marketplace_name not in self.MARKETPLACES:
            logger.error(f"Unknown marketplace: {marketplace_name}")
            return None
        
        marketplace = self.MARKETPLACES[marketplace_name]
        
        if not marketplace.get('enabled', False):
            logger.warning(f"Marketplace {marketplace_name} is disabled")
            return None
        
        try:
            # Construct URL
            onion = marketplace['onion']
            stats_path = marketplace.get('stats_path', '/stats')
            url = f"http://{onion}{stats_path}"
            
            # Fetch page
            html = self.tor_client.fetch_page(url)
            
            if not html:
                logger.error(f"Failed to fetch stats from {marketplace_name}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract cryptocurrency stats (this is marketplace-specific)
            stats = self._parse_payment_stats(soup, marketplace_name)
            
            if stats:
                stats['marketplace'] = marketplace_name
                stats['timestamp'] = datetime.now()
                stats['url'] = url
                
                self.scrape_history.append(stats)
                
                logger.info(
                    f"Scraped {marketplace_name}: "
                    f"BTC={stats.get('btc_percentage', 0):.1f}%, "
                    f"XMR={stats.get('xmr_percentage', 0):.1f}%"
                )
                
                return stats
            else:
                logger.warning(f"No payment stats found for {marketplace_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping {marketplace_name}: {e}")
            return None
    
    def _parse_payment_stats(
        self, 
        soup: BeautifulSoup, 
        marketplace_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse payment method statistics from HTML.
        
        This method needs to be customized per marketplace as each
        has different HTML structure.
        
        Args:
            soup: BeautifulSoup parsed HTML
            marketplace_name: Name of marketplace
            
        Returns:
            Dict with payment stats or None
        """
        try:
            # Generic extraction patterns (customize per marketplace)
            
            # Pattern 1: Look for stats tables
            stats_table = soup.find('table', class_=re.compile(r'stats|statistics', re.I))
            if stats_table:
                return self._extract_from_table(stats_table)
            
            # Pattern 2: Look for JSON data in script tags
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                if 'payment' in script.text.lower() or 'crypto' in script.text.lower():
                    try:
                        data = json.loads(script.text)
                        if 'bitcoin' in str(data).lower():
                            return self._extract_from_json(data)
                    except:
                        continue
            
            # Pattern 3: Look for specific text patterns
            text = soup.get_text()
            
            # Search for percentage patterns like "Bitcoin: 45%" "Monero: 55%"
            btc_match = re.search(r'Bitcoin[:\s]+(\d+\.?\d*)%', text, re.I)
            xmr_match = re.search(r'Monero[:\s]+(\d+\.?\d*)%', text, re.I)
            
            if btc_match and xmr_match:
                btc_pct = float(btc_match.group(1))
                xmr_pct = float(xmr_match.group(1))
                
                return {
                    'btc_percentage': btc_pct,
                    'xmr_percentage': xmr_pct,
                    'total_transactions': None,  # Unknown
                    'extraction_method': 'text_pattern'
                }
            
            # Pattern 4: Search for transaction counts
            btc_count_match = re.search(r'Bitcoin.*?(\d+,?\d*)\s+transactions?', text, re.I)
            xmr_count_match = re.search(r'Monero.*?(\d+,?\d*)\s+transactions?', text, re.I)
            
            if btc_count_match and xmr_count_match:
                btc_count = int(btc_count_match.group(1).replace(',', ''))
                xmr_count = int(xmr_count_match.group(1).replace(',', ''))
                total = btc_count + xmr_count
                
                if total > 0:
                    return {
                        'btc_percentage': (btc_count / total) * 100,
                        'xmr_percentage': (xmr_count / total) * 100,
                        'btc_count': btc_count,
                        'xmr_count': xmr_count,
                        'total_transactions': total,
                        'extraction_method': 'transaction_counts'
                    }
            
            logger.debug(f"Could not extract payment stats from {marketplace_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing payment stats: {e}")
            return None
    
    def _extract_from_table(self, table) -> Optional[Dict]:
        """Extract stats from HTML table."""
        try:
            rows = table.find_all('tr')
            btc_pct = None
            xmr_pct = None
            
            for row in rows:
                text = row.get_text().lower()
                if 'bitcoin' in text or 'btc' in text:
                    match = re.search(r'(\d+\.?\d*)%', text)
                    if match:
                        btc_pct = float(match.group(1))
                elif 'monero' in text or 'xmr' in text:
                    match = re.search(r'(\d+\.?\d*)%', text)
                    if match:
                        xmr_pct = float(match.group(1))
            
            if btc_pct is not None and xmr_pct is not None:
                return {
                    'btc_percentage': btc_pct,
                    'xmr_percentage': xmr_pct,
                    'extraction_method': 'html_table'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting from table: {e}")
            return None
    
    def _extract_from_json(self, data: Dict) -> Optional[Dict]:
        """Extract stats from JSON data."""
        try:
            # Look for payment/crypto related keys
            if 'payments' in data:
                payments = data['payments']
                if 'bitcoin' in payments and 'monero' in payments:
                    btc_val = payments['bitcoin']
                    xmr_val = payments['monero']
                    
                    # Could be percentages or counts
                    if isinstance(btc_val, (int, float)) and isinstance(xmr_val, (int, float)):
                        total = btc_val + xmr_val
                        if total > 0:
                            return {
                                'btc_percentage': (btc_val / total) * 100,
                                'xmr_percentage': (xmr_val / total) * 100,
                                'extraction_method': 'json_data'
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting from JSON: {e}")
            return None
    
    def scrape_all_marketplaces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape statistics from all enabled marketplaces.
        
        Args:
            limit: Maximum number of marketplaces to scrape
            
        Returns:
            List of scrape results
        """
        results = []
        scraped = 0
        
        for marketplace_name, config in self.MARKETPLACES.items():
            if scraped >= limit:
                break
            
            if not config.get('enabled', False):
                continue
            
            logger.info(f"Scraping marketplace {scraped + 1}/{limit}: {marketplace_name}")
            
            stats = self.scrape_marketplace_stats(marketplace_name)
            if stats:
                results.append(stats)
                scraped += 1
            
            # Rate limiting - be respectful
            import time
            time.sleep(5)  # 5 second delay between requests
        
        return results
    
    def calculate_aggregate_stats(
        self, 
        results: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Calculate aggregate statistics across all marketplaces.
        
        Args:
            results: Optional list of scrape results. If None, uses scrape_history.
            
        Returns:
            Dict with aggregate statistics
        """
        if results is None:
            results = self.scrape_history
        
        if not results:
            return {
                'status': 'no_data',
                'message': 'No marketplace data available'
            }
        
        # Calculate weighted average based on transaction counts (if available)
        total_btc_weighted = 0
        total_xmr_weighted = 0
        total_weight = 0
        
        marketplaces_included = []
        
        for result in results:
            btc_pct = result.get('btc_percentage', 0)
            xmr_pct = result.get('xmr_percentage', 0)
            tx_count = result.get('total_transactions', 1)  # Default weight of 1
            
            total_btc_weighted += btc_pct * tx_count
            total_xmr_weighted += xmr_pct * tx_count
            total_weight += tx_count
            
            marketplaces_included.append(result.get('marketplace', 'unknown'))
        
        if total_weight == 0:
            return {
                'status': 'error',
                'message': 'Invalid data weights'
            }
        
        avg_btc_pct = total_btc_weighted / total_weight
        avg_xmr_pct = total_xmr_weighted / total_weight
        
        # Calculate trend (if we have historical data)
        xmr_trend = self._calculate_xmr_trend()
        
        return {
            'status': 'success',
            'timestamp': datetime.now(),
            'marketplaces_count': len(results),
            'marketplaces_included': marketplaces_included,
            'btc_percentage': avg_btc_pct,
            'xmr_percentage': avg_xmr_pct,
            'xmr_adoption_trend': xmr_trend,  # 'increasing', 'decreasing', 'stable'
            'confidence': self._calculate_confidence(results),
            'raw_results': results
        }
    
    def _calculate_xmr_trend(self) -> str:
        """Calculate XMR adoption trend over time."""
        if len(self.scrape_history) < 2:
            return 'insufficient_data'
        
        # Compare last 3 vs previous 3 scrapes
        recent_scrapes = self.scrape_history[-3:]
        older_scrapes = self.scrape_history[-6:-3] if len(self.scrape_history) >= 6 else []
        
        if not older_scrapes:
            return 'insufficient_data'
        
        recent_avg = sum(s.get('xmr_percentage', 0) for s in recent_scrapes) / len(recent_scrapes)
        older_avg = sum(s.get('xmr_percentage', 0) for s in older_scrapes) / len(older_scrapes)
        
        diff = recent_avg - older_avg
        
        if diff > 2:
            return 'increasing'
        elif diff < -2:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_confidence(self, results: List[Dict]) -> float:
        """
        Calculate confidence score for the aggregate statistics.
        
        Based on:
        - Number of marketplaces scraped
        - Consistency of results
        - Availability of transaction counts
        """
        if not results:
            return 0.0
        
        # Base confidence on sample size
        sample_confidence = min(len(results) / 10, 1.0)  # Max at 10 marketplaces
        
        # Check consistency (low variance = higher confidence)
        xmr_percentages = [r.get('xmr_percentage', 0) for r in results]
        if len(xmr_percentages) > 1:
            import statistics
            std_dev = statistics.stdev(xmr_percentages)
            consistency_confidence = max(0, 1 - (std_dev / 50))  # Penalize high variance
        else:
            consistency_confidence = 0.5
        
        # Check if we have transaction counts (more reliable)
        has_tx_counts = sum(1 for r in results if r.get('total_transactions') is not None)
        tx_confidence = has_tx_counts / len(results)
        
        # Weighted average
        overall_confidence = (
            sample_confidence * 0.4 +
            consistency_confidence * 0.4 +
            tx_confidence * 0.2
        )
        
        return overall_confidence

