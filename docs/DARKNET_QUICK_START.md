# Darknet Monitoring - Quick Start

## TL;DR

Track Bitcoin vs Monero adoption on darknet marketplaces as a privacy demand indicator.

**Higher XMR usage = Bullish signal** (increased privacy demand)

##Quick Setup (5 minutes)

1. **Install Tor**:
   ```bash
   # macOS
   brew install tor
   
   # Linux
   sudo apt install tor
   ```

2. **Start Tor**:
   ```bash
   tor
   ```

3. **Install dependencies**:
   ```bash
   pip install requests[socks] PySocks beautifulsoup4 aiohttp-socks
   ```

4. **Test connection**:
   ```bash
   python test_darknet_monitoring.py
   ```

## How It Works

```
Tor Network → Darknet Marketplaces → Scrape Stats Pages
                                           ↓
                              BTC: 40% vs XMR: 60%
                                           ↓
                              Generate Trading Signal
```

##Signal Logic

| XMR Adoption | Signal | Reasoning |
|--------------|--------|-----------|
| > 60% | 🟢 BULLISH | High privacy demand |
| 35-60% | ⚪ NEUTRAL | Watch for trend |
| < 35% | 🔴 BEARISH | BTC dominance |

## Configuration

Edit `src/darknet/marketplace_scraper.py`:

```python
MARKETPLACES = {
    'Market Name': {
        'onion': 'xxxxxxxxxxxxxxxxxxxxx.onion',
        'stats_path': '/stats',
        'enabled': True  # Enable this
    }
}
```

Get .onion addresses from:
- dark.fail (Tor directory)
- Dread (darknet Reddit)
- Verified darknet forums

## Integration

Add to `.env`:
```env
DARKNET_MONITORING_ENABLED=true
DARKNET_STRATEGY_WEIGHT=0.05  # 5% of signals
DARKNET_UPDATE_INTERVAL_HOURS=24
```

##Legal Note

✅ **Legal**: Scraping public statistics pages for market research
❌ **Illegal**: Facilitating transactions or collecting personal data

We only collect payment method percentages, similar to analyzing exchange volumes.

## Troubleshooting

**Can't connect to Tor?**
- Check Tor is running: `ps aux | grep tor`
- Try port 9150 if using Tor Browser

**No marketplaces configured?**
- Update addresses in `marketplace_scraper.py`
- Addresses change frequently - use verified sources

**Low confidence scores?**
- Scrape more marketplaces (10+ recommended)
- Build history over time (wait a few days)

## Example Output

```
📊 Darknet Adoption Report:
  XMR: 65.3%
  BTC: 34.7%
  Trend: increasing
  Signal Zone: bullish
  Confidence: 0.75
  Marketplaces: 8

💡 Trading Signal: BUY
  Strength: 78%
  Confidence: 71%
```

## Full Documentation

See [DARKNET_MONITORING_GUIDE.md](DARKNET_MONITORING_GUIDE.md) for complete details.

