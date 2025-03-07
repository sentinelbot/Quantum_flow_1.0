
# ml/models/regime_classifier.py
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import os
import pickle
import time
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical

logger = logging.getLogger(__name__)

class RegimeClassifier:
    """
    Market regime classification model
    """
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.model = None
        self.model_name = ""
        self.model_type = ""
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.metadata = {}
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        logger.info("Regime classifier initialized")
        
    def train_model(self, X: np.ndarray, y: np.ndarray, model_type: str = 'random_forest',
                 model_name: str = None) -> Any:
        """
        Train market regime classification model
        
        Args:
            X: Input data
            y: Target labels
            model_type: Type of model ('random_forest' or 'lstm')
            model_name: Name for the model (default: auto-generated)
            
        Returns:
            Any: Trained model
        """
        try:
            # Generate model name if not provided
            if model_name is None:
                timestamp = int(time.time())
                model_name = f"regime_classifier_{model_type}_{timestamp}"
                
            self.model_name = model_name
            self.model_type = model_type
            
            # Encode labels
            encoded_y = self.label_encoder.fit_transform(y)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, encoded_y, test_size=0.2, random_state=42)
            
            if model_type == 'random_forest':
                # Reshape data if necessary
                if len(X_train.shape) == 3:
                    n_samples, n_timesteps, n_features = X_train.shape
                    X_train = X_train.reshape(n_samples, n_timesteps * n_features)
                    X_test = X_test.reshape(X_test.shape[0], n_timesteps * n_features)
                    
                # Standardize features
                X_train = self.scaler.fit_transform(X_train)
                X_test = self.scaler.transform(X_test)
                
                # Create model
                model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
                
                # Define parameter grid
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20, 30],
                    'min_samples_split': [2, 5, 10]
                }
                
                # Use grid search to find best parameters
                grid_search = GridSearchCV(model, param_grid, cv=3, scoring='accuracy', n_jobs=-1)
                grid_search.fit(X_train, y_train)
                
                # Get best model
                model = grid_search.best_estimator_
                
                # Store model parameters
                model_params = grid_search.best_params_
                
            elif model_type == 'lstm':
                # Check if data is in correct shape for LSTM
                if len(X_train.shape) != 3:
                    logger.error("Data must be in 3D shape for LSTM model: [samples, timesteps, features]")
                    return None
                    
                # Get dimensions
                n_samples, n_timesteps, n_features = X_train.shape
                
                # One-hot encode target
                n_classes = len(np.unique(encoded_y))
                y_train_cat = to_categorical(y_train, num_classes=n_classes)
                y_test_cat = to_categorical(y_test, num_classes=n_classes)
                
                # Build LSTM model
                model = Sequential([
                    LSTM(64, input_shape=(n_timesteps, n_features), return_sequences=True),
                    Dropout(0.2),
                    LSTM(32, return_sequences=False),
                    Dropout(0.2),
                    Dense(16, activation='relu'),
                    Dense(n_classes, activation='softmax')
                ])
                
                # Compile model
                model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
                
                # Set up early stopping
                early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
                
                # Train model
                history = model.fit(
                    X_train, y_train_cat,
                    validation_data=(X_test, y_test_cat),
                    epochs=50,
                    batch_size=32,
                    callbacks=[early_stopping],
                    verbose=1
                )
                
                # Store model parameters
                model_params = {
                    'epochs': len(history.history['loss']),
                    'batch_size': 32,
                    'n_timesteps': n_timesteps,
                    'n_features': n_features,
                    'n_classes': n_classes
                }
                
            else:
                logger.error(f"Unknown model type: {model_type}")
                return None
                
            # Evaluate model
            if model_type == 'random_forest':
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                report = classification_report(y_test, y_pred, output_dict=True)
                cm = confusion_matrix(y_test, y_pred)
                
            else:  # LSTM
                y_pred_prob = model.predict(X_test)
                y_pred = np.argmax(y_pred_prob, axis=1)
                accuracy = accuracy_score(y_test, y_pred)
                report = classification_report(y_test, y_pred, output_dict=True)
                cm = confusion_matrix(y_test, y_pred)
                
            # Store model and metadata
            self.model = model
            
            self.metadata = {
                'model_name': model_name,
                'model_type': model_type,
                'classes': self.label_encoder.classes_.tolist(),
                'model_params': model_params,
                'feature_shape': X.shape,
                'performance': {
                    'accuracy': float(accuracy),
                    'f1_score': float(report['weighted avg']['f1-score'])
                },
                'confusion_matrix': cm.tolist(),
                'timestamp': int(time.time())
            }
            
            # Save model
            self.save_model()
            
            logger.info(f"Model trained successfully: {model_name}, accuracy: {accuracy:.4f}")
            
            return model
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return None
            
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict market regime
        
        Args:
            X: Input data
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: Predicted regimes and probabilities
        """
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return np.array([]), np.array([])
                
            # Reshape and standardize data for random forest
            if self.model_type == 'random_forest':
                if len(X.shape) == 3:
                    n_samples, n_timesteps, n_features = X.shape
                    X = X.reshape(n_samples, n_timesteps * n_features)
                    
                X = self.scaler.transform(X)
                
                # Make predictions
                y_pred = self.model.predict(X)
                y_pred_prob = self.model.predict_proba(X)
                
                # Decode predictions
                regime_labels = self.label_encoder.inverse_transform(y_pred)
                
                return regime_labels, y_pred_prob
                
            elif self.model_type == 'lstm':
                # Make predictions
                y_pred_prob = self.model.predict(X)
                y_pred = np.argmax(y_pred_prob, axis=1)
                
                # Decode predictions
                regime_labels = self.label_encoder.inverse_transform(y_pred)
                
                return regime_labels, y_pred_prob
                
        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}")
            return np.array([]), np.array([])
            
    def predict_regime(self, X: np.ndarray) -> List[Dict[str, Any]]:
        """
        Predict market regime with details
        
        Args:
            X: Input data
            
        Returns:
            List[Dict[str, Any]]: Predicted regimes with probabilities
        """
        try:
            regimes, probs = self.predict(X)
            
            results = []
            for i, regime in enumerate(regimes):
                probabilities = {}
                for j, class_name in enumerate(self.label_encoder.classes_):
                    probabilities[class_name] = float(probs[i][j])
                    
                results.append({
                    'regime': regime,
                    'probabilities': probabilities,
                    'confidence': float(np.max(probs[i]))
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Error predicting regime: {str(e)}")
            return []
            
    def save_model(self) -> bool:
        """
        Save model to disk
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.model is None:
                logger.error("No model to save")
                return False
                
            if not self.model_name:
                timestamp = int(time.time())
                self.model_name = f"regime_classifier_{timestamp}"
                
            # Create paths
            model_path = os.path.join(self.model_dir, f"{self.model_name}.pkl")
            scaler_path = os.path.join(self.model_dir, f"{self.model_name}_scaler.pkl")
            encoder_path = os.path.join(self.model_dir, f"{self.model_name}_encoder.pkl")
            metadata_path = os.path.join(self.model_dir, f"{self.model_name}_metadata.pkl")
            
            # Save model
            if self.model_type == 'lstm':
                keras_model_path = os.path.join(self.model_dir, f"{self.model_name}.h5")
                self.model.save(keras_model_path)
            else:
                with open(model_path, 'wb') as f:
                    pickle.dump(self.model, f)
                    
            # Save scaler
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
                
            # Save label encoder
            with open(encoder_path, 'wb') as f:
                pickle.dump(self.label_encoder, f)
                
            # Save metadata
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
                
            logger.info(f"Model saved: {model_path if self.model_type != 'lstm' else keras_model_path}")
            
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
            self.model_name = model_name
            
            # Check for metadata file
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            
            if not os.path.exists(metadata_path):
                logger.error(f"Metadata file not found: {metadata_path}")
                return False
                
            # Load metadata
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
                
            self.model_type = self.metadata.get('model_type', 'unknown')
            
            # Load model
            if self.model_type == 'lstm':
                keras_model_path = os.path.join(self.model_dir, f"{model_name}.h5")
                if not os.path.exists(keras_model_path):
                    logger.error(f"Model file not found: {keras_model_path}")
                    return False
                    
                self.model = load_model(keras_model_path)
                
            else:
                model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
                if not os.path.exists(model_path):
                    logger.error(f"Model file not found: {model_path}")
                    return False
                    
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                    
            # Load scaler
            scaler_path = os.path.join(self.model_dir, f"{model_name}_scaler.pkl")
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                    
            # Load label encoder
            encoder_path = os.path.join(self.model_dir, f"{model_name}_encoder.pkl")
            if os.path.exists(encoder_path):
                with open(encoder_path, 'rb') as f:
                    self.label_encoder = pickle.load(f)
                    
            logger.info(f"Model loaded: {model_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
            
    def evaluate_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Evaluate model performance
        
        Args:
            X: Input data
            y: Target labels
            
        Returns:
            Dict[str, Any]: Evaluation metrics
        """
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return {}
                
            # Encode target
            encoded_y = self.label_encoder.transform(y)
            
            # Reshape and standardize data for random forest
            if self.model_type == 'random_forest':
                if len(X.shape) == 3:
                    n_samples, n_timesteps, n_features = X.shape
                    X = X.reshape(n_samples, n_timesteps * n_features)
                    
                X = self.scaler.transform(X)
                
                # Make predictions
                y_pred = self.model.predict(X)
                
            elif self.model_type == 'lstm':
                # Make predictions
                y_pred_prob = self.model.predict(X)
                y_pred = np.argmax(y_pred_prob, axis=1)
                
            # Calculate metrics
            accuracy = accuracy_score(encoded_y, y_pred)
            report = classification_report(encoded_y, y_pred, output_dict=True)
            cm = confusion_matrix(encoded_y, y_pred)
            
            metrics = {
                'accuracy': float(accuracy),
                'f1_score': float(report['weighted avg']['f1-score']),
                'precision': float(report['weighted avg']['precision']),
                'recall': float(report['weighted avg']['recall']),
                'confusion_matrix': cm.tolist(),
                'classification_report': report
            }
            
            logger.info(f"Model evaluation metrics: accuracy={accuracy:.4f}, f1={report['weighted avg']['f1-score']:.4f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model: {str(e)}")
            return {}
            
def get_class_names(self) -> List[str]:
    """
    Get market regime class names
    
    Returns:
        List[str]: List of class names
    """
    try:
        if hasattr(self.label_encoder, 'classes_'):
            return self.label_encoder.classes_.tolist()
        else:
            return self.metadata.get('classes', [])
            
    except Exception as e:
        logger.error(f"Error getting class names: {str(e)}")
        return []
        
def get_feature_importance(self) -> Dict[str, float]:
    """
    Get feature importance for random forest model
    
    Returns:
        Dict[str, float]: Feature importance scores
    """
    try:
        if self.model_type != 'random_forest' or self.model is None:
            logger.warning("Feature importance is only available for random forest models")
            return {}
            
        # Get feature importance scores
        importance = self.model.feature_importances_
        
        # Create dictionary of feature importance
        feature_names = self.metadata.get('feature_names', [f"feature_{i}" for i in range(len(importance))])
        
        importance_dict = {
            feature_names[i]: float(importance[i])
            for i in range(len(importance))
        }
        
        # Sort by importance
        sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        
        return sorted_importance
        
    except Exception as e:
        logger.error(f"Error getting feature importance: {str(e)}")
        return {}
        
def get_model_summary(self) -> Dict[str, Any]:
    """
    Get model summary and metadata
    
    Returns:
        Dict[str, Any]: Model summary
    """
    try:
        if self.model is None:
            logger.error("Model not loaded")
            return {}
            
        summary = {
            'model_name': self.model_name,
            'model_type': self.model_type,
            'classes': self.get_class_names(),
            'metadata': self.metadata
        }
        
        if self.model_type == 'random_forest':
            summary['n_estimators'] = self.model.n_estimators
            summary['max_depth'] = self.model.max_depth
            summary['feature_importance'] = self.get_feature_importance()
            
        return summary
        
    except Exception as e:
        logger.error(f"Error getting model summary: {str(e)}")
        return {}