import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import joblib
import logging
from datetime import datetime, timedelta
import os

from ..features.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


class XGBoostVolatilityPredictor:
    """Predicts future volatility levels for position sizing and risk management"""

    def __init__(self, model_path: str = "models/volatility_model.pkl"):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_engineer = FeatureEngineer()
        self.model_path = model_path
        self.scaler_path = "models/volatility_scaler.pkl"
        self.feature_columns = []

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self._load_model()

    def _load_model(self):
        """Load existing model and scaler"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("Loaded volatility prediction model")
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
        except Exception as e:
            logger.warning(f"Failed to load volatility model: {e}")

    def _save_model(self):
        """Save model and scaler"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Saved volatility model")
        except Exception as e:
            logger.error(f"Failed to save volatility model: {e}")

    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features for volatility prediction"""
        df_features = self.feature_engineer.engineer_features(df)

        # Calculate actual future volatility (target)
        returns = df_features['close'].pct_change()
        future_vol = returns.rolling(24).std().shift(-24)  # Next 24h volatility

        # Classify volatility into levels
        vol_percentiles = future_vol.rolling(200).rank(pct=True)
        conditions = [
            vol_percentiles <= 0.25,  # Low
            vol_percentiles <= 0.75,  # Normal
            vol_percentiles <= 0.95   # High
        ]
        choices = [0, 1, 2]  # low, normal, high
        df_features['vol_target'] = np.select(conditions, choices, default=3)  # extreme

        # Volatility-specific features
        volatility_features = [
            'atr', 'bb_width', 'returns_std_5', 'returns_std_10', 'returns_std_20',
            'volume_ratio', 'high_low_ratio', 'returns_skew_5', 'returns_kurt_5'
        ]

        # Add market stress indicators
        if 'rsi' in df_features.columns:
            df_features['rsi_extreme'] = ((df_features['rsi'] < 20) | (df_features['rsi'] > 80)).astype(int)

        # Volume surge indicator
        if 'volume_sma' in df_features.columns:
            df_features['volume_surge'] = (df_features['volume'] > df_features['volume_sma'] * 3).astype(int)

        self.feature_columns = [col for col in df_features.columns
                               if col in volatility_features or col.endswith('_surge') or col.endswith('_extreme')]

        # Clean data
        df_clean = df_features.dropna()
        if len(df_clean) == 0:
            raise ValueError("No clean data for volatility model")

        X = df_clean[self.feature_columns]
        y = df_clean['vol_target']

        return X, y

    def train_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train volatility prediction model"""
        logger.info("Training volatility prediction model...")

        try:
            X, y = self.prepare_features(df)

            if len(X) < 100:
                return {'success': False, 'reason': 'insufficient_data'}

            # Time-based split
            split_idx = int(len(X) * 0.8)
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)

            # Train model
            self.model = xgb.XGBClassifier(
                objective='multi:softprob',
                num_class=4,  # low, normal, high, extreme
                max_depth=4,
                learning_rate=0.1,
                n_estimators=100,
                random_state=42
            )

            self.model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = self.model.predict(X_val_scaled)
            accuracy = accuracy_score(y_val, y_pred)

            self._save_model()

            logger.info(f"Volatility model training completed. Accuracy: {accuracy:.3f}")

            return {
                'success': True,
                'accuracy': accuracy,
                'train_samples': len(X_train),
                'val_samples': len(X_val)
            }

        except Exception as e:
            logger.error(f"Volatility model training failed: {e}")
            return {'success': False, 'reason': str(e)}

    def predict(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Predict volatility level"""
        if self.model is None:
            return None

        try:
            df_features = self.feature_engineer.engineer_features(df)
            latest_features = df_features[self.feature_columns].iloc[-1:].fillna(0)
            features_scaled = self.scaler.transform(latest_features)

            probabilities = self.model.predict_proba(features_scaled)[0]
            prediction = self.model.predict(features_scaled)[0]

            vol_map = {0: 'low', 1: 'normal', 2: 'high', 3: 'extreme'}

            return {
                'volatility_level': vol_map[prediction],
                'confidence': max(probabilities),
                'probabilities': {
                    'low': probabilities[0],
                    'normal': probabilities[1],
                    'high': probabilities[2],
                    'extreme': probabilities[3] if len(probabilities) > 3 else 0
                }
            }

        except Exception as e:
            logger.error(f"Volatility prediction failed: {e}")
            return None


class XGBoostSignalFilter:
    """Filters out false signals by analyzing signal quality"""

    def __init__(self, model_path: str = "models/signal_filter_model.pkl"):
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = model_path
        self.scaler_path = "models/signal_filter_scaler.pkl"
        self.feature_columns = []

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self._load_model()

    def _load_model(self):
        """Load existing model"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("Loaded signal filter model")
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
        except Exception as e:
            logger.warning(f"Failed to load signal filter model: {e}")

    def _save_model(self):
        """Save model"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Saved signal filter model")
        except Exception as e:
            logger.error(f"Failed to save signal filter model: {e}")

    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features for signal quality prediction"""
        df_features = df.copy()

        # Generate mock signals (in real implementation, use actual signal history)
        df_features['signal_rsi'] = (df_features['rsi'] < 30).astype(int)
        df_features['signal_macd'] = (df_features['macd'] > df_features['macd_signal']).astype(int)

        # Calculate signal outcomes (did price move in predicted direction?)
        returns_5h = df_features['close'].pct_change(5).shift(-5)
        signal_success = (
            (df_features['signal_rsi'] == 1) & (returns_5h > 0.01) |  # RSI buy signal worked
            (df_features['signal_rsi'] == 0) & (returns_5h < -0.01)   # RSI sell signal worked
        ).astype(int)

        # Context features for signal quality
        context_features = [
            'volume_ratio', 'atr', 'adx', 'bb_pct', 'trend_strength',
            'rsi', 'macd', 'stoch_k'
        ]

        self.feature_columns = [col for col in context_features if col in df_features.columns]

        df_clean = df_features.dropna()
        if len(df_clean) == 0:
            raise ValueError("No clean data for signal filter")

        X = df_clean[self.feature_columns]
        y = df_clean['signal_success'] if 'signal_success' in df_clean.columns else pd.Series([0] * len(df_clean))

        return X, y

    def evaluate_signal(self, df: pd.DataFrame, signal_context: Dict[str, Any]) -> float:
        """Evaluate if a signal is likely to be profitable"""
        if self.model is None:
            return 0.5  # Neutral if no model

        try:
            # Create feature vector from signal context
            feature_vector = pd.DataFrame([signal_context])

            # Ensure we have all required features
            for col in self.feature_columns:
                if col not in feature_vector.columns:
                    feature_vector[col] = 0

            features = feature_vector[self.feature_columns].fillna(0)
            features_scaled = self.scaler.transform(features)

            # Predict signal quality
            probabilities = self.model.predict_proba(features_scaled)[0]
            quality_score = probabilities[1] if len(probabilities) > 1 else 0.5

            return quality_score

        except Exception as e:
            logger.error(f"Signal evaluation failed: {e}")
            return 0.5


class XGBoostExitOptimizer:
    """Optimizes trade exit timing"""

    def __init__(self, model_path: str = "models/exit_optimizer_model.pkl"):
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = model_path
        self.scaler_path = "models/exit_optimizer_scaler.pkl"
        self.feature_columns = []

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        self._load_model()

    def _load_model(self):
        """Load existing model"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("Loaded exit optimizer model")
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
        except Exception as e:
            logger.warning(f"Failed to load exit optimizer model: {e}")

    def should_exit(self, position_context: Dict[str, Any]) -> str:
        """Determine if position should be exited"""
        if self.model is None:
            return "hold"

        try:
            # Create feature vector from position context
            features = pd.DataFrame([{
                'unrealized_pnl_pct': position_context.get('unrealized_pnl_pct', 0),
                'time_in_position_hours': position_context.get('time_in_position_hours', 0),
                'current_rsi': position_context.get('rsi', 50),
                'trend_strength': position_context.get('adx', 25),
                'volatility_level': position_context.get('atr_normalized', 0.02)
            }])

            features_scaled = self.scaler.transform(features)
            prediction = self.model.predict(features_scaled)[0]

            exit_map = {0: "hold", 1: "exit_profit", 2: "exit_loss"}
            return exit_map.get(prediction, "hold")

        except Exception as e:
            logger.error(f"Exit optimization failed: {e}")
            return "hold"