# analysis/backtester.py
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable
import time
import json
from datetime import datetime, timedelta

from exchange.abstract_exchange import AbstractExchange, TradeSignal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class BacktestResult:
    """
    Backtest result container
    """
    def __init__(self):
        self.trades = []
        self.equity_curve = []
        self.stats = {}
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary
        """
        return {
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'stats': self.stats
        }
        
    def to_json(self) -> str:
        """
        Convert to JSON string
        """
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BacktestResult':
        """
        Create from dictionary
        """
        result = cls()
        result.trades = data.get('trades', [])
        result.equity_curve = data.get('equity_curve', [])
        result.stats = data.get('stats', {})
        return result
        
    @classmethod
    def from_json(cls, json_str: str) -> 'BacktestResult':
        """
        Create from JSON string
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

class Backtester:
    """
    Backtesting system for trading strategies
    """
    def __init__(self, exchange: AbstractExchange):
        self.exchange = exchange
        
        logger.info("Backtester initialized")
        
    def run_backtest(self, strategy_class: type, symbol: str, timeframe: str, 
                  start_date: str, end_date: str, initial_capital: float = 10000.0,
                  config: Dict[str, Any] = None) -> BacktestResult:
        """
        Run backtest for a strategy
        
        Args:
            strategy_class: Strategy class to test
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Initial capital
            config: Strategy configuration
            
        Returns:
            BacktestResult: Backtest results
        """
        try:
            # Get historical data
            data = self._get_historical_data(symbol, timeframe, start_date, end_date)
            
            if not data or len(data) < 50:
                logger.warning(f"Insufficient data for backtest: {symbol} {timeframe} {start_date} to {end_date}")
                return BacktestResult()
                
            # Convert to pandas DataFrame
            df = pd.DataFrame(data)
            
            # Initialize backtest state
            capital = initial_capital
            position = 0
            entry_price = 0
            entry_time = None
            trades = []
            equity_curve = []
            
            # Initialize strategy
            if config is None:
                config = {}
                
            config['symbols'] = [symbol]
            config['timeframes'] = [timeframe]
            
            # Create mock user and risk manager for strategy
            mock_user = type('MockUser', (), {'id': 0, 'risk_level': 'medium'})
            mock_risk_manager = type('MockRiskManager', (), {
                'validate_signal': lambda user, signal: signal,
                'calculate_stop_loss': lambda price, side, percent: price * 0.95 if side == 'buy' else price * 1.05,
                'calculate_take_profit': lambda price, side, percent: price * 1.05 if side == 'buy' else price * 0.95
            })
            
            strategy = strategy_class(
                exchange=self.exchange,
                user=mock_user(),
                risk_manager=mock_risk_manager(),
                config=config
            )
            
            # Run backtest
            for i in range(50, len(df)):
                # Get current candle
                current_time = df.iloc[i]['timestamp']
                current_price = df.iloc[i]['close']
                
                # Update strategy with historical data
                historical_data = df.iloc[:i+1].to_dict('records')
                strategy.market_data = {symbol: {timeframe: historical_data}}
                
                # Generate signals
                signals = strategy._generate_signals()
                
                # Process signals
                for signal in signals:
                    # Skip if signal is for a different symbol
                    if signal.symbol != symbol:
                        continue
                        
                    # Process signal based on current position
                    if position == 0:
                        # No position, check for entry signals
                        if signal.side == 'buy':
                            # Enter long position
                            position = 1
                            entry_price = current_price
                            entry_time = current_time
                            size = capital / current_price
                            
                            # Record trade
                            trades.append({
                                'type': 'entry',
                                'side': 'buy',
                                'time': current_time,
                                'price': current_price,
                                'size': size,
                                'value': size * current_price
                            })
                            
                        elif signal.side == 'sell':
                            # Enter short position
                            position = -1
                            entry_price = current_price
                            entry_time = current_time
                            size = capital / current_price
                            
                            # Record trade
                            trades.append({
                                'type': 'entry',
                                'side': 'sell',
                                'time': current_time,
                                'price': current_price,
                                'size': size,
                                'value': size * current_price
                            })
                            
                    elif position == 1:
                        # Long position, check for exit signals
                        if signal.side == 'sell':
                            # Exit long position
                            profit = (current_price - entry_price) / entry_price
                            capital *= (1 + profit)
                            position = 0
                            
                            # Record trade
                            trades.append({
                                'type': 'exit',
                                'side': 'sell',
                                'time': current_time,
                                'price': current_price,
                                'size': size,
                                'value': size * current_price,
                                'profit': profit,
                                'profit_amount': size * (current_price - entry_price)
                            })
                            
                    elif position == -1:
                        # Short position, check for exit signals
                        if signal.side == 'buy':
                            # Exit short position
                            profit = (entry_price - current_price) / entry_price
                            capital *= (1 + profit)
                            position = 0
                            
                            # Record trade
                            trades.append({
                                'type': 'exit',
                                'side': 'buy',
                                'time': current_time,
                                'price': current_price,
                                'size': size,
                                'value': size * current_price,
                                'profit': profit,
                                'profit_amount': size * (entry_price - current_price)
                            })
                            
                # Update equity curve
                current_equity = capital
                if position != 0:
                    # Add unrealized profit/loss
                    if position == 1:
                        profit = (current_price - entry_price) / entry_price
                    else:
                        profit = (entry_price - current_price) / entry_price
                        
                    current_equity = capital * (1 + profit)
                    
                equity_curve.append({
                    'time': current_time,
                    'equity': current_equity
                })
                
            # Close any open position at the end
            if position != 0:
                current_price = df.iloc[-1]['close']
                current_time = df.iloc[-1]['timestamp']
                
                if position == 1:
                    # Exit long position
                    profit = (current_price - entry_price) / entry_price
                    capital *= (1 + profit)
                    
                    # Record trade
                    trades.append({
                        'type': 'exit',
                        'side': 'sell',
                        'time': current_time,
                        'price': current_price,
                        'size': size,
                        'value': size * current_price,
                        'profit': profit,
                        'profit_amount': size * (current_price - entry_price)
                    })
                    
                elif position == -1:
                    # Exit short position
                    profit = (entry_price - current_price) / entry_price
                    capital *= (1 + profit)
                    
                    # Record trade
                    trades.append({
                        'type': 'exit',
                        'side': 'buy',
                        'time': current_time,
                        'price': current_price,
                        'size': size,
                        'value': size * current_price,
                        'profit': profit,
                        'profit_amount': size * (entry_price - current_price)
                    })
                    
            # Calculate statistics
            stats = self._calculate_stats(trades, equity_curve, initial_capital)
            
            # Create result
            result = BacktestResult()
            result.trades = trades
            result.equity_curve = equity_curve
            result.stats = stats
            
            return result
            
        except Exception as e:
            logger.error(f"Error running backtest: {str(e)}")
            return BacktestResult()
            
    def _get_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get historical data for backtest
        
        Args:
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List[Dict[str, Any]]: Historical data
        """
        try:
            # Convert dates to timestamps
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())
            
            # Get data from exchange (in a real implementation, this would handle pagination)
            candles = self.exchange.get_historical_data(symbol, timeframe, limit=1000)
            
            # Filter by date range
            filtered_candles = [
                candle for candle in candles
                if start_timestamp <= candle['timestamp'] <= end_timestamp
            ]
            
            return filtered_candles
            
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
            return []
            
    def _calculate_stats(self, trades: List[Dict[str, Any]], equity_curve: List[Dict[str, Any]], 
                       initial_capital: float) -> Dict[str, Any]:
        """
        Calculate backtest statistics
        
        Args:
            trades: List of trades
            equity_curve: Equity curve
            initial_capital: Initial capital
            
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            # Extract closed trades
            closed_trades = [trade for trade in trades if trade.get('type') == 'exit']
            
            if not closed_trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'total_return': 0,
                    'annualized_return': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0,
                    'sortino_ratio': 0
                }
                
            # Calculate basic statistics
            total_trades = len(closed_trades)
            winning_trades = len([trade for trade in closed_trades if trade.get('profit', 0) > 0])
            losing_trades = len([trade for trade in closed_trades if trade.get('profit', 0) <= 0])
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calculate profit metrics
            gross_profit = sum([trade.get('profit_amount', 0) for trade in closed_trades if trade.get('profit', 0) > 0])
            gross_loss = sum([trade.get('profit_amount', 0) for trade in closed_trades if trade.get('profit', 0) <= 0])
            
            profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
            
            # Calculate returns
            final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
            total_return = (final_equity - initial_capital) / initial_capital * 100
            
            # Calculate drawdown
            max_equity = initial_capital
            max_drawdown = 0
            
            for point in equity_curve:
                equity = point['equity']
                max_equity = max(max_equity, equity)
                drawdown = (max_equity - equity) / max_equity * 100
                max_drawdown = max(max_drawdown, drawdown)
                
            # Calculate annualized return
            if equity_curve:
                start_time = equity_curve[0]['time']
                end_time = equity_curve[-1]['time']
                
                days = (end_time - start_time) / 86400  # Convert seconds to days
                years = days / 365
                
                annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
            else:
                annualized_return = 0
                
            # Calculate risk-adjusted returns
            if len(equity_curve) > 1:
                # Calculate daily returns
                daily_returns = []
                prev_equity = initial_capital
                
                for point in equity_curve:
                    equity = point['equity']
                    daily_return = (equity - prev_equity) / prev_equity
                    daily_returns.append(daily_return)
                    prev_equity = equity
                    
                # Calculate Sharpe ratio (risk-free rate = 0 for simplicity)
                mean_return = np.mean(daily_returns)
                std_return = np.std(daily_returns)
                
                sharpe_ratio = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
                
                # Calculate Sortino ratio (downside deviation)
                negative_returns = [r for r in daily_returns if r < 0]
                downside_deviation = np.std(negative_returns) if negative_returns else 0
                
                sortino_ratio = mean_return / downside_deviation * np.sqrt(252) if downside_deviation > 0 else 0
            else:
                sharpe_ratio = 0
                sortino_ratio = 0
                
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'net_profit': gross_profit + gross_loss,
                'total_return': total_return,
                'annualized_return': annualized_return,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return {}
            
    def optimize_strategy(self, strategy_class: type, symbol: str, timeframe: str, 
                       start_date: str, end_date: str, initial_capital: float = 10000.0,
                       parameters: Dict[str, List[Any]] = None) -> Dict[str, Any]:
        """
        Optimize strategy parameters using grid search
        
        Args:
            strategy_class: Strategy class to optimize
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            initial_capital: Initial capital
            parameters: Dictionary of parameters to optimize
            
        Returns:
            Dict[str, Any]: Best parameters and results
        """
        try:
            if parameters is None or not parameters:
                logger.warning("No parameters provided for optimization")
                return {}
                
            # Generate parameter combinations
            param_combinations = self._generate_param_combinations(parameters)
            
            if not param_combinations:
                return {}
                
            # Run backtest for each parameter combination
            results = []
            
            for params in param_combinations:
                # Create config with parameters
                config = {
                    'parameters': params
                }
                
                # Run backtest
                result = self.run_backtest(
                    strategy_class=strategy_class,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    config=config
                )
                
                # Store results
                results.append({
                    'parameters': params,
                    'stats': result.stats
                })
                
            # Find best parameters based on different metrics
            best_return = max(results, key=lambda x: x['stats'].get('total_return', 0))
            best_sharpe = max(results, key=lambda x: x['stats'].get('sharpe_ratio', 0))
            best_sortino = max(results, key=lambda x: x['stats'].get('sortino_ratio', 0))
            best_profit_factor = max(results, key=lambda x: x['stats'].get('profit_factor', 0))
            
            return {
                'best_return': best_return,
                'best_sharpe': best_sharpe,
                'best_sortino': best_sortino,
                'best_profit_factor': best_profit_factor,
                'all_results': results
            }
            
        except Exception as e:
            logger.error(f"Error optimizing strategy: {str(e)}")
            return {}
            
    def _generate_param_combinations(self, parameters: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Generate all combinations of parameters
        
        Args:
            parameters: Dictionary of parameters to optimize
            
        Returns:
            List[Dict[str, Any]]: List of parameter combinations
        """
        try:
            # Basic implementation using recursive approach
            def recursive_combinations(params, keys, current_idx, current_params):
                if current_idx == len(keys):
                    return [current_params.copy()]
                    
                key = keys[current_idx]
                values = params[key]
                result = []
                
                for value in values:
                    current_params[key] = value
                    result.extend(recursive_combinations(params, keys, current_idx + 1, current_params))
                    
                return result
                
            keys = list(parameters.keys())
            return recursive_combinations(parameters, keys, 0, {})
            
        except Exception as e:
            logger.error(f"Error generating parameter combinations: {str(e)}")
            return []
            
    def run_walk_forward_analysis(self, strategy_class: type, symbol: str, timeframe: str, 
                               start_date: str, end_date: str, train_period_days: int = 180,
                               test_period_days: int = 60, parameters: Dict[str, List[Any]] = None,
                               initial_capital: float = 10000.0) -> Dict[str, Any]:
        """
        Run walk-forward analysis (train on historical data, test on out-of-sample data)
        
        Args:
            strategy_class: Strategy class to analyze
            symbol: Trading pair symbol
            timeframe: Chart timeframe
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            train_period_days: Training period in days
            test_period_days: Testing period in days
            parameters: Dictionary of parameters to optimize
            initial_capital: Initial capital
            
        Returns:
            Dict[str, Any]: Walk-forward analysis results
        """
        try:
            if parameters is None or not parameters:
                logger.warning("No parameters provided for walk-forward analysis")
                return {}
                
            # Parse dates
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Calculate periods
            total_days = (end - start).days
            if total_days < train_period_days + test_period_days:
                logger.warning("Insufficient data for walk-forward analysis")
                return {}
                
            # Generate periods
            periods = []
            current_start = start
            
            while current_start + timedelta(days=train_period_days + test_period_days) <= end:
                train_end = current_start + timedelta(days=train_period_days)
                test_end = train_end + timedelta(days=test_period_days)
                
                periods.append({
                    'train_start': current_start.strftime('%Y-%m-%d'),
                    'train_end': train_end.strftime('%Y-%m-%d'),
                    'test_start': train_end.strftime('%Y-%m-%d'),
                    'test_end': test_end.strftime('%Y-%m-%d')
                })
                
                current_start = train_end
                
            # Run analysis for each period
            results = []
            
            for period in periods:
                # Optimize on training data
                optimization_result = self.optimize_strategy(
                    strategy_class=strategy_class,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=period['train_start'],
                    end_date=period['train_end'],
                    parameters=parameters,
                    initial_capital=initial_capital
                )
                
                if not optimization_result:
                    continue
                    
                # Get best parameters (using Sharpe ratio)
                best_params = optimization_result.get('best_sharpe', {}).get('parameters', {})
                
                if not best_params:
                    continue
                    
                # Test on out-of-sample data
                test_config = {
                    'parameters': best_params
                }
                
                test_result = self.run_backtest(
                    strategy_class=strategy_class,
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=period['test_start'],
                    end_date=period['test_end'],
                    initial_capital=initial_capital,
                    config=test_config
                )
                
                # Store results
                results.append({
                    'period': period,
                    'best_parameters': best_params,
                    'train_stats': optimization_result.get('best_sharpe', {}).get('stats', {}),
                    'test_stats': test_result.stats
                })
                
            # Calculate overall performance
            total_return = 0
            total_trades = 0
            winning_trades = 0
            
            for result in results:
                test_stats = result.get('test_stats', {})
                total_return += test_stats.get('total_return', 0)
                total_trades += test_stats.get('total_trades', 0)
                winning_trades += test_stats.get('winning_trades', 0)
                
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            return {
                'periods': results,
                'summary': {
                    'total_periods': len(results),
                    'total_return': total_return,
                    'average_return': total_return / len(results) if results else 0,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'win_rate': win_rate
                }
            }
            
        except Exception as e:
            logger.error(f"Error running walk-forward analysis: {str(e)}")
            return {}