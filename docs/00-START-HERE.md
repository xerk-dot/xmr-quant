# 🎯 START HERE

Welcome! This is your entry point to the Monero Trading Bot.

---

## ✅ Repository Has Been Reorganized

This repo was recently reorganized for better clarity. Here's what you need to know:

### 📁 New Structure

```
├── README.md                  ← Overview and quick start
├── docs/                      ← All documentation (you are here)
│   ├── 00-START-HERE.md      ← This file
│   ├── 01-GETTING-STARTED.md ← Setup checklist
│   ├── 02-SETUP.md           ← Detailed API instructions
│   ├── 03-ARCHITECTURE.md    ← Technical deep-dive
│   └── 06-STATUS.md          ← Current state, costs, risks
│
├── src/
│   ├── core/                  ← REQUIRED: Data, features, bot logic
│   ├── strategies/
│   │   ├── core/             ← REQUIRED: BTC correlation, trend, mean reversion
│   │   ├── ml/               ← OPTIONAL: XGBoost models
│   │   ├── news/             ← OPTIONAL: Twitter + LLM ($$$)
│   │   └── experimental/     ← OPTIONAL: Darknet (unreliable)
│   ├── risk/                 ← REQUIRED: Position sizing, stops
│   ├── execution/            ← REQUIRED: Order management
│   ├── monitoring/           ← REQUIRED: Alerts, metrics
│   └── database/             ← REQUIRED: Storage
│
├── scripts/                   ← Utility scripts
├── tests/                     ← Test suite
└── .env.example               ← Configuration template
```

---

## 🚀 Quick Start Path

### 1. Read the README
Start with: `../README.md` (one level up)

### 2. Follow These Docs in Order

1. **[01-GETTING-STARTED.md](01-GETTING-STARTED.md)** ← Start here
   - Checklist for getting the bot running
   - Minimum requirements
   - What you need to configure

2. **[02-SETUP.md](02-SETUP.md)** ← API keys
   - How to get exchange API keys
   - Telegram bot setup
   - Optional: Twitter, OpenAI, Anthropic
   - Optional: Tor for darknet monitoring

3. **[03-ARCHITECTURE.md](03-ARCHITECTURE.md)** ← How it works
   - System design
   - Data flow
   - Strategy details

4. **[06-STATUS.md](06-STATUS.md)** ← Reality check
   - What works vs what doesn't
   - Cost breakdown
   - Risk assessment
   - Honest evaluation

---

## 💡 What You Need to Know

### ✅ What's Required (FREE)
- Python 3.9+ or Docker
- Exchange API (Binance OR Kraken) - FREE
- Telegram bot - FREE
- PostgreSQL, Redis, InfluxDB - FREE (via Docker)

**Cost**: $0-20/month (just server if using VPS)

### ⚠️ What's Optional (Expensive)
- **News Monitoring**: $110-140/month
  - Twitter API: $100/month
  - OpenAI/Anthropic: $10-20/month
  
- **Darknet Monitoring**: FREE but unreliable
  - Requires Tor
  - Manual .onion address maintenance
  - Not recommended

### 🎯 Core Strategy (The "Edge")

**BTC-XMR Correlation Lag (40% weight)**

The hypothesis: Monero follows Bitcoin price movements with a 6-24 hour delay due to lower liquidity.

**Status**: ⚠️ **UNPROVEN** - Requires validation through paper trading

**Don't risk real money until you've validated this works!**

---

## ⚠️ Critical Warnings

### 🔴 This Bot Is Unproven
- Zero real trades executed
- BTC correlation is a hypothesis, not fact
- No backtest with real data
- No test coverage

### 🔴 Start with Paper Trading
1. Run bot in paper trading mode
2. Monitor for 2-4 weeks minimum
3. Analyze if BTC correlation signals work
4. **Only then** consider $500 live capital

### 🔴 Financial Risk
- Cryptocurrency trading = substantial risk
- Never trade money you can't afford to lose
- Past performance ≠ future results
- This is experimental software

---

## 📋 Your Checklist

### Phase 1: Setup (2-4 hours)
- [ ] Read `../README.md`
- [ ] Read `01-GETTING-STARTED.md`
- [ ] Get exchange API keys (see `02-SETUP.md`)
- [ ] Get Telegram bot token
- [ ] Copy `.env.example` to `.env`
- [ ] Edit `.env` with your keys
- [ ] Set `NEWS_MONITORING_ENABLED=false`
- [ ] Set `DARKNET_MONITORING_ENABLED=false`

### Phase 2: Run (10 minutes)
- [ ] Run `docker-compose up -d`
- [ ] Check logs: `docker-compose logs -f trading-bot`
- [ ] Verify Telegram alert received
- [ ] Check Grafana: http://localhost:3000

### Phase 3: Validate (2-4 weeks)
- [ ] Paper trade for minimum 2 weeks
- [ ] Monitor for BTC correlation signals
- [ ] Analyze results in Grafana
- [ ] Check win rate and P&L
- [ ] **Decision**: Does BTC correlation work?

### Phase 4: Deploy (if profitable)
- [ ] IF paper trading profitable
- [ ] THEN start with $500 live
- [ ] Monitor closely for first week
- [ ] Scale gradually if successful

---

## 🆘 Common Questions

### "Where do I start?"
→ Read `01-GETTING-STARTED.md`

### "How much does this cost?"
→ Minimum: $0-20/month (no paid APIs)
→ Full setup: $115-140/month (with news monitoring)
→ See `06-STATUS.md` for detailed breakdown

### "Is this profitable?"
→ **Unknown!** BTC correlation is unproven.
→ Paper trade first to find out.

### "Can I skip the expensive features?"
→ Yes! Disable news and darknet monitoring.
→ Core strategies (BTC correlation, trend, mean reversion) are FREE.

### "How long until first signal?"
→ May take days. BTC needs to move >3% in 4-12h window.
→ Be patient!

### "Should I enable darknet monitoring?"
→ **No.** It's experimental, unreliable, and requires maintenance.
→ Only for experienced users.

### "Should I enable news monitoring?"
→ **Not yet.** It costs $110+/month.
→ Validate BTC correlation works first.
→ Then consider adding news if profitable.

---

## 📚 Documentation Index

| File | Purpose | Read When |
|------|---------|-----------|
| `00-START-HERE.md` | This file | Right now |
| `01-GETTING-STARTED.md` | Setup checklist | Before setup |
| `02-SETUP.md` | API key instructions | During setup |
| `03-ARCHITECTURE.md` | Technical details | After setup (optional) |
| `06-STATUS.md` | Costs, risks, reality | Before deploying |
| `BTC_CORRELATION_FLOW.md` | Strategy details | When understanding signals |
| `NEWS_MONITORING_GUIDE.md` | News setup | If enabling news (expensive) |
| `DARKNET_QUICK_START.md` | Darknet setup | If enabling darknet (unreliable) |

---

## 🎯 Success Path

```
1. Read docs (you are here) ✓
2. Setup .env file
3. Get API keys
4. Run docker-compose up
5. Paper trade 2-4 weeks
6. Analyze results
7. IF profitable → deploy $500 live
8. IF not profitable → tune or abandon
```

---

## 🚨 Red Flags to Watch For

During paper trading, be concerned if:
- ❌ No signals generated after 2 weeks
- ❌ Win rate <40%
- ❌ Consistent losses
- ❌ BTC moves but XMR doesn't follow
- ❌ Correlation coefficient <0.5

**If you see these, the BTC correlation edge may not exist.**

---

## ✅ Green Flags to Look For

Good signs during paper trading:
- ✅ Regular signal generation (every few days)
- ✅ Win rate >55%
- ✅ Consistent small profits
- ✅ Strong BTC-XMR correlation (>0.7)
- ✅ XMR follows BTC moves with delay

**If you see these, the edge may be real!**

---

## 💬 Need Help?

1. **Check logs first**: `docker-compose logs trading-bot`
2. **Read troubleshooting**: `02-SETUP.md` has a section
3. **Review status**: `06-STATUS.md` for common issues
4. **GitHub Issues**: Report bugs

---

## 🎉 Ready?

**Next Step**: Read [01-GETTING-STARTED.md](01-GETTING-STARTED.md)

**Then**: Follow the setup checklist

**Finally**: Paper trade and validate the edge exists

**Good luck!** 🚀

---

**Remember**: This is experimental. Start with paper trading. Never risk more than you can afford to lose.

