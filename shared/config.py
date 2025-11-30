"""
Configuration management for XMR quant trading system.
Loads environment variables and provides centralized access to configuration.
"""

import os
from typing import List, Tuple

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration management."""

    # CoinMarketCap API
    COINMARKETCAP_API_KEY: str = os.getenv("COINMARKETCAP_API_KEY", "")
    COINMARKETCAP_BASE_URL: str = "https://pro-api.coinmarketcap.com/v1"

    # Kraken API
    KRAKEN_API_KEY: str = os.getenv("KRAKEN_API_KEY", "")
    KRAKEN_API_SECRET: str = os.getenv("KRAKEN_API_SECRET", "")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Trading Configuration
    MAX_POSITION_SIZE: float = float(os.getenv("MAX_POSITION_SIZE", "1000.0"))
    MAX_DRAWDOWN_PERCENT: float = float(os.getenv("MAX_DRAWDOWN_PERCENT", "10.0"))
    RISK_PER_TRADE_PERCENT: float = float(os.getenv("RISK_PER_TRADE_PERCENT", "2.0"))

    # Supported cryptocurrencies
    SUPPORTED_SYMBOLS: list = ["BTC", "XMR", "ZEC", "LTC"]

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Data storage
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    LOGS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

    @classmethod
    def validate(cls) -> Tuple[bool, List[str]]:
        """
        Validate that all required configuration is present.

        Returns:
            Tuple of (is_valid, list of missing keys)
        """
        missing = []

        if not cls.COINMARKETCAP_API_KEY:
            missing.append("COINMARKETCAP_API_KEY")

        if not cls.KRAKEN_API_KEY:
            missing.append("KRAKEN_API_KEY")

        if not cls.KRAKEN_API_SECRET:
            missing.append("KRAKEN_API_SECRET")

        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")

        if not cls.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")

        return len(missing) == 0, missing

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure data and logs directories exist."""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)


# Create directories on import
Config.ensure_directories()
