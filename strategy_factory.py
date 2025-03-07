import logging
from typing import Dict, Any, List
from config.app_config import AppConfig
from risk.risk_manager import RiskManager
from strategies.base_strategy import BaseStrategy
from strategies.scalping import ScalpingStrategy
from strategies.grid_trading import GridTradingStrategy
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.sentiment_based import SentimentBasedStrategy
from strategies.arbitrage import ArbitrageStrategy

logger = logging.getLogger(__name__)

class StrategyFactory:
    """
    Factory for creating strategy instances
    """
    def __init__(self, config: AppConfig, risk_manager: RiskManager):
        self.config = config
        self.risk_manager = risk_manager
       
        # Register strategies
        self.strategies = {
            'scalping': ScalpingStrategy,
            'grid_trading': GridTradingStrategy,
            'trend_following': TrendFollowingStrategy,
            'mean_reversion': MeanReversionStrategy,
            'sentiment_based': SentimentBasedStrategy,
            'arbitrage': ArbitrageStrategy
        }
       
    def create_strategy(self, strategy_name: str, exchange, user, allocation_percent: float = 10) -> BaseStrategy:
        """Create a strategy instance with user-specific configurations"""
        try:
            # Get strategy class
            strategy_class = self.strategies.get(strategy_name.lower())
            
            if not strategy_class:
                logger.error(f"Unsupported strategy: {strategy_name}")
                raise ValueError(f"Unsupported strategy: {strategy_name}")
                
            # Get strategy configuration from trading config
            from config.trading_config import TradingConfig
            trading_config = TradingConfig.get_instance()
            strategy_params = trading_config.get_strategy_parameters(strategy_name)
            
            merged_config = {
                'parameters': strategy_params or {},
                'allocation_percent': allocation_percent
            }
            
            # Add trading pairs from user preferences if available
            if user and hasattr(user, 'trading_pairs'):
                merged_config['symbols'] = [
                    pair for pair, enabled in user.trading_pairs.items() if enabled
                ]
            else:
                # Use default pairs from config
                merged_config['symbols'] = self.config.get('trading.trading_pairs', [])
                
            # Create strategy instance
            strategy = strategy_class(
                exchange=exchange,
                user=user,
                risk_manager=self.risk_manager,
                config=merged_config
            )
            
            logger.info(f"Created {strategy_name} strategy instance with {allocation_percent}% allocation")
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error creating strategy instance: {str(e)}")
            raise
           
    def get_available_strategies(self) -> List[str]:
        """
        Get list of available strategies
       
        Returns:
            List[str]: List of strategy names
        """
        return list(self.strategies.keys())