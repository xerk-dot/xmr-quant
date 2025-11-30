# Trading Strategies

This directory contains different trading strategies for predicting Monero (XMR) price movements.

## Strategy Structure

Each strategy should be implemented in its own subdirectory with the following structure:

```
strategies/
├── strategy_name/
│   ├── __init__.py
│   ├── strategy.py       # Main strategy implementation
│   ├── config.yaml       # Strategy-specific configuration
│   ├── backtest.py       # Backtesting script
│   └── README.md         # Strategy documentation
```

## Base Strategy Interface

All strategies should implement a common interface for consistency:

```python
class BaseStrategy:
    def __init__(self, config):
        """Initialize strategy with configuration."""
        pass

    def generate_signal(self, market_data):
        """
        Generate trading signal based on market data.

        Returns:
            dict: {
                'action': 'buy' | 'sell' | 'hold',
                'confidence': float (0-1),
                'metadata': dict
            }
        """
        pass

    def calculate_position_size(self, signal, portfolio_value):
        """Calculate position size based on signal and portfolio."""
        pass
```

## Available Strategies

Strategies will be implemented here in future iterations.

## Development Guidelines

1. **Backtesting**: Always backtest strategies before live trading
2. **Risk Management**: Integrate with `shared.risk.RiskManager`
3. **Logging**: Use `shared.monitoring.logger` for all logging
4. **Configuration**: Use YAML files for strategy parameters
5. **Documentation**: Document strategy logic, parameters, and expected performance

## Example Usage

```python
from strategies.example_strategy import ExampleStrategy
from shared.market_data import CoinMarketCapClient
from shared.risk import RiskManager

# Initialize components
market_data_client = CoinMarketCapClient()
risk_manager = RiskManager()
strategy = ExampleStrategy(config)

# Get market data
data = market_data_client.get_latest_quotes(['XMR'])

# Generate signal
signal = strategy.generate_signal(data)

# Calculate position size
position_size = risk_manager.calculate_position_size(
    portfolio_value=10000,
    entry_price=data['XMR']['price'],
    stop_loss_price=signal['stop_loss']
)
```
