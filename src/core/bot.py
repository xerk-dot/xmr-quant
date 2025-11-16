import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import pandas as pd
import numpy as np

from src.data.data_aggregator import DataAggregator
from src.features.feature_engineering import FeatureEngineer
from src.signals.signal_aggregator import SignalAggregator
from src.signals.ml_manager import MLModelManager
from src.signals.btc_correlation_strategy import BTCCorrelationStrategy
from src.news.twitter_client import TwitterClient
from src.news.news_classifier import NewsClassifier
from src.news.news_aggregator import NewsAggregator
from src.news.news_sentiment_strategy import NewsSentimentStrategy
from src.darknet.tor_client import TorClient
from src.darknet.marketplace_scraper import MarketplaceScraper
from src.darknet.darknet_adoption_strategy import DarknetAdoptionStrategy
from src.risk.risk_manager import RiskManager
from src.execution.order_manager import OrderManager
from src.database.models import init_database
from src.monitoring.prometheus_metrics import TradingBotMetrics, MetricsCollector
from src.monitoring.telegram_alerts import TelegramAlerts, AlertManager
from prometheus_client import start_http_server
from config import config

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MoneroTradingBot:
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.symbol = 'XMR/USDT'
        self.btc_symbol = 'BTC/USDT'

        self.data_aggregator = DataAggregator()
        self.feature_engineer = FeatureEngineer()

        # BTC-XMR correlation strategy (40% weight - primary alpha source)
        self.btc_correlation_strategy = BTCCorrelationStrategy()

        # ML Model Manager coordinates all XGBoost models
        self.ml_manager = MLModelManager(enable_all_models=True)

        # News monitoring components (optional, based on config)
        self.news_strategy = None
        if config.news_monitoring_available:
            logger.info("Initializing news monitoring system...")
            twitter_client = TwitterClient(config.twitter_bearer_token)
            news_classifier = NewsClassifier(
                provider=config.news_llm_provider,
                api_key=config.llm_api_key,
                model=config.news_llm_model
            )
            news_aggregator = NewsAggregator(
                twitter_client=twitter_client,
                news_classifier=news_classifier,
                aggregation_window_hours=config.news_aggregation_window_hours
            )
            self.news_strategy = NewsSentimentStrategy(news_aggregator=news_aggregator)
        else:
            logger.warning(
                "News monitoring disabled. Set TWITTER_BEARER_TOKEN and "
                "OPENAI_API_KEY/ANTHROPIC_API_KEY to enable."
            )
        
        # Darknet monitoring components (optional, based on config)
        self.darknet_strategy = None
        self.tor_client = None
        if config.darknet_monitoring_available:
            logger.info("Initializing darknet monitoring system...")
            try:
                self.tor_client = TorClient(
                    tor_proxy_host=config.darknet_tor_proxy_host,
                    tor_proxy_port=config.darknet_tor_proxy_port
                )
                
                # Test Tor connection
                if self.tor_client.connect():
                    marketplace_scraper = MarketplaceScraper(self.tor_client)
                    self.darknet_strategy = DarknetAdoptionStrategy(
                        marketplace_scraper=marketplace_scraper,
                        bullish_threshold=config.darknet_bullish_threshold,
                        bearish_threshold=config.darknet_bearish_threshold,
                        min_confidence=config.darknet_min_confidence,
                        update_interval_hours=config.darknet_update_interval_hours
                    )
                    logger.info("Darknet monitoring initialized successfully")
                else:
                    logger.error("Failed to connect to Tor network. Darknet monitoring disabled.")
                    self.tor_client = None
            except Exception as e:
                logger.error(f"Error initializing darknet monitoring: {e}")
                logger.warning("Darknet monitoring disabled")
                self.tor_client = None
                self.darknet_strategy = None
        else:
            logger.info("Darknet monitoring disabled (set DARKNET_MONITORING_ENABLED=true to enable)")

        # Signal aggregator with all strategies
        self.signal_aggregator = SignalAggregator()
        self.signal_aggregator.strategies.append(self.btc_correlation_strategy)
        
        # Add news strategy if available
        if self.news_strategy:
            self.signal_aggregator.strategies.append(self.news_strategy)
        
        # Add darknet strategy if available
        if self.darknet_strategy:
            self.signal_aggregator.strategies.append(self.darknet_strategy)
        
        # Set strategy weights dynamically based on enabled strategies
        strategy_weights = {
            'BTCCorrelation': 0.40,
            'TrendFollowing': 0.125,
            'MeanReversion': 0.125,
            'XGBoostML': 0.25  # ML strategies get 25% if available
        }
        
        # Add optional strategy weights if enabled
        if self.news_strategy:
            strategy_weights['NewsSentiment'] = config.news_strategy_weight
            logger.info(f"News sentiment strategy enabled with {config.news_strategy_weight:.1%} weight")
        
        if self.darknet_strategy:
            strategy_weights['DarknetAdoption'] = config.darknet_strategy_weight
            logger.info(f"Darknet adoption strategy enabled with {config.darknet_strategy_weight:.1%} weight")
        
        self.signal_aggregator.update_weights(strategy_weights)

        self.risk_manager = RiskManager(initial_capital)

        # Monitoring and alerting
        self.metrics = TradingBotMetrics()
        self.metrics_collector = MetricsCollector(self.metrics)
        self.telegram = TelegramAlerts()
        self.alert_manager = AlertManager()

        self.db_session = init_database()
        self.running = False

    async def initialize(self):
        logger.info("Initializing Monero Trading Bot...")

        # Start metrics server
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")

        # Start alert manager
        asyncio.create_task(self.alert_manager.start_alert_processor())

        # Connect to data sources
        await self.data_aggregator.connect_all()

        # Send startup notification
        await self.telegram.send_startup_alert("paper", self.initial_capital)

        logger.info("Bot initialization complete")

    async def run_twice_daily_checks(self):
        """Main trading loop - runs twice daily as per CLAUDE.md"""
        self.running = True
        
        # Start background news monitoring if enabled
        if self.news_strategy:
            asyncio.create_task(self._news_monitoring_loop())
        
        # Start background darknet monitoring if enabled
        if self.darknet_strategy:
            asyncio.create_task(self._darknet_monitoring_loop())

        while self.running:
            try:
                logger.info("Starting trading cycle check...")

                # Fetch market data
                end_time = datetime.now()
                start_time = end_time - timedelta(days=30)

                # Fetch both XMR and BTC data
                xmr_task = self.data_aggregator.fetch_aggregated_ohlcv(
                    symbol=self.symbol,
                    timeframe='1h',
                    since=start_time,
                    limit=720  # 30 days of hourly data
                )
                
                btc_task = self.data_aggregator.fetch_aggregated_ohlcv(
                    symbol=self.btc_symbol,
                    timeframe='1h',
                    since=start_time,
                    limit=720
                )
                
                df, btc_df = await asyncio.gather(xmr_task, btc_task)

                if df.empty:
                    logger.warning("No XMR market data received")
                    await asyncio.sleep(3600)  # Wait 1 hour before retry
                    continue
                
                if btc_df.empty:
                    logger.warning("No BTC market data received")
                else:
                    # Engineer features for BTC data and pass to correlation strategy
                    btc_df = self.feature_engineer.engineer_features(btc_df)
                    self.btc_correlation_strategy.set_btc_data(btc_df)
                    
                    # Log correlation stats
                    corr_report = self.btc_correlation_strategy.get_correlation_report(df)
                    logger.info(f"BTC-XMR Correlation: {corr_report.get('correlation', 0):.3f}, "
                               f"Optimal lag: {corr_report.get('optimal_lag_hours', 0)}h")

                # Engineer features for XMR data
                df = self.feature_engineer.engineer_features(df)

                # Generate signals
                signals = self.signal_aggregator.generate_signals(df)
                if signals:
                    aggregated_signal = self.signal_aggregator.aggregate_signals(signals)

                    if aggregated_signal:
                        await self._process_signal(aggregated_signal, df)

                # Monitor existing positions
                await self._monitor_positions()

                # Update portfolio metrics
                metrics = self.risk_manager.get_portfolio_metrics()
                logger.info(f"Portfolio metrics: {metrics}")

                # Wait for next check (12 hours for twice daily)
                await asyncio.sleep(12 * 3600)

            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _process_signal(self, signal: Any, df: pd.DataFrame):
        """Process a trading signal"""
        logger.info(f"Processing signal: {signal.signal_type} with strength {signal.strength}")

        current_price = df['close'].iloc[-1]

        # Evaluate trade opportunity
        trade_eval = self.risk_manager.evaluate_trade_opportunity(
            signal, current_price, df
        )

        if not trade_eval['approved']:
            logger.info(f"Trade not approved: {trade_eval['reason']}")
            return

        # In live trading, you would place actual orders here
        # For now, we'll just log the trade decision
        logger.info(f"Would place {signal.signal_type} order: {trade_eval}")

        # For paper trading, add to risk manager
        position_id = f"paper_{datetime.now().timestamp()}"
        self.risk_manager.add_position(
            position_id,
            current_price,
            trade_eval['position_size'].units,
            trade_eval['stop_loss'],
            trade_eval['take_profit'],
            trade_eval['position_type']
        )

    async def _monitor_positions(self):
        """Monitor existing positions for stop loss/take profit"""
        if not self.risk_manager.positions:
            return

        # Get current price
        ticker = await self.data_aggregator.fetch_best_bid_ask(self.symbol)
        current_price = ticker['best_bid'] if ticker['best_bid'] else 0

        positions_to_close = []

        for position_id, position in self.risk_manager.positions.items():
            self.risk_manager.update_position_pnl(position_id, current_price)

            if self.risk_manager.check_stop_loss_hit(position_id, current_price):
                positions_to_close.append((position_id, 'stop_loss'))
            elif self.risk_manager.check_take_profit_hit(position_id, current_price):
                positions_to_close.append((position_id, 'take_profit'))

        for position_id, reason in positions_to_close:
            trade_result = self.risk_manager.close_position(
                position_id, current_price, reason
            )
            logger.info(f"Closed position {position_id}: {trade_result}")

    async def _news_monitoring_loop(self):
        """Background task for continuous news monitoring."""
        logger.info("Starting news monitoring background task...")
        
        while self.running:
            try:
                # Update news sentiment
                await self.news_strategy.update_sentiment()
                
                # Get sentiment report
                report = self.news_strategy.get_sentiment_summary()
                if report['status'] == 'ok':
                    logger.info(
                        f"News sentiment updated: {report['overall_sentiment']:.1f}, "
                        f"actionable: {report['is_actionable']}"
                    )
                    
                    # Send Telegram alert for significant news
                    if report['is_actionable'] and report['significant_news_count'] >= 3:
                        await self.telegram.send_message(
                            f"📰 Significant news detected!\n"
                            f"Sentiment: {report['overall_sentiment']:.1f}\n"
                            f"Significant items: {report['significant_news_count']}\n"
                            f"Top news: {report['top_news_summaries'][0]['summary'] if report['top_news_summaries'] else 'N/A'}"
                        )
                
                # Wait for next check
                await asyncio.sleep(config.news_check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in news monitoring loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _darknet_monitoring_loop(self):
        """Background task for darknet adoption monitoring."""
        logger.info("Starting darknet monitoring background task...")
        
        while self.running:
            try:
                # Update darknet adoption data
                logger.info("Updating darknet marketplace adoption data...")
                success = await self.darknet_strategy.update_adoption_data()
                
                if success:
                    # Get adoption report
                    report = self.darknet_strategy.get_adoption_report()
                    
                    if report['status'] == 'ok':
                        logger.info(
                            f"Darknet adoption updated: "
                            f"XMR={report['current_adoption']['xmr_percentage']:.1f}%, "
                            f"BTC={report['current_adoption']['btc_percentage']:.1f}%, "
                            f"trend={report['current_adoption']['trend']}, "
                            f"zone={report['signal_status']['current_zone']}"
                        )
                        
                        # Send Telegram alert for significant adoption changes
                        current_zone = report['signal_status']['current_zone']
                        if current_zone in ['bullish', 'bearish']:
                            xmr_pct = report['current_adoption']['xmr_percentage']
                            trend = report['current_adoption']['trend']
                            confidence = report['data_quality']['confidence']
                            
                            await self.telegram.send_message(
                                f"🧅 Darknet Adoption Update\n"
                                f"Zone: {current_zone.upper()}\n"
                                f"XMR: {xmr_pct:.1f}%\n"
                                f"Trend: {trend}\n"
                                f"Confidence: {confidence:.2f}\n"
                                f"Marketplaces: {report['data_quality']['marketplaces_count']}"
                            )
                else:
                    logger.warning("Failed to update darknet adoption data")
                
                # Wait for next check (default 24 hours)
                await asyncio.sleep(config.darknet_update_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Error in darknet monitoring loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down trading bot...")
        self.running = False
        await self.data_aggregator.disconnect_all()
        
        # Disconnect news monitoring
        if self.news_strategy:
            await self.news_strategy.news_aggregator.twitter_client.disconnect()
            await self.news_strategy.news_aggregator.news_classifier.disconnect()
        
        # Disconnect darknet monitoring
        if self.tor_client:
            self.tor_client.disconnect()
            logger.info("Disconnected from Tor network")
        
        logger.info("Bot shutdown complete")

    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Run a backtest on historical data"""
        from src.backtest.backtester import Backtester

        # This would need historical data - for demo purposes
        logger.info(f"Running backtest from {start_date} to {end_date}")

        # Placeholder - in real implementation, load historical data
        dates = pd.date_range(start_date, end_date, freq='H')
        dummy_data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(len(dates)).cumsum(),
            'high': 100 + np.random.randn(len(dates)).cumsum() + 2,
            'low': 100 + np.random.randn(len(dates)).cumsum() - 2,
            'close': 100 + np.random.randn(len(dates)).cumsum(),
            'volume': np.random.rand(len(dates)) * 1000
        }, index=dates)

        backtester = Backtester(self.initial_capital)
        results = backtester.run_backtest(dummy_data)

        return backtester.generate_report()


async def main():
    """Main entry point"""
    bot = MoneroTradingBot(initial_capital=10000)

    try:
        await bot.initialize()

        # Choose mode: live trading or backtest
        mode = "live"  # or "backtest"

        if mode == "live":
            await bot.run_twice_daily_checks()
        else:
            # Backtest mode
            report = bot.run_backtest("2024-01-01", "2024-02-01")
            print(f"Backtest results: {report}")

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())