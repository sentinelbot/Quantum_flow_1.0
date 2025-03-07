# ml/feature_engineering.py
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import talib
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Feature engineering for trading models
    """
    def __init__(self):
        logger.info("Feature engineer initialized")
        
    def create_technical_features(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """
        Create technical indicator features
        
        Args:
            ohlcv_data: DataFrame with OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with added technical features
        """
        try:
            # Create copy of DataFrame
            df = ohlcv_data.copy()
            
            # Extract OHLCV columns
            open_prices = df['open'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            close_prices = df['close'].values
            volumes = df['volume'].values
            
            # Calculate momentum indicators
            df['rsi_14'] = talib.RSI(close_prices, timeperiod=14)
            df['cci_14'] = talib.CCI(high_prices, low_prices, close_prices, timeperiod=14)
            df['adx_14'] = talib.ADX(high_prices, low_prices, close_prices, timeperiod=14)
            
            # Calculate MACD
            macd, macd_signal, macd_hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist
            
            # Calculate Bollinger Bands
            upper, middle, lower = talib.BBANDS(close_prices, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
            df['bb_upper'] = upper
            df['bb_middle'] = middle
            df['bb_lower'] = lower
            df['bb_width'] = (upper - lower) / middle
            
            # Calculate moving averages
            df['sma_10'] = talib.SMA(close_prices, timeperiod=10)
            df['sma_30'] = talib.SMA(close_prices, timeperiod=30)
            df['sma_50'] = talib.SMA(close_prices, timeperiod=50)
            df['sma_200'] = talib.SMA(close_prices, timeperiod=200)
            
            df['ema_10'] = talib.EMA(close_prices, timeperiod=10)
            df['ema_30'] = talib.EMA(close_prices, timeperiod=30)
            df['ema_50'] = talib.EMA(close_prices, timeperiod=50)
            df['ema_200'] = talib.EMA(close_prices, timeperiod=200)
            
            # Calculate moving average ratios
            df['sma_ratio_10_30'] = df['sma_10'] / df['sma_30']
            df['sma_ratio_50_200'] = df['sma_50'] / df['sma_200']
            
            # Calculate Stochastic Oscillator
            slowk, slowd = talib.STOCH(high_prices, low_prices, close_prices, fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
            df['stoch_k'] = slowk
            df['stoch_d'] = slowd
            
            # Calculate ATR
            df['atr_14'] = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
            df['atr_ratio'] = df['atr_14'] / close_prices
            
            # Calculate volume indicators
            df['obv'] = talib.OBV(close_prices, volumes)
            df['mfi_14'] = talib.MFI(high_prices, low_prices, close_prices, volumes, timeperiod=14)
            
            # Calculate returns
            df['returns_1d'] = df['close'].pct_change(1)
            df['returns_5d'] = df['close'].pct_change(5)
            df['returns_10d'] = df['close'].pct_change(10)
            
            # Calculate volatility
            df['volatility_14'] = df['returns_1d'].rolling(window=14).std()
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating technical features: {str(e)}")
            return ohlcv_data
            
    def create_pattern_features(self, ohlcv_data: pd.DataFrame) -> pd.DataFrame:
        """
        Create candlestick pattern features
        
        Args:
            ohlcv_data: DataFrame with OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with added pattern features
        """
        try:
            # Create copy of DataFrame
            df = ohlcv_data.copy()
            
            # Extract OHLCV columns
            open_prices = df['open'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            close_prices = df['close'].values
            
            # Single candlestick patterns
            df['doji'] = talib.CDLDOJI(open_prices, high_prices, low_prices, close_prices)
            df['hammer'] = talib.CDLHAMMER(open_prices, high_prices, low_prices, close_prices)
            df['hanging_man'] = talib.CDLHANGINGMAN(open_prices, high_prices, low_prices, close_prices)
            df['shooting_star'] = talib.CDLSHOOTINGSTAR(open_prices, high_prices, low_prices, close_prices)
            df['spinning_top'] = talib.CDLSPINNINGTOP(open_prices, high_prices, low_prices, close_prices)
            df['marubozu'] = talib.CDLMARUBOZU(open_prices, high_prices, low_prices, close_prices)
            
            # Double candlestick patterns
            df['engulfing'] = talib.CDLENGULFING(open_prices, high_prices, low_prices, close_prices)
            df['harami'] = talib.CDLHARAMI(open_prices, high_prices, low_prices, close_prices)
            df['harami_cross'] = talib.CDLHARAMICROSS(open_prices, high_prices, low_prices, close_prices)
            df['piercing'] = talib.CDLPIERCING(open_prices, high_prices, low_prices, close_prices)
            df['dark_cloud_cover'] = talib.CDLDARKCLOUDCOVER(open_prices, high_prices, low_prices, close_prices)
            
            # Triple candlestick patterns
            df['morning_star'] = talib.CDLMORNINGSTAR(open_prices, high_prices, low_prices, close_prices)
            df['evening_star'] = talib.CDLEVENINGSTAR(open_prices, high_prices, low_prices, close_prices)
            df['three_white_soldiers'] = talib.CDL3WHITESOLDIERS(open_prices, high_prices, low_prices, close_prices)
            df['three_black_crows'] = talib.CDL3BLACKCROWS(open_prices, high_prices, low_prices, close_prices)
            df['three_inside_up'] = talib.CDL3INSIDE(open_prices, high_prices, low_prices, close_prices)
            
            # Gap patterns
            df['gap_up'] = ((df['open'] - df['close'].shift(1)) / df['close'].shift(1) > 0.01).astype(int)
            df['gap_down'] = ((df['open'] - df['close'].shift(1)) / df['close'].shift(1) < -0.01).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating pattern features: {str(e)}")
            return ohlcv_data
            
    def create_sentiment_features(self, ohlcv_data: pd.DataFrame, 
                               sentiment_data: pd.DataFrame) -> pd.DataFrame:
        """
        Merge sentiment features with OHLCV data
        
        Args:
            ohlcv_data: DataFrame with OHLCV data
            sentiment_data: DataFrame with sentiment data
            
        Returns:
            pd.DataFrame: DataFrame with added sentiment features
        """
        try:
            # Create copy of DataFrame
            df = ohlcv_data.copy()
            
            # Ensure both DataFrames have datetime columns
            if 'datetime' not in df.columns:
                if 'timestamp' in df.columns:
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
                else:
                    logger.error("OHLCV data must have timestamp or datetime column")
                    return df
                    
            if 'datetime' not in sentiment_data.columns:
                if 'timestamp' in sentiment_data.columns:
                    sentiment_data['datetime'] = pd.to_datetime(sentiment_data['timestamp'], unit='s')
                else:
                    logger.error("Sentiment data must have timestamp or datetime column")
                    return df
                    
            # Merge data on datetime
            merged_df = pd.merge_asof(
                df.sort_values('datetime'),
                sentiment_data.sort_values('datetime'),
                on='datetime',
                direction='backward'
            )
            
            # Fill NaN values with forward fill
            for col in sentiment_data.columns:
                if col not in ['timestamp', 'datetime'] and col in merged_df.columns:
                    merged_df[col] = merged_df[col].ffill()
                    
            return merged_df
            
        except Exception as e:
            logger.error(f"Error creating sentiment features: {str(e)}")
            return ohlcv_data
            
    def reduce_dimensionality(self, features: pd.DataFrame, n_components: int = 10) -> pd.DataFrame:
        """
        Reduce dimensionality of features using PCA
        
        Args:
            features: DataFrame with features
            n_components: Number of components for PCA
            
        Returns:
            pd.DataFrame: DataFrame with reduced features
        """
        try:
            # Select only numeric columns
            numeric_df = features.select_dtypes(include=[np.number])
            
            # Drop columns with NaN values
            clean_df = numeric_df.dropna(axis=1)
            
            # Standardize features
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(clean_df)
            
            # Apply PCA
            pca = PCA(n_components=min(n_components, len(clean_df.columns)))
            pca_features = pca.fit_transform(scaled_features)
            
            # Create new DataFrame with PCA components
            pca_df = pd.DataFrame(
                pca_features,
                columns=[f'pca_{i+1}' for i in range(pca_features.shape[1])],
                index=clean_df.index
            )
            
            # Add non-numeric columns back
            result_df = pd.concat([features.drop(clean_df.columns, axis=1), pca_df], axis=1)
            
            logger.info(f"Reduced dimensionality from {len(clean_df.columns)} to {pca_features.shape[1]} features")
            logger.info(f"Explained variance ratio: {pca.explained_variance_ratio_}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error reducing dimensionality: {str(e)}")
            return features
            
    def create_lag_features(self, data: pd.DataFrame, columns: List[str], lag_periods: List[int]) -> pd.DataFrame:
        """
        Create lag features for specified columns
        
        Args:
            data: DataFrame with data
            columns: List of columns to create lag features for
            lag_periods: List of lag periods
            
        Returns:
            pd.DataFrame: DataFrame with added lag features
        """
        try:
            # Create copy of DataFrame
            df = data.copy()
            
            # Create lag features
            for col in columns:
                if col in df.columns:
                    for lag in lag_periods:
                        df[f'{col}_lag_{lag}'] = df[col].shift(lag)
                else:
                    logger.warning(f"Column not found: {col}")
                    
            return df
            
        except Exception as e:
            logger.error(f"Error creating lag features: {str(e)}")
            return data
            
    def create_return_features(self, data: pd.DataFrame, price_column: str = 'close', 
                            periods: List[int] = [1, 5, 10, 20]) -> pd.DataFrame:
        """
        Create return features
        
        Args:
            data: DataFrame with data
            price_column: Column name for price
            periods: List of periods for returns
            
        Returns:
            pd.DataFrame: DataFrame with added return features
        """
        try:
            # Create copy of DataFrame
            df = data.copy()
            
            # Check if price column exists
            if price_column not in df.columns:
                logger.error(f"Price column not found: {price_column}")
                return df
                
            # Create return features
            for period in periods:
                df[f'return_{period}d'] = df[price_column].pct_change(period)
                
            return df
            
        except Exception as e:
            logger.error(f"Error creating return features: {str(e)}")
            return data
            
    def create_volatility_features(self, data: pd.DataFrame, return_column: str = 'return_1d', 
                               windows: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
        """
        Create volatility features
        
        Args:
            data: DataFrame with data
            return_column: Column name for returns
            windows: List of windows for volatility calculation
            
        Returns:
            pd.DataFrame: DataFrame with added volatility features
        """
        try:
            # Create copy of DataFrame
            df = data.copy()
            
            # Create return column if it doesn't exist
            if return_column not in df.columns and 'close' in df.columns:
                df['return_1d'] = df['close'].pct_change(1)
                return_column = 'return_1d'
                
            # Check if return column exists
            if return_column not in df.columns:
                logger.error(f"Return column not found: {return_column}")
                return df
                
            # Create volatility features
            for window in windows:
                df[f'volatility_{window}d'] = df[return_column].rolling(window=window).std()
                
            # Annualize volatility
            for window in windows:
                df[f'volatility_{window}d_annual'] = df[f'volatility_{window}d'] * np.sqrt(252)
                
            return df
            
        except Exception as e:
            logger.error(f"Error creating volatility features: {str(e)}")
            return data
            
    def create_target_variable(self, data: pd.DataFrame, price_column: str = 'close', 
                            horizon: int = 1, threshold: float = 0.0) -> pd.DataFrame:
        """
        Create target variable for classification
        
        Args:
            data: DataFrame with data
            price_column: Column name for price
            horizon: Forecast horizon
            threshold: Threshold for classification
            
        Returns:
            pd.DataFrame: DataFrame with added target variable
        """
        try:
            # Create copy of DataFrame
            df = data.copy()
            
            # Check if price column exists
            if price_column not in df.columns:
                logger.error(f"Price column not found: {price_column}")
                return df
                
            # Calculate future returns
            df[f'future_return_{horizon}d'] = df[price_column].pct_change(horizon).shift(-horizon)
            
            # Create target variable (1 for positive return, 0 for negative return)
            df[f'target_{horizon}d'] = (df[f'future_return_{horizon}d'] > threshold).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating target variable: {str(e)}")
            return data
            
    def create_regime_labels(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Create market regime labels
        
        Args:
            data: DataFrame with OHLCV data
            window: Window for regime calculation
            
        Returns:
            pd.DataFrame: DataFrame with added regime labels
        """
        try:
            # Create copy of DataFrame
            df = data.copy()
            
            # Check if required columns exist
            if 'close' not in df.columns:
                logger.error("Close column not found")
                return df
                
            # Calculate returns
            df['return_1d'] = df['close'].pct_change(1)
            
            # Calculate volatility
            df['volatility'] = df['return_1d'].rolling(window=window).std() * np.sqrt(252)
            
            # Calculate trend
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['trend'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
            
            # Define regimes
            conditions = [
                (df['trend'] == 1) & (df['volatility'] <= df['volatility'].quantile(0.7)),  # Bullish trend, normal volatility
                (df['trend'] == 1) & (df['volatility'] > df['volatility'].quantile(0.7)),   # Bullish trend, high volatility
                (df['trend'] == -1) & (df['volatility'] <= df['volatility'].quantile(0.7)), # Bearish trend, normal volatility
                (df['trend'] == -1) & (df['volatility'] > df['volatility'].quantile(0.7)),  # Bearish trend, high volatility
            ]
            
            choices = ['trending_up', 'volatile_up', 'trending_down', 'volatile_down']
            
            df['regime'] = np.select(conditions, choices, default='unknown')
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating regime labels: {str(e)}")
            return data
