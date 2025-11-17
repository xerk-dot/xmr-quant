"""
Market Cycle Indicators for Monero (XMR)
Adapted from the 30+ Bitcoin market cycle indicators on CoinMarketCap

These indicators help identify market cycle tops/bottoms and regime changes.
Many are adapted from Bitcoin metrics to work with Monero.
"""

import logging
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarketCycleIndicators:
    """
    Implements 30+ market cycle indicators adapted for Monero
    Based on: https://coinmarketcap.com/charts/market-cycle-indicators/
    """

    def __init__(self):
        self.indicators_cache = {}
        self.last_update = None

    def calculate_all_indicators(
        self, df: pd.DataFrame, btc_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """
        Calculate all market cycle indicators

        Args:
            df: XMR price/volume data with OHLCV
            btc_df: Optional BTC data for correlation indicators

        Returns:
            DataFrame with all indicators added
        """
        df = df.copy()

        # Ensure we have required columns
        if "close" not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")

        # Price-based indicators (adapted for XMR)
        df = self._add_price_indicators(df)

        # Momentum indicators
        df = self._add_momentum_indicators(df)

        # Moving average indicators
        df = self._add_moving_average_indicators(df)

        # Volatility indicators
        df = self._add_volatility_indicators(df)

        # Volume indicators
        df = self._add_volume_indicators(df)

        # Market structure indicators
        df = self._add_market_structure_indicators(df)

        # Cross-asset indicators (if BTC data available)
        if btc_df is not None:
            df = self._add_cross_asset_indicators(df, btc_df)

        self.last_update = datetime.now()

        return df

    def _add_price_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Price-based cycle indicators"""

        # 1. Rainbow Chart (position in price bands)
        # Uses logarithmic bands around long-term MA
        ma_350 = df["close"].rolling(350).mean()

        if len(df) > 350:
            log_deviation = np.log(df["close"] / ma_350)

            # Rainbow bands (0-9, where 9 is most overbought)
            df["rainbow_position"] = pd.cut(
                log_deviation,
                bins=[-np.inf, -0.8, -0.5, -0.3, -0.1, 0, 0.1, 0.3, 0.5, 0.8, np.inf],
                labels=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            ).astype(float)
        else:
            df["rainbow_position"] = 4  # Neutral

        # 2. Mayer Multiple (Price / 200 MA)
        ma_200 = df["close"].rolling(200).mean()
        df["mayer_multiple"] = df["close"] / ma_200

        # 3. Price oscillator (short MA / long MA)
        ma_50 = df["close"].rolling(50).mean()
        ma_200 = df["close"].rolling(200).mean()
        df["price_oscillator"] = ma_50 / ma_200

        # 4. Percentage above/below 200 MA
        df["pct_above_ma200"] = (df["close"] - ma_200) / ma_200 * 100

        # 5. 52-week high/low indicator
        high_52w = df["close"].rolling(365).max()
        low_52w = df["close"].rolling(365).min()
        df["pct_from_52w_high"] = (df["close"] - high_52w) / high_52w * 100
        df["pct_from_52w_low"] = (df["close"] - low_52w) / low_52w * 100

        return df

    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Momentum-based cycle indicators"""

        # 6. RSI - 22 Day (like CMC uses)
        df["rsi_22"] = self._calculate_rsi(df["close"], period=22)

        # 7. RSI - 14 Day (standard)
        if "rsi" not in df.columns:
            df["rsi"] = self._calculate_rsi(df["close"], period=14)

        # 8. Stochastic RSI
        df["stoch_rsi"] = self._calculate_stoch_rsi(df["close"])

        # 9. Rate of Change (3-month annualized)
        returns_90d = df["close"].pct_change(90)
        df["roc_3m_annualized"] = returns_90d * (365 / 90) * 100

        # 10. Momentum (12-period)
        df["momentum_12"] = df["close"] / df["close"].shift(12) - 1

        # 11. Momentum strength (normalized)
        df["momentum_strength"] = df["close"].pct_change(20).rolling(20).mean()

        return df

    def _add_moving_average_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Moving average based cycle indicators"""

        # 12. Pi Cycle Top Indicator (111 DMA vs 350 DMA * 2)
        ma_111 = df["close"].rolling(111).mean()
        ma_350 = df["close"].rolling(350).mean()

        df["pi_cycle_111dma"] = ma_111
        df["pi_cycle_350dma_x2"] = ma_350 * 2
        df["pi_cycle_ratio"] = ma_111 / (ma_350 * 2)  # When > 1, potential top

        # 13. 2-Year MA Multiplier
        ma_730 = df["close"].rolling(730).mean()  # 2 years (assuming daily data)
        df["ma_2y"] = ma_730
        df["ma_2y_x5"] = ma_730 * 5  # Traditional top indicator
        df["price_to_2y_ma"] = df["close"] / ma_730

        # 14. Golden Ratio Multiplier (350 DMA with Fibonacci multiples)
        df["golden_ratio_350"] = ma_350
        df["golden_ratio_1618"] = ma_350 * 1.618
        df["golden_ratio_2618"] = ma_350 * 2.618

        # 15. 4-Year Moving Average Ratio
        if len(df) >= 1460:
            ma_4y = df["close"].rolling(1460).mean()
            df["ma_4y_ratio"] = df["close"] / ma_4y
        else:
            df["ma_4y_ratio"] = 1.0

        # 16. Terminal Price (200 WMA for daily data, use 200 DMA)
        df["terminal_price"] = df["close"].rolling(200).mean()

        return df

    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Volatility-based cycle indicators"""

        # 17. Historical volatility (20-day annualized)
        returns = df["close"].pct_change()
        df["volatility_20d"] = returns.rolling(20).std() * np.sqrt(365) * 100

        # 18. Volatility regime (percentile rank)
        df["volatility_percentile"] = df["volatility_20d"].rolling(200).rank(pct=True) * 100

        # 19. Bollinger Band Width
        ma_20 = df["close"].rolling(20).mean()
        std_20 = df["close"].rolling(20).std()
        upper_bb = ma_20 + (2 * std_20)
        lower_bb = ma_20 - (2 * std_20)
        df["bb_width"] = (upper_bb - lower_bb) / ma_20 * 100

        # 20. ATR as % of price
        if "atr" not in df.columns:
            df["atr"] = self._calculate_atr(df)
        df["atr_pct"] = (df["atr"] / df["close"]) * 100

        return df

    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Volume-based cycle indicators"""

        if "volume" not in df.columns:
            logger.warning("No volume data available for volume indicators")
            df["volume"] = 0
            return df

        # 21. Volume oscillator
        vol_short = df["volume"].rolling(5).mean()
        vol_long = df["volume"].rolling(20).mean()
        df["volume_oscillator"] = (vol_short - vol_long) / vol_long * 100

        # 22. Volume trend (20-day)
        df["volume_trend"] = df["volume"].rolling(20).mean() / df["volume"].rolling(50).mean()

        # 23. Volume surge indicator
        vol_ma = df["volume"].rolling(20).mean()
        df["volume_surge"] = df["volume"] / vol_ma

        # 24. On-Balance Volume (OBV) momentum
        obv = (np.sign(df["close"].diff()) * df["volume"]).cumsum()
        df["obv"] = obv
        df["obv_momentum"] = obv.pct_change(20)

        return df

    def _add_market_structure_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Market structure indicators"""

        # 25. Market Regime (trending vs ranging)
        # Using ADX-like calculation
        df["market_regime_score"] = self._calculate_trend_strength(df)

        # 26. Higher highs / Lower lows sequence
        df["hh_sequence"] = self._count_higher_highs(df["close"])
        df["ll_sequence"] = self._count_lower_lows(df["close"])

        # 27. Support/Resistance proximity
        df["near_resistance"] = self._calculate_resistance_proximity(df)
        df["near_support"] = self._calculate_support_proximity(df)

        # 28. Drawdown from ATH
        cummax = df["close"].cummax()
        df["drawdown_from_ath"] = (df["close"] - cummax) / cummax * 100

        # 29. Days since ATH
        df["days_since_ath"] = 0
        ath_indices = df["close"].cummax().diff().ne(0)
        df.loc[ath_indices, "days_since_ath"] = df.index.to_series().diff().dt.days
        df["days_since_ath"] = df["days_since_ath"].replace(0, np.nan).ffill().fillna(0)

        return df

    def _add_cross_asset_indicators(self, df: pd.DataFrame, btc_df: pd.DataFrame) -> pd.DataFrame:
        """Cross-asset indicators using BTC data"""

        # Align timeframes
        if len(btc_df) != len(df):
            logger.warning("BTC and XMR dataframes have different lengths, aligning...")
            btc_df = btc_df.reindex(df.index, method="ffill")

        # 30. XMR/BTC ratio
        df["xmr_btc_ratio"] = df["close"] / btc_df["close"]
        df["xmr_btc_ratio_ma"] = df["xmr_btc_ratio"].rolling(50).mean()
        df["xmr_btc_ratio_deviation"] = (
            (df["xmr_btc_ratio"] - df["xmr_btc_ratio_ma"]) / df["xmr_btc_ratio_ma"] * 100
        )

        # 31. XMR vs BTC momentum divergence
        xmr_momentum = df["close"].pct_change(20)
        btc_momentum = btc_df["close"].pct_change(20)
        df["momentum_divergence"] = xmr_momentum - btc_momentum

        # 32. Correlation with BTC (rolling 30-period)
        df["xmr_btc_correlation"] = (
            df["close"].pct_change().rolling(30).corr(btc_df["close"].pct_change())
        )

        # 33. Beta to BTC
        xmr_returns = df["close"].pct_change()
        btc_returns = btc_df["close"].pct_change()

        covariance = xmr_returns.rolling(60).cov(btc_returns)
        btc_variance = btc_returns.rolling(60).var()
        df["beta_to_btc"] = covariance / btc_variance

        return df

    # Helper methods

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_stoch_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Stochastic RSI"""
        rsi = self._calculate_rsi(series, period)
        stoch_rsi = (
            (rsi - rsi.rolling(period).min())
            / (rsi.rolling(period).max() - rsi.rolling(period).min())
            * 100
        )
        return stoch_rsi

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(period).mean()

        return atr

    def _calculate_trend_strength(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate trend strength (ADX-like)"""
        up_move = df["high"] - df["high"].shift()
        down_move = df["low"].shift() - df["low"]

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        atr = self._calculate_atr(df, period)

        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / atr

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()

        return adx

    def _count_higher_highs(self, series: pd.Series, period: int = 5) -> pd.Series:
        """Count consecutive higher highs"""
        rolling_max = series.rolling(period).max()
        is_higher_high = series >= rolling_max.shift()

        # Count consecutive trues
        consecutive = is_higher_high.groupby(
            (is_higher_high != is_higher_high.shift()).cumsum()
        ).cumsum()
        return consecutive

    def _count_lower_lows(self, series: pd.Series, period: int = 5) -> pd.Series:
        """Count consecutive lower lows"""
        rolling_min = series.rolling(period).min()
        is_lower_low = series <= rolling_min.shift()

        consecutive = is_lower_low.groupby((is_lower_low != is_lower_low.shift()).cumsum()).cumsum()
        return consecutive

    def _calculate_resistance_proximity(self, df: pd.DataFrame, lookback: int = 50) -> pd.Series:
        """Calculate proximity to recent resistance (0-100)"""
        recent_high = df["high"].rolling(lookback).max()
        distance = (recent_high - df["close"]) / df["close"] * 100
        # Normalize to 0-100 where 100 = at resistance
        proximity = 100 * np.exp(-distance / 5)
        return proximity

    def _calculate_support_proximity(self, df: pd.DataFrame, lookback: int = 50) -> pd.Series:
        """Calculate proximity to recent support (0-100)"""
        recent_low = df["low"].rolling(lookback).min()
        distance = (df["close"] - recent_low) / df["close"] * 100
        # Normalize to 0-100 where 100 = at support
        proximity = 100 * np.exp(-distance / 5)
        return proximity

    def get_cycle_position(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Get overall market cycle position (accumulation, markup, distribution, markdown)

        Returns a composite score from multiple indicators
        """
        if len(df) < 200:
            return {"position": "unknown", "score": 0, "confidence": 0, "signals": []}

        latest = df.iloc[-1]
        signals = []
        bullish_score = 0
        bearish_score = 0

        # Analyze key indicators

        # 1. Pi Cycle (if crossed, likely top)
        if latest.get("pi_cycle_ratio", 0) > 1.0:
            bearish_score += 3
            signals.append("pi_cycle_top_signal")

        # 2. Mayer Multiple (> 2.4 often indicates top)
        mayer = latest.get("mayer_multiple", 1)
        if mayer > 2.0:
            bearish_score += 2
        elif mayer < 0.8:
            bullish_score += 2
            signals.append("mayer_multiple_bottom")

        # 3. Rainbow position
        rainbow = latest.get("rainbow_position", 4)
        if rainbow >= 8:
            bearish_score += 2
            signals.append("rainbow_top")
        elif rainbow <= 2:
            bullish_score += 2
            signals.append("rainbow_bottom")

        # 4. RSI extremes
        rsi = latest.get("rsi_22", 50)
        if rsi > 80:
            bearish_score += 1
        elif rsi < 20:
            bullish_score += 1

        # 5. Drawdown from ATH
        drawdown = latest.get("drawdown_from_ath", 0)
        if drawdown < -70:
            bullish_score += 3
            signals.append("deep_drawdown")
        elif drawdown > -5:
            bearish_score += 1

        # 6. Volatility regime
        vol_pct = latest.get("volatility_percentile", 50)
        if vol_pct > 90:
            # High vol can mean top or bottom depending on context
            if bullish_score > bearish_score:
                bullish_score += 1  # Capitulation
            else:
                bearish_score += 1  # Fear spike

        # Determine position
        net_score = bullish_score - bearish_score

        if net_score >= 5:
            position = "accumulation"
        elif net_score >= 2:
            position = "early_markup"
        elif net_score >= -2:
            position = "markup"
        elif net_score >= -5:
            position = "distribution"
        else:
            position = "markdown"

        # Calculate confidence based on signal strength
        total_signals = bullish_score + bearish_score
        confidence = min(total_signals / 10, 1.0)

        return {
            "position": position,
            "score": net_score,
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "confidence": confidence,
            "signals": signals,
        }

    def get_indicator_summary(self, df: pd.DataFrame) -> dict[str, Any]:
        """Get summary of all indicators for latest data point"""
        if len(df) == 0:
            return {}

        latest = df.iloc[-1]

        summary = {
            "timestamp": latest.get("timestamp", datetime.now()),
            # Price indicators
            "mayer_multiple": latest.get("mayer_multiple", np.nan),
            "rainbow_position": latest.get("rainbow_position", np.nan),
            "price_to_2y_ma": latest.get("price_to_2y_ma", np.nan),
            # Momentum
            "rsi_22": latest.get("rsi_22", np.nan),
            "roc_3m_annualized": latest.get("roc_3m_annualized", np.nan),
            # Cycle indicators
            "pi_cycle_ratio": latest.get("pi_cycle_ratio", np.nan),
            "drawdown_from_ath": latest.get("drawdown_from_ath", np.nan),
            # Volatility
            "volatility_percentile": latest.get("volatility_percentile", np.nan),
            # Market structure
            "market_regime_score": latest.get("market_regime_score", np.nan),
            # Cross-asset (if available)
            "xmr_btc_ratio": latest.get("xmr_btc_ratio", np.nan),
            "beta_to_btc": latest.get("beta_to_btc", np.nan),
        }

        # Add cycle position
        cycle_info = self.get_cycle_position(df)
        summary["cycle_position"] = cycle_info["position"]
        summary["cycle_score"] = cycle_info["score"]
        summary["cycle_confidence"] = cycle_info["confidence"]

        return summary
