# XMR Quant Trading System

A quantitative trading system for predicting and trading Monero (XMR) price movements. Built with a modular architecture to support multiple trading strategies and comprehensive risk management.

## 🎯 Overview

This repository provides a professional-grade framework for algorithmic trading of Monero (XMR) with:

- **Multi-strategy support**: Modular architecture for implementing and testing different trading strategies
- **Risk management**: Position sizing, stop-loss/take-profit, and drawdown monitoring
- **Real-time monitoring**: Comprehensive logging, metrics collection, and alerting
- **Market data integration**: CoinMarketCap API for multi-asset price data (BTC, XMR, ZEC, LTC)
- **Exchange integration**: Kraken API for order execution and portfolio management
- **Notifications**: Telegram bot for real-time trade alerts and system status

## 📁 Project Structure

```
xmr-quant/
├── shared/                 # Shared utilities across all strategies
│   ├── config.py          # Centralized configuration management
│   ├── market_data/       # Market data collection and processing
│   ├── exchange/          # Exchange API integration (Kraken)
│   ├── risk/              # Risk management and position sizing
│   ├── monitoring/        # Logging and metrics collection
│   └── notification/      # Telegram bot for alerts
├── strategies/            # Trading strategy implementations
│   └── README.md         # Strategy development guidelines
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
└── pyproject.toml        # Project configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- API keys for:
  - [CoinMarketCap](https://coinmarketcap.com/api/) (market data)
  - [Kraken](https://www.kraken.com/features/api) (exchange)
  - [Telegram Bot](https://core.telegram.org/bots#creating-a-new-bot) (notifications)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/xerk-dot/xmr-quant.git
   cd xmr-quant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up pre-commit hooks** (optional but recommended)
   ```bash
   ./setup_precommit.sh
   # or manually:
   pre-commit install
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Configuration

Edit `.env` with your credentials:

```bash
# CoinMarketCap API
COINMARKETCAP_API_KEY=your_api_key_here

# Kraken API
KRAKEN_API_KEY=your_api_key_here
KRAKEN_API_SECRET=your_api_secret_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Trading Parameters
MAX_POSITION_SIZE=1000.0
MAX_DRAWDOWN_PERCENT=10.0
RISK_PER_TRADE_PERCENT=2.0
```

## 📊 Shared Modules

### Market Data (`shared/market_data/`)

- **CoinMarketCapClient**: Fetch real-time and historical price data for BTC, XMR, ZEC, LTC
- **DataProcessor**: Technical indicators (RSI, Bollinger Bands), moving averages, volatility calculations

```python
from shared.market_data import CoinMarketCapClient, DataProcessor

client = CoinMarketCapClient()
quotes = client.get_latest_quotes(['XMR'])
print(f"XMR Price: ${quotes['XMR']['price']:.2f}")
```

### Exchange Integration (`shared/exchange/`)

- **KrakenClient**: Full Kraken API integration for order execution and portfolio management
- Support for market orders, limit orders, order cancellation, and trade history

```python
from shared.exchange import KrakenClient

kraken = KrakenClient()
balance = kraken.get_account_balance()
ticker = kraken.get_ticker('XMRUSD')
```

### Risk Management (`shared/risk/`)

- **RiskManager**: Position sizing, stop-loss/take-profit calculation, drawdown monitoring
- Risk metrics: Sharpe ratio, maximum drawdown, win rate

```python
from shared.risk import RiskManager

risk_mgr = RiskManager()
position_size = risk_mgr.calculate_position_size(
    portfolio_value=10000,
    entry_price=150.0,
    stop_loss_price=145.0
)
```

### Monitoring (`shared/monitoring/`)

- **Logger**: Structured logging with file rotation
- **MetricsCollector**: Track API calls, trade execution, system performance

### Notifications (`shared/notification/`)

- **TelegramNotifier**: Real-time alerts for trades, system status, and performance reports

```python
from shared.notification import TelegramNotifier

notifier = TelegramNotifier()
notifier.send_trade_notification(
    symbol='XMR',
    side='buy',
    price=150.0,
    volume=10.0
)
```

## 🧠 Trading Strategies

The `strategies/` directory is designed to house multiple trading strategies, each in its own subdirectory. Strategies are currently under development and will be implemented based on various market analysis approaches.

### Strategy Framework

Each strategy should implement:
- Signal generation based on market data
- Position sizing logic
- Entry/exit criteria
- Backtesting capabilities

See [`strategies/README.md`](strategies/README.md) for detailed development guidelines.

### Planned Strategy Categories

- **Technical Analysis**: Price action, indicators, chart patterns
- **Machine Learning**: Predictive models using historical data
- **Market Correlation**: Cross-asset analysis (BTC correlation, privacy coin dynamics)
- **Sentiment Analysis**: News and social media sentiment

*Individual strategy implementations will be added in future updates.*

## 🛠️ Development

### Code Quality

This project uses pre-commit hooks to ensure code quality:

- **Ruff**: Fast Python linter and formatter
- **Mypy**: Static type checking
- **Additional checks**: Trailing whitespace, YAML validation, private key detection

Run manually:
```bash
pre-commit run --all-files
```

### Testing

```bash
# Run all tests (when implemented)
pytest

# Run specific test file
pytest tests/test_strategy.py
```

### Project Configuration

- **pyproject.toml**: Ruff and mypy configuration
- **requirements.txt**: Python dependencies
- **.pre-commit-config.yaml**: Pre-commit hook configuration

## 📈 Usage Example

```python
from shared.market_data import CoinMarketCapClient
from shared.exchange import KrakenClient
from shared.risk import RiskManager
from shared.monitoring import setup_logger
from shared.notification import TelegramNotifier

# Initialize components
logger = setup_logger('trading_bot')
cmc = CoinMarketCapClient()
kraken = KrakenClient()
risk_mgr = RiskManager()
notifier = TelegramNotifier()

# Get market data
quotes = cmc.get_latest_quotes(['XMR'])
xmr_price = quotes['XMR']['price']

# Calculate position size
position_size = risk_mgr.calculate_position_size(
    portfolio_value=10000,
    entry_price=xmr_price,
    stop_loss_price=xmr_price * 0.98  # 2% stop loss
)

# Place order (validation mode)
order = kraken.place_market_order(
    pair='XMRUSD',
    side='buy',
    volume=position_size,
    validate=True  # Validate without executing
)

# Send notification
notifier.send_trade_notification(
    symbol='XMR',
    side='buy',
    price=xmr_price,
    volume=position_size
)
```

## 🔒 Security

- **Never commit API keys**: Use `.env` file (gitignored)
- **Pre-commit hooks**: Detect private keys before commit
- **Validation mode**: Test orders without execution

## 📝 License

This project is for educational and research purposes. Use at your own risk. Cryptocurrency trading involves substantial risk of loss.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Ensure pre-commit hooks pass
4. Submit a pull request

## 📧 Contact

For questions or suggestions, please open an issue on GitHub.

---

**Disclaimer**: This software is provided "as is" without warranty. Trading cryptocurrencies carries significant financial risk. Always do your own research and never invest more than you can afford to lose.
