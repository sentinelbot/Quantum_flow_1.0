# risk/position_sizer.py
import logging
import math
from typing import Dict, Any, Optional

from config.app_config import AppConfig
from database.models.user import RiskLevel

logger = logging.getLogger(__name__)

class PositionSizer:
    """
    Position sizing calculator
    """
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Get position sizing parameters from config
        self.max_position_size_percent = self.config.get('risk.max_position_size_percent', 5.0)
        self.default_risk_per_trade_percent = {
            'low': 1.0,
            'medium': 2.0,
            'high': 3.0
        }
        
    def calculate_position_size(self, account_balance: float, risk_level: str,
                             entry_price: float, stop_loss_price: float,
                             max_risk_percent: float = None) -> float:
        """
        Calculate position size based on risk parameters
        
        Args:
            account_balance: Account balance
            risk_level: Risk level ('low', 'medium', 'high')
            entry_price: Entry price
            stop_loss_price: Stop loss price
            max_risk_percent: Maximum risk percentage (overrides default)
            
        Returns:
            float: Position size
        """
        try:
            # Determine risk percentage based on risk level
            risk_percent = max_risk_percent or self.default_risk_per_trade_percent.get(risk_level.lower(), 2.0)
            
            # Calculate risk amount
            risk_amount = account_balance * (risk_percent / 100)
            
            # Calculate price difference percentage
            price_diff = abs(entry_price - stop_loss_price)
            price_diff_percent = price_diff / entry_price
            
            if price_diff_percent <= 0:
                logger.warning("Invalid stop loss: too close to entry price")
                return 0
                
            # Calculate position size
            position_size = risk_amount / price_diff
            
            # Ensure position size doesn't exceed maximum
            max_position_size = account_balance * (self.max_position_size_percent / 100) / entry_price
            position_size = min(position_size, max_position_size)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0
            
    def calculate_position_size_by_capital_percent(self, account_balance: float, 
                                                capital_percent: float,
                                                entry_price: float) -> float:
        """
        Calculate position size based on percentage of capital
        
        Args:
            account_balance: Account balance
            capital_percent: Percentage of capital to allocate
            entry_price: Entry price
            
        Returns:
            float: Position size
        """
        try:
            # Calculate position value
            position_value = account_balance * (capital_percent / 100)
            
            # Calculate position size
            position_size = position_value / entry_price
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size by capital percent: {str(e)}")
            return 0
            
    def calculate_stop_loss_price(self, entry_price: float, side: str, 
                               risk_percent: float) -> float:
        """
        Calculate stop loss price based on risk percentage
        
        Args:
            entry_price: Entry price
            side: Trade side ('buy' or 'sell')
            risk_percent: Risk percentage
            
        Returns:
            float: Stop loss price
        """
        try:
            if side.lower() == 'buy':
                return entry_price * (1 - risk_percent / 100)
            else:
                return entry_price * (1 + risk_percent / 100)
                
        except Exception as e:
            logger.error(f"Error calculating stop loss price: {str(e)}")
            return entry_price
            
    def calculate_take_profit_price(self, entry_price: float, side: str, 
                                 reward_percent: float) -> float:
        """
        Calculate take profit price based on reward percentage
        
        Args:
            entry_price: Entry price
            side: Trade side ('buy' or 'sell')
            reward_percent: Reward percentage
            
        Returns:
            float: Take profit price
        """
        try:
            if side.lower() == 'buy':
                return entry_price * (1 + reward_percent / 100)
            else:
                return entry_price * (1 - reward_percent / 100)
                
        except Exception as e:
            logger.error(f"Error calculating take profit price: {str(e)}")
            return entry_price
            
    def calculate_position_size_for_multiple_targets(self, account_balance: float, 
                                                 risk_level: str,
                                                 entry_price: float, 
                                                 stop_loss_price: float,
                                                 targets: Dict[float, float]) -> Dict[float, float]:
        """
        Calculate position sizes for multiple take profit targets
        
        Args:
            account_balance: Account balance
            risk_level: Risk level ('low', 'medium', 'high')
            entry_price: Entry price
            stop_loss_price: Stop loss price
            targets: Dictionary of take profit price -> percentage allocation
            
        Returns:
            Dict[float, float]: Dictionary of take profit price -> position size
        """
        try:
            # Calculate total position size
            total_position_size = self.calculate_position_size(
                account_balance, risk_level, entry_price, stop_loss_price
            )
            
            # Calculate position size for each target
            result = {}
            total_percentage = sum(targets.values())
            
            for target_price, percentage in targets.items():
                # Normalize percentage
                normalized_percentage = percentage / total_percentage
                
                # Calculate position size for this target
                target_position_size = total_position_size * normalized_percentage
                
                result[target_price] = target_position_size
                
            return result
            
        except Exception as e:
            logger.error(f"Error calculating position size for multiple targets: {str(e)}")
            return {}
            
    def round_position_size(self, position_size: float, symbol: str) -> float:
        """
        Round position size to appropriate precision for the symbol
        
        Args:
            position_size: Position size
            symbol: Trading pair symbol
            
        Returns:
            float: Rounded position size
        """
        # This is a simplified version
        # In a real implementation, this would get precision from exchange info
        if 'BTC' in symbol:
            return round(position_size, 6)
        elif 'ETH' in symbol:
            return round(position_size, 5)
        else:
            return round(position_size, 2)
