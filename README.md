# 🪙 Monero (XMR) Swing Trading Bot

A modular cryptocurrency trading bot designed for Monero swing trading, featuring BTC-XMR correlation analysis, ML models, and optional news sentiment monitoring.

## 🚀 Quick Start

```bash
# 1. Setup
cp .env.example .env
nano .env  # Add your API keys

# 2. Run
docker-compose up -d

# 3. Monitor
# Grafana: http://localhost:3000
# Telegram: Check for alerts
```

**⚠️ Start with paper trading!** See [Getting Started Guide](docs/01-GETTING-STARTED.md)

---

## 📚 Documentation

**Read in this order:**

1. **[Getting Started](docs/01-GETTING-STARTED.md)** - Quick setup checklist
2. **[Setup Guide](docs/02-SETUP.md)** - Detailed API instructions  
3. **[Architecture](docs/03-ARCHITECTURE.md)** - How the bot works
4. **[Status](docs/06-STATUS.md)** - Current state and requirements

---

## 🎯 Core Strategy

**BTC-XMR Correlation Lag (40% weight - Primary Edge)**

Monero typically lags Bitcoin price movements by 6-24 hours due to:
- Lower liquidity ($50-150M vs BTC's $20-40B daily volume)
- Retail-heavy market structure
- Fragmented exchange availability

When BTC moves >3%, the bot anticipates XMR will follow with a measurable delay.

**Status**: Unproven. Requires real-world validation through paper trading.

---

## 📊 Strategy Breakdown

### ✅ Core Strategies (REQUIRED - Free)
- **BTC Correlation** (40%) - Exploits BTC-XMR lag
- **Trend Following** (12.5%) - EMA crossovers + ADX
- **Mean Reversion** (12.5%) - RSI + Bollinger Bands

### ⚙️ ML Strategies (OPTIONAL - Free but slow first run)
- **XGBoost** (25%) - Regime detection and signal filtering
- Auto-trains on startup (1-2 hours)

### 💰 News Strategies (OPTIONAL - $110/month)
- **News Sentiment** (10%) - Twitter + LLM classification
- Requires Twitter API ($100/mo) + OpenAI ($10-20/mo)

### 🧪 Experimental (OPTIONAL - Unreliable)
- **Darknet Adoption** (5%) - Cryptocurrency usage on darknet markets
- Requires Tor + manual .onion address maintenance
- **Not recommended** unless experienced

---

## 🛠️ Requirements

### Minimum (Core Strategies Only)
- Python 3.9+
- Docker + Docker Compose (or PostgreSQL, Redis, InfluxDB)
- Exchange API (Binance OR Kraken)
- Telegram bot (for alerts)

### Optional
- Twitter API + OpenAI/Anthropic (for news monitoring)
- Tor (for darknet monitoring - not recommended)

---

## 💰 Cost Breakdown

### Free Tier (Minimum Setup)
- **Server**: $0 (local) or $5-20/mo (VPS)
- **Trading**: $0 (paper trading)
- **Total**: $5-20/month

### Full Setup (All Features)
- **Twitter API**: $100/month
- **OpenAI API**: $10-20/month  
- **Server**: $5-20/month
- **Total**: $115-140/month

**Recommendation**: Start with free tier, validate BTC correlation works, then add features.

---

## 📁 Project Structure

```
privacy_coin_swing_trading/
├── docs/                          # All documentation
│   ├── 01-GETTING-STARTED.md
│   ├── 02-SETUP.md
│   └── 03-ARCHITECTURE.md
│
├── src/
│   ├── core/                      # REQUIRED: Data, features, exchange
│   ├── strategies/
│   │   ├── core/                  # REQUIRED: BTC correlation, trend, mean reversion
│   │   ├── ml/                    # OPTIONAL: XGBoost models
│   │   ├── news/                  # OPTIONAL: Twitter + LLM ($$$)
│   │   └── experimental/darknet/  # OPTIONAL: Darknet monitoring (unreliable)
│   ├── risk/                      # REQUIRED: Position sizing, stops
│   ├── execution/                 # REQUIRED: Order management
│   ├── monitoring/                # REQUIRED: Metrics, alerts
│   └── database/                  # REQUIRED: Data storage
│
├── scripts/                       # Utility scripts
│   ├── setup_database.py
│   └── test_connection.py
│
├── tests/                         # Test suite
├── monitoring/                    # Grafana + Prometheus
└── .env.example                   # Configuration template
```

---

## ⚡ Quick Commands

```bash
# Start bot (paper trading)
docker-compose up -d

# View logs
docker-compose logs -f trading-bot

# Stop bot
docker-compose down

# Setup database
python scripts/setup_database.py

# Test connections
python scripts/test_connection.py
```

---

## 📈 Features

### Risk Management
- Multiple position sizing methods (Kelly, fixed fractional, volatility-adjusted)
- ATR-based stop losses
- Support/resistance-based targets
- Portfolio exposure limits (max 30%)
- Daily loss limits (5%)

### Monitoring
- **Grafana Dashboards**: Real-time metrics at http://localhost:3000
- **Prometheus**: Metrics endpoint at http://localhost:9090
- **Telegram Alerts**: Trades, signals, errors, daily summaries

### Data Sources
- **Exchanges**: Binance, Kraken (via CCXT)
- **Optional**: Twitter (news), Tor (darknet)

---

## ⚠️ Warnings

### 🔴 This Bot Has NOT Been Validated
- **Zero real-world trades** have been executed
- **BTC correlation edge is unproven** - it's a hypothesis
- **Backtest uses random data** - not real historical data
- **No test coverage** - bugs likely exist

### 🔴 Financial Risk
- Cryptocurrency trading involves substantial risk
- Past performance does not guarantee future results
- **Never trade with money you cannot afford to lose**
- **Always start with paper trading for 2-4 weeks minimum**

### 🔴 Technical Risk
- Code is untested in production
- Exchange APIs can fail
- Network issues can cause missed trades
- Database failures possible

---

## 🧪 Recommended Path

### Week 1: Setup & Validation
1. Get minimum API keys (exchange + Telegram)
2. Create `.env` file
3. Start in paper trading mode
4. Verify connections and signal generation

### Weeks 2-4: Paper Trading
1. Monitor for BTC correlation signals
2. Track hypothetical P&L in Grafana
3. Analyze win rate and strategy performance
4. **Do NOT use real money yet**

### Month 2: Decision Point
**IF paper trading shows consistent profit:**
- Start with $500 live capital
- Monitor closely
- Scale gradually if successful

**IF paper trading loses money:**
- Analyze why (check logs, correlation data)
- Tune parameters or abandon
- **Do NOT risk real money**

---

## 🔧 Configuration

**Minimum `.env` required:**

```bash
# Exchange (pick ONE)
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret

# Telegram (for alerts)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id

# Disable expensive features
NEWS_MONITORING_ENABLED=false
DARKNET_MONITORING_ENABLED=false
```

See [Setup Guide](docs/02-SETUP.md) for detailed API instructions.

---

## 📖 Learn More

- **[Getting Started](docs/01-GETTING-STARTED.md)** - Setup checklist
- **[Setup Guide](docs/02-SETUP.md)** - API key acquisition
- **[Architecture](docs/03-ARCHITECTURE.md)** - Technical deep-dive
- **[Status Report](docs/06-STATUS.md)** - Current state, costs, risks

---

## 🆘 Support

- **Issues**: GitHub Issues tab
- **Logs**: `docker-compose logs trading-bot`
- **Documentation**: See `docs/` directory

---

## 📄 License

MIT License - See LICENSE file

---

## ⚖️ Disclaimer

**This software is for educational and research purposes only.**

- Not financial advice
- No guarantee of profits
- Substantial risk of loss
- Trade at your own risk
- Developers assume no liability for financial losses

**Start with paper trading. Never invest more than you can afford to lose.**

---

## 🚀 Status

- **Architecture**: ✅ Complete
- **Core Strategies**: ✅ Implemented
- **ML Models**: ⚠️ Untrained (auto-trains on startup)
- **News Monitoring**: ⚠️ Requires paid APIs
- **Darknet**: ⚠️ Experimental (fake addresses)
- **Validation**: ❌ Not yet tested with real trades
- **Production Ready**: ❌ Paper trading recommended

**Bottom Line**: Well-architected but unproven. Worth testing with paper trading, but treat as experimental.

---

**Ready to start?** → [Getting Started Guide](docs/01-GETTING-STARTED.md)
