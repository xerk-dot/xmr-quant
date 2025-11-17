#!/usr/bin/env python3
"""
Market Cycle XGBoost Strategy - Quick Example

This example demonstrates how to use the Market Cycle XGBoost strategy
for Monero trading.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import logging

from src.core.market_cycle_indicators import MarketCycleIndicators
from src.strategies.ml.market_cycle_xgboost import MarketCycleXGBoost
from src.utils.market_data_collector import MarketDataCollector

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def example_1_basic_usage():
    """Example 1: Basic signal generation"""

    print("\n" + "=" * 70)
    print("Example 1: Basic Usage - Generate Trading Signal")
    print("=" * 70 + "\n")

    # Step 1: Collect data
    print("Fetching market data...")
    collector = MarketDataCollector("binance")

    data = collector.fetch_market_cycle_data(
        xmr_symbol="XMR/USDT", btc_symbol="BTC/USDT", timeframe="1h", days=730
    )

    xmr_df = data["xmr"]
    btc_df = data["btc"]

    if xmr_df.empty:
        print("❌ Failed to fetch data")
        return

    print(f"✓ Fetched {len(xmr_df)} candles\n")

    # Step 2: Initialize strategy
    print("Initializing strategy...")
    strategy = MarketCycleXGBoost(min_confidence=0.65)
    print("✓ Strategy ready\n")

    # Step 3: Generate signal
    print("Generating trading signal...")
    signal = strategy.generate_signal(xmr_df, btc_df)

    if signal:
        print("\n📊 SIGNAL GENERATED:")
        print(f"  Action: {signal.signal_type.name}")
        print(f"  Strength: {signal.strength:.2f}")
        print(f"  Confidence: {signal.confidence:.2%}")
        print("\n  Probabilities:")
        print(f"    SELL: {signal.metadata['probabilities']['sell']:.2%}")
        print(f"    HOLD: {signal.metadata['probabilities']['hold']:.2%}")
        print(f"    BUY:  {signal.metadata['probabilities']['buy']:.2%}")
        print("\n  Market Cycle:")
        print(f"    Position: {signal.metadata['cycle_position']}")
        print(f"    Score: {signal.metadata['cycle_score']:.1f}")
        print(f"    Confidence: {signal.metadata['cycle_confidence']:.2%}")
    else:
        print("No signal (low confidence or HOLD recommendation)")

    print("\n" + "=" * 70 + "\n")


def example_2_manual_indicators():
    """Example 2: Manually examine market cycle indicators"""

    print("\n" + "=" * 70)
    print("Example 2: Manual Indicator Analysis")
    print("=" * 70 + "\n")

    # Fetch data
    collector = MarketDataCollector("binance")
    data = collector.fetch_market_cycle_data(timeframe="1h", days=730)

    xmr_df = data["xmr"]
    btc_df = data["btc"]

    if xmr_df.empty:
        print("❌ Failed to fetch data")
        return

    # Calculate indicators
    print("Calculating market cycle indicators...\n")
    indicators = MarketCycleIndicators()
    xmr_with_indicators = indicators.calculate_all_indicators(xmr_df, btc_df)

    # Get latest indicator values
    latest = xmr_with_indicators.iloc[-1]

    print("📈 CURRENT MARKET CYCLE INDICATORS:\n")

    print("Price Indicators:")
    print(f"  Mayer Multiple:        {latest.get('mayer_multiple', 0):.2f} (>2.0 = overheated)")
    print(f"  Rainbow Position:      {latest.get('rainbow_position', 0):.0f}/9 (9 = extreme)")
    print(f"  % Above 200 MA:        {latest.get('pct_above_ma200', 0):.1f}%")

    print("\nMomentum Indicators:")
    print(f"  RSI (22-day):          {latest.get('rsi_22', 0):.1f} (<20 oversold, >80 overbought)")
    print(f"  3M Annualized ROC:     {latest.get('roc_3m_annualized', 0):.1f}%")
    print(f"  Momentum Strength:     {latest.get('momentum_strength', 0):.4f}")

    print("\nCycle Indicators:")
    print(f"  Pi Cycle Ratio:        {latest.get('pi_cycle_ratio', 0):.2f} (>1.0 = potential top)")
    print(f"  2Y MA Multiple:        {latest.get('price_to_2y_ma', 0):.2f}")
    print(f"  Drawdown from ATH:     {latest.get('drawdown_from_ath', 0):.1f}%")

    print("\nVolatility:")
    print(f"  Volatility (20d):      {latest.get('volatility_20d', 0):.1f}%")
    print(f"  Volatility Percentile: {latest.get('volatility_percentile', 0):.0f}%")

    if "xmr_btc_ratio" in latest:
        print("\nCross-Asset:")
        print(f"  XMR/BTC Ratio:         {latest.get('xmr_btc_ratio', 0):.6f}")
        print(f"  Ratio Deviation:       {latest.get('xmr_btc_ratio_deviation', 0):.1f}%")
        print(f"  Beta to BTC:           {latest.get('beta_to_btc', 0):.2f}")

    # Get cycle position
    cycle_info = indicators.get_cycle_position(xmr_with_indicators)

    print("\n🔄 MARKET CYCLE ANALYSIS:")
    print(f"  Position: {cycle_info['position'].upper()}")
    print(f"  Overall Score: {cycle_info['score']:+.1f} (+ = bullish, - = bearish)")
    print(f"  Bullish Score: {cycle_info['bullish_score']}")
    print(f"  Bearish Score: {cycle_info['bearish_score']}")
    print(f"  Confidence: {cycle_info['confidence']:.2%}")

    if cycle_info["signals"]:
        print(f"  Active Signals: {', '.join(cycle_info['signals'])}")

    print("\n" + "=" * 70 + "\n")


def example_3_backtest():
    """Example 3: Backtest the model"""

    print("\n" + "=" * 70)
    print("Example 3: Model Backtesting")
    print("=" * 70 + "\n")

    # Fetch data
    collector = MarketDataCollector("binance")
    data = collector.fetch_market_cycle_data(timeframe="1h", days=730)

    xmr_df = data["xmr"]
    btc_df = data["btc"]

    if xmr_df.empty:
        print("❌ Failed to fetch data")
        return

    # Initialize strategy
    strategy = MarketCycleXGBoost(min_confidence=0.65)

    # Run backtest
    print("Running backtest (this may take a few minutes)...\n")

    results = strategy.backtest_model(xmr_df, btc_df, train_size=0.7)

    if "error" in results:
        print(f"❌ Backtest failed: {results['error']}")
        return

    print("📊 BACKTEST RESULTS:\n")
    print(f"Overall Accuracy:           {results['overall_accuracy']:.2%}")
    print(f"High Confidence Accuracy:   {results['high_confidence_accuracy']:.2%}")
    print("\nSignal Accuracy:")
    print(f"  Buy Signals:              {results['buy_signal_accuracy']:.2%}")
    print(f"  Sell Signals:             {results['sell_signal_accuracy']:.2%}")
    print("\nSignal Counts:")
    print(f"  Total Test Samples:       {results['total_samples']}")
    print(f"  High Confidence Samples:  {results['high_confidence_samples']}")
    print(f"  Buy Signals:              {results['buy_signals']}")
    print(f"  Sell Signals:             {results['sell_signals']}")

    # Show top features
    importance = results["feature_importance"]
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]

    print("\n🔥 TOP 10 MOST IMPORTANT FEATURES:\n")
    for i, (feature, score) in enumerate(top_features, 1):
        print(f"  {i:2d}. {feature:35s} {score:.4f}")

    print("\n" + "=" * 70 + "\n")


def example_4_live_monitoring():
    """Example 4: Live market monitoring (simulated)"""

    print("\n" + "=" * 70)
    print("Example 4: Live Market Monitoring")
    print("=" * 70 + "\n")

    collector = MarketDataCollector("binance")
    strategy = MarketCycleXGBoost(min_confidence=0.70)
    indicators = MarketCycleIndicators()

    print("Fetching latest data...")

    # Fetch latest data
    data = collector.fetch_market_cycle_data(timeframe="1h", days=730)
    xmr_df = data["xmr"]
    btc_df = data["btc"]

    if xmr_df.empty:
        print("❌ Failed to fetch data")
        return

    # Get current price
    current_price = xmr_df["close"].iloc[-1]
    price_24h_ago = xmr_df["close"].iloc[-24]
    change_24h = (current_price - price_24h_ago) / price_24h_ago * 100

    print("\n💰 CURRENT MARKET STATUS:")
    print(f"  XMR Price: ${current_price:.2f}")
    print(f"  24h Change: {change_24h:+.2f}%")

    # Calculate indicators
    xmr_with_indicators = indicators.calculate_all_indicators(xmr_df, btc_df)
    cycle_info = indicators.get_cycle_position(xmr_with_indicators)

    print(f"\n🔄 CYCLE POSITION: {cycle_info['position'].upper()}")
    print(f"  Score: {cycle_info['score']:+.1f}")
    print(f"  Confidence: {cycle_info['confidence']:.2%}")

    # Get model prediction
    prediction = strategy.predict(xmr_with_indicators, btc_df)

    if prediction:
        print("\n🤖 MODEL PREDICTION:")
        print(f"  Action: {prediction['prediction']}")
        print(f"  Confidence: {prediction['confidence']:.2%}")
        print("\n  Probability Distribution:")
        print(
            f"    SELL: {'█' * int(prediction['probabilities']['sell'] * 50)} {prediction['probabilities']['sell']:.1%}"
        )
        print(
            f"    HOLD: {'█' * int(prediction['probabilities']['hold'] * 50)} {prediction['probabilities']['hold']:.1%}"
        )
        print(
            f"    BUY:  {'█' * int(prediction['probabilities']['buy'] * 50)} {prediction['probabilities']['buy']:.1%}"
        )

        # Recommendation
        print("\n💡 RECOMMENDATION:")
        if prediction["confidence"] > 0.75:
            print(f"  ✅ HIGH CONFIDENCE {prediction['prediction']} signal")
            print("  Consider taking action based on your risk tolerance")
        elif prediction["confidence"] > 0.65:
            print(f"  ⚠️  MODERATE confidence {prediction['prediction']} signal")
            print("  Use caution and consider other factors")
        else:
            print("  ⏸️  LOW confidence - recommend WAIT")
            print("  Market conditions unclear")

    print("\n" + "=" * 70 + "\n")


def main():
    """Run all examples"""

    print("\n" + "=" * 70)
    print("       MARKET CYCLE XGBOOST STRATEGY - EXAMPLES")
    print("=" * 70)

    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Manual Indicators", example_2_manual_indicators),
        ("Backtesting", example_3_backtest),
        ("Live Monitoring", example_4_live_monitoring),
    ]

    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print(f"  {len(examples) + 1}. Run All")

    try:
        choice = input("\nSelect example (1-5): ").strip()

        if choice == str(len(examples) + 1):
            # Run all
            for name, func in examples:
                try:
                    func()
                except Exception as e:
                    logger.error(f"Example '{name}' failed: {e}", exc_info=True)
        else:
            idx = int(choice) - 1
            if 0 <= idx < len(examples):
                examples[idx][1]()
            else:
                print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
