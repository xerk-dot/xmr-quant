import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
import xgboost as xgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import joblib
import logging
from datetime import datetime, timedelta
import os

from .base_strategy import BaseStrategy, Signal, SignalType
from ..features.feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


class XGBoostTradingStrategy(BaseStrategy):
    def __init__(
        self,
        params: Optional[Dict[str, Any]] = None,
        model_path: Optional[str] = None,
        retrain_frequency: int = 168  # hours (1 week)
    ):
        default_params = {
            'objective': 'multi:softprob',
            'num_class': 3,  # buy, sell, hold
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1
        }
        if params:
            default_params.update(params)

        super().__init__("XGBoostML", default_params)

        self.model = None
        self.scaler = StandardScaler()
        self.feature_engineer = FeatureEngineer()
        self.model_path = model_path or "models/xgboost_model.pkl"
        self.scaler_path = "models/scaler.pkl"
        self.retrain_frequency = retrain_frequency
        self.last_train_time = None
        self.feature_columns = []

        # Create models directory
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        # Load existing model if available
        self._load_model()

    def _load_model(self):
        """Load existing model and scaler"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("Loaded existing XGBoost model")

            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
                logger.info("Loaded existing scaler")

        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
            self.model = None

    def _save_model(self):
        """Save model and scaler"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            logger.info("Saved XGBoost model and scaler")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target for training - REGIME DETECTION approach"""
        # Engineer features
        df_features = self.feature_engineer.engineer_features(df)

        # Define market regimes based on actual market conditions
        # 0 = ranging (low volatility, no trend)
        # 1 = trending_up (clear uptrend)
        # 2 = trending_down (clear downtrend)
        # 3 = high_volatility (choppy, dangerous)

        # Calculate regime indicators
        returns = df_features['close'].pct_change()
        volatility = returns.rolling(20).std()
        vol_percentile = volatility.rolling(100).rank(pct=True)

        # Trend strength using ADX
        trend_strength = df_features.get('adx', 0)

        # Price position relative to moving averages
        if 'ema_20' in df_features.columns and 'ema_50' in df_features.columns:
            above_short = df_features['close'] > df_features['ema_20']
            above_long = df_features['close'] > df_features['ema_50']
            ema_aligned = df_features['ema_20'] > df_features['ema_50']
        else:
            above_short = above_long = ema_aligned = False

        # Define regime conditions
        ranging = (trend_strength < 25) & (vol_percentile < 0.7)
        trending_up = (trend_strength > 25) & above_short & above_long & ema_aligned
        trending_down = (trend_strength > 25) & ~above_short & ~above_long & ~ema_aligned
        high_vol = vol_percentile > 0.8

        # Create target based on regimes
        conditions = [high_vol, trending_up, trending_down, ranging]
        choices = [3, 1, 2, 0]  # high_vol, trend_up, trend_down, ranging
        df_features['target'] = np.select(conditions, choices, default=0)

        # Select features for training
        feature_columns = [
            col for col in df_features.columns
            if col not in ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                          'future_return', 'target', 'symbol', 'timeframe', 'exchange']
            and not col.endswith('_lag_1')  # avoid look-ahead bias
        ]

        # Remove rows with NaN values
        df_clean = df_features.dropna()

        if len(df_clean) == 0:
            raise ValueError("No clean data available for training")

        X = df_clean[feature_columns]
        y = df_clean['target']

        self.feature_columns = feature_columns
        logger.info(f"Prepared {len(X)} samples with {len(feature_columns)} features")

        return X, y

    def train_model(
        self,
        df: pd.DataFrame,
        validation_split: float = 0.2,
        use_time_split: bool = True
    ) -> Dict[str, Any]:
        """Train the XGBoost model"""
        logger.info("Training XGBoost model...")

        try:
            X, y = self.prepare_features(df)

            if len(X) < 100:
                logger.warning("Insufficient data for training")
                return {'success': False, 'reason': 'insufficient_data'}

            # Split data
            if use_time_split:
                split_idx = int(len(X) * (1 - validation_split))
                X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
                y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
            else:
                X_train, X_val, y_train, y_val = train_test_split(
                    X, y, test_size=validation_split, random_state=42, stratify=y
                )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)

            # Train model
            self.model = xgb.XGBClassifier(**self.params)
            self.model.fit(
                X_train_scaled, y_train,
                eval_set=[(X_val_scaled, y_val)],
                verbose=False
            )

            # Evaluate
            y_pred = self.model.predict(X_val_scaled)
            accuracy = accuracy_score(y_val, y_pred)

            # Get feature importance
            feature_importance = dict(zip(
                self.feature_columns,
                self.model.feature_importances_
            ))

            self.last_train_time = datetime.now()
            self._save_model()

            logger.info(f"Model training completed. Validation accuracy: {accuracy:.3f}")

            return {
                'success': True,
                'accuracy': accuracy,
                'feature_importance': feature_importance,
                'train_samples': len(X_train),
                'val_samples': len(X_val),
                'class_distribution': y.value_counts().to_dict()
            }

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return {'success': False, 'reason': str(e)}

    def predict_regime(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Predict market regime using the trained model"""
        if self.model is None:
            logger.warning("No trained model available")
            return None

        try:
            # Engineer features for latest data
            df_features = self.feature_engineer.engineer_features(df)

            if len(df_features) == 0:
                return None

            # Get latest row features
            latest_features = df_features[self.feature_columns].iloc[-1:].fillna(0)

            # Scale features
            features_scaled = self.scaler.transform(latest_features)

            # Get prediction probabilities
            probabilities = self.model.predict_proba(features_scaled)[0]

            # Get prediction
            prediction = self.model.predict(features_scaled)[0]

            # Map to regime names
            regime_map = {
                0: 'ranging',
                1: 'trending_up',
                2: 'trending_down',
                3: 'high_volatility'
            }

            regime = regime_map.get(prediction, 'ranging')
            confidence = max(probabilities)

            logger.info(f"Detected regime: {regime} (confidence: {confidence:.2f})")

            return {
                'regime': regime,
                'confidence': confidence,
                'probabilities': {
                    'ranging': probabilities[0] if len(probabilities) > 0 else 0,
                    'trending_up': probabilities[1] if len(probabilities) > 1 else 0,
                    'trending_down': probabilities[2] if len(probabilities) > 2 else 0,
                    'high_volatility': probabilities[3] if len(probabilities) > 3 else 0
                }
            }

        except Exception as e:
            logger.error(f"Regime prediction failed: {e}")
            return None

    def should_retrain(self) -> bool:
        """Check if model should be retrained"""
        if self.model is None:
            return True

        if self.last_train_time is None:
            return True

        time_since_training = datetime.now() - self.last_train_time
        return time_since_training > timedelta(hours=self.retrain_frequency)

    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        """Generate trading signal based on REGIME DETECTION"""
        if len(df) < 50:
            return None

        # Check if retrain is needed
        if self.should_retrain():
            logger.info("Retraining regime detection model...")
            logger.info("⏳ This may take 1-2 hours on first run...")
            train_result = self.train_model(df)
            if not train_result.get('success', False):
                logger.warning(f"Model retraining failed: {train_result.get('reason', 'unknown')}")
                logger.warning("ML signals will be unavailable until model is trained")
                return None

        # Get regime prediction
        prediction_result = self.predict_regime(df)
        if prediction_result is None:
            return None

        regime = prediction_result['regime']
        confidence = prediction_result['confidence']

        # Apply strategy based on detected regime
        signal_type = None
        strength = 0.5

        latest = df.iloc[-1]

        if regime == 'trending_up':
            # In uptrend: look for pullback entries
            if latest.get('rsi', 50) < 40:  # Oversold in uptrend
                signal_type = SignalType.BUY
                strength = 0.8
            elif latest.get('rsi', 50) > 70:  # Overbought in uptrend
                signal_type = SignalType.HOLD

        elif regime == 'trending_down':
            # In downtrend: look for rallies to short
            if latest.get('rsi', 50) > 60:  # Overbought in downtrend
                signal_type = SignalType.SELL
                strength = 0.8
            elif latest.get('rsi', 50) < 30:  # Oversold in downtrend
                signal_type = SignalType.HOLD

        elif regime == 'ranging':
            # Mean reversion in ranging market
            if latest.get('rsi', 50) < 30:
                signal_type = SignalType.BUY
                strength = 0.6
            elif latest.get('rsi', 50) > 70:
                signal_type = SignalType.SELL
                strength = 0.6

        elif regime == 'high_volatility':
            # Stay out during high volatility
            signal_type = SignalType.HOLD
            strength = 0.1
            logger.info("High volatility detected - staying out")

        if signal_type is None or signal_type == SignalType.HOLD:
            return None

        # Adjust strength based on regime confidence
        strength = strength * confidence

        return Signal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            strategy_name=self.name,
            timestamp=pd.Timestamp.now(),
            metadata={
                'detected_regime': regime,
                'regime_confidence': confidence,
                'rsi': latest.get('rsi', 0),
                'strategy': f"{regime}_strategy"
            }
        )

    def validate_signal(self, signal: Signal, df: pd.DataFrame) -> bool:
        """Validate ML signal"""
        # Basic validation - check if confidence is above threshold
        return signal.confidence > 0.6

    def calculate_signal_strength(self, df: pd.DataFrame) -> float:
        """Calculate signal strength (handled in generate_signal)"""
        return 0.5

    def calculate_confidence(self, df: pd.DataFrame) -> float:
        """Calculate confidence (handled in generate_signal)"""
        return 0.5

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from trained model"""
        if self.model is None:
            return None

        return dict(zip(self.feature_columns, self.model.feature_importances_))

    def backtest_model(
        self,
        df: pd.DataFrame,
        train_size: float = 0.7
    ) -> Dict[str, Any]:
        """Backtest the ML model performance"""
        try:
            X, y = self.prepare_features(df)

            # Time-based split for backtesting
            split_idx = int(len(X) * train_size)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            # Train model
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            model = xgb.XGBClassifier(**self.params)
            model.fit(X_train_scaled, y_train)

            # Predictions
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)

            accuracy = accuracy_score(y_test, y_pred)

            # Calculate directional accuracy for trading
            correct_directions = 0
            total_signals = 0

            for i in range(len(y_test)):
                if y_test.iloc[i] != 1:  # Not hold
                    total_signals += 1
                    if y_pred[i] == y_test.iloc[i]:
                        correct_directions += 1

            directional_accuracy = correct_directions / total_signals if total_signals > 0 else 0

            return {
                'overall_accuracy': accuracy,
                'directional_accuracy': directional_accuracy,
                'total_samples': len(y_test),
                'trading_signals': total_signals,
                'class_report': classification_report(y_test, y_pred, output_dict=True),
                'feature_importance': dict(zip(self.feature_columns, model.feature_importances_))
            }

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {'error': str(e)}