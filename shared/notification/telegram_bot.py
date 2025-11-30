"""
Telegram bot for notifications and alerts.
"""

import asyncio
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

from ..config import Config
from ..monitoring.logger import get_logger

logger = get_logger(__name__)


class TelegramNotifier:
    """Telegram bot for sending notifications."""

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier.

        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID
        """
        self.token = token or Config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or Config.TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None

    async def send_message_async(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message asynchronously.

        Args:
            message: Message text
            parse_mode: Parse mode ('HTML' or 'Markdown')

        Returns:
            True if successful, False otherwise
        """
        if not self.bot or not self.chat_id:
            logger.warning("Telegram bot not configured")
            return False

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode=parse_mode)
            logger.info(f"Sent Telegram message: {message[:50]}...")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message synchronously.

        Args:
            message: Message text
            parse_mode: Parse mode ('HTML' or 'Markdown')

        Returns:
            True if successful, False otherwise
        """
        return asyncio.run(self.send_message_async(message, parse_mode))

    def send_trade_notification(
        self, symbol: str, side: str, price: float, volume: float, status: str = "executed"
    ) -> bool:
        """
        Send a trade notification.

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            price: Execution price
            volume: Trade volume
            status: Trade status

        Returns:
            True if successful
        """
        emoji = "🟢" if side.lower() == "buy" else "🔴"
        message = f"""
{emoji} <b>Trade {status.upper()}</b>

<b>Symbol:</b> {symbol}
<b>Side:</b> {side.upper()}
<b>Price:</b> ${price:.2f}
<b>Volume:</b> {volume:.4f}
<b>Value:</b> ${price * volume:.2f}
"""
        return self.send_message(message.strip())

    def send_alert(self, title: str, message: str, level: str = "info") -> bool:
        """
        Send an alert notification.

        Args:
            title: Alert title
            message: Alert message
            level: Alert level ('info', 'warning', 'error')

        Returns:
            True if successful
        """
        emoji_map = {"info": "ℹ️", "warning": "⚠️", "error": "🚨"}

        emoji = emoji_map.get(level.lower(), "ℹ️")
        formatted_message = f"""
{emoji} <b>{title}</b>

{message}
"""
        return self.send_message(formatted_message.strip())

    def send_performance_report(self, metrics: dict) -> bool:
        """
        Send a performance report.

        Args:
            metrics: Dictionary of performance metrics

        Returns:
            True if successful
        """
        message = "📊 <b>Performance Report</b>\n\n"

        for key, value in metrics.items():
            if isinstance(value, float):
                message += f"<b>{key}:</b> {value:.2f}\n"
            else:
                message += f"<b>{key}:</b> {value}\n"

        return self.send_message(message.strip())
