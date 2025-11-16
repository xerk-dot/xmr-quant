"""
Test script for BTC-XMR Correlation Strategy

This script validates the correlation strategy by:
1. Fetching historical BTC and XMR data
2. Calculating correlation and optimal lag
3. Simulating signal generation
4. Providing performance analytics
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

from src.data.data_aggregator import DataAggregator
from src.features.feature_engineering import FeatureEngineer
from src.signals.btc_correlation_strategy import BTCCorrelationStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_btc_correlation():
    """Test the BTC correlation strategy"""
    
    print("=" * 60)
    print("BTC-XMR Correlation Strategy Test")
    print("=" * 60)
    
    # Initialize components
    data_aggregator = DataAggregator()
    feature_engineer = FeatureEngineer()
    btc_strategy = BTCCorrelationStrategy()
    
    # Connect to exchanges
    await data_aggregator.connect_all()
    
    try:
        # Fetch historical data (30 days)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        print("\n📊 Fetching market data...")
        print(f"Period: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
        
        xmr_task = data_aggregator.fetch_aggregated_ohlcv(
            symbol='XMR/USDT',
            timeframe='1h',
            since=start_time,
            limit=720
        )
        
        btc_task = data_aggregator.fetch_aggregated_ohlcv(
            symbol='BTC/USDT',
            timeframe='1h',
            since=start_time,
            limit=720
        )
        
        xmr_df, btc_df = await asyncio.gather(xmr_task, btc_task)
        
        if xmr_df.empty or btc_df.empty:
            print("❌ Failed to fetch market data")
            return
        
        print(f"✓ XMR data: {len(xmr_df)} candles")
        print(f"✓ BTC data: {len(btc_df)} candles")
        
        # Engineer features
        print("\n🔧 Engineering features...")
        xmr_df = feature_engineer.engineer_features(xmr_df)
        btc_df = feature_engineer.engineer_features(btc_df)
        
        # Set BTC data for strategy
        btc_strategy.set_btc_data(btc_df)
        
        # Calculate correlation
        print("\n📈 Analyzing BTC-XMR correlation...")
        corr_report = btc_strategy.get_correlation_report(xmr_df)
        
        print(f"\nCorrelation Coefficient: {corr_report['correlation']:.3f}")
        print(f"Optimal Lag: {corr_report['optimal_lag_hours']} hours")
        
        if abs(corr_report['correlation']) > 0.7:
            print("✓ Strong correlation detected!")
        elif abs(corr_report['correlation']) > 0.5:
            print("✓ Moderate correlation detected")
        else:
            print("⚠️  Weak correlation - strategy may not be effective currently")
        
        # Detect current BTC move
        print("\n🔍 Detecting BTC movements...")
        btc_move = btc_strategy.detect_btc_move(btc_df)
        
        if btc_move:
            print(f"\n🚨 BTC Move Detected:")
            print(f"   Direction: {btc_move['direction'].upper()}")
            print(f"   Magnitude: {btc_move['magnitude']:.2%}")
            print(f"   Window: {btc_move['window']} hours")
            print(f"   Volume Confirmed: {'✓' if btc_move['volume_confirmed'] else '✗'}")
        else:
            print("No significant BTC movement in recent periods")
        
        # Generate signal
        print("\n💡 Generating trading signal...")
        signal = btc_strategy.generate_signal(xmr_df)
        
        if signal:
            print(f"\n{'='*60}")
            print("TRADING SIGNAL GENERATED")
            print(f"{'='*60}")
            print(f"Type: {signal.signal_type.value.upper()}")
            print(f"Strength: {signal.strength:.2%}")
            print(f"Confidence: {signal.confidence:.2%}")
            print(f"Strategy: {signal.strategy_name}")
            print(f"\nMetadata:")
            for key, value in signal.metadata.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
            print(f"{'='*60}")
        else:
            print("No signal generated at this time")
        
        # Historical analysis
        print("\n📊 Historical Performance Analysis...")
        analyze_historical_performance(xmr_df, btc_df, btc_strategy)
        
    finally:
        await data_aggregator.disconnect_all()


def analyze_historical_performance(xmr_df: pd.DataFrame, btc_df: pd.DataFrame, 
                                   strategy: BTCCorrelationStrategy):
    """Analyze how the strategy would have performed historically"""
    
    # Simple backtest: look for BTC moves and check if XMR followed
    btc_returns = btc_df['close'].pct_change()
    xmr_returns = xmr_df['close'].pct_change()
    
    # Find significant BTC moves (>3%)
    significant_moves = []
    for i in range(4, len(btc_df) - 24):  # Need 4h lookback and 24h lookahead
        move_4h = (btc_df['close'].iloc[i] - btc_df['close'].iloc[i-4]) / btc_df['close'].iloc[i-4]
        
        if abs(move_4h) > 0.03:  # 3% threshold
            # Check if XMR followed in next 8-24 hours
            xmr_follow_8h = (xmr_df['close'].iloc[i+8] - xmr_df['close'].iloc[i]) / xmr_df['close'].iloc[i]
            xmr_follow_16h = (xmr_df['close'].iloc[i+16] - xmr_df['close'].iloc[i]) / xmr_df['close'].iloc[i]
            xmr_follow_24h = (xmr_df['close'].iloc[i+24] - xmr_df['close'].iloc[i]) / xmr_df['close'].iloc[i]
            
            # Check if XMR moved in same direction
            same_dir_8h = (move_4h > 0 and xmr_follow_8h > 0) or (move_4h < 0 and xmr_follow_8h < 0)
            same_dir_16h = (move_4h > 0 and xmr_follow_16h > 0) or (move_4h < 0 and xmr_follow_16h < 0)
            same_dir_24h = (move_4h > 0 and xmr_follow_24h > 0) or (move_4h < 0 and xmr_follow_24h < 0)
            
            significant_moves.append({
                'btc_move': move_4h,
                'xmr_8h': xmr_follow_8h,
                'xmr_16h': xmr_follow_16h,
                'xmr_24h': xmr_follow_24h,
                'success_8h': same_dir_8h,
                'success_16h': same_dir_16h,
                'success_24h': same_dir_24h
            })
    
    if significant_moves:
        df_moves = pd.DataFrame(significant_moves)
        
        print(f"\nFound {len(significant_moves)} significant BTC moves (>3%) in the period")
        print(f"\nSuccess Rate (XMR followed BTC direction):")
        print(f"  After  8 hours: {df_moves['success_8h'].mean():.1%}")
        print(f"  After 16 hours: {df_moves['success_16h'].mean():.1%}")
        print(f"  After 24 hours: {df_moves['success_24h'].mean():.1%}")
        
        print(f"\nAverage XMR move following BTC signal:")
        print(f"  After  8 hours: {df_moves['xmr_8h'].mean():.2%}")
        print(f"  After 16 hours: {df_moves['xmr_16h'].mean():.2%}")
        print(f"  After 24 hours: {df_moves['xmr_24h'].mean():.2%}")
        
        # Calculate potential returns if we traded every signal
        print(f"\nSimulated Returns (if traded every signal):")
        trades_8h = [abs(row['xmr_8h']) if row['success_8h'] else -abs(row['xmr_8h']) 
                     for _, row in df_moves.iterrows()]
        trades_16h = [abs(row['xmr_16h']) if row['success_16h'] else -abs(row['xmr_16h']) 
                      for _, row in df_moves.iterrows()]
        
        print(f"  8h horizon:  {sum(trades_8h):.2%} total, {np.mean(trades_8h):.2%} per trade")
        print(f"  16h horizon: {sum(trades_16h):.2%} total, {np.mean(trades_16h):.2%} per trade")
    else:
        print("No significant BTC moves found in the period")


if __name__ == "__main__":
    asyncio.run(test_btc_correlation())

