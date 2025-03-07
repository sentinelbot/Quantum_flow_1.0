# config/trading_config.py
import logging
import os
import json
from typing import Dict, List, Any, Optional, Union
from threading import Lock
from config.app_config import AppConfig

class TradingConfig:
    """
    Advanced Trading Configuration Management System

    Provides comprehensive configuration management for trading strategies,
    with singleton pattern, thread-safe operations, and flexible configuration handling.
    """
    
    _instance = None
    _lock = Lock()
    
    @classmethod
    def get_instance(cls):
        """
        Get singleton instance of TradingConfig.

        Returns:
            TradingConfig: Singleton instance of the trading configuration
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        Initialize TradingConfig with configuration loading.

        Args:
            config_path (str, optional): Path to configuration file. Defaults to "config/settings.json".
        """
        # Logging setup
        self.logger = logging.getLogger(__name__)
        
        # Configuration management
        self.app_config = None
        if isinstance(config_path, AppConfig):
            self.app_config = config_path
        else:
            self.app_config = AppConfig(config_path)
        
        # Trading configuration attributes
        self.trading_pairs: Dict[str, bool] = {}
        self.timeframes: List[str] = []
        self.strategy_configs: Dict[str, Dict[str, Any]] = {}
        
        # Load configuration
        self.load_config()
    
    def load_config(self) -> None:
        """
        Load and initialize trading configuration.
        Handles default configurations if no specific settings are found.
        """
        try:
            # Load trading pairs
            self.trading_pairs = self.app_config.get("trading.pairs", {})
            if not self.trading_pairs:
                default_pairs = self.app_config.get("trading.default_pairs", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
                self.trading_pairs = {pair: True for pair in default_pairs}
            
            # Load timeframes
            self.timeframes = self.app_config.get("trading.timeframes", [])
            if not self.timeframes:
                self.timeframes = self.app_config.get("trading.default_timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
            
            # Load strategy configurations
            self.strategy_configs = self.app_config.get("strategies", {})
            if not self.strategy_configs:
                self.strategy_configs = self._get_default_strategy_configs()
            
            self.logger.info("Trading configuration loaded successfully")
        
        except Exception as e:
            self.logger.error(f"Error loading trading configuration: {str(e)}")
    
    def _get_default_strategy_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate default strategy configurations.

        Returns:
            Dict[str, Dict[str, Any]]: Default configurations for trading strategies
        """
        return {
            "scalping": {
                "enabled": True,
                "timeframes": ["1m", "5m"],
                "parameters": {
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "ema_fast_period": 9,
                    "ema_slow_period": 21,
                    "take_profit_percent": 1.0,
                    "stop_loss_percent": 0.5
                }
            },
            "grid_trading": {
                "enabled": True,
                "timeframes": ["1h"],
                "parameters": {
                    "grid_levels": 10,
                    "grid_spacing_percent": 1.0,
                    "total_investment_percent": 20.0,
                    "dynamic_boundaries": True,
                    "volatility_factor": 1.5
                }
            },
            "trend_following": {
                "enabled": True,
                "timeframes": ["4h", "1d"],
                "parameters": {
                    "ema_short_period": 20,
                    "ema_long_period": 50,
                    "macd_fast_period": 12,
                    "macd_slow_period": 26,
                    "macd_signal_period": 9,
                    "take_profit_percent": 5.0,
                    "stop_loss_percent": 2.0,
                    "trailing_stop_percent": 1.0
                }
            },
            "mean_reversion": {
                "enabled": True,
                "timeframes": ["15m", "1h"],
                "parameters": {
                    "bollinger_period": 20,
                    "bollinger_std_dev": 2.0,
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "take_profit_percent": 2.0,
                    "stop_loss_percent": 1.0
                }
            },
            "sentiment_based": {
                "enabled": True,
                "timeframes": ["1h", "4h"],
                "parameters": {
                    "sentiment_threshold_positive": 0.6,
                    "sentiment_threshold_negative": 0.4,
                    "news_impact_time_hours": 24,
                    "volatility_adjustment": True,
                    "take_profit_percent": 3.0,
                    "stop_loss_percent": 2.0
                }
            },
            "arbitrage": {
                "enabled": True,
                "parameters": {
                    "min_profit_percent": 0.5,
                    "max_execution_time_ms": 1000,
                    "max_slippage_percent": 0.1,
                    "triangular": {
                        "enabled": True,
                        "min_profit_percent": 0.2
                    },
                    "cross_exchange": {
                        "enabled": True,
                        "exchanges": ["binance", "kucoin"],
                        "min_profit_percent": 0.8
                    }
                }
            }
        }
    
    def get_enabled_pairs(self) -> List[str]:
        """
        Retrieve list of currently enabled trading pairs.

        Returns:
            List[str]: List of enabled trading pairs
        """
        return [pair for pair, enabled in self.trading_pairs.items() if enabled]
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """
        Retrieve configuration for a specific strategy.

        Args:
            strategy_name (str): Name of the strategy

        Returns:
            Dict[str, Any]: Strategy configuration
        """
        return self.strategy_configs.get(strategy_name.lower(), {})
    
    def get_strategy_parameters(
        self, 
        strategy_name: str, 
        parameter_name: Optional[str] = None, 
        default: Any = None
    ) -> Union[Dict[str, Any], Any]:
        """
        Retrieve strategy parameters with flexible retrieval options.

        Args:
            strategy_name (str): Name of the strategy
            parameter_name (Optional[str]): Specific parameter to retrieve
            default (Any): Default value if parameter not found

        Returns:
            Strategy parameters or specific parameter value
        """
        strategy_config = self.get_strategy_config(strategy_name)
        parameters = strategy_config.get("parameters", {})
        
        if parameter_name is None:
            return parameters
        
        return parameters.get(parameter_name, default)
    
    def set_strategy_parameter(
        self, 
        strategy_name: str, 
        parameter_name: str, 
        value: Any
    ) -> bool:
        """
        Update a specific strategy parameter.

        Args:
            strategy_name (str): Name of the strategy
            parameter_name (str): Parameter to update
            value (Any): New parameter value

        Returns:
            bool: Success status of parameter update
        """
        strategy_name = strategy_name.lower()
        
        if strategy_name not in self.strategy_configs:
            self.logger.warning(f"Strategy not found: {strategy_name}")
            return False
        
        if "parameters" not in self.strategy_configs[strategy_name]:
            self.strategy_configs[strategy_name]["parameters"] = {}
        
        self.strategy_configs[strategy_name]["parameters"][parameter_name] = value
        
        # Save updated configuration
        return self.save_strategy_config(strategy_name, self.strategy_configs[strategy_name])
    
    def save_strategy_config(
        self, 
        strategy_name: str, 
        config: Dict[str, Any]
    ) -> bool:
        """
        Save configuration for a specific strategy.

        Args:
            strategy_name (str): Name of the strategy
            config (Dict[str, Any]): Configuration to save

        Returns:
            bool: Success status of configuration save
        """
        try:
            strategy_name = strategy_name.lower()
            self.strategy_configs[strategy_name] = config
            
            # Use app_config's save mechanism
            if hasattr(self.app_config, 'set'):
                self.app_config.set(f"strategies.{strategy_name}", config)
                if hasattr(self.app_config, 'save_config'):
                    self.app_config.save_config()
            
            self.logger.info(f"Saved configuration for strategy: {strategy_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving strategy configuration: {str(e)}")
            return False
    
    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """
        Check if a strategy is enabled.

        Args:
            strategy_name (str): Name of the strategy

        Returns:
            bool: True if strategy is enabled, False otherwise
        """
        strategy_config = self.get_strategy_config(strategy_name)
        return strategy_config.get("enabled", False)
    
    def get_strategy_timeframes(self, strategy_name: str) -> List[str]:
        """
        Get timeframes for a specific strategy.

        Args:
            strategy_name (str): Name of the strategy

        Returns:
            List[str]: List of timeframes for the strategy
        """
        strategy_config = self.get_strategy_config(strategy_name)
        return strategy_config.get("timeframes", [])
    
    def enable_strategy(self, strategy_name: str) -> bool:
        """
        Enable a strategy.

        Args:
            strategy_name (str): Name of the strategy

        Returns:
            bool: Success status of strategy enabling
        """
        strategy_name = strategy_name.lower()
        if strategy_name in self.strategy_configs:
            self.strategy_configs[strategy_name]["enabled"] = True
            return self.save_strategy_config(strategy_name, self.strategy_configs[strategy_name])
        
        self.logger.warning(f"Strategy not found: {strategy_name}")
        return False
    
    def disable_strategy(self, strategy_name: str) -> bool:
        """
        Disable a strategy.

        Args:
            strategy_name (str): Name of the strategy

        Returns:
            bool: Success status of strategy disabling
        """
        strategy_name = strategy_name.lower()
        if strategy_name in self.strategy_configs:
            self.strategy_configs[strategy_name]["enabled"] = False
            return self.save_strategy_config(strategy_name, self.strategy_configs[strategy_name])
        
        self.logger.warning(f"Strategy not found: {strategy_name}")
        return False
    
    def update_strategy_parameters(
        self, 
        strategy_name: str, 
        parameters: Dict[str, Any]
    ) -> bool:
        """
        Update parameters for a specific strategy.

        Args:
            strategy_name (str): Name of the strategy
            parameters (Dict[str, Any]): Parameters to update

        Returns:
            bool: Success status of parameter update
        """
        strategy_name = strategy_name.lower()
        if strategy_name in self.strategy_configs:
            if "parameters" not in self.strategy_configs[strategy_name]:
                self.strategy_configs[strategy_name]["parameters"] = {}
            
            self.strategy_configs[strategy_name]["parameters"].update(parameters)
            return self.save_strategy_config(strategy_name, self.strategy_configs[strategy_name])
        
        self.logger.warning(f"Strategy not found: {strategy_name}")
        return False
    
    def enable_trading_pair(self, pair: str) -> bool:
        """
        Enable a trading pair.

        Args:
            pair (str): Trading pair to enable

        Returns:
            bool: Success status of pair enabling
        """
        try:
            self.trading_pairs[pair] = True
            
            if hasattr(self.app_config, 'set'):
                self.app_config.set(f"trading.pairs.{pair}", True)
                if hasattr(self.app_config, 'save_config'):
                    self.app_config.save_config()
            
            self.logger.info(f"Enabled trading pair: {pair}")
            return True
        except Exception as e:
            self.logger.error(f"Error enabling trading pair: {str(e)}")
            return False
    
    def disable_trading_pair(self, pair: str) -> bool:
        """
        Disable a trading pair.

        Args:
            pair (str): Trading pair to disable

        Returns:
            bool: Success status of pair disabling
        """
        try:
            if pair in self.trading_pairs:
                self.trading_pairs[pair] = False
                
                if hasattr(self.app_config, 'set'):
                    self.app_config.set(f"trading.pairs.{pair}", False)
                    if hasattr(self.app_config, 'save_config'):
                        self.app_config.save_config()
                
                self.logger.info(f"Disabled trading pair: {pair}")
                return True
            
            self.logger.warning(f"Trading pair not found: {pair}")
            return False
        except Exception as e:
            self.logger.error(f"Error disabling trading pair: {str(e)}")
            return False
    
    def validate_strategy_parameters(
        self, 
        strategy_name: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[str]]:
        """
        Validate parameters for a specific strategy.

        Args:
            strategy_name (str): Name of the strategy
            parameters (Optional[Dict[str, Any]]): Parameters to validate

        Returns:
            Dict[str, List[str]]: Validation errors by parameter
        """
        strategy_name = strategy_name.lower()
        errors: Dict[str, List[str]] = {}
        
        if strategy_name not in self.strategy_configs:
            errors["strategy"] = [f"Strategy '{strategy_name}' not found"]
            return errors
        
        parameters = parameters or self.get_strategy_parameters(strategy_name)
        
        # Common parameter validations
        for param in ["take_profit_percent", "stop_loss_percent"]:
            if param in parameters and parameters[param] <= 0:
                errors.setdefault(param, []).append(f"Parameter '{param}' must be greater than 0")
        
        # Strategy-specific validations
        if strategy_name == "scalping":
            # Validate scalping-specific parameters
            for param in ["rsi_period", "ema_fast_period", "ema_slow_period"]:
                if param in parameters and parameters[param] <= 0:
                    errors.setdefault(param, []).append(f"Parameter '{param}' must be greater than 0")

                    # Strategy-specific validations
        if strategy_name == "scalping":
            # Validate scalping-specific parameters
            for param in ["rsi_period", "ema_fast_period", "ema_slow_period"]:
                if param in parameters and parameters[param] <= 0:
                    errors.setdefault(param, []).append(f"Parameter '{param}' must be greater than 0")
            
            # Validate RSI thresholds
            rsi_overbought = parameters.get("rsi_overbought")
            rsi_oversold = parameters.get("rsi_oversold")
            
            if rsi_overbought is not None and (rsi_overbought < 50 or rsi_overbought > 100):
                errors.setdefault("rsi_overbought", []).append("RSI overbought must be between 50 and 100")
            
            if rsi_oversold is not None and (rsi_oversold < 0 or rsi_oversold > 50):
                errors.setdefault("rsi_oversold", []).append("RSI oversold must be between 0 and 50")
        
        elif strategy_name == "grid_trading":
            # Validate grid trading parameters
            if "grid_levels" in parameters:
                grid_levels = parameters["grid_levels"]
                if grid_levels < 2:
                    errors.setdefault("grid_levels", []).append("Grid levels must be at least 2")
                
                if "grid_spacing_percent" in parameters:
                    grid_spacing = parameters["grid_spacing_percent"]
                    if grid_spacing <= 0:
                        errors.setdefault("grid_spacing_percent", []).append("Grid spacing must be greater than 0")
        
        elif strategy_name == "trend_following":
            # Validate trend following parameters
            for param in ["ema_short_period", "ema_long_period"]:
                if param in parameters and parameters[param] <= 0:
                    errors.setdefault(param, []).append(f"Parameter '{param}' must be greater than 0")
            
            # Ensure long period is longer than short period
            if ("ema_short_period" in parameters and 
                "ema_long_period" in parameters and 
                parameters["ema_short_period"] >= parameters["ema_long_period"]):
                errors.setdefault("ema_periods", []).append("Long EMA period must be greater than short EMA period")
        
        return errors
    
    def get_all(self) -> Dict[str, Any]:
        """
        Retrieve complete trading configuration.

        Returns:
            Dict[str, Any]: Complete trading configuration
        """
        return {
            "trading_pairs": self.trading_pairs,
            "timeframes": self.timeframes,
            "strategies": self.strategy_configs
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value using dot notation.

        Args:
            key (str): Configuration key in dot notation
            default (Any, optional): Default value if key not found

        Returns:
            Any: Configuration value or default
        """
        parts = key.split('.')
        config = self.get_all()
        
        for part in parts:
            if isinstance(config, dict) and part in config:
                config = config[part]
            else:
                return default
        
        return config