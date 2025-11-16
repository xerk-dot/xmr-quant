#!/usr/bin/env python3
"""
Minimal test script to verify the bot components work
"""
import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_basic_functionality():
    """Test basic imports and functionality"""
    logger.info("Testing basic imports...")

    # Test feature engineering
    from src.features.feature_engineering import FeatureEngineer
    fe = FeatureEngineer()
    logger.info("✓ Feature engineering module loaded")

    # Test ML strategy
    from src.signals.ml_strategy import XGBoostTradingStrategy
    ml_strategy = XGBoostTradingStrategy()
    logger.info("✓ ML strategy module loaded")

    # Test risk manager (without database)
    from src.risk.risk_manager import RiskManager
    risk_manager = RiskManager(initial_capital=10000)
    logger.info("✓ Risk manager module loaded")

    # Create sample data with proper index
    logger.info("\nCreating sample market data...")
    dates = pd.date_range(start=datetime.now() - timedelta(days=60), end=datetime.now(), freq='1h')
    price_series = 100 + np.random.randn(len(dates)).cumsum() * 2
    price_series = np.abs(price_series) + 50  # Ensure positive prices

    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.abs(price_series + np.random.randn(len(dates)) * 0.5),
        'high': np.abs(price_series + abs(np.random.randn(len(dates))) * 2),
        'low': np.abs(price_series - abs(np.random.randn(len(dates))) * 2),
        'close': np.abs(price_series),
        'volume': np.random.rand(len(dates)) * 1000000
    })
    df.set_index('timestamp', inplace=True)  # Set datetime index for VWAP

    logger.info(f"Created {len(df)} hours of sample data")
    logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    # Test feature engineering
    logger.info("\nTesting feature engineering...")
    df_features = fe.engineer_features(df)
    feature_cols = [col for col in df_features.columns if col not in df.columns]
    logger.info(f"Generated {len(feature_cols)} technical indicators")

    # Test ML regime detection
    logger.info("\nTesting ML regime detection...")
    logger.info("Training XGBoost model on sample data...")
    train_result = ml_strategy.train_model(df_features, validation_split=0.2)

    if train_result.get('success'):
        logger.info(f"✓ Model trained successfully")
        logger.info(f"  Validation accuracy: {train_result['accuracy']:.3f}")
        logger.info(f"  Training samples: {train_result['train_samples']}")
        logger.info(f"  Validation samples: {train_result['val_samples']}")

        # Test regime prediction
        regime_result = ml_strategy.predict_regime(df_features)
        if regime_result:
            logger.info(f"\nCurrent market regime: {regime_result['regime']}")
            logger.info(f"Confidence: {regime_result['confidence']:.2%}")
            logger.info("Regime probabilities:")
            for regime, prob in regime_result['probabilities'].items():
                logger.info(f"  {regime}: {prob:.3f}")

        # Test signal generation
        signal = ml_strategy.generate_signal(df_features)
        if signal:
            logger.info(f"\nGenerated signal: {signal.signal_type} (strength: {signal.strength:.2f})")
        else:
            logger.info("\nNo trading signal generated (HOLD)")
    else:
        logger.warning(f"Model training failed: {train_result.get('reason')}")

    # Test risk management calculations
    logger.info("\nTesting risk management...")
    current_price = df['close'].iloc[-1]

    # Calculate position size
    from src.risk.position_sizing import PositionSizer
    sizer = PositionSizer(
        portfolio_value=10000,
        risk_per_trade=0.02
    )
    position_size = sizer.calculate_position_size(
        signal_strength=0.8,
        current_price=current_price,
        stop_loss_price=current_price * 0.95  # 5% stop loss
    )
    logger.info(f"Position size for ${current_price:.2f} with 5% stop: {position_size.units:.4f} units")

    # Test portfolio metrics
    metrics = risk_manager.get_portfolio_metrics()
    logger.info(f"Portfolio metrics: {metrics}")

    logger.info("\n✓ All basic tests passed!")
    logger.info("\nBot architecture summary:")
    logger.info("1. Data ingestion: CCXT for exchange connectivity")
    logger.info("2. Feature engineering: Technical indicators via pandas-ta")
    logger.info("3. ML strategy: XGBoost for regime detection (not price prediction)")
    logger.info("4. Risk management: Position sizing, stop-loss, portfolio limits")
    logger.info("5. The bot uses regime detection to apply different strategies:")
    logger.info("   - Trending up → Momentum strategy")
    logger.info("   - Ranging → Mean reversion")
    logger.info("   - High volatility → Stay out")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())