# 🎯 Getting Started Checklist

**Current Status: Bot requires setup before it can run**

This checklist will get you from zero to a running bot in minimal time.

---

## ✅ Pre-Flight Checklist

### 1. Configuration File
- [ ] Copy `env.example` to `.env`: `cp env.example .env`
- [ ] Edit `.env` with your actual values

### 2. Minimum Required Configuration

**You MUST have at least these to run:**

```bash
# In your .env file:

# ✅ ONE exchange (pick Binance OR Kraken)
BINANCE_API_KEY=your_real_key_here
BINANCE_SECRET=your_real_secret_here

# ✅ Telegram for alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# ✅ Disable optional features for now
NEWS_MONITORING_ENABLED=false
DARKNET_MONITORING_ENABLED=false
```

### 3. Get API Keys

#### Exchange (REQUIRED - pick one)
- [ ] **Binance**: https://www.binance.com/en/my/settings/api-management
  - Enable: Read + Spot Trading
  - Disable: Withdrawals
- [ ] **Kraken**: https://www.kraken.com/u/security/api
  - Enable: Query + Create Orders
  - Disable: Withdrawals

#### Telegram (REQUIRED - for alerts)
- [ ] Message `@BotFather` on Telegram → `/newbot`
- [ ] Get bot token (looks like `123456:ABC...`)
- [ ] Message your bot
- [ ] Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
- [ ] Copy chat ID from response

See `SETUP.md` for detailed instructions.

---

## 🚀 Run the Bot

### Option A: Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f trading-bot

# Check status
docker-compose ps
```

### Option B: Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Start databases (if not using Docker)
# You'll need PostgreSQL, Redis, and InfluxDB running

# Run bot
python run_bot.py --mode paper --capital 10000
```

---

## 📊 Verify It's Working

### Check Dashboards
- **Grafana**: http://localhost:3000 (login: admin/grafana_admin_123)
- **Prometheus**: http://localhost:9090

### Check Telegram
You should receive a startup message like:
```
🚀 Trading Bot Started
Mode: paper
Capital: $10,000
```

### Check Logs
Look for these messages:
```
✅ Connected to binance
✅ BTC-XMR Correlation: 0.78, Optimal lag: 8h
✅ Portfolio metrics: {...}
```

---

## ⚠️ Common Issues

### "Config not found"
→ You forgot to create `.env` file
→ Run: `cp env.example .env`

### "Invalid API key"
→ Double-check your exchange API keys
→ Make sure you copied the entire key (no spaces)

### "No module named 'ta'"
→ Install dependencies: `pip install -r requirements.txt`

### "Database connection failed"
→ If using Docker: `docker-compose up -d postgres`
→ If local: Make sure PostgreSQL is running

### "No signals generated"
→ This is normal! BTC correlation strategy needs:
  - 30+ days of data
  - BTC to move >3% in 4-12h window
  - Correlation >0.6
→ May take days to see first signal

---

## 📈 What Happens Next?

### Day 1-3: Bot Initialization
- Fetches 30 days of historical data
- Calculates BTC-XMR correlation
- Trains ML models (may take hours on first run)
- Waits for trading signals

### Day 4-7: First Signals
- You should start seeing signals in Telegram
- Check Grafana for signal history
- Monitor paper trading P&L

### Week 2-4: Validation
- Analyze win rate and profit factor
- Check if BTC correlation edge is working
- Consider tweaking strategy weights

### Month 2+: Consider Live Trading
- Only if paper trading shows consistent profit
- Start with small capital ($500-1000)
- Monitor closely

---

## 🎓 Learn More

### Essential Reading
1. **SETUP.md** - Detailed setup guide with API instructions
2. **ARCHITECTURE.md** - How the bot works internally
3. **QUICK_REFERENCE.md** - System flow diagrams
4. **BTC_CORRELATION_FLOW.md** - Main strategy explained

### Key Files to Understand
1. `main.py` - Orchestrates everything
2. `src/signals/btc_correlation_strategy.py` - Primary edge (40% weight)
3. `src/risk/risk_manager.py` - Position sizing and stops
4. `config/config.py` - All configuration

---

## 🔧 Optional Features (Skip for Now)

### News Monitoring
- **Cost**: $100-150/month (Twitter + OpenAI APIs)
- **Setup**: See SETUP.md → "News Monitoring Setup"
- **Worth it?**: Unproven. Skip until core bot is profitable.

### Darknet Monitoring
- **Status**: Experimental, unreliable
- **Requires**: Tor + Real .onion addresses
- **Worth it?**: Probably not. Skip unless you're experienced.

### ML Models
- **Status**: Will auto-train on first run
- **Time**: 1-2 hours for initial training
- **Worth it?**: Yes, provides confirmation signals (25% weight)

---

## 💰 Cost Breakdown

### Minimum Setup (Just BTC Correlation)
- **Exchange fees**: $0 (no trading yet)
- **Server**: $5-20/month (VPS) or $0 (local)
- **Total**: ~$5-20/month

### With News Monitoring
- **Twitter API**: $100/month
- **OpenAI API**: $10-20/month
- **Total**: ~$115-140/month

### Live Trading Costs
- **Exchange fees**: 0.1-0.2% per trade
- **Slippage**: 0.1-0.5% per trade
- **Estimated**: $10-50/month depending on trade frequency

---

## ✨ Quick Reference

### Start Bot
```bash
docker-compose up -d
```

### Stop Bot
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f trading-bot
```

### Restart Bot
```bash
docker-compose restart trading-bot
```

### Check Database
```bash
docker-compose exec postgres psql -U trading_bot -d monero_trading
```

### Update Code
```bash
git pull
docker-compose up -d --build
```

---

## 🆘 Need Help?

1. **Check logs first**: `docker-compose logs trading-bot`
2. **Read SETUP.md**: Detailed troubleshooting section
3. **GitHub Issues**: Report bugs
4. **Double-check .env**: Most issues are config problems

---

## ⚖️ Legal Disclaimer

This is experimental software for educational purposes. Cryptocurrency trading involves substantial risk of loss. Never trade with money you cannot afford to lose. Past performance does not guarantee future results. The developers assume no liability for financial losses.

---

**Ready?** → Start with the checklist at the top of this file. Good luck! 🚀

