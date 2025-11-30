

This repo is for indie quant. trying to predict monero price (XMR).


The repo is structured with two folders:
- shared: files that are shared across strats
    - market_data: market data collection and processing (use coinmarketcap for data. import bitcoin, monero, zcash, ltc)
    - exchange: exchange API interaction (use kraken api)
    - risk: risk management (limits etc)
    - monitoring: monitoring and alerting
    - notification: notification (telegram bot)
- theses: different strategies to predict XMR price, a folder for each (dont implement yet, we will get to this later)
