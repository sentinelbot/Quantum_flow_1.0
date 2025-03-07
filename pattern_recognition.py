
# ml/models/pattern_recognition.py
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score, roc_auc_score
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Dense, Flatten, Dropout, Input, LSTM, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import os
import pickle
import time

logger = logging.getLogger(__name__)

class PatternRecognition:
    """
    Pattern recognition model for identifying chart patterns
    """
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.model = None
        self.model_name = ""
        self.model_type = ""
        self.scaler = StandardScaler()
        self.metadata = {}
        
        # Create model directory if it doesn't exist
        os.makedirs(model_dir, exist_ok=True)
        
        logger.info("Pattern recognition model initialized")
        
    def build_cnn_model(self, sequence_length: int, n_features: int, n_classes: int) -> Model:
        """
        Build CNN model for pattern recognition
        
        Args:
            sequence_length: Length of input sequence
            n_features: Number of features
            n_classes: Number of classes
            
        Returns:
            Model: CNN model
        """
        try:
            # Input layer
            inputs = Input(shape=(sequence_length, n_features))
            
            # CNN layers
            x = Conv1D(filters=64, kernel_size=3, activation='relu', padding='same')(inputs)
            x = BatchNormalization()(x)
            x = MaxPooling1D(pool_size=2)(x)
            
            x = Conv1D(filters=128, kernel_size=3, activation='relu', padding='same')(x)
            x = BatchNormalization()(x)
            x = MaxPooling1D(pool_size=2)(x)
            
            x = Conv1D(filters=128, kernel_size=3, activation='relu', padding='same')(x)
            x = BatchNormalization()(x)
            x = MaxPooling1D(pool_size=2)(x)
            
            # Flatten and dense layers
            x = Flatten()(x)
            x = Dense(128, activation='relu')(x)
            x = Dropout(0.3)(x)
            x = Dense(64, activation='relu')(x)
            x = Dropout(0.3)(x)
            
            # Output layer
            if n_classes == 2:
                outputs = Dense(1, activation='sigmoid')(x)
            else:
                outputs = Dense(n_classes, activation='softmax')(x)
                
            # Create model
            model = Model(inputs=inputs, outputs=outputs)
            
            # Compile model
            if n_classes == 2:
                model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])
            else:
                model.compile(optimizer=Adam(learning_rate=0.001), loss='sparse_categorical_crossentropy', metrics=['accuracy'])
                
            return model
            
        except Exception as e:
            logger.error(f"Error building CNN model: {str(e)}")
            return None
            
    def build_lstm_model(self, sequence_length: int, n_features: int, n_classes: int) -> Model:
        """
        Build LSTM model for pattern recognition
        
        Args:
            sequence_length: Length of input sequence
            n_features: Number of features
            n_classes: Number of classes
            
        Returns:
            Model: LSTM model
        """
        try:
            # Input layer
            inputs = Input(shape=(sequence_length, n_features))
            
            # LSTM layers
            x = LSTM(64, return_sequences=True)(inputs)
            x = Dropout(0.2)(x)
            x = LSTM(64, return_sequences=False)(x)
            x = Dropout(0.2)(x)
            
            # Dense layers
            x = Dense(32, activation='relu')(x)
            x = Dropout(0.2)(x)
            
            # Output layer
            if n_classes == 2:
                outputs = Dense(1, activation='sigmoid')(x)
            else:
                outputs = Dense(n_classes, activation='softmax')(x)
                
            # Create model
            model = Model(inputs=inputs, outputs=outputs)
            
            # Compile model
            if n_classes == 2:
                model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])
            else:
                model.compile(optimizer=Adam(learning_rate=0.001), loss='sparse_categorical_crossentropy', metrics=['accuracy'])
                
            return model
            
        except Exception as e:
            logger.error(f"Error building LSTM model: {str(e)}")
            return None
            
    def train_deep_learning_model(self, X: np.ndarray, y: np.ndarray, model_type: str = 'cnn',
                              epochs: int = 50, batch_size: int = 32,
                              model_name: str = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Train deep learning model for pattern recognition
        
        Args:
            X: Input features
            y: Target labels
            model_type: Type of model ('cnn' or 'lstm')
            epochs: Number of epochs for training
            batch_size: Batch size for training
            model_name: Name for the model (default: auto-generated)
            
        Returns:
            Tuple[Any, Dict[str, Any]]: Trained model and training history
        """
        try:
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Determine number of classes
            if len(y.shape) > 1:
                n_classes = y.shape[1]
            else:
                n_classes = len(np.unique(y))
                
            # Convert to one-hot encoding for multiclass
            if n_classes > 2 and len(y.shape) == 1:
                from tensorflow.keras.utils import to_categorical
                y_train = to_categorical(y_train)
                y_val = to_categorical(y_val)
                
            # Get input dimensions
            sequence_length, n_features = X.shape[1], X.shape[2]
            
            # Generate model name if not provided
            if model_name is None:
                timestamp = int(time.time())
                model_name = f"pattern_recognition_{model_type}_{timestamp}"
                
            self.model_name = model_name
            self.model_type = model_type
            
            # Build model based on type
            if model_type == 'cnn':
                model = self.build_cnn_model(sequence_length, n_features, n_classes)
            elif model_type == 'lstm':
                model = self.build_lstm_model(sequence_length, n_features, n_classes)
            else:
                logger.error(f"Unknown model type: {model_type}")
                return None, {}
                
            if model is None:
                return None, {}
                
            # Set up callbacks
            callbacks = [
                EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
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
                'sequence_length': sequence_length,
                'n_features': n_features,
                'n_classes': n_classes,
                'training_params': {
                    'epochs': epochs,
                    'batch_size': batch_size,
                    'final_loss': float(history.history['loss'][-1]),
                    'final_val_loss': float(history.history['val_loss'][-1]),
                    'best_epoch': int(np.argmin(history.history['val_loss'])) + 1
                },
                'timestamp': int(time.time())
            }
            
            # Save model and metadata
            self.save_model()
            
            logger.info(f"Deep learning model trained successfully: {model_name}")
            
            return model, history.history
            
        except Exception as e:
            logger.error(f"Error training deep learning model: {str(e)}")
            return None, {}
            
    def train_ml_model(self, X: np.ndarray, y: np.ndarray, model_type: str = 'random_forest',
                    model_name: str = None) -> Any:
        """
        Train traditional machine learning model for pattern recognition
        
        Args:
            X: Input features
            y: Target labels
            model_type: Type of model ('random_forest', 'gradient_boosting', or 'svm')
            model_name: Name for the model (default: auto-generated)
            
        Returns:
            Any: Trained model
        """
        try:
            # Reshape input data if necessary
            if len(X.shape) == 3:
                X = X.reshape(X.shape[0], -1)
                
            # Generate model name if not provided
            if model_name is None:
                timestamp = int(time.time())
                model_name = f"pattern_recognition_{model_type}_{timestamp}"
                
            self.model_name = model_name
            self.model_type = model_type
            
            # Standardize features
            X = self.scaler.fit_transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Build model based on type
            if model_type == 'random_forest':
                model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'max_depth': [None, 10, 20, 30],
                    'min_samples_split': [2, 5, 10]
                }
            elif model_type == 'gradient_boosting':
                model = GradientBoostingClassifier(random_state=42)
                param_grid = {
                    'n_estimators': [50, 100, 200],
                    'learning_rate': [0.01, 0.1, 0.2],
                    'max_depth': [3, 5, 7]
                }
            elif model_type == 'svm':
                model = SVC(probability=True, random_state=42)
                param_grid = {
                    'C': [0.1, 1, 10],
                    'kernel': ['linear', 'rbf'],
                    'gamma': ['scale', 'auto', 0.1]
                }
            else:
                logger.error(f"Unknown model type: {model_type}")
                return None
                
            # Use grid search for hyperparameter tuning
            grid_search = GridSearchCV(model, param_grid, cv=3, scoring='f1_weighted', n_jobs=-1)
            grid_search.fit(X_train, y_train)
            
            # Get best model
            best_model = grid_search.best_estimator_
            
            # Evaluate model
            y_pred = best_model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average='weighted')
            
            # Store model and metadata
            self.model = best_model
            
            self.metadata = {
                'model_name': model_name,
                'model_type': model_type,
                'best_params': grid_search.best_params_,
                'feature_shape': X.shape,
                'performance': {
                    'accuracy': float(accuracy),
                    'f1_score': float(f1)
                },
                'timestamp': int(time.time())
            }
            
            # Save model and metadata
            self.save_model()
            
            logger.info(f"ML model trained successfully: {model_name}, accuracy: {accuracy:.4f}, f1: {f1:.4f}")
            
            return best_model
            
        except Exception as e:
            logger.error(f"Error training ML model: {str(e)}")
            return None
            
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions
        
        Args:
            X: Input features
            
        Returns:
            np.ndarray: Predicted classes or probabilities
        """
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return np.array([])
                
            # Check if deep learning model
            if self.model_type in ['cnn', 'lstm']:
                # Ensure input has correct shape for deep learning model
                if len(X.shape) == 2:
                    # Reshape to (samples, sequence_length, features)
                    X = X.reshape(X.shape[0], -1, 1)
                    
                # Make predictions
                predictions = self.model.predict(X)
                
            else:  # Machine learning model
                # Reshape input data if necessary
                if len(X.shape) == 3:
                    X = X.reshape(X.shape[0], -1)
                    
                # Standardize features
                X = self.scaler.transform(X)
                
                # Make predictions
                predictions = self.model.predict_proba(X)
                
            return predictions
            
        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}")
            return np.array([])
            
    def recognize_patterns(self, X: np.ndarray, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Recognize patterns in data
        
        Args:
            X: Input data
            threshold: Probability threshold for recognition
            
        Returns:
            List[Dict[str, Any]]: Recognized patterns with probabilities
        """
        try:
            # Get predictions
            predictions = self.predict(X)
            
            results = []
            
            # Check if binary classification
            if predictions.shape[1] == 1:
                # Binary classification
                for i, prob in enumerate(predictions):
                    if prob[0] >= threshold:
                        results.append({
                            'index': i,
                            'pattern': 'positive',
                            'probability': float(prob[0])
                        })
            else:
                # Multiclass classification
                for i, probs in enumerate(predictions):
                    max_prob = np.max(probs)
                    if max_prob >= threshold:
                        max_class = np.argmax(probs)
                        results.append({
                            'index': i,
                            'pattern': str(max_class),  # Class name should be mapped to actual pattern names
                            'probability': float(max_prob)
                        })
                        
            return results
            
        except Exception as e:
            logger.error(f"Error recognizing patterns: {str(e)}")
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
                self.model_name = f"pattern_recognition_{timestamp}"
                
            # Create path
            model_path = os.path.join(self.model_dir, f"{self.model_name}.pkl")
            
            # Save model
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
                
            # Save scaler
            scaler_path = os.path.join(self.model_dir, f"{self.model_name}_scaler.pkl")
            with open(scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
                
            # Save metadata
            metadata_path = os.path.join(self.model_dir, f"{self.model_name}_metadata.pkl")
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
                
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
            model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
            scaler_path = os.path.join(self.model_dir, f"{model_name}_scaler.pkl")
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
                
            # Load model
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
                
            # Load scaler if available
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                    
            # Load metadata if available
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    self.metadata = pickle.load(f)
                    self.model_type = self.metadata.get('model_type', '')
            else:
                logger.warning(f"Metadata file not found: {metadata_path}")
                self.metadata = {'model_name': model_name}
                
            self.model_name = model_name
            
            logger.info(f"Model loaded: {model_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
            
    def evaluate_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Evaluate model performance
        
        Args:
            X: Input features
            y: Target labels
            
        Returns:
            Dict[str, Any]: Evaluation metrics
        """
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return {}
                
            # Reshape input data if necessary for ML models
            if self.model_type not in ['cnn', 'lstm'] and len(X.shape) == 3:
                X = X.reshape(X.shape[0], -1)
                X = self.scaler.transform(X)
                
            # Make predictions
            if self.model_type in ['cnn', 'lstm']:
                y_pred_prob = self.model.predict(X)
                
                # Convert probabilities to class predictions
                if y_pred_prob.shape[1] == 1:  # Binary
                    y_pred = (y_pred_prob > 0.5).astype(int)
                else:  # Multiclass
                    y_pred = np.argmax(y_pred_prob, axis=1)
            else:
                y_pred = self.model.predict(X)
                y_pred_prob = self.model.predict_proba(X)
                
            # Calculate metrics
            accuracy = accuracy_score(y, y_pred)
            
            # Generate classification report
            report = classification_report(y, y_pred, output_dict=True)
            
            # Generate confusion matrix
            cm = confusion_matrix(y, y_pred)
            
            # Calculate AUC-ROC for binary classification
            if len(np.unique(y)) == 2:
                if y_pred_prob.shape[1] == 1:  # CNN/LSTM binary output
                    auc_roc = roc_auc_score(y, y_pred_prob)
                else:  # ML model output
                    auc_roc = roc_auc_score(y, y_pred_prob[:, 1])
                    
                metrics = {
                    'accuracy': float(accuracy),
                    'f1_score': float(report['weighted avg']['f1-score']),
                    'precision': float(report['weighted avg']['precision']),
                    'recall': float(report['weighted avg']['recall']),
                    'auc_roc': float(auc_roc),
                    'confusion_matrix': cm.tolist(),
                    'classification_report': report
                }
            else:
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