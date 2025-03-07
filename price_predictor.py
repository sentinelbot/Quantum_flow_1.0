# ml/models/price_predictor.py
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model, Model
from tensorflow.keras.layers import Dense, LSTM, Dropout, BatchNormalization, Input, Conv1D, MaxPooling1D, Flatten, Bidirectional, GRU
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import os
import pickle
import time

logger = logging.getLogger(__name__)

class PricePredictor:
    """
    Price prediction model using deep learning
    """
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.model = None
        self.model_name = ""
        self.metadata = {}
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        logger.info("Price predictor initialized")
        
    def build_lstm_model(self, lookback_periods: int, feature_dim: int, output_dim: int = 1) -> Sequential:
        """
        Build LSTM model for price prediction
        
        Args:
            lookback_periods: Number of lookback periods
            feature_dim: Number of features
            output_dim: Number of output dimensions
            
        Returns:
            Sequential: LSTM model
        """
        try:
            model = Sequential([
                LSTM(64, return_sequences=True, input_shape=(lookback_periods, feature_dim)),
                Dropout(0.2),
                LSTM(64, return_sequences=False),
                Dropout(0.2),
                Dense(32, activation='relu'),
                Dense(output_dim)
            ])
            
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
            
            return model
            
        except Exception as e:
            logger.error(f"Error building LSTM model: {str(e)}")
            return None
            
    def build_gru_model(self, lookback_periods: int, feature_dim: int, output_dim: int = 1) -> Sequential:
        """
        Build GRU model for price prediction
        
        Args:
            lookback_periods: Number of lookback periods
            feature_dim: Number of features
            output_dim: Number of output dimensions
            
        Returns:
            Sequential: GRU model
        """
        try:
            model = Sequential([
                Bidirectional(GRU(64, return_sequences=True), input_shape=(lookback_periods, feature_dim)),
                Dropout(0.2),
                Bidirectional(GRU(64, return_sequences=False)),
                Dropout(0.2),
                Dense(32, activation='relu'),
                Dense(output_dim)
            ])
            
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
            
            return model
            
        except Exception as e:
            logger.error(f"Error building GRU model: {str(e)}")
            return None
            
    def build_cnn_lstm_model(self, lookback_periods: int, feature_dim: int, output_dim: int = 1) -> Model:
        """
        Build CNN-LSTM hybrid model for price prediction
        
        Args:
            lookback_periods: Number of lookback periods
            feature_dim: Number of features
            output_dim: Number of output dimensions
            
        Returns:
            Model: CNN-LSTM model
        """
        try:
            # Input layer
            inputs = Input(shape=(lookback_periods, feature_dim))
            
            # CNN layers
            x = Conv1D(filters=64, kernel_size=3, padding='same', activation='relu')(inputs)
            x = MaxPooling1D(pool_size=2)(x)
            x = Conv1D(filters=128, kernel_size=3, padding='same', activation='relu')(x)
            x = MaxPooling1D(pool_size=2)(x)
            
            # LSTM layers
            x = LSTM(64, return_sequences=True)(x)
            x = Dropout(0.2)(x)
            x = LSTM(64, return_sequences=False)(x)
            x = Dropout(0.2)(x)
            
            # Dense layers
            x = Dense(32, activation='relu')(x)
            outputs = Dense(output_dim)(x)
            
            # Create model
            model = Model(inputs=inputs, outputs=outputs)
            
            # Compile model
            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
            
            return model
            
        except Exception as e:
            logger.error(f"Error building CNN-LSTM model: {str(e)}")
            return None
            
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray,
                 model_type: str = 'lstm', epochs: int = 100, batch_size: int = 32,
                 model_name: str = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Train price prediction model
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features
            y_val: Validation targets
            model_type: Type of model ('lstm', 'gru', or 'cnn_lstm')
            epochs: Number of epochs for training
            batch_size: Batch size for training
            model_name: Name for the model (default: auto-generated)
            
        Returns:
            Tuple[Any, Dict[str, Any]]: Trained model and training history
        """
        try:
            lookback_periods, feature_dim = X_train.shape[1], X_train.shape[2]
            output_dim = y_train.shape[1] if len(y_train.shape) > 1 else 1
            
            # Generate model name if not provided
            if model_name is None:
                timestamp = int(time.time())
                model_name = f"price_predictor_{model_type}_{timestamp}"
                
            self.model_name = model_name
            
            # Build model based on type
            if model_type == 'lstm':
                model = self.build_lstm_model(lookback_periods, feature_dim, output_dim)
            elif model_type == 'gru':
                model = self.build_gru_model(lookback_periods, feature_dim, output_dim)
            elif model_type == 'cnn_lstm':
                model = self.build_cnn_lstm_model(lookback_periods, feature_dim, output_dim)
            else:
                logger.error(f"Unknown model type: {model_type}")
                return None, {}
                
            if model is None:
                return None, {}
                
            # Set up callbacks
            model_path = os.path.join(self.model_dir, f"{model_name}.h5")
            callbacks = [
                EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
                ModelCheckpoint(model_path, save_best_only=True, monitor='val_loss')
            ]
            
            # Train model
            history = model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=1
            )
            
            # Store model and metadata
            self.model = model
            
            self.metadata = {
                'model_name': model_name,
                'model_type': model_type,
                'lookback_periods': lookback_periods,
                'feature_dim': feature_dim,
                'output_dim': output_dim,
                'training_params': {
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'final_loss': float(history.history['loss'][-1]),
                    'final_val_loss': float(history.history['val_loss'][-1]),
                    'best_epoch': int(np.argmin(history.history['val_loss'])) + 1
                },
                'timestamp': int(time.time())
            }
            
            # Save metadata
            self._save_metadata()
            
            logger.info(f"Model trained successfully: {model_name}")
            
            return model, history.history
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return None, {}
            
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make price predictions
        
        Args:
            X: Input features
            
        Returns:
            np.ndarray: Predicted prices
        """
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return np.array([])
                
            # Make predictions
            predictions = self.model.predict(X)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}")
            return np.array([])
            
    def predict_next_n_prices(self, last_sequence: np.ndarray, n_steps: int = 5) -> np.ndarray:
        """
        Predict next N prices recursively
        
        Args:
            last_sequence: Last known sequence of data
            n_steps: Number of steps to predict ahead
            
        Returns:
            np.ndarray: Predicted prices
        """
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return np.array([])
                
            if n_steps <= 0:
                return np.array([])
                
            # Initialize with the last known sequence
            current_sequence = last_sequence.copy()
            predictions = []
            
            # Predict n steps ahead
            for _ in range(n_steps):
                # Reshape for prediction
                input_seq = current_sequence.reshape(1, current_sequence.shape[0], current_sequence.shape[1])
                
                # Make prediction
                pred = self.model.predict(input_seq)[0]
                predictions.append(pred)
                
                # Update sequence for next prediction (shift sequence and add new prediction)
                # This assumes that the prediction is for the closing price (feature index 3)
                # Adjust this logic based on your exact feature set
                new_row = current_sequence[-1].copy()
                new_row[3] = pred[0]  # Assuming pred is for closing price
                
                current_sequence = np.vstack([current_sequence[1:], new_row.reshape(1, -1)])
                
            return np.array(predictions)
            
        except Exception as e:
            logger.error(f"Error predicting next N prices: {str(e)}")
            return np.array([])
            
    def save_model(self, model_name: str = None) -> bool:
        """
        Save model to disk
        
        Args:
            model_name: Name for the model (default: self.model_name)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.model is None:
                logger.error("No model to save")
                return False
                
            if model_name is not None:
                self.model_name = model_name
                
            if not self.model_name:
                timestamp = int(time.time())
                self.model_name = f"price_predictor_{timestamp}"
                
            # Save model
            model_path = os.path.join(self.model_dir, f"{self.model_name}.h5")
            self.model.save(model_path)
            
            # Update metadata
            self.metadata['model_name'] = self.model_name
            self.metadata['saved_path'] = model_path
            
            # Save metadata
            self._save_metadata()
            
            logger.info(f"Model saved: {model_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return False
            
    def load_model(self, model_name: str) -> bool:
        """
        Load model from disk
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            model_path = os.path.join(self.model_dir, f"{model_name}.h5")
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
                
            # Load model
            self.model = load_model(model_path)
            self.model_name = model_name
            
            # Load metadata if available
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
            else:
                logger.warning(f"Metadata file not found: {metadata_path}")
                self.metadata = {'model_name': model_name}
                
            logger.info(f"Model loaded: {model_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
            
    def _save_metadata(self) -> bool:
        """
        Save model metadata to disk
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.model_name:
                logger.error("No model name specified")
                return False
                
            metadata_path = os.path.join(self.model_dir, f"{self.model_name}_metadata.pkl")
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
                
            logger.info(f"Metadata saved: {metadata_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving metadata: {str(e)}")
            return False
            
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model performance
        
        Args:
            X_test: Test features
            y_test: Test targets
            
        Returns:
            Dict[str, float]: Evaluation metrics
        """
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return {}
                
            # Evaluate model
            loss, mae = self.model.evaluate(X_test, y_test, verbose=0)
            
            # Make predictions
            y_pred = self.model.predict(X_test)
            
            # Calculate RMSE
            rmse = np.sqrt(np.mean(np.square(y_pred - y_test)))
            
            # Calculate MAPE
            mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
            
            # Calculate directional accuracy
            if len(y_test.shape) > 1:
                direction_actual = np.diff(y_test, axis=0) > 0
                direction_pred = np.diff(y_pred, axis=0) > 0
                directional_accuracy = np.mean(direction_actual == direction_pred) * 100
            else:
                direction_actual = np.diff(y_test) > 0
                direction_pred = np.diff(y_pred) > 0
                directional_accuracy = np.mean(direction_actual == direction_pred) * 100
                
            metrics = {
                'loss': float(loss),
                'mae': float(mae),
                'rmse': float(rmse),
                'mape': float(mape),
                'directional_accuracy': float(directional_accuracy)
            }
            
            logger.info(f"Model evaluation metrics: {metrics}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {str(e)}")
            return {}
            
    def get_model_summary(self) -> str:
        """
        Get model summary
        
        Returns:
            str: Model summary
        """
        try:
            if self.model is None:
                return "Model not loaded"
                
            # Create string buffer to capture summary
            from io import StringIO
            import sys
            
            buffer = StringIO()
            sys.stdout = buffer
            self.model.summary()
            sys.stdout = sys.__stdout__
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error getting model summary: {str(e)}")
            return f"Error: {str(e)}"
