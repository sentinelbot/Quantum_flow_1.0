import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import os
import time
import json
import glob
import pickle
from datetime import datetime

from ml.data_processor import DataProcessor
from ml.feature_engineering import FeatureEngineer
from ml.models.price_predictor import PricePredictor
from ml.models.pattern_recognition import PatternRecognition
from ml.models.regime_classifier import RegimeClassifier

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Coordinator for training and managing all ML models
    """
    def __init__(self, model_dir: str = "models", data_dir: str = "data"):
        self.model_dir = model_dir
        self.data_dir = data_dir
        
        # Create directories if they don't exist
        os.makedirs(model_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        self.data_processor = DataProcessor(cache_dir=os.path.join(model_dir, "cache"))
        self.feature_engineer = FeatureEngineer()
        
        # Training status
        self.training_status = {}
        
        logger.info("Model trainer initialized")
    
    def update_models(self) -> bool:
        """
        Update and retrain machine learning models with the latest data.
        
        Performs model evaluation, retraining, and validation to ensure
        optimal prediction accuracy with current market conditions.
        
        Returns:
            bool: True if update was successful
        """
        try:
            logger.info("Starting scheduled model update process")
            
            # Get the list of models that need updating
            models_to_update = self._get_models_requiring_updates()
            
            if not models_to_update:
                logger.info("No models require updates at this time")
                return True
                
            # Process each model that needs updating
            updated_count = 0
            for model_info in models_to_update:
                model_name = model_info.get('name', 'unknown')
                model_type = self._determine_model_type(model_name)
                
                try:
                    logger.info(f"Updating model: {model_name} (Type: {model_type})")
                    
                    # Set training status
                    job_id = f"update_{model_name}_{int(time.time())}"
                    self.training_status[job_id] = {
                        'status': 'updating',
                        'progress': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Load training data
                    training_data = self._load_latest_training_data(model_name, model_type)
                    
                    if not training_data:
                        logger.warning(f"No training data available for {model_name}")
                        self.training_status[job_id]['status'] = 'failed'
                        self.training_status[job_id]['error'] = 'No training data available'
                        continue
                    
                    # Update model based on its type
                    success = False
                    if model_type == 'price_prediction':
                        success = self._update_price_prediction_model(model_name, training_data)
                    elif model_type == 'pattern_recognition':
                        success = self._update_pattern_recognition_model(model_name, training_data)
                    elif model_type == 'regime_classifier':
                        success = self._update_regime_classifier(model_name, training_data)
                    
                    if success:
                        updated_count += 1
                        self.training_status[job_id]['status'] = 'completed'
                        self.training_status[job_id]['progress'] = 100
                    else:
                        self.training_status[job_id]['status'] = 'failed'
                        self.training_status[job_id]['error'] = 'Update failed'
                    
                except Exception as e:
                    logger.error(f"Failed to update model {model_name}: {str(e)}")
                    if job_id in self.training_status:
                        self.training_status[job_id]['status'] = 'failed'
                        self.training_status[job_id]['error'] = str(e)
            
            logger.info(f"Model update process completed. Updated {updated_count} of {len(models_to_update)} models")
            return True
            
        except Exception as e:
            logger.error(f"Model update process failed: {str(e)}")
            return False
    
    def _get_models_requiring_updates(self) -> List[Dict[str, Any]]:
        """
        Determine which models need to be updated based on 
        data changes and time elapsed since last update.
        
        Returns:
            list: Models requiring updates
        """
        try:
            models_to_update = []
            
            # Check H5 model files (deep learning models)
            h5_files = glob.glob(os.path.join(self.model_dir, "*.h5"))
            for model_path in h5_files:
                model_name = os.path.basename(model_path).replace(".h5", "")
                models_to_update.extend(self._check_model_update_needed(model_name, model_path))
            
            # Check PKL model files (classical ML models)
            pkl_files = glob.glob(os.path.join(self.model_dir, "*.pkl"))
            for model_path in pkl_files:
                # Skip metadata, scaler, and encoder files
                filename = os.path.basename(model_path)
                if '_metadata' in filename or '_scaler' in filename or '_encoder' in filename:
                    continue
                
                model_name = filename.replace(".pkl", "")
                models_to_update.extend(self._check_model_update_needed(model_name, model_path))
            
            return models_to_update
            
        except Exception as e:
            logger.error(f"Error determining models for update: {str(e)}")
            return []
    
    def _check_model_update_needed(self, model_name: str, model_path: str) -> List[Dict[str, Any]]:
        """
        Check if a specific model needs to be updated.
        
        Args:
            model_name: Name of the model
            model_path: Path to the model file
            
        Returns:
            List containing model info if update needed, empty list otherwise
        """
        try:
            # Check for metadata
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            
            # If no metadata exists, schedule for update
            if not os.path.exists(metadata_path):
                return [{
                    'name': model_name,
                    'path': model_path,
                    'last_updated': 0,
                    'reason': 'no_metadata'
                }]
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            # Get last update time
            last_updated = metadata.get('last_updated', 0)
            
            # Default update frequency: 1 day
            update_frequency_hours = metadata.get('update_frequency_hours', 24)
            update_interval = update_frequency_hours * 3600  # Convert to seconds
            
            # Check if update is due
            current_time = time.time()
            if (current_time - last_updated) > update_interval:
                return [{
                    'name': model_name,
                    'path': model_path,
                    'last_updated': last_updated,
                    'reason': 'time_elapsed'
                }]
            
            # No update needed
            return []
            
        except Exception as e:
            logger.error(f"Error checking model {model_name}: {str(e)}")
            # Return model for update if check fails
            return [{
                'name': model_name,
                'path': model_path,
                'last_updated': 0,
                'reason': 'error_checking'
            }]
    
    def _determine_model_type(self, model_name: str) -> str:
        """
        Determine the type of model based on its name.
        
        Args:
            model_name: Name of the model
            
        Returns:
            str: Model type ('price_prediction', 'pattern_recognition', or 'regime_classifier')
        """
        if model_name.startswith('price_'):
            return 'price_prediction'
        elif model_name.startswith('pattern_'):
            return 'pattern_recognition'
        elif model_name.startswith('regime_'):
            return 'regime_classifier'
        else:
            return 'unknown'
    
    def _load_latest_training_data(self, model_name: str, model_type: str) -> Optional[Dict[str, Any]]:
        """
        Load the latest training data for a specific model.
        
        Args:
            model_name: Name of the model
            model_type: Type of the model
            
        Returns:
            Optional[Dict[str, Any]]: Training data or None if not available
        """
        try:
            # First try to load model-specific data
            data = self.load_training_data(model_name)
            if data:
                return data
            
            # If not available, try to load data based on model type
            if model_type == 'price_prediction':
                # Extract symbol and timeframe from model name
                parts = model_name.split('_')
                if len(parts) >= 3:
                    symbol = parts[1]
                    timeframe = parts[2]
                    data = self.load_training_data(f"price_{symbol}_{timeframe}")
                    if data:
                        return data
            
            elif model_type == 'pattern_recognition':
                # Extract pattern name from model name
                parts = model_name.split('_')
                if len(parts) >= 2:
                    pattern_name = parts[1]
                    data = self.load_training_data(f"pattern_{pattern_name}")
                    if data:
                        return data
            
            elif model_type == 'regime_classifier':
                # Try to load general regime data
                data = self.load_training_data("regime_data")
                if data:
                    return data
            
            # If no specific data found, try to use default datasets
            default_data_path = os.path.join(self.data_dir, f"default_{model_type}.pkl")
            if os.path.exists(default_data_path):
                with open(default_data_path, 'rb') as f:
                    return pickle.load(f)
            
            logger.warning(f"No training data found for {model_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading training data for {model_name}: {str(e)}")
            return None
    
    def _update_price_prediction_model(self, model_name: str, training_data: Dict[str, Any]) -> bool:
        """
        Update a price prediction model with new data.
        
        Args:
            model_name: Name of the model
            training_data: Training data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load existing model
            model = self.load_price_prediction_model(model_name)
            if not model:
                logger.error(f"Failed to load price prediction model: {model_name}")
                return False
            
            # Extract model type from model name
            parts = model_name.split('_')
            if len(parts) < 4:
                logger.error(f"Invalid model name format: {model_name}")
                return False
            
            model_type = parts[3]  # Assuming format: price_symbol_timeframe_modeltype_timestamp
            
            # Retrain model
            X_train = training_data.get('X_train')
            y_train = training_data.get('y_train')
            X_val = training_data.get('X_test')
            y_val = training_data.get('y_test')
            
            if X_train is None or y_train is None:
                logger.error(f"Invalid training data for {model_name}")
                return False
            
            # Train model
            _, history = model.train_model(
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                model_type=model_type,
                epochs=50,  # Reduced epochs for updates
                batch_size=32,
                model_name=model_name
            )
            
            # Save updated model
            model.save_model()
            
            # Update metadata
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
            else:
                metadata = {}
            
            metadata['last_updated'] = time.time()
            metadata['update_frequency_hours'] = 24
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Price prediction model updated successfully: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating price prediction model {model_name}: {str(e)}")
            return False
    
    def _update_pattern_recognition_model(self, model_name: str, training_data: Dict[str, Any]) -> bool:
        """
        Update a pattern recognition model with new data.
        
        Args:
            model_name: Name of the model
            training_data: Training data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load existing model
            model = self.load_pattern_recognition_model(model_name)
            if not model:
                logger.error(f"Failed to load pattern recognition model: {model_name}")
                return False
            
            # Extract model type from model name
            parts = model_name.split('_')
            if len(parts) < 3:
                logger.error(f"Invalid model name format: {model_name}")
                return False
            
            model_type = parts[2]  # Assuming format: pattern_patternname_modeltype_timestamp
            
            # Prepare training data
            X = training_data.get('X')
            y = training_data.get('y')
            
            if X is None or y is None:
                logger.error(f"Invalid training data for {model_name}")
                return False
            
            # Update model based on type
            if model_type in ['cnn', 'lstm']:
                # Deep learning model
                _, history = model.train_deep_learning_model(
                    X=X,
                    y=y,
                    model_type=model_type,
                    epochs=30,  # Reduced epochs for updates
                    batch_size=32,
                    model_name=model_name
                )
            else:
                # Classical ML model
                model.train_ml_model(
                    X=X,
                    y=y,
                    model_type=model_type,
                    model_name=model_name
                )
            
            # Update metadata
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
            else:
                metadata = {}
            
            metadata['last_updated'] = time.time()
            metadata['update_frequency_hours'] = 24
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Pattern recognition model updated successfully: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating pattern recognition model {model_name}: {str(e)}")
            return False
    
    def _update_regime_classifier(self, model_name: str, training_data: Dict[str, Any]) -> bool:
        """
        Update a regime classifier with new data.
        
        Args:
            model_name: Name of the model
            training_data: Training data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load existing model
            model = self.load_regime_classifier(model_name)
            if not model:
                logger.error(f"Failed to load regime classifier: {model_name}")
                return False
            
            # Extract model type from model name
            parts = model_name.split('_')
            if len(parts) < 2:
                logger.error(f"Invalid model name format: {model_name}")
                return False
            
            model_type = parts[1]  # Assuming format: regime_modeltype_timestamp
            
            # Prepare training data
            X = training_data.get('X')
            y = training_data.get('y')
            
            if X is None or y is None:
                logger.error(f"Invalid training data for {model_name}")
                return False
            
            # Train model
            model.train_model(
                X=X,
                y=y,
                model_type=model_type,
                model_name=model_name
            )
            
            # Update metadata
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
            else:
                metadata = {}
            
            metadata['last_updated'] = time.time()
            metadata['update_frequency_hours'] = 24
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Regime classifier updated successfully: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating regime classifier {model_name}: {str(e)}")
            return False
        
    def train_price_prediction_model(self, data: List[Dict[str, Any]], symbol: str, 
                                  timeframe: str, model_type: str = 'lstm') -> str:
        """
        Train price prediction model
        
        Args:
            data: OHLCV data
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            model_type: Type of model ('lstm', 'gru', or 'cnn_lstm')
            
        Returns:
            str: Model name or empty string if training failed
        """
        try:
            # Set training status
            job_id = f"price_{symbol}_{timeframe}_{int(time.time())}"
            self.training_status[job_id] = {
                'status': 'preprocessing',
                'progress': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Preprocess data
            preprocessed_data, metadata = self.data_processor.preprocess_ohlcv_data(
                data,
                lookback_periods=20,
                predict_periods=5,
                test_size=0.2,
                scaler_name=f"price_{symbol}_{timeframe}"
            )
            
            if not preprocessed_data:
                logger.error(f"Failed to preprocess data for {symbol} {timeframe}")
                self.training_status[job_id]['status'] = 'failed'
                self.training_status[job_id]['error'] = 'Preprocessing failed'
                return ""
                
            # Update status
            self.training_status[job_id]['status'] = 'training'
            self.training_status[job_id]['progress'] = 20
            
            # Create model instance
            price_predictor = PricePredictor(model_dir=self.model_dir)
            
            # Generate model name
            model_name = f"price_{symbol}_{timeframe}_{model_type}_{int(time.time())}"
            
            # Train model
            model, history = price_predictor.train_model(
                X_train=preprocessed_data['X_train'],
                y_train=preprocessed_data['y_train'],
                X_val=preprocessed_data['X_test'],
                y_val=preprocessed_data['y_test'],
                model_type=model_type,
                epochs=100,
                batch_size=32,
                model_name=model_name
            )
            
            if model is None:
                logger.error(f"Failed to train price prediction model for {symbol} {timeframe}")
                self.training_status[job_id]['status'] = 'failed'
                self.training_status[job_id]['error'] = 'Training failed'
                return ""
                
            # Update status
            self.training_status[job_id]['status'] = 'evaluating'
            self.training_status[job_id]['progress'] = 80
            
            # Evaluate model
            metrics = price_predictor.evaluate_model(
                X_test=preprocessed_data['X_test'],
                y_test=preprocessed_data['y_test']
            )
            
            # Save model
            price_predictor.save_model()
            
            # Save scaler
            self.data_processor.save_scaler(f"price_{symbol}_{timeframe}")
            
            # Update status
            self.training_status[job_id]['status'] = 'completed'
            self.training_status[job_id]['progress'] = 100
            self.training_status[job_id]['metrics'] = metrics
            self.training_status[job_id]['model_name'] = model_name
            
            logger.info(f"Price prediction model trained successfully: {model_name}")
            
            return model_name
            
        except Exception as e:
            logger.error(f"Error training price prediction model: {str(e)}")
            if job_id in self.training_status:
                self.training_status[job_id]['status'] = 'failed'
                self.training_status[job_id]['error'] = str(e)
            return ""
            
    def train_pattern_recognition_model(self, data: List[Dict[str, Any]], labels: List[int],
                                    pattern_name: str, model_type: str = 'cnn') -> str:
        """
        Train pattern recognition model
        
        Args:
            data: OHLCV data
            labels: Pattern labels (1 for pattern, 0 for no pattern)
            pattern_name: Name of the pattern
            model_type: Type of model ('cnn', 'lstm', or 'random_forest')
            
        Returns:
            str: Model name or empty string if training failed
        """
        try:
            # Set training status
            job_id = f"pattern_{pattern_name}_{int(time.time())}"
            self.training_status[job_id] = {
                'status': 'preprocessing',
                'progress': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Convert to numpy arrays
            X = np.array(data)
            y = np.array(labels)
            
            # Update status
            self.training_status[job_id]['status'] = 'training'
            self.training_status[job_id]['progress'] = 20
            
            # Create model instance
            pattern_model = PatternRecognition(model_dir=self.model_dir)
            
            # Generate model name
            model_name = f"pattern_{pattern_name}_{model_type}_{int(time.time())}"
            
            # Train model
            if model_type in ['cnn', 'lstm']:
                model, history = pattern_model.train_deep_learning_model(
                    X=X,
                    y=y,
                    model_type=model_type,
                    epochs=50,
                    batch_size=32,
                    model_name=model_name
                )
            else:
                model = pattern_model.train_ml_model(
                    X=X,
                    y=y,
                    model_type=model_type,
                    model_name=model_name
                )
                
            if model is None:
                logger.error(f"Failed to train pattern recognition model for {pattern_name}")
                self.training_status[job_id]['status'] = 'failed'
                self.training_status[job_id]['error'] = 'Training failed'
                return ""
                
            # Update status
            self.training_status[job_id]['status'] = 'completed'
            self.training_status[job_id]['progress'] = 100
            self.training_status[job_id]['model_name'] = model_name
            
            logger.info(f"Pattern recognition model trained successfully: {model_name}")
            
            return model_name
            
        except Exception as e:
            logger.error(f"Error training pattern recognition model: {str(e)}")
            if job_id in self.training_status:
                self.training_status[job_id]['status'] = 'failed'
                self.training_status[job_id]['error'] = str(e)
            return ""
            
    def train_regime_classifier(self, data: List[Dict[str, Any]], labels: List[str],
                            model_type: str = 'random_forest') -> str:
        """
        Train market regime classifier
        
        Args:
            data: OHLCV data
            labels: Regime labels
            model_type: Type of model ('random_forest' or 'lstm')
            
        Returns:
            str: Model name or empty string if training failed
        """
        try:
            # Set training status
            job_id = f"regime_{model_type}_{int(time.time())}"
            self.training_status[job_id] = {
                'status': 'preprocessing',
                'progress': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Convert to numpy arrays
            X = np.array(data)
            y = np.array(labels)
            
            # Update status
            self.training_status[job_id]['status'] = 'training'
            self.training_status[job_id]['progress'] = 20
            
            # Create model instance
            regime_model = RegimeClassifier(model_dir=self.model_dir)
            
            # Generate model name
            model_name = f"regime_{model_type}_{int(time.time())}"
            
            # Train model
            model = regime_model.train_model(
                X=X,
                y=y,
                model_type=model_type,
                model_name=model_name
            )
            
            if model is None:
                logger.error(f"Failed to train regime classifier")
                self.training_status[job_id]['status'] = 'failed'
                self.training_status[job_id]['error'] = 'Training failed'
                return ""
                
            # Update status
            self.training_status[job_id]['status'] = 'completed'
            self.training_status[job_id]['progress'] = 100
            self.training_status[job_id]['model_name'] = model_name
            
            logger.info(f"Regime classifier trained successfully: {model_name}")
            
            return model_name
            
        except Exception as e:
            logger.error(f"Error training regime classifier: {str(e)}")
            if job_id in self.training_status:
                self.training_status[job_id]['status'] = 'failed'
                self.training_status[job_id]['error'] = str(e)
            return ""
            
    def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a training job
        
        Args:
            job_id: Training job ID
            
        Returns:
            Dict[str, Any]: Training status
        """
        return self.training_status.get(job_id, {
            'status': 'not_found',
            'error': 'Training job not found'
        })
        
    def get_all_training_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all training jobs
        
        Returns:
            Dict[str, Dict[str, Any]]: All training statuses
        """
        return self.training_status
        
    def load_price_prediction_model(self, model_name: str) -> Optional[PricePredictor]:
        """
        Load price prediction model
        
        Args:
            model_name: Model name
            
        Returns:
            Optional[PricePredictor]: Loaded model or None if loading failed
        """
        try:
            model = PricePredictor(model_dir=self.model_dir)
            success = model.load_model(model_name)
            
            if success:
                logger.info(f"Price prediction model loaded: {model_name}")
                return model
            else:
                logger.error(f"Failed to load price prediction model: {model_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading price prediction model: {str(e)}")
            return None
            
    def load_pattern_recognition_model(self, model_name: str) -> Optional[PatternRecognition]:
        """
        Load pattern recognition model
        
        Args:
            model_name: Model name
            
        Returns:
            Optional[PatternRecognition]: Loaded model or None if loading failed
        """
        try:
            model = PatternRecognition(model_dir=self.model_dir)
            success = model.load_model(model_name)
            
            if success:
                logger.info(f"Pattern recognition model loaded: {model_name}")
                return model
            else:
                logger.error(f"Failed to load pattern recognition model: {model_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading pattern recognition model: {str(e)}")
            return None
            
    def load_regime_classifier(self, model_name: str) -> Optional[RegimeClassifier]:
        """
        Load market regime classifier
        
        Args:
            model_name: Model name
            
        Returns:
            Optional[RegimeClassifier]: Loaded model or None if loading failed
        """
        try:
            model = RegimeClassifier(model_dir=self.model_dir)
            success = model.load_model(model_name)
            
            if success:
                logger.info(f"Regime classifier loaded: {model_name}")
                return model
            else:
                logger.error(f"Failed to load regime classifier: {model_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading regime classifier: {str(e)}")
            return None
            
    def list_available_models(self) -> Dict[str, List[str]]:
        """
        List all available models
        
        Returns:
            Dict[str, List[str]]: Dictionary of model types and names
        """
        try:
            models = {
                'price_prediction': [],
                'pattern_recognition': [],
                'regime_classifier': []
            }
            
            # List all files in model directory
            for filename in os.listdir(self.model_dir):
                if filename.endswith('.h5') or filename.endswith('.pkl'):
                    # Skip metadata and scaler files
                    if '_metadata' in filename or '_scaler' in filename or '_scaler' in filename or '_encoder' in filename:
                        continue
                        
                    # Get model name (remove extension)
                    model_name = os.path.splitext(filename)[0]
                    
                    # Categorize model
                    if model_name.startswith('price_'):
                        models['price_prediction'].append(model_name)
                    elif model_name.startswith('pattern_'):
                        models['pattern_recognition'].append(model_name)
                    elif model_name.startswith('regime_'):
                        models['regime_classifier'].append(model_name)
                        
            return models
            
        except Exception as e:
            logger.error(f"Error listing available models: {str(e)}")
            return {'price_prediction': [], 'pattern_recognition': [], 'regime_classifier': []}
            
    def get_model_metadata(self, model_name: str) -> Dict[str, Any]:
        """
        Get metadata for a model
        
        Args:
            model_name: Model name
            
        Returns:
            Dict[str, Any]: Model metadata
        """
        try:
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            
            if not os.path.exists(metadata_path):
                logger.error(f"Metadata file not found: {metadata_path}")
                return {}
                
            # Load metadata
            with open(metadata_path, 'rb') as f:
                import pickle
                metadata = pickle.load(f)
                
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting model metadata: {str(e)}")
            return {}
            
    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model and its associated files
        
        Args:
            model_name: Model name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if model files exist
            h5_path = os.path.join(self.model_dir, f"{model_name}.h5")
            pkl_path = os.path.join(self.model_dir, f"{model_name}.pkl")
            metadata_path = os.path.join(self.model_dir, f"{model_name}_metadata.pkl")
            scaler_path = os.path.join(self.model_dir, f"{model_name}_scaler.pkl")
            encoder_path = os.path.join(self.model_dir, f"{model_name}_encoder.pkl")
            
            # Delete model file
            if os.path.exists(h5_path):
                os.remove(h5_path)
            elif os.path.exists(pkl_path):
                os.remove(pkl_path)
            else:
                logger.error(f"Model file not found: {model_name}")
                return False
                
            # Delete metadata file
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                
            # Delete scaler file
            if os.path.exists(scaler_path):
                os.remove(scaler_path)
                
            # Delete encoder file
            if os.path.exists(encoder_path):
                os.remove(encoder_path)
                
            logger.info(f"Model deleted: {model_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting model: {str(e)}")
            return False
            
    def save_training_data(self, data: Any, data_name: str) -> bool:
        """
        Save training data to disk
        
        Args:
            data: Data to save
            data_name: Name for the data file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create data path
            data_path = os.path.join(self.data_dir, f"{data_name}.pkl")
            
            # Save data
            with open(data_path, 'wb') as f:
                import pickle
                pickle.dump(data, f)
                
            logger.info(f"Training data saved: {data_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving training data: {str(e)}")
            return False
            
    def load_training_data(self, data_name: str) -> Any:
        """
        Load training data from disk
        
        Args:
            data_name: Name of the data file
            
        Returns:
            Any: Loaded data or None if loading failed
        """
        try:
            # Create data path
            data_path = os.path.join(self.data_dir, f"{data_name}.pkl")
            
            if not os.path.exists(data_path):
                logger.error(f"Data file not found: {data_path}")
                return None
                
            # Load data
            with open(data_path, 'rb') as f:
                import pickle
                data = pickle.load(f)
                
            logger.info(f"Training data loaded: {data_path}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading training data: {str(e)}")
            return None