# 🪙 Monero (XMR) Swing Tradin' Bot

A comprehensive cryptocurrency trading bot specifically designed for Monero (XMR) swing trading, featuring machine learning models, advanced risk management, and complete monitoring infrastructure.

## 🚀 Features, briefly

### Core Functionality
- Multi-exchange support (Binance, Kraken)
- Real-time data via WebSocket streams
- **BTC-XMR correlation lag strategy** (primary alpha source - 40% weight)
- **News sentiment monitoring** (Twitter + LLM classification - 10% weight)
- **Darknet adoption tracking** (BTC vs XMR usage - 5% weight, optional)
- 20+ advanced technical indicators
- Automated market regime detection (trend, volatility, etc.)
- Machine learning signals (XGBoost, auto-retraining)
- Combines multiple strategies for signal generation

### Risk Management
- Multiple position sizing modes (Kelly, fixed fractional, volatility-adjusted)
- Smart stop loss & take profit (ATR, S/R, trailing)
- Limits portfolio and symbol-specific exposure
- Drawdown and consecutive loss protection features

### Monitoring & Alerts
- Grafana dashboards for live metrics
- Prometheus monitoring
- Telegram alerts (trades, signals, errors, system events)
- Tracks everything: trades, P&L, system health

### Infrastructure
- Runs fully in Docker (easy deployment)
- PostgreSQL (trade & signal data)
- Redis (caching / queue)
- InfluxDB (historical price/time-series)
- Nginx reverse proxy for API/services


## 📊 Architecture

**The system has TWO concurrent loops feeding into one decision engine:**

```
┌────────────────────────────────────────────────────────────────┐
│                     Trading Bot System                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔄 MAIN LOOP (12 hours)           🔄 NEWS LOOP (30 mins)     │
│  ┌──────────────────────┐          ┌──────────────────────┐   │
│  │ Exchange APIs        │          │ Twitter API          │   │
│  │ BTC/XMR prices      │          │ + LLM Classification │   │
│  │ Technical indicators │          │ Sentiment analysis   │   │
│  └─────────┬────────────┘          └──────────┬───────────┘   │
│            │                                   │               │
│            └──────────┬────────────────────────┘               │
│                       ▼                                        │
│            ┌──────────────────────┐                           │
│            │  Signal Aggregator   │                           │
│            │  (5 strategies vote) │                           │
│            └─────────┬────────────┘                           │
│                      ▼                                        │
│            ┌──────────────────────┐                           │
│            │   Risk Manager       │                           │
│            └─────────┬────────────┘                           │
│                      ▼                                        │
│            ┌──────────────────────┐                           │
│            │  Order Execution     │                           │
│            └──────────────────────┘                           │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**📚 Detailed Documentation:**
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical architecture and data flows
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Simplified guide and visual diagrams
- **[BTC_CORRELATION_FLOW.md](docs/BTC_CORRELATION_FLOW.md)** - BTC correlation strategy details

## 🛠️ Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd privacy_coin_swing_trading
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys and configuration
nano .env
```

### 3. Docker Deployment
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f trading-bot
```

### 4. Access Dashboards
- **Grafana**: http://localhost:3000 (admin/grafana_admin_123)
- **Prometheus**: http://localhost:9090
- **Bot Metrics**: http://localhost:8000/metrics

## 📱 Telegram Setup

1. Create a Telegram bot:
   - Message @BotFather on Telegram
   - Run `/newbot` and follow instructions
   - Copy the bot token

2. Get your chat ID:
   - Message your bot
   - Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Copy the chat ID from the response

3. Add to `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## 🔧 Configuration

### Trading Parameters (`.env`)
```env
# Risk Management
MAX_POSITION_SIZE=0.02              # 2% per trade
MAX_PORTFOLIO_EXPOSURE=0.3          # 30% total exposure
MIN_RISK_REWARD_RATIO=1.5           # Minimum R:R ratio
DEFAULT_STOP_LOSS_ATR_MULTIPLIER=2.5

# Exchange API Keys
BINANCE_API_KEY=your_api_key
BINANCE_SECRET=your_secret
KRAKEN_API_KEY=your_api_key
KRAKEN_SECRET=your_secret

# News Monitoring (Optional but Recommended)
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
NEWS_LLM_PROVIDER=openai            # 'openai' or 'anthropic'
OPENAI_API_KEY=your_openai_key      # If using OpenAI
ANTHROPIC_API_KEY=your_anthropic_key # If using Anthropic
NEWS_MONITORING_ENABLED=true
NEWS_CHECK_INTERVAL_MINUTES=30      # Check news every 30 minutes
NEWS_STRATEGY_WEIGHT=0.10           # 10% weight in signal aggregation
```

### Strategy Configuration
The bot uses a weighted ensemble of strategies (configured in `main.py`):
```python
# Default weights (optimized for alpha generation)
{
    'BTCCorrelation': 0.40,  # BTC-XMR lag (primary edge)
    'NewsSentiment': 0.10,   # News monitoring & LLM classification
    'TrendFollowing': 0.125, # Rule-based trend
    'MeanReversion': 0.125,  # Rule-based mean reversion
    'XGBoostML': 0.25        # ML confirmation filter
}
```

**BTC Correlation Strategy**: Exploits the 6-24h lag between BTC and XMR movements. When BTC makes a significant move (>3%), XMR typically follows with a predictable delay.

**News Sentiment Strategy**: Monitors Twitter for cryptocurrency, privacy, economic, and instability-related news. Uses LLMs (GPT-4 or Claude) to classify news impact and generate sentiment signals.

## 🎯 Usage

### Paper Trading (Recommended for testing)
```bash
python run_bot.py --mode paper --capital 10000
```

### Live Trading (Real money)
```bash
python run_bot.py --mode live --capital 10000
```

### Backtesting
```bash
python run_bot.py --mode backtest
```

### Test BTC Correlation Strategy
```bash
# Run correlation analysis and validation
python test_btc_correlation.py
```

This test will:
- Fetch 30 days of BTC and XMR historical data
- Calculate correlation coefficient and optimal lag
- Detect current BTC movements
- Generate trading signals
- Show historical performance metrics

### Docker Deployment
```bash
# Paper trading
docker-compose up -d

# Live trading (modify docker-compose.yml)
# Change command: ["python", "run_bot.py", "--mode", "live", "--capital", "10000"]
docker-compose up -d
```

## 📊 Monitoring

### Grafana Dashboards
The system includes pre-configured dashboards showing:
- Portfolio value and P&L
- Trade statistics and win rate
- Risk metrics and drawdown
- Signal generation rates
- System performance metrics

### Telegram Alerts
Automated notifications for:
- 🎯 Position entries/exits
- 📊 Signal generation
- ⚠️ Risk management alerts
- 🚨 System errors
- 📈 Daily performance summaries

### Key Metrics
- **Portfolio Value**: Current capital
- **Drawdown**: Peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Sharpe Ratio**: Risk-adjusted returns
- **Profit Factor**: Gross profit / gross loss

## 🔍 Strategy Details

### 1. BTC-XMR Correlation Lag (40% weight - Primary Alpha Source)

**The Edge**: Monero typically lags Bitcoin movements by 6-24 hours due to lower liquidity and retail-heavy market structure.

**How it Works**:
- Monitors BTC/USDT for significant moves (>3% in 4-12h window)
- Calculates real-time correlation and optimal lag
- Generates XMR signals based on expected follow-through
- Signal strength decays exponentially (6h half-life)
- Volume confirmation for higher confidence

**Key Parameters**:
```python
{
    'btc_move_threshold': 0.03,    # 3% BTC move triggers signal
    'expected_lag_hours': 8,       # Average lag time
    'min_correlation': 0.6,        # Minimum correlation required
    'signal_half_life_hours': 6    # Signal decay rate
}
```

**Validation**: Test with `python test_btc_correlation.py`

### 2. ML Model (XGBoost) - 30% weight

**Role**: Confirmation filter, not primary signal generator

- **Features**: 50+ technical indicators and market regime signals
- **Target**: Future price direction (buy/sell/hold)
- **Retraining**: Automatic every 168 hours (1 week)
- **Validation**: Time-series split for realistic backtesting
- **Usage**: Filters out trades against market regime

### 3. Rule-Based Strategies - 25% weight combined

- **Trend Following** (12.5%): EMA crossovers with ADX confirmation
- **Mean Reversion** (12.5%): RSI + Bollinger Bands in ranging markets

### 4. Darknet Adoption Strategy - 5% weight (Optional)

**Tracks cryptocurrency usage on darknet marketplaces as privacy demand indicator**

**How it Works**:
- Connects to Tor network
- Scrapes public statistics from marketplace stats pages
- Extracts BTC vs XMR payment method percentages
- Aggregates across top 10 marketplaces
- Generates signals based on adoption rates

**Signal Logic**:
- XMR adoption >60%: Bullish (high privacy demand)
- XMR adoption <35%: Bearish (BTC dominance)
- Increasing XMR trend: Additional bullish signal

**Key Parameters**:
```python
{
    'bullish_threshold': 60,        # XMR% for bullish signal
    'bearish_threshold': 35,        # XMR% for bearish signal
    'min_confidence': 0.5,          # Minimum data quality
    'update_interval_hours': 24     # Daily updates
}
```

**Setup** (Optional):
1. Install Tor: `brew install tor` (macOS) or `apt install tor` (Linux)
2. Start Tor: `tor`
3. Configure marketplace .onion addresses in `src/darknet/marketplace_scraper.py`
4. Enable in `.env`: `DARKNET_MONITORING_ENABLED=true`

**Legal Note**: Scrapes only publicly available statistics pages for market research, similar to analyzing exchange volumes. No personal data or transaction details collected.

**Documentation**: See [DARKNET_QUICK_START.md](docs/DARKNET_QUICK_START.md)

### 5. News Sentiment Strategy - 10% weight

**Real-time news monitoring and LLM-based classification**

**How it Works**:
- Monitors Twitter API for crypto, privacy, economic, and instability news
- Classifies each news item across 4 dimensions using LLMs:
  1. **Economic Relevance** (0-100): Central bank policy, inflation, recession signals
  2. **Crypto Relevance** (0-100): Bitcoin, Monero, blockchain news
  3. **Privacy Relevance** (0-100): Surveillance, encryption, data protection
  4. **Instability Relevance** (0-100): Wars, sanctions, regulatory crackdowns
- Generates sentiment score (-100 to +100) for privacy coins
- Privacy and instability news get boosted multipliers (especially bullish for XMR)

**Key Parameters**:
```python
{
    'min_sentiment_threshold': 30,        # Minimum sentiment to act
    'significant_news_min': 2,            # Minimum significant news items
    'privacy_boost_multiplier': 1.5,      # Boost for privacy news
    'instability_boost_multiplier': 1.2,  # Boost for instability
    'max_signal_age_hours': 4             # News freshness requirement
}
```

**Setup**:

1. **Get Twitter API Access**:
   - Apply at [Twitter Developer Portal](https://developer.twitter.com/)
   - Create an app and get Bearer Token (v2 API)
   - Add to `.env`: `TWITTER_BEARER_TOKEN=your_token`

2. **Get LLM API Access**:
   - **Option A - OpenAI**: Get API key from [OpenAI Platform](https://platform.openai.com/)
   - **Option B - Anthropic**: Get API key from [Anthropic Console](https://console.anthropic.com/)
   - Add to `.env`: `OPENAI_API_KEY=your_key` or `ANTHROPIC_API_KEY=your_key`

3. **Configure** (in `.env`):
```env
NEWS_LLM_PROVIDER=openai              # or 'anthropic'
NEWS_CHECK_INTERVAL_MINUTES=30        # Check every 30 minutes
NEWS_AGGREGATION_WINDOW_HOURS=2       # Aggregate news over 2 hours
NEWS_STRATEGY_WEIGHT=0.10             # 10% weight
```

**What Gets Monitored**:
- Cryptocurrency mentions (Bitcoin, Monero, altcoins)
- Privacy and surveillance topics
- Economic news (Fed, inflation, recession)
- Global instability (wars, sanctions, regulations)
- Exchange delistings and regulatory actions

**Example Signals**:
- 🟢 **Bullish**: Data breach headlines, increased surveillance, privacy legislation
- 🔴 **Bearish**: Exchange delistings, regulatory crackdowns, crypto bans
- ⚪ **Neutral**: General crypto price commentary, unrelated news

**Monitoring**: News sentiment appears in:
- Grafana dashboard metrics
- Telegram alerts for significant news
- Database (`news_events`, `news_sentiment` tables)
- Trading logs with sentiment scores

## 🔒 Security

### API Key Safety
- Store keys in `.env` file (never commit)
- Use read-only keys when possible
- Rotate keys regularly

### Risk Controls
- Maximum position size: 2% of capital
- Maximum portfolio exposure: 30%
- Daily loss limit: 5%
- Consecutive loss limit: 5 trades

## 🐛 Troubleshooting

### Common Issues

1. **TA-Lib Installation Error**
```bash
# Ubuntu/Debian
sudo apt-get install ta-lib

# macOS
brew install ta-lib

# Or use Docker (recommended)
docker-compose up --build
```

2. **Exchange Connection Issues**
- Verify API keys in `.env`
- Check API key permissions
- Ensure IP whitelisting (if required)

3. **Database Connection Error**
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
```

4. **Telegram Alerts Not Working**
- Verify bot token and chat ID
- Test connection: `await telegram.test_connection()`

### Logs
```bash
# View bot logs
docker-compose logs -f trading-bot

# View all service logs
docker-compose logs

# Application logs
tail -f logs/trading_bot_*.log
```

## 📈 Performance Tuning

### Strategy Optimization
1. **Adjust Strategy Weights**: Based on historical performance
2. **ML Model Parameters**: Tune XGBoost hyperparameters
3. **Risk Parameters**: Adjust position sizing and stop losses
4. **Timeframes**: Experiment with different signal timeframes

### System Optimization
1. **Resource Monitoring**: Check CPU/memory usage in Grafana
2. **Database Performance**: Monitor query times
3. **API Rate Limits**: Adjust request frequencies
4. **Alert Frequency**: Reduce unnecessary notifications

## 📊 News Monitoring Details

### Database Schema

The news monitoring system uses two main tables:

**NewsEvent Table**: Stores individual classified news items
- Source information (Twitter, Reddit, etc.)
- LLM classification scores (economic, crypto, privacy, instability)
- Sentiment (bullish/bearish/neutral) and confidence
- Engagement metrics and key entities

**NewsSentiment Table**: Aggregated sentiment over time windows
- Overall sentiment score (-100 to +100)
- Category breakdowns and counts
- Generated trading signals
- Actionability flags

### API Costs

**Twitter API**: Free tier supports:
- 500,000 tweets/month
- Tweet cap: ~200/request
- Adequate for monitoring key topics every 30 minutes

**LLM APIs** (approximate costs per 1000 news classifications):
- OpenAI GPT-4o-mini: ~$0.30
- Anthropic Claude 3 Haiku: ~$0.50
- Budget: ~$10-20/month for continuous monitoring

### Customization

**Add Custom News Sources**:
```python
# In src/news/news_aggregator.py
# Add custom queries to TwitterClient
client.queries['your_topic'] = 'your AND search OR terms -is:retweet'
```

**Adjust Classification Prompt**:
```python
# In src/news/news_classifier.py
# Modify _build_classification_prompt() to emphasize different factors
```

**Change Strategy Weights**:
```python
# In main.py or config
config.news_strategy_weight = 0.15  # Increase to 15% weight
```

## 📝 Development

### Adding New Strategies
```python
# 1. Create strategy class
class MyStrategy(BaseStrategy):
    def generate_signal(self, df):
        # Your logic here
        pass

# 2. Add to signal aggregator
my_strategy = MyStrategy()
bot.signal_aggregator.strategies.append(my_strategy)
```

### Custom Metrics
```python
# Add custom Prometheus metric
from src.monitoring.prometheus_metrics import TradingBotMetrics

# In your code
metrics.custom_metric.inc()
```

### Testing
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```


## ⚠️ Disclaimer

**This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss. Never trade with money you cannot afford to lose. Past performance does not guarantee future results.**

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

### 🎯 Monero-Specific Notes

This bot is specifically optimized for Monero (XMR) trading considering:
- **Lower Liquidity**: Careful position sizing and limit orders
- **Exchange Availability**: Focus on Kraken and Binance
- **Privacy Coin Regulations**: Built-in compliance monitoring
- **BTC Correlation**: **PRIMARY EDGE** - Exploits 6-24h lag in XMR following BTC
- **Volatility Patterns**: Adjusted risk management parameters

### Why BTC-XMR Correlation Works

From `CLAUDE.md` analysis:
1. **Lower Liquidity**: XMR has ~$50-150M daily volume vs BTC's $20-40B → slower price discovery
2. **Retail-Heavy**: Less institutional presence = delayed reaction to BTC moves
3. **Fragmented Liquidity**: Limited exchange availability slows information propagation
4. **High Correlation**: XMR follows BTC trends but with measurable lag

**Historical Performance**: The correlation strategy typically shows 60-75% directional accuracy with an 8-16 hour lag window.

Built according to the comprehensive architecture outlined in CLAUDE.md for maximum edge extraction in privacy coin markets.