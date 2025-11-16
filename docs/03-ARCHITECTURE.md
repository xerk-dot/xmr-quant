# Monero Trading Bot - Complete Architecture

## System Overview

The bot is a **multi-source, event-driven trading system** with two concurrent execution loops:

1. **Main Trading Loop** (12-hour cycle) - Price-based signals
2. **News Monitoring Loop** (30-minute cycle) - Sentiment-based signals

Both feed into a unified signal aggregator that produces weighted trading decisions.

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MONERO TRADING BOT                             │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    INITIALIZATION PHASE                          │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                   │   │
│  │  1. Load Config (.env variables)                                │   │
│  │  2. Initialize Database (PostgreSQL)                            │   │
│  │  3. Start Prometheus Metrics Server (port 8000)                 │   │
│  │  4. Connect to Exchanges (Binance, Kraken via CCXT)            │   │
│  │  5. Initialize Telegram Alerts                                  │   │
│  │  6. Start Alert Manager Background Task                         │   │
│  │  7. Optional: Initialize News Monitoring System                 │   │
│  │     └─> Twitter Client + LLM Classifier + News Aggregator      │   │
│  │                                                                   │   │
│  └───────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │                  TWO CONCURRENT LOOPS START                    │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────┐
│                      LOOP 1: MAIN TRADING CYCLE                           │
│                      (Runs every 12 hours)                                │
└───────────────────────────────────────────────────────────────────────────┘

STEP 1: DATA COLLECTION (Parallel)
┌──────────────────────┐          ┌──────────────────────┐
│   Fetch XMR/USDT     │          │   Fetch BTC/USDT     │
│   • 30 days history  │          │   • 30 days history  │
│   • 1h candles       │          │   • 1h candles       │
│   • Multi-exchange   │          │   • Multi-exchange   │
└──────────┬───────────┘          └──────────┬───────────┘
           │                                 │
           └──────────┬──────────────────────┘
                      ▼
            ┌─────────────────┐
            │ DataAggregator  │
            │  (best price)   │
            └────────┬────────┘
                     │
                     ▼

STEP 2: FEATURE ENGINEERING
┌─────────────────────────────────────────────────────┐
│  FeatureEngineer.engineer_features()                 │
│  ┌───────────────────────────────────────────────┐  │
│  │ Technical Indicators:                         │  │
│  │  • EMAs (20, 50, 200)                        │  │
│  │  • RSI, MACD, ADX                            │  │
│  │  • Bollinger Bands, ATR                      │  │
│  │  • Volume metrics, OBV                       │  │
│  │                                               │  │
│  │ Market Regime Detection:                      │  │
│  │  • Trend strength                            │  │
│  │  • Volatility classification                 │  │
│  │  • Volume profile                            │  │
│  └───────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼

STEP 3: MULTI-STRATEGY SIGNAL GENERATION (Parallel)
┌──────────────────────────────────────────────────────────────┐
│                   SignalAggregator                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                       │    │
│  │  Strategy 1: BTCCorrelation (40% weight)            │    │
│  │  ┌────────────────────────────────────────┐         │    │
│  │  │ • Calculate BTC-XMR correlation        │         │    │
│  │  │ • Detect BTC moves (>3% in 4/12/24h)  │         │    │
│  │  │ • Check optimal lag (typically 8-16h)  │         │    │
│  │  │ • Generate BUY/SELL if BTC moved       │         │    │
│  │  │ • Signal decays over 6h half-life      │         │    │
│  │  └────────────────────────────────────────┘         │    │
│  │                                                       │    │
│  │  Strategy 2: NewsSentiment (10% weight) [optional]  │    │
│  │  ┌────────────────────────────────────────┐         │    │
│  │  │ • Get latest aggregated sentiment      │         │    │
│  │  │ • Check if actionable (>threshold)     │         │    │
│  │  │ • Privacy/instability boost applied    │         │    │
│  │  │ • Generate signal if confident         │         │    │
│  │  └────────────────────────────────────────┘         │    │
│  │                                                       │    │
│  │  Strategy 3: TrendFollowing (12.5% weight)          │    │
│  │  ┌────────────────────────────────────────┐         │    │
│  │  │ • EMA crossover (20/50)                │         │    │
│  │  │ • ADX strength confirmation            │         │    │
│  │  │ • Volume validation                    │         │    │
│  │  └────────────────────────────────────────┘         │    │
│  │                                                       │    │
│  │  Strategy 4: MeanReversion (12.5% weight)           │    │
│  │  ┌────────────────────────────────────────┐         │    │
│  │  │ • RSI oversold/overbought             │         │    │
│  │  │ • Bollinger Band touches               │         │    │
│  │  │ • Low ADX (ranging market)            │         │    │
│  │  └────────────────────────────────────────┘         │    │
│  │                                                       │    │
│  │  Strategy 5: XGBoostML (25% weight)                 │    │
│  │  ┌────────────────────────────────────────┐         │    │
│  │  │ • ML predictions on 50+ features       │         │    │
│  │  │ • Auto-retraining weekly               │         │    │
│  │  │ • Confidence-based signals             │         │    │
│  │  └────────────────────────────────────────┘         │    │
│  │                                                       │    │
│  └───────────────────────┬───────────────────────────────────┘
│                          │                                     │
│                          ▼                                     │
│      ┌───────────────────────────────────────┐                │
│      │  Weighted Voting Aggregation:         │                │
│      │  • Each strategy gets weight          │                │
│      │  • Multiply by strength * confidence  │                │
│      │  • Sum up BUY/SELL/HOLD scores        │                │
│      │  • Winner = highest score             │                │
│      └───────────────────┬───────────────────┘                │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼

STEP 4: RISK MANAGEMENT EVALUATION
┌────────────────────────────────────────────────────┐
│  RiskManager.evaluate_trade_opportunity()           │
│  ┌──────────────────────────────────────────────┐  │
│  │ Position Sizing:                             │  │
│  │  • Kelly Criterion / Fixed Fractional        │  │
│  │  • Max 2% per trade                          │  │
│  │  • Volatility adjustment                     │  │
│  │                                               │  │
│  │ Portfolio Limits:                             │  │
│  │  • Max 30% total exposure                    │  │
│  │  • Check existing positions                  │  │
│  │  • Daily loss limits                         │  │
│  │                                               │  │
│  │ Stop Loss / Take Profit:                      │  │
│  │  • ATR-based stops (2.5x multiplier)         │  │
│  │  • Support/Resistance levels                 │  │
│  │  • Min 1.5:1 risk/reward ratio              │  │
│  │                                               │  │
│  │ Validation:                                   │  │
│  │  • Signal strength > threshold               │  │
│  │  • Market conditions suitable                │  │
│  │  • No conflicting positions                  │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
           ▼ APPROVED                  ▼ REJECTED
                                  ┌─────────────┐
STEP 5: EXECUTION                 │  Log reason │
┌─────────────────────────────┐   │  Continue   │
│  OrderManager               │   └─────────────┘
│  • Place limit order        │
│  • Fallback to market       │
│  • Track position           │
│  • Update database          │
│  • Send Telegram alert      │
└────────────┬────────────────┘
             │
             ▼

STEP 6: POSITION MONITORING
┌────────────────────────────────────────────────────┐
│  Monitor open positions:                            │
│  • Check stop loss hit                             │
│  • Check take profit hit                           │
│  • Update trailing stops                           │
│  • Calculate unrealized P&L                        │
│  • Close if conditions met                         │
└────────────────────────────────────────────────────┘
             │
             ▼

STEP 7: METRICS & WAIT
┌────────────────────────────────────────────────────┐
│  • Update Prometheus metrics                       │
│  • Log portfolio status                            │
│  • Sleep 12 hours (until next cycle)              │
└────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────┐
│                   LOOP 2: NEWS MONITORING CYCLE                           │
│                   (Runs every 30 minutes in background)                   │
│                   (Only if NEWS_MONITORING_ENABLED=true)                  │
└───────────────────────────────────────────────────────────────────────────┘

STEP 1: FETCH NEWS FROM TWITTER
┌────────────────────────────────────────────────────┐
│  TwitterClient.fetch_recent_tweets()                │
│  ┌──────────────────────────────────────────────┐  │
│  │ Queries (last 2 hours):                     │  │
│  │  • crypto AND (monero OR XMR OR privacy)    │  │
│  │  • bitcoin AND (regulation OR ban)          │  │
│  │  • (surveillance OR encryption)             │  │
│  │  • (fed OR inflation OR recession)          │  │
│  │  • (war OR sanctions OR instability)        │  │
│  │                                               │  │
│  │ Returns: ~20-50 tweets per query            │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────┘
                         │
                         ▼

STEP 2: LLM CLASSIFICATION (Batch Processing)
┌────────────────────────────────────────────────────┐
│  NewsClassifier.classify_news()                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ For each news item:                          │  │
│  │                                               │  │
│  │ Send to LLM (GPT-4 or Claude):              │  │
│  │  ┌────────────────────────────────────┐     │  │
│  │  │ Classify on 4 dimensions (0-100):  │     │  │
│  │  │  1. Economic Relevance             │     │  │
│  │  │  2. Crypto Relevance               │     │  │
│  │  │  3. Privacy Relevance              │     │  │
│  │  │  4. Instability Relevance          │     │  │
│  │  │                                     │     │  │
│  │  │ Generate sentiment (-100 to +100): │     │  │
│  │  │  • Bullish for privacy coins       │     │  │
│  │  │  • Bearish for privacy coins       │     │  │
│  │  │  • Neutral                          │     │  │
│  │  └────────────────────────────────────┘     │  │
│  │                                               │  │
│  │ Store in database (NewsEvent table)         │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────┬───────────────────────────┘
                         │
                         ▼

STEP 3: SENTIMENT AGGREGATION
┌────────────────────────────────────────────────────┐
│  NewsAggregator.aggregate_sentiment()               │
│  ┌──────────────────────────────────────────────┐  │
│  │ Over 2-hour window:                          │  │
│  │                                               │  │
│  │ Calculate weighted sentiment:                │  │
│  │  • Privacy news: 1.5x multiplier            │  │
│  │  • Instability news: 1.2x multiplier        │  │
│  │  • Recent news: higher weight               │  │
│  │  • High engagement: bonus weight            │  │
│  │                                               │  │
│  │ Generate aggregate score:                    │  │
│  │  overall_sentiment = Σ(score × weight)      │  │
│  │                                               │  │
│  │ Determine actionability:                     │  │
│  │  • |sentiment| > 30 threshold               │  │
│  │  • At least 2 significant news items        │  │
│  │  • News is fresh (<4 hours)                 │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Store in database (NewsSentiment table)           │
└────────────────────────┬───────────────────────────┘
                         │
                         ▼

STEP 4: ALERT & CACHE UPDATE
┌────────────────────────────────────────────────────┐
│  • Log sentiment update                            │
│  • If highly significant (3+ items):              │
│    └─> Send Telegram alert                        │
│  • Update news strategy cache                      │
│  • Available for next main trading cycle          │
└────────────────────────┬───────────────────────────┘
                         │
                         ▼

STEP 5: WAIT
┌────────────────────────────────────────────────────┐
│  Sleep 30 minutes                                  │
│  (Repeat cycle)                                    │
└────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────┐
│                     DATA PERSISTENCE LAYER                                │
└───────────────────────────────────────────────────────────────────────────┘

PostgreSQL Database Tables:
┌──────────────────────────────────────────────────────────┐
│  trades                                                   │
│  • Trade history (entry/exit, P&L, metadata)            │
├──────────────────────────────────────────────────────────┤
│  positions                                                │
│  • Current open positions, unrealized P&L                │
├──────────────────────────────────────────────────────────┤
│  signals                                                  │
│  • Generated signals from all strategies                 │
├──────────────────────────────────────────────────────────┤
│  news_events (NEW)                                       │
│  • Individual news items with LLM classification         │
│  • Scores: economic, crypto, privacy, instability        │
│  • Sentiment: -100 to +100                               │
├──────────────────────────────────────────────────────────┤
│  news_sentiment (NEW)                                    │
│  • Aggregated sentiment over time windows                │
│  • Overall scores and actionability flags                │
└──────────────────────────────────────────────────────────┘

InfluxDB (Time-series):
┌──────────────────────────────────────────────────────────┐
│  • OHLCV data (long-term storage)                        │
│  • Portfolio value history                               │
│  • Metrics over time                                     │
└──────────────────────────────────────────────────────────┘

Redis (Caching):
┌──────────────────────────────────────────────────────────┐
│  • Recent market data                                    │
│  • Active signals cache                                  │
│  • Task queue for async operations                       │
└──────────────────────────────────────────────────────────┘


┌───────────────────────────────────────────────────────────────────────────┐
│                     MONITORING & ALERTING LAYER                           │
└───────────────────────────────────────────────────────────────────────────┘

Prometheus Metrics (port 8000):
┌──────────────────────────────────────────────────────────┐
│  • active_positions_count                                │
│  • portfolio_value                                       │
│  • signals_generated_total (by strategy)                │
│  • trades_executed_total                                 │
│  • win_rate                                              │
│  • profit_factor                                         │
│  • news_sentiment_score (NEW)                            │
│  • news_events_processed_total (NEW)                     │
└──────────────────────────────────────────────────────────┘

Grafana Dashboards:
┌──────────────────────────────────────────────────────────┐
│  • Real-time portfolio metrics                           │
│  • Strategy performance comparison                       │
│  • BTC-XMR correlation gauge                            │
│  • News sentiment over time (NEW)                        │
│  • Risk metrics and drawdown                             │
└──────────────────────────────────────────────────────────┘

Telegram Alerts:
┌──────────────────────────────────────────────────────────┐
│  • Position entries/exits                                │
│  • Signal generation                                     │
│  • Risk management alerts                                │
│  • System errors                                         │
│  • Daily performance summaries                           │
│  • Significant news detection (NEW)                      │
└──────────────────────────────────────────────────────────┘
```

---

## Component Dependency Graph

```
┌─────────────────────────────────────────────────────────┐
│                      MoneroTradingBot                    │
│                     (main orchestrator)                  │
└──────────┬──────────────────────────────────────────────┘
           │
           ├──> DataAggregator
           │    └──> ExchangeClient (CCXT)
           │         ├──> Binance
           │         └──> Kraken
           │
           ├──> FeatureEngineer
           │    ├──> TechnicalIndicators
           │    └──> MarketRegime
           │
           ├──> SignalAggregator
           │    ├──> BTCCorrelationStrategy
           │    ├──> NewsSentimentStrategy (optional)
           │    │    └──> NewsAggregator
           │    │         ├──> TwitterClient
           │    │         └──> NewsClassifier
           │    │              ├──> OpenAI API
           │    │              └──> Anthropic API
           │    ├──> TrendFollowingStrategy
           │    ├──> MeanReversionStrategy
           │    └──> MLManager
           │         └──> XGBoostML Strategy
           │
           ├──> RiskManager
           │    ├──> PositionSizing
           │    └──> StopLoss
           │
           ├──> OrderManager
           │    └──> ExchangeClient
           │
           ├──> TradingBotMetrics (Prometheus)
           │
           ├──> TelegramAlerts
           │
           └──> Database (PostgreSQL)
                ├──> trades
                ├──> positions
                ├──> signals
                ├──> news_events
                └──> news_sentiment
```

---

## Key Integration Points

### 1. **News → Signal Flow**
```
Twitter API 
  → TwitterClient.fetch_tweets() 
  → NewsClassifier.classify() [LLM API call]
  → NewsAggregator.aggregate_sentiment()
  → NewsSentimentStrategy.generate_signal()
  → SignalAggregator.weighted_voting()
  → RiskManager.evaluate_trade()
```

### 2. **BTC Correlation → Signal Flow**
```
Exchange API (BTC + XMR data)
  → DataAggregator.fetch_ohlcv()
  → FeatureEngineer.engineer_features()
  → BTCCorrelationStrategy.detect_btc_move()
  → BTCCorrelationStrategy.generate_signal()
  → SignalAggregator.weighted_voting()
  → RiskManager.evaluate_trade()
```

### 3. **Traditional Signals → Flow**
```
Exchange API (XMR data)
  → FeatureEngineer.engineer_features()
  → [TrendFollowing | MeanReversion].generate_signal()
  → SignalAggregator.weighted_voting()
  → RiskManager.evaluate_trade()
```

### 4. **ML Signals → Flow**
```
Exchange API (XMR data)
  → FeatureEngineer.engineer_features()
  → MLManager.generate_predictions()
  → XGBoostML.generate_signal()
  → SignalAggregator.weighted_voting()
  → RiskManager.evaluate_trade()
```

---

## Execution Timing

### Main Loop (12-hour cycle)
```
00:00 - Trading cycle executes
  ├─ Fetch data (5 sec)
  ├─ Engineer features (10 sec)
  ├─ Generate signals (5 sec)
  ├─ Risk evaluation (1 sec)
  ├─ Execute trades (2 sec)
  └─ Monitor positions (2 sec)

12:00 - Trading cycle executes (repeat)
```

### News Loop (30-minute cycle)
```
00:00 - Fetch news
00:02 - Classify with LLM (2-3 min for batch)
00:05 - Aggregate sentiment
00:06 - Update cache
00:30 - Repeat
01:00 - Repeat
... continuous ...
```

**Note**: News sentiment is **always available** when main trading cycle runs, because it updates 24x per day vs main loop's 2x per day.

---

## Configuration Flow

```
.env file
  ↓
config.py (TradingConfig class)
  ↓
main.py reads config
  ├─ If NEWS_MONITORING_ENABLED=true
  │   └─> Initialize news components
  ├─ If OPENAI_API_KEY or ANTHROPIC_API_KEY set
  │   └─> Initialize LLM classifier
  └─ Set strategy weights dynamically
```

---

## Critical Dependencies

### Required Always
- Exchange API keys (Binance/Kraken)
- PostgreSQL database
- Redis cache
- InfluxDB (time-series)

### Optional (News Monitoring)
- Twitter Bearer Token
- OpenAI API Key OR Anthropic API Key
- `NEWS_MONITORING_ENABLED=true`

**If news components missing**: Bot runs without news strategy (weights rebalanced to other strategies)

---

## Summary: Why It Feels Fragmented

You have **5 independent signal sources** feeding into one aggregator:

1. **BTCCorrelationStrategy** - 40% (price lag)
2. **NewsSentimentStrategy** - 10% (events)
3. **TrendFollowing** - 12.5% (rules)
4. **MeanReversion** - 12.5% (rules)
5. **XGBoostML** - 25% (ML)

**This is intentional** - diversification of alpha sources. But it means:
- More moving parts
- More configuration
- More potential failure points

**The architecture is sound, but documentation was missing.** This document should clarify the flow.

