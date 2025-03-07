# ml/data_processor.py
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
import pickle
import os
import time

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Data processing pipeline for machine learning models
    """
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.scalers = {}
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info("Data processor initialized")
        
    def preprocess_ohlcv_data(self, data: List[Dict[str, Any]], lookback_periods: int = 10, 
                            predict_periods: int = 1, test_size: float = 0.2,
                            scaler_name: str = "price_scaler") -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Preprocess OHLCV data for time series prediction
        
        Args:
            data: List of OHLCV candles
            lookback_periods: Number of periods to use for features
            predict_periods: Number of periods to predict ahead
            test_size: Test set size
            scaler_name: Name for the price scaler
            
        Returns:
            Tuple[Dict[str, np.ndarray], Dict[str, Any]]: Preprocessed data and metadata
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Extract features
            features = df[['open', 'high', 'low', 'close', 'volume']].values
            
            # Scale features
            if scaler_name in self.scalers:
                scaler = self.scalers[scaler_name]
                features_scaled = scaler.transform(features)
            else:
                scaler = StandardScaler()
                features_scaled = scaler.fit_transform(features)
                self.scalers[scaler_name] = scaler
                
            # Create sequences
            X, y = self._create_sequences(features_scaled, lookback_periods, predict_periods)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=False)
            
            # Prepare return data
            preprocessed_data = {
                'X_train': X_train,
                'X_test': X_test,
                'y_train': y_train,
                'y_test': y_test
            }
            
            metadata = {
                'lookback_periods': lookback_periods,
                'predict_periods': predict_periods,
                'feature_shape': features.shape,
                'scaler_name': scaler_name,
                'columns': ['open', 'high', 'low', 'close', 'volume']
            }
            
            return preprocessed_data, metadata
            
        except Exception as e:
            logger.error(f"Error preprocessing OHLCV data: {str(e)}")
            return {}, {}
            
    def _create_sequences(self, data: np.ndarray, lookback_periods: int, predict_periods: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for time series prediction
        
        Args:
            data: Input data array
            lookback_periods: Number of periods to use for features
            predict_periods: Number of periods to predict ahead
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: X and y arrays
        """
        X, y = [], []
        
        for i in range(len(data) - lookback_periods - predict_periods + 1):
            X.append(data[i:(i + lookback_periods)])
            y.append(data[i + lookback_periods:i + lookback_periods + predict_periods, 3])  # Predict close price
            
        return np.array(X), np.array(y)
        
    def prepare_technical_indicators(self, data: List[Dict[str, Any]], 
                                  indicators: Dict[str, List[Any]],
                                  lookback_periods: int = 10, 
                                  predict_periods: int = 1,
                                  test_size: float = 0.2) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Prepare data with technical indicators for prediction
        
        Args:
            data: List of OHLCV candles
            indicators: Dictionary of technical indicators
            lookback_periods: Number of periods to use for features
            predict_periods: Number of periods to predict ahead
            test_size: Test set size
            
        Returns:
            Tuple[Dict[str, np.ndarray], Dict[str, Any]]: Preprocessed data and metadata
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Create feature DataFrame
            feature_df = pd.DataFrame()
            
            # Add OHLCV columns
            feature_df['open'] = df['open']
            feature_df['high'] = df['high']
            feature_df['low'] = df['low']
            feature_df['close'] = df['close']
            feature_df['volume'] = df['volume']
            
            # Add technical indicators
            for indicator_name, indicator_values in indicators.items():
                if isinstance(indicator_values, list):
                    if len(indicator_values) == len(df):
                        feature_df[indicator_name] = indicator_values
                elif isinstance(indicator_values, dict):
                    for sub_name, sub_values in indicator_values.items():
                        if isinstance(sub_values, list) and len(sub_values) == len(df):
                            feature_df[f"{indicator_name}_{sub_name}"] = sub_values
                            
            # Drop NaN values
            feature_df.dropna(inplace=True)
            
            # Extract features
            feature_columns = feature_df.columns
            features = feature_df.values
            
            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            self.scalers['technical_scaler'] = scaler
            
            # Create sequences
            X, y = self._create_sequences(features_scaled, lookback_periods, predict_periods)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=False)
            
            # Prepare return data
            preprocessed_data = {
                'X_train': X_train,
                'X_test': X_test,
                'y_train': y_train,
                'y_test': y_test
            }
            
            metadata = {
                'lookback_periods': lookback_periods,
                'predict_periods': predict_periods,
                'feature_shape': features.shape,
                'feature_columns': list(feature_columns),
                'scaler_name': 'technical_scaler'
            }
            
            return preprocessed_data, metadata
            
        except Exception as e:
            logger.error(f"Error preparing technical indicators: {str(e)}")
            return {}, {}
            
    def prepare_sentiment_data(self, price_data: List[Dict[str, Any]], 
                            sentiment_data: List[Dict[str, Any]],
                            lookback_periods: int = 10, 
                            predict_periods: int = 1,
                            test_size: float = 0.2) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Prepare price and sentiment data for prediction
        
        Args:
            price_data: List of OHLCV candles
            sentiment_data: List of sentiment data points
            lookback_periods: Number of periods to use for features
            predict_periods: Number of periods to predict ahead
            test_size: Test set size
            
        Returns:
            Tuple[Dict[str, np.ndarray], Dict[str, Any]]: Preprocessed data and metadata
        """
        try:
            # Convert to DataFrames
            price_df = pd.DataFrame(price_data)
            sentiment_df = pd.DataFrame(sentiment_data)
            
            # Ensure sentiment data has timestamp
            if 'timestamp' not in sentiment_df.columns:
                logger.error("Sentiment data must have timestamp column")
                return {}, {}
                
            # Convert timestamps to datetime for merging
            price_df['datetime'] = pd.to_datetime(price_df['timestamp'], unit='s')
            sentiment_df['datetime'] = pd.to_datetime(sentiment_df['timestamp'], unit='s')
            
            # Merge data on datetime
            merged_df = pd.merge_asof(
                price_df.sort_values('datetime'),
                sentiment_df.sort_values('datetime'),
                on='datetime',
                direction='backward'
            )
            
            # Create feature DataFrame
            feature_df = pd.DataFrame()
            
            # Add OHLCV columns
            feature_df['open'] = merged_df['open']
            feature_df['high'] = merged_df['high']
            feature_df['low'] = merged_df['low']
            feature_df['close'] = merged_df['close']
            feature_df['volume'] = merged_df['volume']
            
            # Add sentiment columns
            for col in sentiment_df.columns:
                if col not in ['timestamp', 'datetime']:
                    feature_df[col] = merged_df[col]
                    
            # Drop NaN values
            feature_df.dropna(inplace=True)
            
            # Extract features
            feature_columns = feature_df.columns
            features = feature_df.values
            
            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            self.scalers['sentiment_scaler'] = scaler
            
            # Create sequences
            X, y = self._create_sequences(features_scaled, lookback_periods, predict_periods)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=False)
            
            # Prepare return data
            preprocessed_data = {
                'X_train': X_train,
                'X_test': X_test,
                'y_train': y_train,
                'y_test': y_test
            }
            
            metadata = {
                'lookback_periods': lookback_periods,
                'predict_periods': predict_periods,
                'feature_shape': features.shape,
                'feature_columns': list(feature_columns),
                'scaler_name': 'sentiment_scaler'
            }
            
            return preprocessed_data, metadata
            
        except Exception as e:
            logger.error(f"Error preparing sentiment data: {str(e)}")
            return {}, {}
            
    def prepare_market_regime_data(self, data: List[Dict[str, Any]], labels: List[str],
                               lookback_periods: int = 20, test_size: float = 0.2) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Prepare data for market regime classification
        
        Args:
            data: List of OHLCV candles
            labels: List of regime labels
            lookback_periods: Number of periods to use for features
            test_size: Test set size
            
        Returns:
            Tuple[Dict[str, np.ndarray], Dict[str, Any]]: Preprocessed data and metadata
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Extract features
            features = df[['open', 'high', 'low', 'close', 'volume']].values
            
            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            self.scalers['regime_scaler'] = scaler
            
            # Create sequences
            X, y = self._create_sequences_for_classification(features_scaled, labels, lookback_periods)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=True, stratify=y)
            
            # Prepare return data
            preprocessed_data = {
                'X_train': X_train,
                'X_test': X_test,
                'y_train': y_train,
                'y_test': y_test
            }
            
            # Get unique labels
            unique_labels = np.unique(y)
            
            metadata = {
                'lookback_periods': lookback_periods,
                'feature_shape': features.shape,
                'scaler_name': 'regime_scaler',
                'columns': ['open', 'high', 'low', 'close', 'volume'],
                'labels': unique_labels.tolist()
            }
            
            return preprocessed_data, metadata
            
        except Exception as e:
            logger.error(f"Error preparing market regime data: {str(e)}")
            return {}, {}
            
    def _create_sequences_for_classification(self, data: np.ndarray, labels: List[str], 
                                         lookback_periods: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for classification
        
        Args:
            data: Input data array
            labels: List of labels
            lookback_periods: Number of periods to use for features
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: X and y arrays
        """
        X, y = [], []
        
        # Ensure labels are aligned with data
        if len(labels) != len(data) - lookback_periods + 1:
            # Adjust labels to match sequence length
            labels = labels[lookback_periods - 1:]
            
        for i in range(len(data) - lookback_periods + 1):
            X.append(data[i:(i + lookback_periods)])
            y.append(labels[i])
            
        return np.array(X), np.array(y)
        
    def save_scaler(self, scaler_name: str) -> bool:
        """
        Save scaler to cache directory
        
        Args:
            scaler_name: Name of scaler to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if scaler_name in self.scalers:
                scaler = self.scalers[scaler_name]
                scaler_path = os.path.join(self.cache_dir, f"{scaler_name}.pkl")
                
                with open(scaler_path, 'wb') as f:
                    pickle.dump(scaler, f)
                    
                logger.info(f"Saved scaler: {scaler_name}")
                return True
            else:
                logger.warning(f"Scaler not found: {scaler_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving scaler {scaler_name}: {str(e)}")
            return False
            
    def load_scaler(self, scaler_name: str) -> bool:
        """
        Load scaler from cache directory
        
        Args:
            scaler_name: Name of scaler to load
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            scaler_path = os.path.join(self.cache_dir, f"{scaler_name}.pkl")
            
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    scaler = pickle.load(f)
                    
                self.scalers[scaler_name] = scaler
                logger.info(f"Loaded scaler: {scaler_name}")
                return True
            else:
                logger.warning(f"Scaler file not found: {scaler_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading scaler {scaler_name}: {str(e)}")
            return False
            
    def generate_features(self, data: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """
        Generate features from OHLCV data
        
        Args:
            data: List of OHLCV candles
            
        Returns:
            Dict[str, List[float]]: Dictionary of features
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Calculate returns
            df['returns'] = df['close'].pct_change()
            
            # Calculate volatility features
            df['volatility_1d'] = df['returns'].rolling(window=1).std() * np.sqrt(252)
            df['volatility_5d'] = df['returns'].rolling(window=5).std() * np.sqrt(252)
            df['volatility_20d'] = df['returns'].rolling(window=20).std() * np.sqrt(252)
            
            # Calculate volume features
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma20'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma20']
            
            # Calculate price features
            df['price_ma5'] = df['close'].rolling(window=5).mean()
            df['price_ma20'] = df['close'].rolling(window=20).mean()
            df['price_ma50'] = df['close'].rolling(window=50).mean()
            df['price_ma200'] = df['close'].rolling(window=200).mean()
            
            # Calculate price ratios
            df['price_ratio_5_20'] = df['price_ma5'] / df['price_ma20']
            df['price_ratio_20_50'] = df['price_ma20'] / df['price_ma50']
            df['price_ratio_50_200'] = df['price_ma50'] / df['price_ma200']
            
            # Calculate range features
            df['daily_range'] = (df['high'] - df['low']) / df['close']
            df['daily_range_ma5'] = df['daily_range'].rolling(window=5).mean()
            df['daily_range_ma20'] = df['daily_range'].rolling(window=20).mean()
            
            # Extract features
            features = {}
            for column in df.columns:
                if column not in ['timestamp', 'datetime']:
                    features[column] = df[column].tolist()
                    
            return features
            
        except Exception as e:
            logger.error(f"Error generating features: {str(e)}")
            return {}
