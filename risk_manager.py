# risk/risk_manager.py
import logging
from typing import Dict, List, Any, Optional
import time
import math
from datetime import datetime

from config.app_config import AppConfig
from database.models.user import RiskLevel
from exchange.abstract_exchange import TradingSignal as TradeSignal
from services.user_trading_manager import UserTradingManager
from database.repository.position_repository import PositionRepository
from exchange.exchange_factory import ExchangeFactory
from analysis.market_analyzer import MarketAnalyzer

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Comprehensive risk management system for controlling trade risk
    """
    def __init__(self, config: AppConfig, db):
        self.config = config
        self.db = db
        
        # Get risk parameters from config
        self.default_risk_level = self.config.get('risk.default_risk_level', 'medium')
        self.max_open_positions = self.config.get('risk.max_open_positions', 10)
        self.max_position_size_percent = self.config.get('risk.max_position_size_percent', 5.0)
        self.default_stop_loss_percent = self.config.get('risk.default_stop_loss_percent', 2.0)
        
        # Drawdown protection thresholds
        self.drawdown_stages = {
            1: self.config.get('risk.drawdown_protection.stage1_threshold', 5.0),
            2: self.config.get('risk.drawdown_protection.stage2_threshold', 10.0),
            3: self.config.get('risk.drawdown_protection.stage3_threshold', 15.0),
            4: self.config.get('risk.drawdown_protection.stage4_threshold', 20.0)
        }
        
        # Risk level constants
        self.RISK_LEVEL_LOW = 1
        self.RISK_LEVEL_MEDIUM = 2
        self.RISK_LEVEL_HIGH = 3
        self.RISK_LEVEL_EXTREME = 4
        
        # User risk state cache
        self.user_risk_state = {}
        
        # Position correlation data
        self.correlation_matrix = {}
        
        # Reference to notification manager (may be set later)
        self.notification_manager = None
        
        logger.info("Risk manager initialized")

    def validate_signal(self, user, signal: TradeSignal) -> Optional[TradeSignal]:
        """Validate a trading signal against risk parameters"""
        try:
            # Get trading settings
            trading_manager = UserTradingManager(self.db)
            settings = trading_manager.get_trading_settings(user.id)
            
            if not settings:
                logger.warning(f"No trading settings found for user {user.id}, using defaults")
                settings = {
                    'trading_mode': 'paper',
                    'risk_level': 'medium',
                    'is_paused': False,
                    'max_open_positions': 5,
                    'max_position_size': 0.1
                }
            
            # Check if trading is paused
            if settings.get('is_paused', False):
                logger.info(f"Signal rejected: Trading is paused for user {user.id}")
                return None
            
            # Check trading mode
            trading_mode = settings.get('trading_mode', 'paper')
            
            # Get user risk state
            risk_state = self._get_user_risk_state(user.id)
            
            # Check if trading is allowed
            if not self._is_trading_allowed(user, risk_state):
                logger.warning(f"Trading not allowed for user {user.id}")
                return None
            
            # For live trading, apply additional risk checks
            if trading_mode == 'live':
                # Check maximum open positions
                position_repo = PositionRepository(self.db)
                open_positions_count = position_repo.get_open_positions_count(user.id)
                
                if open_positions_count >= settings.get('max_open_positions', 5):
                    logger.info(f"Signal rejected: Maximum open positions reached for user {user.id}")
                    return None
                
                # Check position size against maximum allowed
                max_position_size = settings.get('max_position_size', 0.1)
                
                # Calculate position size
                exchange_factory = ExchangeFactory()
                exchange = exchange_factory.create_exchange('binance', user)
                
                account_balance = exchange.get_account_balance()
                position_value = signal.quantity * signal.price
                position_size_percent = position_value / account_balance if account_balance > 0 else 1
                
                if position_size_percent > max_position_size:
                    # Adjust position size to maximum allowed
                    logger.info(f"Adjusting position size from {position_size_percent:.4f} to {max_position_size:.4f}")
                    adjusted_quantity = (max_position_size * account_balance) / signal.price
                    signal.quantity = adjusted_quantity
            
            # Check against market conditions
            market_analyzer = MarketAnalyzer()
            
            # Check volatility
            volatility = market_analyzer.get_current_volatility(signal.symbol)
            max_allowed_volatility = self._get_max_volatility_for_risk_level(
                settings.get('risk_level', 'medium')
            )
            
            if volatility > max_allowed_volatility:
                logger.info(
                    f"Signal rejected: Market volatility too high for user's risk level "
                    f"({volatility:.2f}% > {max_allowed_volatility:.2f}%)"
                )
                return None
            
            # Check liquidity
            liquidity = market_analyzer.get_current_liquidity(signal.symbol)
            min_required_liquidity = self._get_min_liquidity_for_position_size(position_value)
            
            if liquidity < min_required_liquidity:
                logger.info("Signal rejected: Insufficient market liquidity for position size")
                return None
            
            # Calculate position size
            position_size = self._calculate_position_size(user, signal, risk_state)
            
            if position_size <= 0:
                logger.warning(f"Position size too small for user {user.id}")
                return None
            
            # Set position size in signal
            signal.quantity = position_size
            
            # Set stop loss and take profit
            if not signal.stop_loss:
                signal.stop_loss = self._calculate_stop_loss(
                    signal, 
                    settings.get('risk_level', 'medium')
                )
            
            if not signal.take_profit:
                signal.take_profit = self._calculate_take_profit(
                    signal, 
                    settings.get('risk_level', 'medium')
                )
            
            # Check portfolio risk
            if not self._check_portfolio_risk(user, signal, risk_state):
                logger.warning(f"Signal rejected due to portfolio risk for user {user.id}")
                return None
            
            logger.info(
                f"Validated signal for user {user.id}, "
                f"symbol: {signal.symbol}, side: {signal.side}, "
                f"quantity: {signal.quantity}"
            )
            return signal
            
        except Exception as e:
            logger.error(f"Error validating signal for user {user.id}: {str(e)}")
            return None

    def _get_max_volatility_for_risk_level(self, risk_level):
        """Get maximum allowed volatility based on risk level"""
        volatility_limits = {
            'low': 5.0,      # 5% max volatility for low risk
            'medium': 10.0,  # 10% max volatility for medium risk
            'high': 20.0     # 20% max volatility for high risk
        }
        
        return volatility_limits.get(risk_level.lower(), 10.0)
    
    def _get_min_liquidity_for_position_size(self, position_value):
        """Get minimum required liquidity for a given position size"""
        # Minimum liquidity should be at least 20x the position size to ensure easy execution
        return position_value * 20
    
    def _calculate_stop_loss(self, signal, risk_level):
        """Calculate appropriate stop loss based on risk level"""
        # Percentage drop from entry price to trigger stop loss
        stop_loss_percentages = {
            'low': 0.02,     # 2% for low risk
            'medium': 0.05,  # 5% for medium risk
            'high': 0.10     # 10% for high risk
        }
        
        percentage = stop_loss_percentages.get(risk_level.lower(), 0.05)
        
        if signal.side.lower() == 'buy':
            return signal.price * (1 - percentage)
        else:
            return signal.price * (1 + percentage)
    
    def _calculate_take_profit(self, signal, risk_level):
        """Calculate appropriate take profit based on risk level"""
        # Percentage gain from entry price to trigger take profit
        take_profit_percentages = {
            'low': 0.03,     # 3% for low risk
            'medium': 0.08,  # 8% for medium risk
            'high': 0.15     # 15% for high risk
        }
        
        percentage = take_profit_percentages.get(risk_level.lower(), 0.08)
        
        if signal.side.lower() == 'buy':
            return signal.price * (1 + percentage)
        else:
            return signal.price * (1 - percentage)

    def assess_portfolio_risk(self):
        """
        Perform a comprehensive assessment of portfolio risk across all active users.
        
        Analyzes current positions, market conditions, and potential exposures
        to provide risk metrics and trigger protective measures when necessary.
        
        Returns:
            bool: True if assessment completed successfully
        """
        try:
            logger.info("Performing scheduled portfolio risk assessment")
            
            # Get users with active positions
            active_users = self._get_users_with_positions()
            
            if not active_users:
                logger.info("No active positions found for risk assessment")
                return True
                
            assessment_results = {}
            for user_id in active_users:
                try:
                    # Get user risk state
                    risk_state = self._get_user_risk_state(user_id)
                    
                    # Force update of risk state
                    self._update_user_risk_state(user_id)
                    
                    # Get user data
                    user_repo = self.db.get_repository('user')
                    user = user_repo.get_user_by_id(user_id)
                    
                    if not user:
                        logger.warning(f"User {user_id} not found during risk assessment")
                        continue
                    
                    # Perform portfolio analysis
                    metrics = self._analyze_portfolio(user_id, risk_state)
                    
                    # Determine risk actions
                    actions = self._determine_risk_actions(user_id, metrics, risk_state)
                    
                    # Implement risk actions if needed
                    if actions:
                        self._implement_risk_actions(user_id, actions, risk_state)
                    
                    # Record assessment
                    assessment_results[user_id] = {
                        'metrics': metrics,
                        'actions': actions,
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"Portfolio risk assessment completed for user {user_id}")
                    
                except Exception as e:
                    logger.error(f"Error assessing portfolio risk for user {user_id}: {str(e)}")
            
            # Store assessment results for reporting
            self._record_assessment_results(assessment_results)
            
            logger.info(f"Portfolio risk assessment completed for {len(assessment_results)} users")
            return True
            
        except Exception as e:
            logger.error(f"Error performing portfolio risk assessment: {str(e)}")
            return False

    def _get_user_risk_state(self, user_id: int) -> Dict[str, Any]:
        """
        Get or create risk state for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: User risk state
        """
        if user_id not in self.user_risk_state:
            # Initialize risk state
            self.user_risk_state[user_id] = {
                'drawdown_stage': 0,
                'max_equity': 0,
                'current_equity': 0,
                'open_positions': {},
                'position_correlation': {},
                'last_updated': 0
            }
            
        # Check if update is needed
        current_time = time.time()
        if current_time - self.user_risk_state[user_id]['last_updated'] > 60:
            self._update_user_risk_state(user_id)
            
        return self.user_risk_state[user_id]

    def _update_user_risk_state(self, user_id: int) -> None:
        """
        Update risk state for a user
        
        Args:
            user_id: User ID
        """
        try:
            # Get user
            user_repo = self.db.get_repository('user')
            user = user_repo.get_user_by_id(user_id)
            
            if not user:
                logger.warning(f"User {user_id} not found")
                return
                
            # Get open positions
            position_repo = self.db.get_repository('position')
            open_positions = position_repo.get_open_positions_by_user(user_id)
            
            # Update risk state
            risk_state = self.user_risk_state[user_id]
            
            # Update equity
            risk_state['current_equity'] = user.equity
            
            if user.equity > risk_state['max_equity']:
                risk_state['max_equity'] = user.equity
                
            # Calculate drawdown
            if risk_state['max_equity'] > 0:
                drawdown_percent = (risk_state['max_equity'] - risk_state['current_equity']) / risk_state['max_equity'] * 100
                
                # Determine drawdown stage
                if drawdown_percent >= self.drawdown_stages[4]:
                    risk_state['drawdown_stage'] = 4
                elif drawdown_percent >= self.drawdown_stages[3]:
                    risk_state['drawdown_stage'] = 3
                elif drawdown_percent >= self.drawdown_stages[2]:
                    risk_state['drawdown_stage'] = 2
                elif drawdown_percent >= self.drawdown_stages[1]:
                    risk_state['drawdown_stage'] = 1
                else:
                    risk_state['drawdown_stage'] = 0
                    
            # Update open positions
            risk_state['open_positions'] = {
                position.symbol: {
                    'id': position.id,
                    'side': position.side.value,
                    'entry_price': position.average_entry_price,
                    'quantity': position.current_quantity,
                    'strategy': position.strategy
                }
                for position in open_positions
            }
            
            # Update position correlation
            self._update_position_correlation(user_id, list(risk_state['open_positions'].keys()))
            
            # Update timestamp
            risk_state['last_updated'] = time.time()
            
        except Exception as e:
            logger.error(f"Error updating risk state for user {user_id}: {str(e)}")

    def _is_trading_allowed(self, user, risk_state: Dict[str, Any]) -> bool:
        """
        Check if trading is allowed for a user
        
        Args:
            user: User object
            risk_state: User risk state
            
        Returns:
            bool: True if trading is allowed, False otherwise
        """
        # Check if user is paused
        if user.is_paused:
            return False
            
        # Check drawdown stage
        if risk_state['drawdown_stage'] == 4:
            # Stage 4: Complete trading halt
            return False
        elif risk_state['drawdown_stage'] == 3:
            # Stage 3: Allow closing positions only
            # This is checked later in signal validation
            pass
        elif risk_state['drawdown_stage'] == 2:
            # Stage 2: Pause new entries
            # Allow only if closing an existing position
            if 'side' in risk_state and risk_state['side'].lower() == 'sell':
                return True
            return False
            
        # Check maximum open positions
        if len(risk_state['open_positions']) >= self.max_open_positions:
            logger.warning(f"Maximum open positions reached for user {user.id}")
            return False
            
        return True

    def _calculate_position_size(self, user, signal: TradeSignal, risk_state: Dict[str, Any]) -> float:
        """
        Calculate appropriate position size
        
        Args:
            user: User object
            signal: Trade signal
            risk_state: User risk state
            
        Returns:
            float: Position size
        """
        try:
            # Get user balance
            if hasattr(user, 'balance') and user.balance > 0:
                balance = user.balance
            else:
                # Get balance from exchange
                quote_currency = signal.symbol.split('/')[1]
                balance_data = self.exchange.get_balance(quote_currency)
                balance = balance_data.get('free', 0)
                
            if balance <= 0:
                logger.warning(f"Insufficient balance for user {user.id}")
                return 0
                
            # Determine base risk percentage based on user's risk level
            if hasattr(user, 'risk_level'):
                risk_level = user.risk_level.value if hasattr(user.risk_level, 'value') else user.risk_level
            else:
                risk_level = self.default_risk_level
                
            if risk_level == 'low':
                risk_percent = 1.0
            elif risk_level == 'medium':
                risk_percent = 2.0
            elif risk_level == 'high':
                risk_percent = 3.0
            else:
                risk_percent = 2.0
                
            # Apply drawdown reduction
            if risk_state['drawdown_stage'] == 1:
                # Stage 1: Reduce position sizing by 25%
                risk_percent *= 0.75
            elif risk_state['drawdown_stage'] >= 2:
                # Stage 2+: Reduce position sizing by 50%
                risk_percent *= 0.5
                
            # Calculate maximum position size
            max_position_size = balance * (self.max_position_size_percent / 100)
            
            # Calculate position size based on risk per trade
            if signal.stop_loss and signal.price:
                # Risk-based position sizing using stop loss
                risk_amount = balance * (risk_percent / 100)
                price_diff_percent = abs(signal.price - signal.stop_loss) / signal.price * 100
                
                if price_diff_percent > 0:
                    position_size = risk_amount / price_diff_percent
                else:
                    position_size = max_position_size * 0.5  # Default to half of max if no stop loss
            else:
                # Default position size
                position_size = balance * (risk_percent / 100) / signal.price
                
            # Ensure position size doesn't exceed maximum
            position_size = min(position_size, max_position_size / signal.price)
            
            # Round position size to appropriate precision
            position_size = self._round_position_size(position_size, signal.symbol)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size for user {user.id}: {str(e)}")
            return 0

    def _round_position_size(self, position_size: float, symbol: str) -> float:
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

    def _update_position_correlation(self, user_id: int, symbols: List[str]) -> None:
        """
        Update position correlation for a user
        
        Args:
            user_id: User ID
            symbols: List of symbols
        """
        try:
            if not symbols:
                return
                
            risk_state = self.user_risk_state[user_id]
            
            # Get correlation matrix (simplified version)
            # In a real implementation, this would use historical price data
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols):
                    if i >= j:
                        continue
                        
                    key = f"{symbol1}_{symbol2}"
                    
                    # Use cached correlation or set a default
                    if key in self.correlation_matrix:
                        correlation = self.correlation_matrix[key]
                    else:
                        # Default correlation between different assets (moderate correlation)
                        correlation = 0.3
                        self.correlation_matrix[key] = correlation
                        
                    # Store in risk state
                    if 'position_correlation' not in risk_state:
                        risk_state['position_correlation'] = {}
                        
                    risk_state['position_correlation'][key] = correlation
                    
        except Exception as e:
            logger.error(f"Error updating position correlation for user {user_id}: {str(e)}")
    
    def _check_portfolio_risk(self, user, signal: TradeSignal, risk_state: Dict[str, Any]) -> bool:
        """
        Evaluate portfolio risk for a potential new trading signal
        
        Args:
            user: User object
            signal: Trade signal
            risk_state: User risk state
            
        Returns:
            bool: True if signal passes portfolio risk checks, False otherwise
        """
        try:
            # Calculate total current allocation
            total_allocation = self._calculate_total_allocation(user, risk_state)
            
            # Calculate new position value
            new_position_value = signal.price * signal.quantity
            
            # Calculate new total allocation percentage
            new_allocation = (total_allocation + new_position_value) / risk_state['current_equity'] * 100
            
            # Maximum allowed portfolio allocation
            max_allocation = 80  # 80% maximum allocation
            
            if new_allocation > max_allocation:
                logger.warning(f"Signal rejected: Would exceed maximum allocation for user {user.id}")
                return False
                
            # Check correlation risk with existing positions
            if not self._check_correlation_risk(user, signal, risk_state):
                logger.warning(f"Signal rejected: High correlation risk for user {user.id}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking portfolio risk for user {user.id}: {str(e)}")
            return False

    def _calculate_total_allocation(self, user, risk_state: Dict[str, Any]) -> float:
        """
        Calculate total portfolio allocation value
        
        Args:
            user: User object
            risk_state: User risk state
            
        Returns:
            float: Total allocation value
        """
        total_value = 0
        
        for symbol, position in risk_state['open_positions'].items():
            position_value = position['entry_price'] * position['quantity']
            total_value += position_value
            
        return total_value

    def _check_correlation_risk(self, user, signal: TradeSignal, risk_state: Dict[str, Any]) -> bool:
        """
        Assess correlation risk of a new position with existing portfolio
        
        Args:
            user: User object
            signal: Trade signal
            risk_state: User risk state
            
        Returns:
            bool: True if correlation risk is acceptable, False otherwise
        """
        # Skip if no existing positions
        if not risk_state['open_positions']:
            return True
            
        # Skip if no correlation data
        if not risk_state['position_correlation']:
            return True
            
        # Check correlation with each existing position
        high_correlation_count = 0
        
        for existing_symbol in risk_state['open_positions'].keys():
            if existing_symbol == signal.symbol:
                # Same symbol, check if it's the opposite side (hedging)
                existing_side = risk_state['open_positions'][existing_symbol]['side']
                
                if existing_side != signal.side:
                    # Hedging, so it's okay
                    continue
                else:
                    # Adding to existing position, so check other correlations
                    pass
                    
            # Check correlation
            key = f"{signal.symbol}_{existing_symbol}"
            reverse_key = f"{existing_symbol}_{signal.symbol}"
            
            if key in risk_state['position_correlation']:
                correlation = risk_state['position_correlation'][key]
            elif reverse_key in risk_state['position_correlation']:
                correlation = risk_state['position_correlation'][reverse_key]
            else:
                # Default correlation
                correlation = 0.3
                
            # Count high correlations
            if correlation > 0.7:
                high_correlation_count += 1
                
        # Reject if too many high correlations
        if high_correlation_count > 2:
            return False
            
        return True

    def _analyze_portfolio(self, user_id, risk_state):
        """
        Perform comprehensive analysis of portfolio risk metrics
        
        Args:
            user_id: User ID
            risk_state: User's risk state
            
        Returns:
            dict: Detailed portfolio risk metrics
        """
        try:
            metrics = {
                'position_count': len(risk_state['open_positions']),
                'total_exposure': 0,
                'exposure_percent': 0,
                'highest_concentration': 0,
                'concentration_symbol': '',
                'portfolio_correlation': 0,
                'potential_drawdown': 0,
                'value_at_risk': 0,
                'overnight_exposure': 0,
                'volatility_exposure': 0
            }
            
            # Skip if no positions
            if not risk_state['open_positions']:
                return metrics
                
            # Calculate exposure
            total_value = 0
            largest_position_value = 0
            largest_position_symbol = ''
            
            for symbol, position in risk_state['open_positions'].items():
                position_value = position['entry_price'] * position['quantity']
                total_value += position_value
                
                if position_value > largest_position_value:
                    largest_position_value = position_value
                    largest_position_symbol = symbol
            
            # Calculate metrics
            metrics['total_exposure'] = total_value
            
            if risk_state['current_equity'] > 0:
                metrics['exposure_percent'] = (total_value / risk_state['current_equity']) * 100
                
            if total_value > 0:
                metrics['highest_concentration'] = (largest_position_value / total_value) * 100
                metrics['concentration_symbol'] = largest_position_symbol
                
            # Calculate portfolio correlation (average)
            if 'position_correlation' in risk_state and risk_state['position_correlation']:
                correlations = list(risk_state['position_correlation'].values())
                metrics['portfolio_correlation'] = sum(correlations) / len(correlations)
                
            # Calculate potential drawdown (simplified)
            metrics['potential_drawdown'] = metrics['exposure_percent'] * 0.1
            metrics['value_at_risk'] = metrics['total_exposure'] * 0.05
            
            # Check for overnight positions
            metrics['overnight_exposure'] = total_value
            
            # Volatility exposure (simplified)
            metrics['volatility_exposure'] = total_value * 0.2
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio for user {user_id}: {str(e)}")
            return {}
        
        def _determine_risk_actions(self, user_id, metrics, risk_state):
            """
            Identify and prioritize risk mitigation actions based on portfolio metrics
            
            Args:
                user_id: User ID
                metrics: Portfolio risk metrics
                risk_state: User's risk state
                
            Returns:
                List[dict]: Prioritized risk mitigation actions
            """
        try:
            actions = []
            
            # High Overall Exposure Risk
            if metrics['exposure_percent'] > 70:
                actions.append({
                    'type': 'reduce_exposure',
                    'reason': 'Excessive Portfolio Allocation',
                    'threshold': 70,
                    'current': metrics['exposure_percent'],
                    'severity': 'high',
                    'recommendation': 'Immediately reduce total portfolio exposure'
                })
                
            # High Position Concentration Risk
            if metrics['highest_concentration'] > 40:
                actions.append({
                    'type': 'reduce_concentration',
                    'reason': 'Overexposure to Single Asset',
                    'symbol': metrics['concentration_symbol'],
                    'threshold': 40,
                    'current': metrics['highest_concentration'],
                    'severity': 'medium',
                    'recommendation': f'Diversify positions, reduce allocation in {metrics["concentration_symbol"]}'
                })
                
            # Portfolio Correlation Risk
            if metrics['portfolio_correlation'] > 0.7:
                actions.append({
                    'type': 'diversify',
                    'reason': 'High Asset Correlation',
                    'threshold': 0.7,
                    'current': metrics['portfolio_correlation'],
                    'severity': 'medium',
                    'recommendation': 'Introduce uncorrelated assets to reduce portfolio risk'
                })
                
            # Potential Drawdown Risk
            if metrics['potential_drawdown'] > 15:
                actions.append({
                    'type': 'reduce_exposure',
                    'reason': 'High Potential Drawdown',
                    'threshold': 15,
                    'current': metrics['potential_drawdown'],
                    'severity': 'high',
                    'recommendation': 'Implement strict risk management to limit potential losses'
                })
                
            # Overnight Exposure Risk
            if metrics['overnight_exposure'] > 0.5 * risk_state['current_equity']:
                actions.append({
                    'type': 'reduce_overnight',
                    'reason': 'Excessive Overnight Position Risk',
                    'threshold': 50,
                    'current': (metrics['overnight_exposure'] / risk_state['current_equity']) * 100,
                    'severity': 'medium',
                    'recommendation': 'Reduce overnight positions to minimize after-hours risk'
                })
                
            return actions
            
        except Exception as e:
            logger.error(f"Error determining risk actions for user {user_id}: {str(e)}")
            return []

    def _implement_risk_actions(self, user_id, actions, risk_state):
        """
        Execute risk mitigation strategies based on identified actions
        
        Args:
            user_id: User ID
            actions: List of risk mitigation actions
            risk_state: User's risk state
        """
        try:
            # Retrieve user information
            user_repo = self.db.get_repository('user')
            user = user_repo.get_user_by_id(user_id)
            
            if not user:
                logger.warning(f"User {user_id} not found during risk mitigation")
                return
                
            # Categorize actions by severity
            high_severity_actions = [a for a in actions if a['severity'] == 'high']
            medium_severity_actions = [a for a in actions if a['severity'] == 'medium']
            
            # Implement high-severity actions
            if high_severity_actions:
                # Dynamically adjust user's risk parameters
                if hasattr(user, 'max_position_size_percent'):
                    user.max_position_size_percent *= 0.75
                    user_repo.update_user(user)
                
                # Update risk state with additional protective measures
                risk_state['risk_reduction_active'] = True
                risk_state['risk_reduction_reason'] = high_severity_actions[0]['reason']
                risk_state['risk_reduction_expiry'] = time.time() + 86400  # 24-hour protection period
            
            # Send comprehensive risk notification
            if hasattr(self, 'notification_manager') and self.notification_manager:
                self._send_risk_notification(user_id, actions)
                    
            logger.info(f"Implemented {len(actions)} risk management actions for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error implementing risk actions for user {user_id}: {str(e)}")

    def _send_risk_notification(self, user_id, actions):
        """
        Generate and dispatch detailed risk management notifications
        
        Args:
            user_id: User ID
            actions: List of risk mitigation actions
        """
        try:
            if not hasattr(self, 'notification_manager') or not self.notification_manager:
                return
                
            # Skip if no actions are required
            if not actions:
                return
                
            # Construct comprehensive notification message
            message = "Portfolio Risk Management Alert\n\n"
            message += "Detailed Risk Assessment:\n"
            
            # Annotate specific risk details
            for action in actions:
                if action['type'] == 'reduce_exposure':
                    message += f"- Exposure Alert: Current {action['current']:.1f}% exceeds {action['threshold']}% threshold\n"
                elif action['type'] == 'reduce_concentration':
                    message += f"- Concentration Risk: {action['symbol']} represents {action['current']:.1f}% of portfolio\n"
                elif action['type'] == 'diversify':
                    message += f"- Correlation Risk: Portfolio correlation at {action['current']:.2f}\n"
                elif action['type'] == 'reduce_overnight':
                    message += f"- Overnight Exposure: {action['current']:.1f}% of equity at risk\n"
            
            message += "\nRecommended Immediate Actions:\n"
            
            # Provide specific, actionable recommendations
            recommendations = set()
            for action in actions:
                recommendations.add(action['recommendation'])
            
            for recommendation in recommendations:
                message += f"- {recommendation}\n"
            
            # Send comprehensive notification
            self.notification_manager.send_notification(
                user_id=user_id,
                message=message,
                notification_type="risk_management"
            )
            
        except Exception as e:
            logger.error(f"Error sending risk notification to user {user_id}: {str(e)}")

        def _record_assessment_results(self, results):
            """
            Persistently record portfolio risk assessment results for future analysis and reporting
            
            Args:
                results: Comprehensive risk assessment results dictionary
            """
            try:
                # In a production environment, this would involve:
                # 1. Storing results in a dedicated risk assessment database
                # 2. Creating historical records for compliance and audit purposes
                
                # Log summary statistics
                high_risk_users = sum(1 for user_id, data in results.items() 
                                    if any(a['severity'] == 'high' for a in data.get('actions', [])))
                
                logger.info(f"Risk Assessment Summary: {len(results)} users evaluated")
                logger.info(f"High-Risk Users Identified: {high_risk_users}")
                
                # Optional: Persist results to long-term storage
                self._persist_risk_assessment_data(results)
                
            except Exception as e:
                logger.error(f"Error recording risk assessment results: {str(e)}")

    def _persist_risk_assessment_data(self, results):
        """
        Store risk assessment data for long-term tracking and analysis
        
        Args:
            results: Comprehensive risk assessment results
        """
        try:
            # This method would interface with a data storage system
            # Potential implementations:
            # - Write to a time-series database
            # - Store in a data warehouse
            # - Create persistent log files
            
            risk_log_repo = self.db.get_repository('risk_log')
            
            for user_id, assessment in results.items():
                risk_log_repo.create_risk_log_entry({
                    'user_id': user_id,
                    'timestamp': assessment['timestamp'],
                    'metrics': assessment['metrics'],
                    'actions': assessment['actions']
                })
                
        except Exception as e:
            logger.error(f"Error persisting risk assessment data: {str(e)}")

    def get_drawdown_stage(self, user_id: int) -> int:
        """
        Retrieve the current drawdown risk stage for a specific user
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            int: Current drawdown stage (0-4)
        """
        risk_state = self._get_user_risk_state(user_id)
        return risk_state['drawdown_stage']

    def get_max_position_size(self, user_id: int, symbol: str) -> float:
        """
        Calculate maximum allowable position size for a given trading symbol
        
        Args:
            user_id: Unique identifier for the user
            symbol: Trading pair symbol
            
        Returns:
            float: Maximum position size
        """
        try:
            user_repo = self.db.get_repository('user')
            user = user_repo.get_user_by_id(user_id)
            
            if not user:
                logger.warning(f"User {user_id} not found for max position size calculation")
                return 0
                
            risk_state = self._get_user_risk_state(user_id)
            
            # Determine base risk percentage based on user's risk profile
            risk_level = self._get_risk_level_percentage(user)
            
            # Apply drawdown stage adjustments
            risk_percent = self._adjust_risk_percent_for_drawdown(risk_level, risk_state)
            
            # Calculate maximum position size
            balance = user.balance
            max_position_size = balance * (self.max_position_size_percent / 100)
            
            # Placeholder for getting actual symbol price
            # In production, this would come from an exchange or market data service
            price = self._get_symbol_current_price(symbol)
            
            # Convert to position size and round
            max_position_size /= price
            max_position_size = self._round_position_size(max_position_size, symbol)
            
            return max_position_size
            
        except Exception as e:
            logger.error(f"Error calculating max position size for user {user_id}: {str(e)}")
            return 0

    def _get_risk_level_percentage(self, user) -> float:
        """
        Convert user's risk level to a corresponding percentage
        
        Args:
            user: User object
            
        Returns:
            float: Risk percentage
        """
        if hasattr(user, 'risk_level'):
            risk_level = user.risk_level.value if hasattr(user.risk_level, 'value') else user.risk_level
        else:
            risk_level = self.default_risk_level
        
        risk_percentages = {
            'low': 1.0,
            'medium': 2.0,
            'high': 3.0
        }
        
        return risk_percentages.get(risk_level, 2.0)

    def _adjust_risk_percent_for_drawdown(self, base_risk_percent: float, risk_state: Dict[str, Any]) -> float:
        """
        Adjust risk percentage based on current drawdown stage
        
        Args:
            base_risk_percent: Initial risk percentage
            risk_state: Current user risk state
            
        Returns:
            float: Adjusted risk percentage
        """
        if risk_state['drawdown_stage'] == 1:
            # Stage 1: Reduce position sizing by 25%
            return base_risk_percent * 0.75
        elif risk_state['drawdown_stage'] >= 2:
            # Stage 2+: Reduce position sizing by 50%
            return base_risk_percent * 0.5
        
        return base_risk_percent

    def _get_symbol_current_price(self, symbol: str) -> float:
        """
        Retrieve current market price for a trading symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            float: Current market price
        """
        # Placeholder implementation
        # In production, this would use an exchange or market data API
        return 1000.0  # Default placeholder price