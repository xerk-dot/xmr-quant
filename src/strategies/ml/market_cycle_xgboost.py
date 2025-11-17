"""
XGBoost Strategy Using Market Cycle Indicators for Monero
Uses 30+ market cycle indicators to predict XMR price movements
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler

from ...core.market_cycle_indicators import MarketCycleIndicators
from ..base import BaseStrategy, Signal, SignalType

logger = logging.getLogger(__name__)


class MarketCycleXGBoost(BaseStrategy):
    """
    XGBoost strategy using market cycle indicators

    This strategy uses 30+ market cycle indicators (adapted from Bitcoin cycle indicators)
    to predict Monero price movements using XGBoost machine learning.

    The model predicts one of 3 outcomes:
    - 0: SELL (bearish)
    - 1: HOLD (neutral/uncertain)
    - 2: BUY (bullish)
    """

    def __init__(
        self,
        params: dict[str, Any] | None = None,
        model_path: str | None = None,
        retrain_frequency: int = 168,  # hours (1 week)
        min_confidence: float = 0.65,
    ):
        default_params = {
            "objective": "multi:softprob",
            "num_class": 3,  # sell, hold, buy
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1,
            "random_state": 42,
            "n_jobs": -1,
            "eval_metric": "mlogloss",
        }

        if params:
            default_params.update(params)

        super().__init__("MarketCycleXGBoost", default_params)

        self.model = None
        self.scaler = StandardScaler()
        self.cycle_indicators = MarketCycleIndicators()

        self.model_path = model_path or "data/models/market_cycle_xgboost.pkl"
        self.scaler_path = "data/models/market_cycle_scaler.pkl"
        self.feature_path = "data/models/market_cycle_features.pkl"

        self.retrain_frequency = retrain_frequency
        self.last_train_time: datetime | None = None
        self.feature_columns: list[str] = []
        self.min_confidence = min_confidence

        # Create models directory
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        # Load existing model if available
        self._load_model()

    def _load_model(self):
        """Load existing model, scaler, and feature columns"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("✓ Loaded market cycle XGBoost model")

            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
                logger.info("✓ Loaded scaler")

            if os.path.exists(self.feature_path):
                self.feature_columns = joblib.load(self.feature_path)
                logger.info(f"✓ Loaded {len(self.feature_columns)} feature columns")

        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
            self.model = None

    def _save_model(self):
        """Save model, scaler, and feature columns"""
        try:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            joblib.dump(self.feature_columns, self.feature_path)
            logger.info("✓ Saved market cycle XGBoost model")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def prepare_features(
        self, df: pd.DataFrame, btc_df: pd.DataFrame | None = None
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and target for training

        Args:
            df: XMR price data
            btc_df: Optional BTC price data for correlation features

        Returns:
            (X, y) - features and target
        """

        # Calculate all market cycle indicators
        df_features = self.cycle_indicators.calculate_all_indicators(df, btc_df)

        # Create target variable: future return classification
        # Look ahead 24 hours (or 24 periods)
        future_return = df_features["close"].pct_change(24).shift(-24)

        # Define thresholds for buy/sell signals
        buy_threshold = 0.03  # 3% gain
        sell_threshold = -0.02  # 2% loss

        # Create target:
        # 2 = BUY (expect significant upside)
        # 1 = HOLD (uncertain or small movement)
        # 0 = SELL (expect downside)
        conditions = [
            future_return <= sell_threshold,  # Sell
            future_return >= buy_threshold,  # Buy
        ]
        choices = [0, 2]  # sell, buy
        df_features["target"] = np.select(conditions, choices, default=1)  # default = hold

        # Select feature columns (exclude price/target columns)
        exclude_cols = {
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "target",
            "symbol",
            "timeframe",
            "exchange",
            # Exclude the raw moving averages (keep ratios/indicators)
            "pi_cycle_111dma",
            "pi_cycle_350dma_x2",
            "ma_2y",
            "ma_2y_x5",
            "golden_ratio_350",
            "golden_ratio_1618",
            "golden_ratio_2618",
            "terminal_price",
            "obv",  # OBV is cumulative, use obv_momentum instead
        }

        feature_columns = [
            col
            for col in df_features.columns
            if col not in exclude_cols
            and not col.endswith("_lag_1")  # Avoid look-ahead bias
            and pd.api.types.is_numeric_dtype(df_features[col])
        ]

        # Remove rows with NaN values
        df_clean = df_features.dropna(subset=feature_columns + ["target"])

        if len(df_clean) == 0:
            raise ValueError("No clean data available for training")

        X = df_clean[feature_columns]
        y = df_clean["target"]

        self.feature_columns = feature_columns

        logger.info(f"Prepared {len(X)} samples with {len(feature_columns)} market cycle features")
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")

        return X, y

    def train_model(
        self, df: pd.DataFrame, btc_df: pd.DataFrame | None = None, validation_split: float = 0.2
    ) -> dict[str, Any]:
        """Train the XGBoost model on market cycle indicators"""

        logger.info("=" * 60)
        logger.info("Training Market Cycle XGBoost Model")
        logger.info("=" * 60)

        try:
            X, y = self.prepare_features(df, btc_df)

            if len(X) < 200:
                logger.warning("Insufficient data for training (need at least 200 samples)")
                return {"success": False, "reason": "insufficient_data"}

            # Time-based split (important for time series!)
            split_idx = int(len(X) * (1 - validation_split))
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

            logger.info(f"Training set: {len(X_train)} samples")
            logger.info(f"Validation set: {len(X_val)} samples")

            # Handle class imbalance with sample weights
            class_counts = y_train.value_counts()
            class_weights = {
                cls: len(y_train) / (len(class_counts) * count)
                for cls, count in class_counts.items()
            }
            sample_weights = y_train.map(class_weights)

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)

            # Train model with early stopping
            self.model = xgb.XGBClassifier(**self.params)

            logger.info("Training XGBoost model... (this may take a few minutes)")

            self.model.fit(
                X_train_scaled,
                y_train,
                sample_weight=sample_weights,
                eval_set=[(X_train_scaled, y_train), (X_val_scaled, y_val)],
                early_stopping_rounds=20,
                verbose=False,
            )

            # Evaluate on validation set
            y_pred = self.model.predict(X_val_scaled)

            accuracy = accuracy_score(y_val, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_val, y_pred, average="weighted", zero_division=0
            )

            # Get feature importance
            feature_importance = dict(
                zip(self.feature_columns, self.model.feature_importances_, strict=False)
            )

            # Sort by importance
            top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:15]

            self.last_train_time = datetime.now()
            self._save_model()

            logger.info("=" * 60)
            logger.info("✓ Model training completed!")
            logger.info(f"  Validation Accuracy: {accuracy:.3f}")
            logger.info(f"  Precision: {precision:.3f}")
            logger.info(f"  Recall: {recall:.3f}")
            logger.info(f"  F1 Score: {f1:.3f}")
            logger.info("")
            logger.info("Top 15 Most Important Features:")
            for i, (feature, importance) in enumerate(top_features, 1):
                logger.info(f"  {i:2d}. {feature:30s} {importance:.4f}")
            logger.info("=" * 60)

            return {
                "success": True,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "feature_importance": feature_importance,
                "top_features": top_features,
                "train_samples": len(X_train),
                "val_samples": len(X_val),
                "class_distribution": y.value_counts().to_dict(),
            }

        except Exception as e:
            logger.error(f"Model training failed: {e}", exc_info=True)
            return {"success": False, "reason": str(e)}

    def predict(
        self, df: pd.DataFrame, btc_df: pd.DataFrame | None = None
    ) -> dict[str, Any] | None:
        """Predict using trained model"""

        if self.model is None:
            logger.warning("No trained model available")
            return None

        try:
            # Calculate market cycle indicators
            df_features = self.cycle_indicators.calculate_all_indicators(df, btc_df)

            if len(df_features) == 0:
                return None

            # Get latest row features
            latest_features = df_features[self.feature_columns].iloc[-1:].fillna(0)

            # Scale features
            features_scaled = self.scaler.transform(latest_features)

            # Get predictions
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]

            # Map predictions
            action_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
            predicted_action = action_map[prediction]
            confidence = max(probabilities)

            # Get cycle position for context
            cycle_info = self.cycle_indicators.get_cycle_position(df_features)

            return {
                "prediction": predicted_action,
                "confidence": confidence,
                "probabilities": {
                    "sell": probabilities[0],
                    "hold": probabilities[1],
                    "buy": probabilities[2],
                },
                "cycle_position": cycle_info["position"],
                "cycle_score": cycle_info["score"],
                "cycle_confidence": cycle_info["confidence"],
            }

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return None

    def should_retrain(self) -> bool:
        """Check if model should be retrained"""
        if self.model is None:
            return True

        if self.last_train_time is None:
            return True

        time_since_training = datetime.now() - self.last_train_time
        return time_since_training > timedelta(hours=self.retrain_frequency)

    def generate_signal(
        self, df: pd.DataFrame, btc_df: pd.DataFrame | None = None
    ) -> Signal | None:
        """Generate trading signal based on market cycle indicators"""

        if len(df) < 400:  # Need more data for cycle indicators
            logger.warning("Insufficient data for market cycle analysis (need 400+ periods)")
            return None

        # Check if retrain is needed
        if self.should_retrain():
            logger.info("Retraining market cycle model...")
            train_result = self.train_model(df, btc_df)

            if not train_result.get("success", False):
                logger.warning(f"Model retraining failed: {train_result.get('reason', 'unknown')}")
                return None

        # Get prediction
        prediction_result = self.predict(df, btc_df)

        if prediction_result is None:
            return None

        predicted_action = prediction_result["prediction"]
        confidence = prediction_result["confidence"]

        # Only generate signals with sufficient confidence
        if confidence < self.min_confidence:
            logger.debug(f"Confidence too low: {confidence:.2f} < {self.min_confidence}")
            return None

        # Map prediction to signal type
        signal_map = {"BUY": SignalType.BUY, "SELL": SignalType.SELL, "HOLD": None}

        signal_type = signal_map.get(predicted_action)

        if signal_type is None:
            return None

        # Calculate strength (scale confidence to 0.5-1.0 range)
        strength = 0.5 + (confidence - self.min_confidence) / (1 - self.min_confidence) * 0.5
        strength = min(1.0, max(0.5, strength))

        logger.info(
            f"Market Cycle Signal: {predicted_action} | "
            f"Confidence: {confidence:.2%} | "
            f"Cycle: {prediction_result['cycle_position']}"
        )

        return Signal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            strategy_name=self.name,
            timestamp=pd.Timestamp.now(),
            metadata={
                "predicted_action": predicted_action,
                "probabilities": prediction_result["probabilities"],
                "cycle_position": prediction_result["cycle_position"],
                "cycle_score": prediction_result["cycle_score"],
                "cycle_confidence": prediction_result["cycle_confidence"],
            },
        )

    def validate_signal(self, signal: Signal, df: pd.DataFrame) -> bool:
        """Validate signal"""
        # Check confidence threshold
        if signal.confidence < self.min_confidence:
            return False

        # Check if we have recent data
        if len(df) < 50:
            return False

        return True

    def calculate_signal_strength(self, df: pd.DataFrame) -> float:
        """Calculate signal strength (handled in generate_signal)"""
        return 0.5

    def calculate_confidence(self, df: pd.DataFrame) -> float:
        """Calculate confidence (handled in generate_signal)"""
        return 0.5

    def get_feature_importance(self) -> dict[str, float] | None:
        """Get feature importance from trained model"""
        if self.model is None:
            return None

        return dict(zip(self.feature_columns, self.model.feature_importances_, strict=False))

    def backtest_model(
        self, df: pd.DataFrame, btc_df: pd.DataFrame | None = None, train_size: float = 0.7
    ) -> dict[str, Any]:
        """Backtest the model performance"""

        try:
            X, y = self.prepare_features(df, btc_df)

            # Time-based split
            split_idx = int(len(X) * train_size)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            # Train model
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            model = xgb.XGBClassifier(**self.params)
            model.fit(X_train_scaled, y_train, verbose=False)

            # Predictions
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)

            accuracy = accuracy_score(y_test, y_pred)

            # Calculate trading metrics
            # Only consider high-confidence predictions
            high_conf_mask = np.max(y_pred_proba, axis=1) >= self.min_confidence

            if high_conf_mask.sum() > 0:
                filtered_accuracy = accuracy_score(y_test[high_conf_mask], y_pred[high_conf_mask])
            else:
                filtered_accuracy = 0

            # Calculate buy/sell accuracy separately
            buy_mask = y_pred == 2
            sell_mask = y_pred == 0

            buy_accuracy = (
                accuracy_score(y_test[buy_mask], y_pred[buy_mask]) if buy_mask.sum() > 0 else 0
            )
            sell_accuracy = (
                accuracy_score(y_test[sell_mask], y_pred[sell_mask]) if sell_mask.sum() > 0 else 0
            )

            return {
                "overall_accuracy": accuracy,
                "high_confidence_accuracy": filtered_accuracy,
                "buy_signal_accuracy": buy_accuracy,
                "sell_signal_accuracy": sell_accuracy,
                "total_samples": len(y_test),
                "high_confidence_samples": high_conf_mask.sum(),
                "buy_signals": buy_mask.sum(),
                "sell_signals": sell_mask.sum(),
                "class_report": classification_report(y_test, y_pred, output_dict=True),
                "feature_importance": dict(
                    zip(self.feature_columns, model.feature_importances_, strict=False)
                ),
            }

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {"error": str(e)}
