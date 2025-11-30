"""
Metrics collection and tracking system.
"""

import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional


class MetricsCollector:
    """Collect and track system and trading metrics."""

    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.

        Args:
            max_history: Maximum number of historical data points to keep
        """
        self.max_history = max_history

        # Metrics storage
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))

        # API call tracking
        self.api_calls: Dict[str, int] = defaultdict(int)
        self.api_errors: Dict[str, int] = defaultdict(int)

        # Trading metrics
        self.trades_executed: int = 0
        self.trades_successful: int = 0
        self.trades_failed: int = 0

        # Performance tracking
        self.start_time = time.time()

    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            value: Increment value
        """
        self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        """
        Set a gauge metric.

        Args:
            name: Gauge name
            value: Gauge value
        """
        self.gauges[name] = value
        self.histograms[name].append({"timestamp": datetime.utcnow().isoformat(), "value": value})

    def record_timer(self, name: str, duration: float) -> None:
        """
        Record a timer metric.

        Args:
            name: Timer name
            duration: Duration in seconds
        """
        self.timers[name].append(duration)

        # Keep only recent timings
        if len(self.timers[name]) > self.max_history:
            self.timers[name] = self.timers[name][-self.max_history :]

    def record_api_call(self, api_name: str, success: bool = True) -> None:
        """
        Record an API call.

        Args:
            api_name: Name of the API
            success: Whether the call was successful
        """
        self.api_calls[api_name] += 1

        if not success:
            self.api_errors[api_name] += 1

    def record_trade(self, success: bool = True) -> None:
        """
        Record a trade execution.

        Args:
            success: Whether the trade was successful
        """
        self.trades_executed += 1

        if success:
            self.trades_successful += 1
        else:
            self.trades_failed += 1

    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self.counters.get(name, 0)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value."""
        return self.gauges.get(name)

    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """
        Get statistics for a timer.

        Args:
            name: Timer name

        Returns:
            Dictionary with min, max, avg, and count
        """
        timings = self.timers.get(name, [])

        if not timings:
            return {}

        return {
            "min": min(timings),
            "max": max(timings),
            "avg": sum(timings) / len(timings),
            "count": len(timings),
        }

    def get_api_stats(self) -> Dict[str, Dict]:
        """
        Get API call statistics.

        Returns:
            Dictionary with stats for each API
        """
        stats = {}

        for api_name, call_count in self.api_calls.items():
            error_count = self.api_errors.get(api_name, 0)
            success_rate = ((call_count - error_count) / call_count * 100) if call_count > 0 else 0

            stats[api_name] = {
                "total_calls": call_count,
                "errors": error_count,
                "success_rate": success_rate,
            }

        return stats

    def get_trading_stats(self) -> Dict[str, Any]:
        """
        Get trading statistics.

        Returns:
            Dictionary with trading metrics
        """
        success_rate = (
            (self.trades_successful / self.trades_executed * 100) if self.trades_executed > 0 else 0
        )

        return {
            "total_trades": self.trades_executed,
            "successful_trades": self.trades_successful,
            "failed_trades": self.trades_failed,
            "success_rate": success_rate,
        }

    def get_uptime(self) -> float:
        """
        Get system uptime in seconds.

        Returns:
            Uptime in seconds
        """
        return time.time() - self.start_time

    def get_all_metrics(self) -> Dict:
        """
        Get all collected metrics.

        Returns:
            Dictionary with all metrics
        """
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": {name: self.get_timer_stats(name) for name in self.timers},
            "api_stats": self.get_api_stats(),
            "trading_stats": self.get_trading_stats(),
            "uptime_seconds": self.get_uptime(),
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()
        self.histograms.clear()
        self.api_calls.clear()
        self.api_errors.clear()
        self.trades_executed = 0
        self.trades_successful = 0
        self.trades_failed = 0
        self.start_time = time.time()


# Global metrics collector instance
_global_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return _global_metrics
