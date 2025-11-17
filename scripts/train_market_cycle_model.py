#!/usr/bin/env python3
"""
Train Market Cycle XGBoost Model for Monero

This script:
1. Collects historical XMR and BTC data
2. Calculates 30+ market cycle indicators
3. Trains an XGBoost model to predict XMR price movements
4. Evaluates model performance
5. Saves the trained model for use in trading bot
"""

import logging
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.market_cycle_indicators import MarketCycleIndicators
from src.strategies.ml.market_cycle_xgboost import MarketCycleXGBoost
from src.utils.market_data_collector import MarketDataCollector, collect_and_save_market_data

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main training pipeline"""

    print("\n" + "=" * 70)
    print(" " * 15 + "MARKET CYCLE XGBOOST TRAINER")
    print("=" * 70 + "\n")

    # Configuration
    timeframe = "1h"
    days_history = 730  # 2 years
    exchange = "binance"

    print("Configuration:")
    print(f"  Exchange: {exchange}")
    print(f"  Timeframe: {timeframe}")
    print(f"  History: {days_history} days")
    print()

    # Step 1: Collect Data
    print("\n" + "=" * 70)
    print("STEP 1: Collecting Historical Data")
    print("=" * 70 + "\n")

    collector = MarketDataCollector(exchange)

    # Try to load cached data first
    try:
        xmr_df = collector.load_data(f"xmr_usdt_{timeframe}_{days_history}d.csv")
        btc_df = collector.load_data(f"btc_usdt_{timeframe}_{days_history}d.csv")

        if xmr_df.empty or btc_df.empty:
            raise FileNotFoundError("Cached data not found or empty")

        print("✓ Loaded cached data")

    except (FileNotFoundError, Exception):
        print("Fetching fresh data from exchange...")
        data = collect_and_save_market_data(
            timeframe=timeframe, days=days_history, exchange=exchange
        )
        xmr_df = data["xmr"]
        btc_df = data["btc"]

    if xmr_df.empty or btc_df.empty:
        print("❌ Failed to collect data!")
        return

    print("\n✓ Data ready:")
    print(f"  XMR: {len(xmr_df)} candles")
    print(f"  BTC: {len(btc_df)} candles")
    print(f"  Date range: {xmr_df.index[0]} to {xmr_df.index[-1]}")

    # Step 2: Calculate Market Cycle Indicators
    print("\n" + "=" * 70)
    print("STEP 2: Calculating Market Cycle Indicators")
    print("=" * 70 + "\n")

    cycle_indicators = MarketCycleIndicators()

    print("Calculating 30+ market cycle indicators...")
    xmr_with_indicators = cycle_indicators.calculate_all_indicators(xmr_df, btc_df)

    print(f"✓ Calculated {len(xmr_with_indicators.columns)} total features")

    # Show indicator summary
    summary = cycle_indicators.get_indicator_summary(xmr_with_indicators)

    print("\nCurrent Market Cycle Indicators:")
    print(f"  Mayer Multiple: {summary.get('mayer_multiple', 0):.2f}")
    print(f"  Rainbow Position: {summary.get('rainbow_position', 0):.0f}/9")
    print(f"  Pi Cycle Ratio: {summary.get('pi_cycle_ratio', 0):.2f}")
    print(f"  RSI (22d): {summary.get('rsi_22', 0):.1f}")
    print(f"  Drawdown from ATH: {summary.get('drawdown_from_ath', 0):.1f}%")
    print(f"  Cycle Position: {summary.get('cycle_position', 'unknown')}")
    print(f"  Cycle Score: {summary.get('cycle_score', 0):.1f}")

    # Step 3: Train XGBoost Model
    print("\n" + "=" * 70)
    print("STEP 3: Training XGBoost Model")
    print("=" * 70 + "\n")

    # Initialize model
    model = MarketCycleXGBoost(
        min_confidence=0.65,
        retrain_frequency=168,  # 1 week
    )

    # Train model
    print("Starting model training...")
    print("(This may take 5-10 minutes depending on your hardware)\n")

    train_result = model.train_model(xmr_with_indicators, btc_df)

    if not train_result.get("success"):
        print(f"❌ Training failed: {train_result.get('reason')}")
        return

    print("\n✓ Training completed successfully!")

    # Step 4: Evaluate Model
    print("\n" + "=" * 70)
    print("STEP 4: Model Evaluation")
    print("=" * 70 + "\n")

    print("Running backtest...")
    backtest_result = model.backtest_model(xmr_with_indicators, btc_df, train_size=0.7)

    if "error" not in backtest_result:
        print("\nBacktest Results:")
        print(f"  Overall Accuracy: {backtest_result['overall_accuracy']:.2%}")
        print(f"  High Confidence Accuracy: {backtest_result['high_confidence_accuracy']:.2%}")
        print(f"  Buy Signal Accuracy: {backtest_result['buy_signal_accuracy']:.2%}")
        print(f"  Sell Signal Accuracy: {backtest_result['sell_signal_accuracy']:.2%}")
        print(f"  Total Test Samples: {backtest_result['total_samples']}")
        print(f"  High Confidence Signals: {backtest_result['high_confidence_samples']}")
        print(f"  Buy Signals: {backtest_result['buy_signals']}")
        print(f"  Sell Signals: {backtest_result['sell_signals']}")

    # Step 5: Test Prediction
    print("\n" + "=" * 70)
    print("STEP 5: Testing Real-Time Prediction")
    print("=" * 70 + "\n")

    prediction = model.predict(xmr_with_indicators, btc_df)

    if prediction:
        print("Current Prediction:")
        print(f"  Action: {prediction['prediction']}")
        print(f"  Confidence: {prediction['confidence']:.2%}")
        print("  Probabilities:")
        print(f"    - SELL: {prediction['probabilities']['sell']:.2%}")
        print(f"    - HOLD: {prediction['probabilities']['hold']:.2%}")
        print(f"    - BUY:  {prediction['probabilities']['buy']:.2%}")
        print(f"  Cycle Position: {prediction['cycle_position']}")
        print(f"  Cycle Confidence: {prediction['cycle_confidence']:.2%}")

    # Step 6: Save Model Info
    print("\n" + "=" * 70)
    print("STEP 6: Saving Model Information")
    print("=" * 70 + "\n")

    # Save training report
    report_filename = f"data/models/training_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(report_filename, "w") as f:
        f.write("Market Cycle XGBoost Training Report\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Training Date: {datetime.now()}\n")
        f.write(f"Timeframe: {timeframe}\n")
        f.write(f"History: {days_history} days\n")
        f.write(f"Samples: {len(xmr_with_indicators)}\n\n")

        f.write("Training Results:\n")
        f.write(f"  Accuracy: {train_result['accuracy']:.3f}\n")
        f.write(f"  Precision: {train_result['precision']:.3f}\n")
        f.write(f"  Recall: {train_result['recall']:.3f}\n")
        f.write(f"  F1 Score: {train_result['f1_score']:.3f}\n\n")

        f.write("Top 15 Features:\n")
        for i, (feat, imp) in enumerate(train_result["top_features"], 1):
            f.write(f"  {i:2d}. {feat:40s} {imp:.4f}\n")

    print(f"✓ Saved training report: {report_filename}")

    # Final Summary
    print("\n" + "=" * 70)
    print("✓ TRAINING PIPELINE COMPLETED")
    print("=" * 70)
    print("\nModel saved to: data/models/market_cycle_xgboost.pkl")
    print("The model is now ready to use in your trading bot!")
    print("\nTo use in your bot:")
    print("  1. Import: from src.strategies.ml.market_cycle_xgboost import MarketCycleXGBoost")
    print("  2. Initialize: strategy = MarketCycleXGBoost()")
    print("  3. Generate signals: signal = strategy.generate_signal(xmr_df, btc_df)")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
    except Exception as e:
        logger.error(f"Training failed with error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
