"""
Tor client for accessing onion sites.

Uses tor+requests or stem library to connect to Tor network
and scrape darknet marketplace statistics.

LEGAL DISCLAIMER:
This module is for research and market analysis purposes only.
Scraping publicly available marketplace statistics to gauge cryptocurrency
adoption rates is analogous to analyzing on-chain metrics or exchange volumes.
DO NOT use this to facilitate illegal activities.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime
import aiohttp
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class TorClient:
    """
    Client for making requests through Tor network.
    
    Connects via SOCKS5 proxy to local Tor instance.
    Requires Tor to be running (e.g., Tor Browser or system tor daemon).
    """
    
    def __init__(
        self,
        tor_proxy_host: str = '127.0.0.1',
        tor_proxy_port: int = 9050,
        timeout: int = 30
    ):
        """
        Initialize Tor client.
        
        Args:
            tor_proxy_host: Tor SOCKS5 proxy host
            tor_proxy_port: Tor SOCKS5 proxy port (9050 for system tor, 9150 for Tor Browser)
            timeout: Request timeout in seconds
        """
        self.tor_proxy_host = tor_proxy_host
        self.tor_proxy_port = tor_proxy_port
        self.timeout = timeout
        
        # SOCKS5 proxy URL for Tor
        self.proxies = {
            'http': f'socks5h://{tor_proxy_host}:{tor_proxy_port}',
            'https': f'socks5h://{tor_proxy_host}:{tor_proxy_port}'
        }
        
        self.session: Optional[requests.Session] = None
        self.aio_session: Optional[aiohttp.ClientSession] = None
        
    def connect(self) -> bool:
        """
        Establish connection to Tor network.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.session = requests.Session()
            self.session.proxies.update(self.proxies)
            
            # Test connection by checking Tor
            response = self.session.get(
                'https://check.torproject.org/api/ip',
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('IsTor'):
                    logger.info(f"Connected to Tor network. IP: {data.get('IP')}")
                    return True
                else:
                    logger.error("Connected but not using Tor network")
                    return False
            else:
                logger.error(f"Failed to verify Tor connection: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Tor: {e}")
            return False
    
    async def connect_async(self) -> bool:
        """Establish async connection to Tor network."""
        try:
            # For async, we'll use aiohttp with socks proxy
            import aiohttp_socks
            
            connector = aiohttp_socks.ProxyConnector.from_url(
                f'socks5://{self.tor_proxy_host}:{self.tor_proxy_port}'
            )
            
            self.aio_session = aiohttp.ClientSession(connector=connector)
            
            # Test connection
            async with self.aio_session.get(
                'https://check.torproject.org/api/ip',
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                if data.get('IsTor'):
                    logger.info(f"Async connected to Tor network. IP: {data.get('IP')}")
                    return True
                else:
                    logger.error("Connected but not using Tor network")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to connect to Tor (async): {e}")
            return False
    
    def fetch_page(self, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        """
        Fetch a page through Tor.
        
        Args:
            url: URL to fetch (.onion or clearnet)
            headers: Optional HTTP headers
            
        Returns:
            Page HTML content or None if failed
        """
        if not self.session:
            logger.error("Not connected to Tor. Call connect() first.")
            return None
        
        try:
            default_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'
            }
            if headers:
                default_headers.update(headers)
            
            logger.info(f"Fetching: {url[:50]}...")
            
            response = self.session.get(
                url,
                headers=default_headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                logger.debug(f"Successfully fetched {url}")
                return response.text
            else:
                logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def fetch_page_async(self, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        """Async version of fetch_page."""
        if not self.aio_session:
            logger.error("Not connected to Tor (async). Call connect_async() first.")
            return None
        
        try:
            default_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'
            }
            if headers:
                default_headers.update(headers)
            
            logger.info(f"Fetching (async): {url[:50]}...")
            
            async with self.aio_session.get(
                url,
                headers=default_headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    logger.debug(f"Successfully fetched {url}")
                    return text
                else:
                    logger.warning(f"Failed to fetch {url}: Status {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def disconnect(self):
        """Close connections."""
        if self.session:
            self.session.close()
            self.session = None
        logger.info("Disconnected from Tor")
    
    async def disconnect_async(self):
        """Close async connections."""
        if self.aio_session:
            await self.aio_session.close()
            self.aio_session = None
        logger.info("Disconnected from Tor (async)")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Tor connection and get circuit info.
        
        Returns:
            Dict with connection status and info
        """
        if not self.session:
            return {'connected': False, 'error': 'No session'}
        
        try:
            # Check Tor status
            response = self.session.get(
                'https://check.torproject.org/api/ip',
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'connected': True,
                    'using_tor': data.get('IsTor', False),
                    'ip': data.get('IP'),
                    'timestamp': datetime.now()
                }
            else:
                return {
                    'connected': False,
                    'error': f'Status code: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }

