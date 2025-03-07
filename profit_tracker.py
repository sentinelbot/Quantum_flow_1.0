# profit/profit_tracker.py
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ProfitTracker:
    """
    Comprehensive Profit Tracking and Performance Analysis System

    Provides advanced tracking and reporting of trading performance, 
    including profit calculations, strategy analysis, and comprehensive 
    financial insights for trading activities.
    """

    def __init__(
        self, 
        user_repository=None, 
        trade_repository=None, 
        analytics_repository=None, 
        fee_calculator=None,
        config=None,
        notification_manager=None
    ):
        """
        Initialize Profit Tracking System with configurable dependencies.

        Args:
            user_repository (UserRepository): Repository for user data management
            trade_repository (TradeRepository): Repository for trade data management
            analytics_repository (AnalyticsRepository): Repository for performance analytics
            fee_calculator (FeeCalculator): System for calculating trading fees
            config (dict, optional): Configuration settings for profit tracking
            notification_manager (NotificationManager): System for sending notifications
        """
        # Initialize repositories and dependencies
        self.user_repository = user_repository
        self.trade_repository = trade_repository
        self.analytics_repository = analytics_repository
        self.fee_calculator = fee_calculator
        self.notification_manager = notification_manager
        self.config = config or {}

        logger.info("Profit Tracker initialized successfully")

    def generate_daily_report(self):
        """
        Generate comprehensive daily performance reports for all users.
        
        Calculates key performance metrics, creates formatted reports,
        and distributes them to users and administrators. Reports include
        profit/loss summaries, fee analysis, and performance benchmarking.
        
        Returns:
            bool: True if report generation was successful
        """
        try:
            logger.info("Generating daily profit reports")
            
            # Get date range for reporting
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
            
            # Get active users
            users = self._get_active_users()
            
            if not users:
                logger.info("No active users found for profit reporting")
                return True
                
            report_count = 0
            
            for user in users:
                try:
                    # Generate user-specific report
                    report = self._generate_user_report(user.id, start_date, end_date)
                    
                    if report:
                        # Store report
                        self._store_report(user.id, report)
                        
                        # Send report to user
                        self._send_report_notification(user.id, report)
                        
                        report_count += 1
                        
                except Exception as e:
                    logger.error(f"Error generating report for user {user.id}: {str(e)}")
            
            # Generate executive summary for administrators
            if report_count > 0:
                self._generate_admin_summary(start_date, end_date)
            
            logger.info(f"Daily profit reports generated for {report_count} users")
            return True
            
        except Exception as e:
            logger.error(f"Error generating daily profit reports: {str(e)}")
            return False

    def record_trade_profit(self, user_id: int, trade_id: int, 
                             profit: float, profit_percentage: float) -> bool:
        """
        Record and process profit from a completed trade.

        Manages comprehensive trade profit recording, including:
        - Updating trade details
        - Tracking user performance metrics
        - Recording analytics data

        Args:
            user_id (int): Unique user identifier
            trade_id (int): Unique trade identifier
            profit (float): Total profit amount
            profit_percentage (float): Profit percentage

        Returns:
            bool: Indicates successful profit recording
        """
        try:
            # Validate repository dependencies
            if not self._validate_repositories():
                logger.error("Repositories not fully configured")
                return False

            # Update trade profit details
            if not self._update_trade_profit(trade_id, profit, profit_percentage):
                return False

            # Update user performance metrics
            if not self._update_user_performance(user_id, profit):
                return False

            # Record performance in analytics
            self._record_performance_analytics(user_id, profit)

            logger.info(f"Profit recorded for trade {trade_id}: {profit}")
            return True

        except Exception as e:
            logger.error(f"Error recording trade profit: {str(e)}")
            return False

    def _validate_repositories(self) -> bool:
        """
        Validate the availability of required repositories.

        Returns:
            bool: Indicates whether all necessary repositories are configured
        """
        required_repositories = [
            self.user_repository, 
            self.trade_repository, 
            self.analytics_repository
        ]
        return all(required_repositories)

    def _update_trade_profit(self, trade_id: int, profit: float, profit_percentage: float) -> bool:
        """
        Update trade profit details in the repository.

        Args:
            trade_id (int): Unique trade identifier
            profit (float): Total profit amount
            profit_percentage (float): Profit percentage

        Returns:
            bool: Indicates successful trade update
        """
        try:
            return self.trade_repository.update_trade(
                trade_id=trade_id,
                profit=profit,
                profit_percentage=profit_percentage
            )
        except Exception as e:
            logger.error(f"Error updating trade profit: {str(e)}")
            return False

    def _update_user_performance(self, user_id: int, profit: float) -> bool:
        """
        Update comprehensive user performance metrics.

        Args:
            user_id (int): Unique user identifier
            profit (float): Trade profit amount

        Returns:
            bool: Indicates successful user performance update
        """
        try:
            user = self.user_repository.get_user_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            # Calculate performance metrics
            new_total_profit = user.total_profit + profit
            win_count = user.win_count + (1 if profit > 0 else 0)
            loss_count = user.loss_count + (1 if profit <= 0 else 0)

            return self.user_repository.update_user(
                user_id=user_id,
                total_profit=new_total_profit,
                win_count=win_count,
                loss_count=loss_count
            )
        except Exception as e:
            logger.error(f"Error updating user performance: {str(e)}")
            return False

    def _record_performance_analytics(self, user_id: int, profit: float):
        """
        Record detailed performance analytics for the user.

        Args:
            user_id (int): Unique user identifier
            profit (float): Trade profit amount
        """
        try:
            user = self.user_repository.get_user_by_id(user_id)
            if not user:
                return

            win_count = user.win_count
            loss_count = user.loss_count
            total_trades = win_count + loss_count

            win_rate = (win_count / total_trades) if total_trades > 0 else 0

            self.analytics_repository.add_performance_record(
                user_id=user_id,
                win_rate=win_rate,
                total_profit=user.total_profit,
                total_trades=total_trades,
                timestamp=int(datetime.now().timestamp())
            )
        except Exception as e:
            logger.error(f"Error recording performance analytics: {str(e)}")

    def get_user_profit_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive profit summary for a user.

        Provides detailed insights into trading performance, 
        including:
        - Overall profit metrics
        - Win/loss statistics
        - Temporal profit analysis
        - Strategy performance breakdown

        Args:
            user_id (int): Unique user identifier

        Returns:
            Dict[str, Any]: Comprehensive profit summary
        """
        try:
            # Retrieve user trades
            trades = self.trade_repository.get_trades_by_user(user_id, limit=1000)
            
            # Calculate performance metrics
            win_trades = [t for t in trades if t.profit and t.profit > 0]
            loss_trades = [t for t in trades if t.profit and t.profit <= 0]
            
            win_count = len(win_trades)
            loss_count = len(loss_trades)
            total_trades = win_count + loss_count
            
            win_rate = win_count / total_trades if total_trades > 0 else 0
            
            total_profit = sum(t.profit for t in trades if t.profit)
            avg_win = sum(t.profit for t in win_trades) / win_count if win_count > 0 else 0
            avg_loss = sum(t.profit for t in loss_trades) / loss_count if loss_count > 0 else 0
            
            # Temporal profit analysis
            now = datetime.now()
            today_start = datetime(now.year, now.month, now.day)
            week_start = now - timedelta(days=now.weekday())
            month_start = datetime(now.year, now.month, 1)
            
            today_profit = sum(t.profit for t in trades if t.closed_at and t.closed_at >= today_start and t.profit)
            week_profit = sum(t.profit for t in trades if t.closed_at and t.closed_at >= week_start and t.profit)
            month_profit = sum(t.profit for t in trades if t.closed_at and t.closed_at >= month_start and t.profit)
            
            # Strategy and symbol performance
            strategy_profit = self._calculate_strategy_performance(trades)
            
            return {
                'total_profit': total_profit,
                'win_count': win_count,
                'loss_count': loss_count,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'today_profit': today_profit,
                'week_profit': week_profit,
                'month_profit': month_profit,
                'strategy_profit': strategy_profit
            }
        
        except Exception as e:
            logger.error(f"Error generating profit summary: {str(e)}")
            return {}

    def calculate_drawdown(self, user_id: int) -> Dict[str, float]:
        """
        Calculate advanced drawdown metrics for a user.

        Analyzes the maximum and current drawdown based on 
        historical performance data.

        Args:
            user_id (int): Unique user identifier

        Returns:
            Dict[str, float]: Drawdown metrics
        """
        try:
            # Retrieve performance records
            records = self.analytics_repository.get_performance_by_date_range(
                start_date=datetime.now() - timedelta(days=365),
                end_date=datetime.now()
            )
            
            if not records:
                return {
                    'max_drawdown': 0,
                    'current_drawdown': 0
                }
            
            # Extract equity values
            equity_values = [record.data.get('equity', 0) for record in records]
            
            if not equity_values:
                return {
                    'max_drawdown': 0,
                    'current_drawdown': 0
                }
            
            # Calculate drawdown metrics
            peak = equity_values[0]
            max_drawdown = 0
            
            for value in equity_values:
                peak = max(peak, value)
                drawdown = (peak - value) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calculate current drawdown
            current_value = equity_values[-1]
            current_drawdown = (peak - current_value) / peak if peak > 0 else 0
            
            return {
                'max_drawdown': max_drawdown,
                'current_drawdown': current_drawdown
            }
        
        except Exception as e:
            logger.error(f"Error calculating drawdown: {str(e)}")
            return {
                'max_drawdown': 0,
                'current_drawdown': 0
            }

    def _calculate_strategy_performance(self, trades: List) -> Dict[str, float]:
        """
        Calculate profit performance by trading strategy.

        Args:
            trades (List): List of user trades

        Returns:
            Dict[str, float]: Profit breakdown by strategy
        """
        strategy_profit = {}
        for trade in trades:
            if trade.profit and trade.strategy:
                strategy_profit[trade.strategy] = strategy_profit.get(trade.strategy, 0) + trade.profit
        return strategy_profit
        
    def _get_active_users(self):
        """
        Get list of active users for profit reporting.
        
        Returns:
            list: Active user objects
        """
        try:
            if not self.user_repository:
                logger.warning("User repository not available for profit reporting")
                return []
                
            return self.user_repository.get_active_users()
            
        except Exception as e:
            logger.error(f"Error retrieving active users: {str(e)}")
            return []

    def _generate_user_report(self, user_id, start_date, end_date):
        """
        Generate profit report for a specific user.
        
        Args:
            user_id: User identifier
            start_date: Report period start date
            end_date: Report period end date
            
        Returns:
            dict: Profit report data
        """
        try:
            # Get trades for the specified period
            trades = self._get_user_trades(user_id, start_date, end_date)
            
            if not trades:
                logger.info(f"No trades found for user {user_id} in reporting period")
                return None
                
            # Calculate basic metrics
            total_trades = len(trades)
            profitable_trades = sum(1 for trade in trades if trade.profit > 0)
            losing_trades = total_trades - profitable_trades
            
            # Calculate profit metrics
            gross_profit = sum(trade.profit for trade in trades if trade.profit > 0)
            gross_loss = sum(trade.profit for trade in trades if trade.profit < 0)
            net_profit = gross_profit + gross_loss
            
            # Calculate fees
            total_fees = self._calculate_total_fees(trades)
            
            # Calculate percentage values
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
            
            # Generate strategy breakdown
            strategy_performance = self._calculate_strategy_breakdown(trades)
            
            # Generate asset breakdown
            asset_performance = self._calculate_asset_breakdown(trades)
            
            # Create report
            report = {
                'user_id': user_id,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'net_profit': net_profit,
                'profit_factor': profit_factor,
                'total_fees': total_fees,
                'net_after_fees': net_profit - total_fees,
                'strategy_performance': strategy_performance,
                'asset_performance': asset_performance,
                'timestamp': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report for user {user_id}: {str(e)}")
            return None

    def _calculate_total_fees(self, trades):
        """
        Calculate total fees for a set of trades.
        
        Args:
            trades: List of trades
            
        Returns:
            float: Total fees
        """
        try:
            total_fees = 0
            
            for trade in trades:
                # Use fee calculator if available
                if self.fee_calculator:
                    fee = self.fee_calculator.calculate_fee(
                        price=trade.entry_price,
                        quantity=trade.quantity,
                        exchange=trade.exchange
                    )
                    total_fees += fee
                else:
                    # Fallback to basic fee calculation
                    total_fees += trade.fee if hasattr(trade, 'fee') else 0
                    
            return total_fees
            
        except Exception as e:
            logger.error(f"Error calculating fees: {str(e)}")
            return 0

    def _calculate_strategy_breakdown(self, trades):
        """
        Calculate performance breakdown by strategy.
        
        Args:
            trades: List of trades
            
        Returns:
            dict: Strategy performance metrics
        """
        try:
            strategy_metrics = {}
            
            # Group trades by strategy
            for trade in trades:
                strategy = trade.strategy_name if hasattr(trade, 'strategy_name') else 'unknown'
                
                if strategy not in strategy_metrics:
                    strategy_metrics[strategy] = {
                        'trade_count': 0,
                        'win_count': 0,
                        'lose_count': 0,
                        'profit': 0,
                        'loss': 0,
                        'net_profit': 0
                    }
                    
                metrics = strategy_metrics[strategy]
                metrics['trade_count'] += 1
                
                if trade.profit > 0:
                    metrics['win_count'] += 1
                    metrics['profit'] += trade.profit
                else:
                    metrics['lose_count'] += 1
                    metrics['loss'] += trade.profit
                    
                metrics['net_profit'] += trade.profit
            
            # Calculate derived metrics
            for strategy, metrics in strategy_metrics.items():
                metrics['win_rate'] = (metrics['win_count'] / metrics['trade_count'] * 100) if metrics['trade_count'] > 0 else 0
                metrics['profit_factor'] = abs(metrics['profit'] / metrics['loss']) if metrics['loss'] != 0 else float('inf')
                
            return strategy_metrics
            
        except Exception as e:
            logger.error(f"Error calculating strategy breakdown: {str(e)}")
            return {}

    def _calculate_asset_breakdown(self, trades):
        """
        Calculate performance breakdown by asset.
        
        Args:
            trades: List of trades
            
        Returns:
            dict: Asset performance metrics
        """
        try:
            asset_metrics = {}
            
            # Group trades by asset
            for trade in trades:
                asset = trade.symbol.split('/')[0] if hasattr(trade, 'symbol') and '/' in trade.symbol else 'unknown'
                
                if asset not in asset_metrics:
                    asset_metrics[asset] = {
                        'trade_count': 0,
                        'win_count': 0,
                        'lose_count': 0,
                        'profit': 0,
                        'loss': 0,
                        'net_profit': 0
                    }
                    
                metrics = asset_metrics[asset]
                metrics['trade_count'] += 1
                
                if trade.profit > 0:
                    metrics['win_count'] += 1
                    metrics['profit'] += trade.profit
                else:
                    metrics['lose_count'] += 1
                    metrics['loss'] += trade.profit
                    
                metrics['net_profit'] += trade.profit
            
            # Calculate derived metrics
            for asset, metrics in asset_metrics.items():
                metrics['win_rate'] = (metrics['win_count'] / metrics['trade_count'] * 100) if metrics['trade_count'] > 0 else 0
                metrics['profit_factor'] = abs(metrics['profit'] / metrics['loss']) if metrics['loss'] != 0 else float('inf')
                
            return asset_metrics
            
        except Exception as e:
            logger.error(f"Error calculating asset breakdown: {str(e)}")
            return {}

    def _get_user_trades(self, user_id, start_date, end_date):
        """
        Get user's trades for a specific time period.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            
        Returns:
            list: Trades in the specified period
        """
        try:
            if not self.trade_repository:
                logger.warning("Trade repository not available")
                return []
                
            return self.trade_repository.get_trades_by_user_and_date_range(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(f"Error retrieving trades for user {user_id}: {str(e)}")
            return []

    def _store_report(self, user_id, report):
        """
        Store profit report for future reference.
        
        Args:
            user_id: User identifier
            report: Report data
        """
        try:
            # In a production system, this would store to a database
            # For now, we'll just log it
            logger.info(f"Stored profit report for user {user_id}")
            
            # If analytics repository is available, store the report
            if self.analytics_repository:
                self.analytics_repository.store_profit_report(
                    user_id=user_id,
                    report_data=report,
                    report_type="daily",
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Error storing profit report for user {user_id}: {str(e)}")

    def _send_report_notification(self, user_id, report):
        """
        Send profit report notification to user.
        
        Args:
            user_id: User identifier
            report: Report data
        """
        try:
            if not self.notification_manager:
                return
                
            # Format report for notification
            message = self._format_report_message(report)
            
            # Send notification
            self.notification_manager.send_notification(
                user_id=user_id,
                message=message,
                notification_type="profit_report"
            )
            
        except Exception as e:
            logger.error(f"Error sending profit report notification to user {user_id}: {str(e)}")

    def _format_report_message(self, report):
        """
        Format profit report for notification.
        
        Args:
            report: Report data
            
        Returns:
            str: Formatted message
        """
        try:
            # Format date range
            start_date = datetime.fromisoformat(report['period_start']).strftime('%Y-%m-%d')
            end_date = datetime.fromisoformat(report['period_end']).strftime('%Y-%m-%d')
            
            # Create message
            message = f"Daily Profit Report: {start_date} to {end_date}\n\n"
            
            # Add summary metrics
            message += f"Total Trades: {report['total_trades']}\n"
            message += f"Win Rate: {report['win_rate']:.2f}%\n"
            message += f"Net Profit: {report['net_profit']:.2f}\n"
            message += f"Fees: {report['total_fees']:.2f}\n"
            message += f"Net After Fees: {report['net_after_fees']:.2f}\n\n"
            
            # Add top performing strategy
            if report['strategy_performance']:
                top_strategy = max(
                    report['strategy_performance'].items(),
                    key=lambda x: x[1]['net_profit']
                )
                message += f"Top Strategy: {top_strategy[0]} ({top_strategy[1]['net_profit']:.2f})\n"
            
            # Add top performing asset
            if report['asset_performance']:
                top_asset = max(
                    report['asset_performance'].items(),
                    key=lambda x: x[1]['net_profit']
                )
                message += f"Top Asset: {top_asset[0]} ({top_asset[1]['net_profit']:.2f})\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting report message: {str(e)}")
            return "Daily Profit Report is available"

    def _generate_admin_summary(self, start_date, end_date):
        """
        Generate executive summary for administrators.
        
        Args:
            start_date: Report period start date
            end_date: Report period end date
        """
        try:
            # Get platform-wide metrics
            total_profit = self._calculate_platform_total_profit(start_date, end_date)
            total_trades = self._calculate_platform_total_trades(start_date, end_date)
            total_fees = self._calculate_platform_total_fees(start_date, end_date)
            
            # Create admin report
            admin_report = {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_trades': total_trades,
                'total_profit': total_profit,
                'total_fees': total_fees,
                'net_platform_profit': total_profit - total_fees,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store admin report
            if self.analytics_repository:
                self.analytics_repository.store_admin_report(
                    report_data=admin_report,
                    report_type="daily_summary",
                    timestamp=datetime.now()
                )
            
            # Send notification to admins
            if self.notification_manager:
                admin_users = self.user_repository.get_admin_users() if self.user_repository else []
                
                for admin in admin_users:
                    self.notification_manager.send_notification(
                        user_id=admin.id,
                        message=self._format_admin_report_message(admin_report),
                        notification_type="admin_report"
                    )
            
            # Log summary
            logger.info(
                f"Platform Summary: {total_trades} trades, "
                f"{total_profit:.2f} profit, {total_fees:.2f} fees"
            )
            
        except Exception as e:
            logger.error(f"Error generating admin summary: {str(e)}")

    def _format_admin_report_message(self, report):
        """
        Format admin report for notification.
        
        Args:
            report: Report data
            
        Returns:
            str: Formatted message
        """
        try:
            # Format date range
            start_date = datetime.fromisoformat(report['period_start']).strftime('%Y-%m-%d')
            end_date = datetime.fromisoformat(report['period_end']).strftime('%Y-%m-%d')
            
            # Create message
            message = f"Daily Platform Summary: {start_date} to {end_date}\n\n"
            
            # Add summary metrics
            message += f"Total Trades: {report['total_trades']}\n"
            message += f"Total Profit: {report['total_profit']:.2f}\n"
            message += f"Total Fees: {report['total_fees']:.2f}\n"
            message += f"Net Platform Profit: {report['net_platform_profit']:.2f}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting admin report message: {str(e)}")
            return "Daily Platform Summary is available"

    def _calculate_platform_total_profit(self, start_date, end_date):
        """
        Calculate total platform profit for a period.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            float: Total profit
        """
        try:
            if not self.trade_repository:
                return 0
                
            trades = self.trade_repository.get_trades_by_date_range(
                start_date=start_date,
                end_date=end_date
            )
            
            return sum(trade.profit for trade in trades if hasattr(trade, 'profit'))
            
        except Exception as e:
            logger.error(f"Error calculating platform total profit: {str(e)}")
            return 0

    def _calculate_platform_total_trades(self, start_date, end_date):
        """
        Calculate total platform trades for a period.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            int: Total trades
        """
        try:
            if not self.trade_repository:
                return 0
                
            trades = self.trade_repository.get_trades_by_date_range(
                start_date=start_date,
                end_date=end_date
            )
            
            return len(trades)
            
        except Exception as e:
            logger.error(f"Error calculating platform total trades: {str(e)}")
            return 0

    def _calculate_platform_total_fees(self, start_date, end_date):
        """
        Calculate total platform fees for a period.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            float: Total fees
        """
        try:
            if not self.trade_repository:
                return 0
                
            trades = self.trade_repository.get_trades_by_date_range(
                start_date=start_date,
                end_date=end_date
            )
            
            return self._calculate_total_fees(trades)
            
        except Exception as e:
            logger.error(f"Error calculating platform total fees: {str(e)}")
            return 0