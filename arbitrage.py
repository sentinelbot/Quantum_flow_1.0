# strategies/arbitrage.py
import logging
import time
from typing import Dict, List, Any, Optional

from exchange.abstract_exchange import TradeSignal, AbstractExchange
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class ArbitrageStrategy(BaseStrategy):
    """
    Arbitrage trading strategy
    
    Identifies and exploits price differences between exchanges or trading pairs
    """
    def __init__(self, exchange, user, risk_manager, config: Dict[str, Any]):
        super().__init__('arbitrage', exchange, user, risk_manager, config)
        
        # Get parameters
        params = config.get('parameters', {})
        self.min_profit_percent = params.get('min_profit_percent', 0.5)
        self.max_execution_time_ms = params.get('max_execution_time_ms', 1000)
        self.max_slippage_percent = params.get('max_slippage_percent', 0.1)
        
        # Get triangular arbitrage config
        triangular_config = params.get('triangular', {})
        self.triangular_enabled = triangular_config.get('enabled', True)
        self.triangular_min_profit = triangular_config.get('min_profit_percent', 0.2)
        
        # Get cross-exchange arbitrage config
        cross_exchange_config = params.get('cross_exchange', {})
        self.cross_exchange_enabled = cross_exchange_config.get('enabled', True)
        self.cross_exchange_min_profit = cross_exchange_config.get('min_profit_percent', 0.8)
        self.exchanges = cross_exchange_config.get('exchanges', ['binance', 'kucoin'])
        
        # Arbitrage opportunities
        self.opportunities = {}
        
        # Set update interval
        self.update_interval = 10  # 10 seconds for faster reaction
        
    def _update(self) -> None:
        """
        Update arbitrage opportunities
        """
        try:
            if self.triangular_enabled:
                self._update_triangular_opportunities()
                
            if self.cross_exchange_enabled:
                self._update_cross_exchange_opportunities()
                
        except Exception as e:
            logger.error(f"Error updating arbitrage opportunities: {str(e)}")
            
    def _update_triangular_opportunities(self) -> None:
        """
        Update triangular arbitrage opportunities
        """
        # Get all symbols
        all_symbols = set(self.symbols)
        
        # Find potential triangular paths
        triangle_paths = []
        
        for symbol1 in all_symbols:
            base1, quote1 = symbol1.split('/')
            
            for symbol2 in all_symbols:
                if symbol1 == symbol2:
                    continue
                    
                base2, quote2 = symbol2.split('/')
                
                # Check if symbols can form a path
                if quote1 == base2:
                    # Find a third symbol to complete the triangle
                    symbol3 = f"{base1}/{quote2}"
                    
                    if symbol3 in all_symbols:
                        # Found a triangle path
                        triangle_paths.append([symbol1, symbol2, symbol3])
                        
        # Check each path for arbitrage opportunities
        for path in triangle_paths:
            symbol1, symbol2, symbol3 = path
            
            # Get ticker data
            ticker1 = self.exchange.get_ticker(symbol1)
            ticker2 = self.exchange.get_ticker(symbol2)
            ticker3 = self.exchange.get_ticker(symbol3)
            
            if not all([ticker1, ticker2, ticker3]):
                continue
                
            # Calculate arbitrage profit
            # For a triangle A/B -> B/C -> C/A
            # Buy A with B, Buy C with B, Sell C for A
            price1 = ticker1.get('price', 0)
            price2 = ticker2.get('price', 0)
            price3 = ticker3.get('price', 0)
            
            if not all([price1, price2, price3]):
                continue
                
            # Calculate profit
            profit_percent = (1 / price1) * price2 * price3 - 1
            profit_percent *= 100  # Convert to percentage
            
            # Check if profitable
            if profit_percent > self.triangular_min_profit:
                logger.info(f"Found triangular arbitrage opportunity: {symbol1} -> {symbol2} -> {symbol3}, profit: {profit_percent:.2f}%")
                
                # Store opportunity
                opportunity_id = f"tri_{symbol1}_{symbol2}_{symbol3}"
                self.opportunities[opportunity_id] = {
                    'type': 'triangular',
                    'path': path,
                    'profit_percent': profit_percent,
                    'timestamp': time.time()
                }
                
    def _update_cross_exchange_opportunities(self) -> None:
        """
        Update cross-exchange arbitrage opportunities
        """
        # This is a placeholder as we don't have other exchanges initialized
        # In a real implementation, this would check prices across different exchanges
        pass
        
    def _generate_signals(self) -> List[TradeSignal]:
        """
        Generate trading signals based on arbitrage opportunities
        
        Returns:
            List[TradeSignal]: List of trade signals
        """
        signals = []
        
        try:
            # Check each opportunity
            current_time = time.time()
            expired_opportunities = []
            
            for opp_id, opportunity in self.opportunities.items():
                # Skip if opportunity is too old (10 seconds)
                if current_time - opportunity['timestamp'] > 10:
                    expired_opportunities.append(opp_id)
                    continue
                    
                # Generate signals based on opportunity type
                if opportunity['type'] == 'triangular':
                    tri_signals = self._generate_triangular_signals(opportunity)
                    signals.extend(tri_signals)
                elif opportunity['type'] == 'cross_exchange':
                    cross_signals = self._generate_cross_exchange_signals(opportunity)
                    signals.extend(cross_signals)
                    
                # Remove opportunity after generating signals
                expired_opportunities.append(opp_id)
                
            # Clean up expired opportunities
            for opp_id in expired_opportunities:
                if opp_id in self.opportunities:
                    del self.opportunities[opp_id]
                    
        except Exception as e:
            logger.error(f"Error generating arbitrage signals: {str(e)}")
            
        return signals
        
    def _generate_triangular_signals(self, opportunity: Dict[str, Any]) -> List[TradeSignal]:
        """
        Generate signals for triangular arbitrage
        """
        signals = []
        
        try:
            path = opportunity['path']
            symbol1, symbol2, symbol3 = path
            
            # Get ticker data
            ticker1 = self.exchange.get_ticker(symbol1)
            ticker2 = self.exchange.get_ticker(symbol2)
            ticker3 = self.exchange.get_ticker(symbol3)
            
            if not all([ticker1, ticker2, ticker3]):
                return []
                
            # Get current prices
            price1 = ticker1.get('price', 0)
            price2 = ticker2.get('price', 0)
            price3 = ticker3.get('price', 0)
            
            if not all([price1, price2, price3]):
                return []
                
            # Verify opportunity still exists
            profit_percent = (1 / price1) * price2 * price3 - 1
            profit_percent *= 100  # Convert to percentage
            
            if profit_percent < self.triangular_min_profit:
                return []
                
            # Create signals for each step of the triangle
            # Step 1: Buy first pair
            signal1 = TradeSignal(
                symbol=symbol1,
                side='buy',
                price=price1,
                order_type='market'
            )
            
            # Step 2: Buy second pair
            signal2 = TradeSignal(
                symbol=symbol2,
                side='buy',
                price=price2,
                order_type='market'
            )
            
            # Step 3: Sell third pair
            signal3 = TradeSignal(
                symbol=symbol3,
                side='sell',
                price=price3,
                order_type='market'
            )
            
            signals.extend([signal1, signal2, signal3])
            logger.info(f"Generated triangular arbitrage signals for {symbol1} -> {symbol2} -> {symbol3}, profit: {profit_percent:.2f}%")
            
        except Exception as e:
            logger.error(f"Error generating triangular arbitrage signals: {str(e)}")
            
        return signals
        
    def _generate_cross_exchange_signals(self, opportunity: Dict[str, Any]) -> List[TradeSignal]:
        """
        Generate signals for cross-exchange arbitrage
        """
        # This is a placeholder as we don't have other exchanges initialized
        return []