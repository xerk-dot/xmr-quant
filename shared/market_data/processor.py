"""
Data processing utilities for market data.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class DataProcessor:
    """Utilities for processing and transforming market data."""

    @staticmethod
    def quotes_to_dataframe(quotes: Dict) -> pd.DataFrame:
        """
        Convert quotes dictionary to pandas DataFrame.

        Args:
            quotes: Dictionary of quotes from CCXT

        Returns:
            DataFrame with quote data
        """
        if not quotes:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(quotes, orient="index")

        # Convert timestamp to datetime if present
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        if "last_updated" in df.columns:
            df["last_updated"] = pd.to_datetime(df["last_updated"])

        return df

    @staticmethod
    def historical_to_dataframe(historical_data: List[Dict]) -> pd.DataFrame:
        """
        Convert historical quotes list to pandas DataFrame.

        Args:
            historical_data: List of historical quote dictionaries

        Returns:
            DataFrame with historical data
        """
        if not historical_data:
            return pd.DataFrame()

        df = pd.DataFrame(historical_data)

        # Convert timestamp to datetime and set as index
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)

        # Sort by timestamp
        df.sort_index(inplace=True)

        return df

    @staticmethod
    def calculate_returns(df: pd.DataFrame, price_column: str = "price") -> pd.DataFrame:
        """
        Calculate returns from price data.

        Args:
            df: DataFrame with price data
            price_column: Name of the price column

        Returns:
            DataFrame with added return columns
        """
        df = df.copy()

        # Simple returns
        df["returns"] = df[price_column].pct_change()

        # Log returns
        df["log_returns"] = np.log(df[price_column] / df[price_column].shift(1))

        return df

    @staticmethod
    def calculate_moving_averages(
        df: pd.DataFrame, price_column: str = "price", windows: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Calculate moving averages.

        Args:
            df: DataFrame with price data
            price_column: Name of the price column
            windows: List of window sizes (defaults to [7, 14, 30])

        Returns:
            DataFrame with added moving average columns
        """
        if windows is None:
            windows = [7, 14, 30]

        df = df.copy()

        for window in windows:
            df[f"ma_{window}"] = df[price_column].rolling(window=window).mean()
            df[f"ema_{window}"] = df[price_column].ewm(span=window, adjust=False).mean()

        return df

    @staticmethod
    def calculate_volatility(
        df: pd.DataFrame, returns_column: str = "returns", window: int = 30
    ) -> pd.DataFrame:
        """
        Calculate rolling volatility.

        Args:
            df: DataFrame with returns data
            returns_column: Name of the returns column
            window: Rolling window size

        Returns:
            DataFrame with added volatility column
        """
        df = df.copy()

        df[f"volatility_{window}"] = df[returns_column].rolling(window=window).std()

        # Annualized volatility (assuming daily data)
        df[f"volatility_{window}_annualized"] = df[f"volatility_{window}"] * np.sqrt(365)

        return df

    @staticmethod
    def normalize_data(
        df: pd.DataFrame, columns: Optional[List[str]] = None, method: str = "minmax"
    ) -> pd.DataFrame:
        """
        Normalize data using specified method.

        Args:
            df: DataFrame to normalize
            columns: Columns to normalize (defaults to all numeric columns)
            method: Normalization method ('minmax' or 'zscore')

        Returns:
            DataFrame with normalized columns
        """
        df = df.copy()

        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in columns:
            if method == "minmax":
                min_val = df[col].min()
                max_val = df[col].max()
                df[f"{col}_normalized"] = (df[col] - min_val) / (max_val - min_val)
            elif method == "zscore":
                mean_val = df[col].mean()
                std_val = df[col].std()
                df[f"{col}_normalized"] = (df[col] - mean_val) / std_val

        return df

    @staticmethod
    def add_technical_indicators(df: pd.DataFrame, price_column: str = "price") -> pd.DataFrame:
        """
        Add common technical indicators.

        Args:
            df: DataFrame with price data
            price_column: Name of the price column

        Returns:
            DataFrame with added technical indicators
        """
        df = df.copy()

        # RSI (Relative Strength Index)
        delta = df[price_column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df["bb_middle"] = df[price_column].rolling(window=20).mean()
        bb_std = df[price_column].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
        df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

        return df
