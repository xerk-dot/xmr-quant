"""
Risk management system for position sizing and risk controls.
"""

from typing import Dict, Optional, Tuple

from ..config import Config


class RiskManager:
    """Risk management for trading operations."""

    def __init__(
        self,
        max_position_size: Optional[float] = None,
        max_drawdown_percent: Optional[float] = None,
        risk_per_trade_percent: Optional[float] = None,
    ):
        """
        Initialize risk manager.

        Args:
            max_position_size: Maximum position size in USD
            max_drawdown_percent: Maximum allowed drawdown percentage
            risk_per_trade_percent: Risk per trade as percentage of portfolio
        """
        self.max_position_size = max_position_size or Config.MAX_POSITION_SIZE
        self.max_drawdown_percent = max_drawdown_percent or Config.MAX_DRAWDOWN_PERCENT
        self.risk_per_trade_percent = risk_per_trade_percent or Config.RISK_PER_TRADE_PERCENT

        # Track portfolio metrics
        self.peak_portfolio_value = 0.0
        self.current_portfolio_value = 0.0

    def calculate_position_size(
        self, portfolio_value: float, entry_price: float, stop_loss_price: float
    ) -> float:
        """
        Calculate position size based on risk parameters.

        Args:
            portfolio_value: Current portfolio value in USD
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price

        Returns:
            Position size in units of the asset
        """
        # Calculate risk amount in USD
        risk_amount = portfolio_value * (self.risk_per_trade_percent / 100)

        # Calculate price risk per unit
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            return 0.0

        # Calculate position size
        position_size = risk_amount / price_risk

        # Apply maximum position size limit
        max_units = self.max_position_size / entry_price
        position_size = min(position_size, max_units)

        return position_size

    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        atr: Optional[float] = None,
        atr_multiplier: float = 2.0,
        fixed_percent: Optional[float] = None,
    ) -> float:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            side: 'buy' or 'sell'
            atr: Average True Range (for ATR-based stops)
            atr_multiplier: Multiplier for ATR
            fixed_percent: Fixed percentage for stop loss

        Returns:
            Stop loss price
        """
        if atr is not None:
            # ATR-based stop loss
            stop_distance = atr * atr_multiplier
        elif fixed_percent is not None:
            # Fixed percentage stop loss
            stop_distance = entry_price * (fixed_percent / 100)
        else:
            # Default to 2% stop loss
            stop_distance = entry_price * 0.02

        if side.lower() == "buy":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def calculate_take_profit(
        self, entry_price: float, stop_loss_price: float, side: str, risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate take profit price based on risk-reward ratio.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            side: 'buy' or 'sell'
            risk_reward_ratio: Desired risk-reward ratio

        Returns:
            Take profit price
        """
        risk = abs(entry_price - stop_loss_price)
        reward = risk * risk_reward_ratio

        if side.lower() == "buy":
            return entry_price + reward
        else:
            return entry_price - reward

    def check_drawdown(
        self, current_value: float, peak_value: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Check if current drawdown exceeds maximum allowed.

        Args:
            current_value: Current portfolio value
            peak_value: Peak portfolio value (optional, will use tracked value if not provided)

        Returns:
            Tuple of (is_within_limit, current_drawdown_percent)
        """
        if peak_value is not None:
            self.peak_portfolio_value = max(self.peak_portfolio_value, peak_value)
        else:
            self.peak_portfolio_value = max(self.peak_portfolio_value, current_value)

        self.current_portfolio_value = current_value

        if self.peak_portfolio_value == 0:
            return True, 0.0

        drawdown_percent = (
            (self.peak_portfolio_value - current_value) / self.peak_portfolio_value
        ) * 100

        is_within_limit = drawdown_percent <= self.max_drawdown_percent

        return is_within_limit, drawdown_percent

    def validate_order(
        self, order_value: float, portfolio_value: float, current_positions_value: float = 0.0
    ) -> Tuple[bool, str]:
        """
        Validate if an order meets risk management criteria.

        Args:
            order_value: Value of the order in USD
            portfolio_value: Current portfolio value
            current_positions_value: Total value of current positions

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check if order exceeds max position size
        if order_value > self.max_position_size:
            return (
                False,
                f"Order value ${order_value:.2f} exceeds max position size ${self.max_position_size:.2f}",
            )

        # Check if total exposure would be too high
        total_exposure = (current_positions_value + order_value) / portfolio_value * 100
        if total_exposure > 95:  # Don't use more than 95% of portfolio
            return False, f"Total exposure {total_exposure:.1f}% would exceed 95% of portfolio"

        # Check drawdown
        is_within_drawdown, current_drawdown = self.check_drawdown(portfolio_value)
        if not is_within_drawdown:
            return (
                False,
                f"Current drawdown {current_drawdown:.2f}% exceeds maximum {self.max_drawdown_percent:.2f}%",
            )

        return True, "Order validated"

    def calculate_risk_metrics(
        self, returns: list, risk_free_rate: float = 0.02
    ) -> Dict[str, float]:
        """
        Calculate risk metrics for a series of returns.

        Args:
            returns: List of returns
            risk_free_rate: Risk-free rate for Sharpe ratio calculation

        Returns:
            Dictionary of risk metrics
        """
        if not returns:
            return {}

        import numpy as np

        returns_array = np.array(returns)

        # Calculate metrics
        total_return = np.prod(1 + returns_array) - 1
        avg_return = np.mean(returns_array)
        volatility = np.std(returns_array)

        # Sharpe ratio
        sharpe_ratio = (avg_return - risk_free_rate / 252) / volatility if volatility > 0 else 0

        # Maximum drawdown
        cumulative = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)

        # Win rate
        winning_trades = np.sum(returns_array > 0)
        total_trades = len(returns_array)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        return {
            "total_return": total_return,
            "avg_return": avg_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": total_trades,
        }
