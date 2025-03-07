import logging
from telebot import types
from datetime import datetime

# Setup logger
logger = logging.getLogger(__name__)

# Import required services
from market_data.price_service import PriceService
from profit.stats_service import StatsService
from profit.profit_tracker import ProfitTracker
from reporting.report_generator import ReportGenerator
from services.pairs_manager import PairsManager
from services.strategy_manager import StrategyManager
from services.user_trading_manager import UserTradingManager
from notification.notification_manager import NotificationManager
from market_data.market_analysis import MarketAnalysisService
from database.repository.position_repository import PositionRepository
from database.repository.trade_repository import TradeRepository

def _handle_mode_command(self, message):
    """Handle /mode command to switch between paper and live trading"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Parse arguments
        args = message.text.split()
        
        if len(args) > 1:
            mode = args[1].lower()
            
            if mode in ['paper', 'live']:
                # Get UserTradingManager service
                trading_manager = UserTradingManager(self.db)
                
                # Actually set the trading mode
                success = trading_manager.set_trading_mode(user.id, mode)
                
                if success:
                    response = f"🔄 Trading mode has been set to *{mode.upper()}*"
                    
                    # Add warnings for live mode
                    if mode == 'live':
                        response += "\n\n⚠️ **WARNING: LIVE TRADING ACTIVATED** ⚠️\nYour bot will now execute trades using real funds."
                else:
                    response = "❌ Failed to update trading mode. Please try again later."
            else:
                response = "❌ Invalid trading mode. Use 'paper' or 'live'."
                
            self.send_message(chat_id, response)
        else:
            # Show mode options
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("Paper Trading", callback_data="mode_paper"),
                types.InlineKeyboardButton("Live Trading", callback_data="mode_live")
            )
            
            # Get current mode
            trading_manager = UserTradingManager(self.db)
            settings = trading_manager.get_trading_settings(user.id)
            current_mode = settings.get('trading_mode', 'paper').capitalize() if settings else "Paper"
            
            response = (
                "🔄 *Trading Mode Settings*\n\n"
                "Select your preferred trading mode:\n\n"
                "• *Paper Trading:* Simulated trading with virtual funds\n"
                "• *Live Trading:* Real trading with actual funds\n\n"
                f"Current mode: *{current_mode} Trading*"
            )
            
            self.send_message(chat_id, response, reply_markup=markup)
    except Exception as e:
        self.logger.error(f"Error handling mode command: {e}")

def _handle_risk_command(self, message):
    """Handle /risk command to set user's risk level"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Parse arguments
        args = message.text.split()
        
        if len(args) > 1:
            risk_level = args[1].lower()
            
            if risk_level in ['low', 'medium', 'high']:
                # Get UserTradingManager service
                trading_manager = UserTradingManager(self.db)
                
                # Set the risk level
                success = trading_manager.set_risk_level(user.id, risk_level)
                
                if success:
                    response = f"⚠️ Risk level has been set to *{risk_level.upper()}*"
                    
                    # Add explanations for each risk level
                    if risk_level == 'low':
                        response += "\n\nLow risk means smaller position sizes and more conservative strategies."
                    elif risk_level == 'medium':
                        response += "\n\nMedium risk is the default balanced approach."
                    elif risk_level == 'high':
                        response += "\n\nHigh risk allows larger position sizes and more aggressive strategies."
                else:
                    response = "❌ Failed to update risk level. Please try again later."
            else:
                response = "❌ Invalid risk level. Use 'low', 'medium', or 'high'."
                
            self.send_message(chat_id, response)
        else:
            # Show risk level options using inline keyboard
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("Low Risk", callback_data="risk_low"),
                types.InlineKeyboardButton("Medium Risk", callback_data="risk_medium"),
                types.InlineKeyboardButton("High Risk", callback_data="risk_high")
            )
            
            # Get current risk level
            trading_manager = UserTradingManager(self.db)
            settings = trading_manager.get_trading_settings(user.id)
            current_risk = settings.get('risk_level', 'medium').capitalize() if settings else "Medium"
            
            response = (
                "🛡️ *Risk Level Settings*\n\n"
                "Select your preferred risk level:\n\n"
                "• *Low Risk:* Conservative approach, smaller position sizes, tighter stop-losses\n"
                "• *Medium Risk:* Balanced approach, moderate position sizes\n"
                "• *High Risk:* Aggressive approach, larger position sizes, wider stop-losses\n\n"
                f"Current risk level: *{current_risk}*"
            )
            
            self.send_message(chat_id, response, reply_markup=markup)
    except Exception as e:
        self.logger.error(f"Error handling risk command: {e}")

def _handle_pause_command(self, message):
    """Handle /pause command to pause all trading"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get UserTradingManager service
        trading_manager = UserTradingManager(self.db)
        
        # Pause trading for this user
        success = trading_manager.set_paused_state(user.id, True)
        
        if success:
            response = "⏸️ Trading has been paused. No new trades will be opened.\n\nUse /resume to resume trading."
        else:
            response = "❌ Failed to pause trading. Please try again later."
            
        self.send_message(chat_id, response)
    except Exception as e:
        self.logger.error(f"Error handling pause command: {e}")

def _handle_resume_command(self, message):
    """Handle /resume command to resume trading"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get UserTradingManager service
        trading_manager = UserTradingManager(self.db)
        
        # Resume trading for this user
        success = trading_manager.set_paused_state(user.id, False)
        
        if success:
            response = "▶️ Trading has been resumed. The bot will now open new positions according to your settings."
        else:
            response = "❌ Failed to resume trading. Please try again later."
            
        self.send_message(chat_id, response)
    except Exception as e:
        self.logger.error(f"Error handling resume command: {e}")

def _handle_status_command(self, message):
    """Handle /status command to show current trading status"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get UserTradingManager service
        trading_manager = UserTradingManager(self.db)
        
        # Get user's trading settings
        settings = trading_manager.get_trading_settings(user.id)
        
        if settings:
            # Format the status message
            status_emoji = "⏸️" if settings.get('is_paused', False) else "▶️"
            mode_emoji = "🧪" if settings.get('trading_mode') == 'paper' else "💰"
            risk_emoji = {
                'low': "🟢",
                'medium': "🟠",
                'high': "🔴"
            }.get(settings.get('risk_level', 'medium'), "🟠")
            
            response = f"*Current Trading Status*\n\n"
            response += f"{status_emoji} Trading Status: {'Paused' if settings.get('is_paused', False) else 'Active'}\n"
            response += f"{mode_emoji} Trading Mode: {settings.get('trading_mode', 'paper').upper()}\n"
            response += f"{risk_emoji} Risk Level: {settings.get('risk_level', 'medium').upper()}\n"
            response += f"📊 Max Open Positions: {settings.get('max_open_positions', 5)}\n"
            response += f"💵 Max Position Size: {settings.get('max_position_size', 0.1)}\n"
            
            # Get active positions
            position_repo = PositionRepository(self.db)
            active_positions = position_repo.get_open_positions_count(user.id)
            
            response += f"\n📈 Active Positions: {active_positions}"
            
            # Get profit statistics
            profit_tracker = ProfitTracker(self.db)
            profit_stats = profit_tracker.get_user_profit_statistics(user.id)
            
            if profit_stats:
                response += f"\n\n*Profit Statistics*\n"
                response += f"💰 Total Profit: {profit_stats.get('total_profit', 0):.2f} USD\n"
                response += f"🔄 Total Trades: {profit_stats.get('total_trades', 0)}\n"
                response += f"✅ Win Rate: {profit_stats.get('win_rate', 0):.1f}%\n"
        else:
            response = "❌ Failed to retrieve trading status. Please try again later."
            
        self.send_message(chat_id, response)
    except Exception as e:
        self.logger.error(f"Error handling status command: {e}")

def _handle_performance_command(self, message):
    """Handle /performance command to show trading performance metrics"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get ProfitTracker service
        profit_tracker = ProfitTracker(self.db)
        
        # Get detailed performance statistics
        performance_stats = profit_tracker.get_user_detailed_performance(user.id)
        
        if performance_stats:
            # Format performance message with actual data
            response = f"📈 *Trading Performance*\n\n"
            
            response += "*Overall Statistics:*\n"
            response += f"• Total Trades: *{performance_stats.get('total_trades', 0)}*\n"
            response += f"• Win Rate: *{performance_stats.get('win_rate', 0):.1f}%*\n"
            response += f"• Profit Factor: *{performance_stats.get('profit_factor', 0):.2f}*\n"
            response += f"• Total Return: *{performance_stats.get('total_return_percentage', 0):.1f}%*\n"
            response += f"• Max Drawdown: *{performance_stats.get('max_drawdown', 0):.1f}%*\n\n"
            
            # Time-based performance
            time_stats = performance_stats.get('time_based', {})
            response += "*Time-Based Performance:*\n"
            response += f"• Today: *{time_stats.get('today', 0):.1f}%*\n"
            response += f"• This Week: *{time_stats.get('week', 0):.1f}%*\n"
            response += f"• This Month: *{time_stats.get('month', 0):.1f}%*\n"
            response += f"• This Year: *{time_stats.get('year', 0):.1f}%*\n\n"
            
            # Strategy performance
            strategy_stats = performance_stats.get('strategies', {})
            if strategy_stats:
                response += "*Top Strategies:*\n"
                for strategy, performance in strategy_stats.items():
                    response += f"• {strategy}: *{performance:.1f}%*\n"
            
            response += "\nFor detailed analysis, use /report to generate a complete performance report."
        else:
            response = "❌ No performance data available yet. Start trading to generate statistics."
            
        self.send_message(chat_id, response)
    except Exception as e:
        self.logger.error(f"Error handling performance command: {e}")

def _handle_trades_command(self, message):
    """Handle /trades command to show recent trade history"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get trade history repository
        trade_repo = TradeRepository(self.db)
        
        # Get recent trades (limit to 5)
        recent_trades = trade_repo.get_recent_trades(user.id, limit=5)
        
        if recent_trades and len(recent_trades) > 0:
            response = f"📊 *Recent Trades*\n\n"
            
            for idx, trade in enumerate(recent_trades, 1):
                # Format each trade entry
                symbol = trade.get('symbol', 'UNKNOWN')
                strategy = trade.get('strategy', 'Unknown')
                
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                
                direction = "Buy" if trade.get('direction', '') == 'long' else "Sell"
                exit_direction = "Sell" if direction == "Buy" else "Buy"
                
                profit_pct = trade.get('profit_percentage', 0)
                profit_type = "Profit" if profit_pct >= 0 else "Loss"
                
                # Calculate time ago
                close_time = trade.get('close_time')
                time_ago = "Unknown"
                
                if close_time:
                    now = datetime.now()
                    diff = now - close_time
                    
                    if diff.days > 0:
                        time_ago = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
                    elif diff.seconds // 3600 > 0:
                        hours = diff.seconds // 3600
                        time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                    else:
                        minutes = diff.seconds // 60
                        time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                
                response += f"*{idx}. {symbol}* ({strategy})\n"
                response += f"{direction} at ${entry_price:.4f} → {exit_direction} at ${exit_price:.4f}\n"
                response += f"{profit_type}: {abs(profit_pct):.2f}% | {time_ago}\n\n"
                
            response += "Use /performance for overall statistics."
        else:
            response = "📊 No trade history available yet. Start trading to see your results here."
            
        self.send_message(chat_id, response)
    except Exception as e:
        self.logger.error(f"Error handling trades command: {e}")

def _handle_open_command(self, message):
    """Handle /open command to show current open positions"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get position repository
        position_repo = PositionRepository(self.db)
        
        # Get current price service
        price_service = PriceService()
        
        # Get open positions
        open_positions = position_repo.get_open_positions(user.id)
        
        if open_positions and len(open_positions) > 0:
            response = f"🔍 *Open Positions*\n\n"
            
            total_pnl_pct = 0
            
            for idx, position in enumerate(open_positions, 1):
                # Format each position entry
                symbol = position.get('symbol', 'UNKNOWN')
                strategy = position.get('strategy', 'Unknown')
                
                entry_price = position.get('entry_price', 0)
                
                # Get current price from price service
                current_price = entry_price
                try:
                    current_price = price_service.get_current_price(symbol)
                except Exception as price_error:
                    self.logger.error(f"Error getting current price for {symbol}: {price_error}")
                
                # Calculate unrealized P/L
                direction = position.get('direction', 'long')
                if direction == 'long':
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                
                total_pnl_pct += pnl_pct
                
                # Format direction
                direction_text = "Buy" if direction == 'long' else "Sell"
                
                # Get stop loss and take profit
                stop_loss = position.get('stop_loss', 0)
                take_profit = position.get('take_profit', 0)
                
                response += f"*{idx}. {symbol}* ({strategy})\n"
                response += f"{direction_text} at ${entry_price:.4f} | Current: ${current_price:.4f}\n"
                response += f"Unrealized P/L: {'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%\n"
                
                if stop_loss and take_profit:
                    response += f"Stop Loss: ${stop_loss:.4f} | Take Profit: ${take_profit:.4f}\n\n"
                else:
                    response += "\n"
            
            # Add total unrealized P/L
            response += f"*Total Unrealized P/L:* {'+' if total_pnl_pct >= 0 else ''}{total_pnl_pct:.2f}%"
        else:
            response = "🔍 No open positions at the moment."
            
        self.send_message(chat_id, response)
    except Exception as e:
        self.logger.error(f"Error handling open command: {e}")

def _handle_stats_command(self, message):
    """Handle /stats command to show detailed performance metrics"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get advanced statistics service
        stats_service = StatsService(self.db)
        
        # Get detailed statistics
        stats = stats_service.get_detailed_stats(user.id)
        
        if stats:
            response = f"📊 *Detailed Performance Metrics*\n\n"
            
            # Trade statistics
            trade_stats = stats.get('trade_stats', {})
            response += "*Trade Statistics:*\n"
            response += f"• Total Trades: *{trade_stats.get('total_trades', 0)}*\n"
            
            winning_trades = trade_stats.get('winning_trades', 0)
            losing_trades = trade_stats.get('losing_trades', 0)
            total_trades = winning_trades + losing_trades
            
            if total_trades > 0:
                win_rate = (winning_trades / total_trades) * 100
                response += f"• Winning Trades: *{winning_trades} ({win_rate:.1f}%)*\n"
                response += f"• Losing Trades: *{losing_trades} ({100 - win_rate:.1f}%)*\n"
            
            response += f"• Average Win: *{trade_stats.get('avg_win', 0):.2f}%*\n"
            response += f"• Average Loss: *{trade_stats.get('avg_loss', 0):.2f}%*\n"
            response += f"• Largest Win: *{trade_stats.get('largest_win', 0):.2f}%*\n"
            response += f"• Largest Loss: *{trade_stats.get('largest_loss', 0):.2f}%*\n\n"
            
            # Risk metrics
            risk_metrics = stats.get('risk_metrics', {})
            response += "*Risk Metrics:*\n"
            response += f"• Profit Factor: *{risk_metrics.get('profit_factor', 0):.2f}*\n"
            response += f"• Sharpe Ratio: *{risk_metrics.get('sharpe_ratio', 0):.2f}*\n"
            response += f"• Sortino Ratio: *{risk_metrics.get('sortino_ratio', 0):.2f}*\n"
            response += f"• Max Drawdown: *{risk_metrics.get('max_drawdown', 0):.2f}%*\n"
            response += f"• Recovery Factor: *{risk_metrics.get('recovery_factor', 0):.2f}*\n\n"
            
            # Portfolio growth
            portfolio = stats.get('portfolio', {})
            response += "*Portfolio Growth:*\n"
            response += f"• Starting Capital: *${portfolio.get('starting_capital', 0):.2f}*\n"
            response += f"• Current Value: *${portfolio.get('current_value', 0):.2f}*\n"
            response += f"• Total Return: *{portfolio.get('total_return', 0):.2f}%*\n"
            response += f"• Monthly Return: *{portfolio.get('monthly_return', 0):.2f}%*\n"
            response += f"• Annual Return: *{portfolio.get('annual_return', 0):.2f}%*\n"
        else:
            response = "📊 No statistics available yet. Start trading to generate performance metrics."
            
        self.send_message(chat_id, response)
    except Exception as e:
        self.logger.error(f"Error handling stats command: {e}")

def _handle_report_command(self, message):
    """Handle /report command to generate performance report"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Send initial message
        report_message = (
            "📋 *Performance Report*\n\n"
            "I'm generating a comprehensive performance report for your account.\n\n"
            "This may take a few moments. I'll send you the report as soon as it's ready.\n\n"
            "The report will include:\n"
            "• Detailed performance metrics\n"
            "• Trade history analysis\n"
            "• Strategy performance breakdown\n"
            "• Risk analysis\n"
            "• Recommendations for improvement"
        )
        
        self.send_message(chat_id, report_message)
        
        # Generate report in a separate thread to avoid blocking
        from threading import Thread
        
        def generate_report():
            try:
                # Get report generator service
                report_gen = ReportGenerator(self.db)
                
                # Generate the report
                report_url = report_gen.generate_user_report(user.id)
                
                if report_url:
                    success_message = (
                        "📊 Your performance report is ready!\n\n"
                        f"You can view or download the full report here:\n{report_url}\n\n"
                        "The report contains detailed analysis of your trading performance and recommendations for improvement."
                    )
                    self.send_message(chat_id, success_message)
                else:
                    error_message = (
                        "❌ Unable to generate report at this time. There might not be enough trading data yet.\n\n"
                        "Please try again later or contact support if the problem persists."
                    )
                    self.send_message(chat_id, error_message)
            except Exception as e:
                self.logger.error(f"Error generating report: {e}")
                self.send_message(chat_id, "❌ An error occurred while generating your report. Please try again later.")
        
        # Start report generation in background
        report_thread = Thread(target=generate_report)
        report_thread.daemon = True
        report_thread.start()
            
    except Exception as e:
        self.logger.error(f"Error handling report command: {e}")

def _handle_pairs_command(self, message):
    """Handle /pairs command to manage trading pairs"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get trading pairs manager
        pairs_manager = PairsManager(self.db)
        
        # Get user's trading pairs
        active_pairs, inactive_pairs = pairs_manager.get_user_pairs(user.id)
        
        response = f"🔄 *Trading Pairs*\n\n"
        
        if active_pairs:
            response += "*Active Pairs:*\n"
            for pair in active_pairs:
                response += f"✅ {pair}\n"
            response += "\n"
        else:
            response += "*Active Pairs:*\nNo active pairs\n\n"
        
        if inactive_pairs:
            response += "*Inactive Pairs:*\n"
            for pair in inactive_pairs:
                response += f"❌ {pair}\n"
            response += "\n"
        else:
            response += "*Inactive Pairs:*\nNo inactive pairs\n\n"
        
        response += "To enable or disable a pair, use:\n/pair enable [symbol] or /pair disable [symbol]"
        
        # Create inline keyboard for pair management
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Enable Pair", callback_data="pair_enable"),
            types.InlineKeyboardButton("Disable Pair", callback_data="pair_disable"),
            types.InlineKeyboardButton("Enable All", callback_data="pair_enable_all"),
            types.InlineKeyboardButton("Disable All", callback_data="pair_disable_all")
        )
        
        self.send_message(chat_id, response, reply_markup=markup)
            
    except Exception as e:
        self.logger.error(f"Error handling pairs command: {e}")

def _handle_strategies_command(self, message):
    """Handle /strategies command to manage trading strategies"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get strategy manager
        strategy_manager = StrategyManager(self.db)
        
        # Get user's strategies and allocations
        active_strategies, inactive_strategies = strategy_manager.get_user_strategies(user.id)
        
        response = f"🧠 *Trading Strategies*\n\n"
        
        if active_strategies:
            response += "*Active Strategies:*\n"
            for strategy, allocation in active_strategies.items():
                response += f"• {strategy}: *{allocation}%* allocation\n"
            response += "\n"
        else:
            response += "*Active Strategies:*\nNo active strategies\n\n"
        
        if inactive_strategies:
            response += "*Inactive Strategies:*\n"
            for strategy in inactive_strategies:
                response += f"• {strategy}\n"
            response += "\n"
        else:
            response += "*Inactive Strategies:*\nNo inactive strategies\n\n"
        
        response += "To adjust strategy allocation, use:\n/strategy adjust [name] [percentage]"
        
        # Create inline keyboard for strategy management
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Enable Strategy", callback_data="strategy_enable"),
            types.InlineKeyboardButton("Disable Strategy", callback_data="strategy_disable"),
            types.InlineKeyboardButton("Adjust Allocation", callback_data="strategy_adjust")
        )
        
        self.send_message(chat_id, response, reply_markup=markup)
            
    except Exception as e:
        self.logger.error(f"Error handling strategies command: {e}")

def _handle_alerts_command(self, message):
    """Handle /alerts command to manage notification settings"""
    try:
        chat_id = message.chat.id
        user = self.get_user_by_telegram_id(str(chat_id))
        
        if not user:
            self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
            return
            
        # Get notification manager
        notification_manager = NotificationManager(self.db)
        
        # Get user's alert settings
        alert_settings = notification_manager.get_user_notification_settings(user.id)
        
        response = f"🔔 *Notification Settings*\n\n"
        
        if alert_settings:
            response += "*Current Settings:*\n"
            for alert_type, enabled in alert_settings.items():
                status = "✅" if enabled else "❌"
                # Format alert type name for display
                display_name = alert_type.replace("_", " ").title()
                response += f"{status} {display_name}\n"
        else:
            response += "*Current Settings:*\nDefault notification settings applied\n"
        
        response += "\nTo toggle an alert type, use:\n/alert toggle [type]"
        
        # Create inline keyboard for alert management
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Trade Execution", callback_data="alert_trade_execution"),
            types.InlineKeyboardButton("Take Profit Hit", callback_data="alert_take_profit"),
            types.InlineKeyboardButton("Stop Loss Hit", callback_data="alert_stop_loss"),
            types.InlineKeyboardButton("Position Adjustment", callback_data="alert_position"),
            types.InlineKeyboardButton("Daily Summary", callback_data="alert_daily"),
            types.InlineKeyboardButton("System Alerts", callback_data="alert_system")
        )
        
        self.send_message(chat_id, response, reply_markup=markup)
    except Exception as e:
        self.logger.error(f"Error handling alerts command: {e}")

def _handle_data_command(self, message):
   """Handle /data command to show market data analysis"""
   try:
       chat_id = message.chat.id
       user = self.get_user_by_telegram_id(str(chat_id))
       
       if not user:
           self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
           return
           
       # Get market data service
       market_service = MarketAnalysisService()
       
       # Get market analysis data
       market_data = market_service.get_current_market_analysis()
       
       if market_data:
           response = f"📊 *Market Data Analysis*\n\n"
           
           # Current market analysis
           trend_data = market_data.get('trends', {})
           response += "*Current Market Analysis:*\n"
           for key, value in trend_data.items():
               response += f"• {key} Trend: *{value}*\n"
           
           # Add overall market indicators
           market_indicators = market_data.get('market_indicators', {})
           response += f"• Market Volatility: *{market_indicators.get('volatility', 'Medium')}*\n"
           response += f"• Market Sentiment: *{market_indicators.get('sentiment', 'Neutral')}*\n\n"
           
           # Technical indicators
           tech_indicators = market_data.get('technical_indicators', {})
           if tech_indicators:
               response += "*Key Technical Indicators:*\n"
               for symbol, indicators in tech_indicators.items():
                   for indicator_name, indicator_value in indicators.items():
                       response += f"• {symbol} {indicator_name}: *{indicator_value}*\n"
               response += "\n"
           
           # Recent market events
           events = market_data.get('market_events', {})
           if events:
               response += "*Recent Market Events:*\n"
               for event_type, event_data in events.items():
                   response += f"• {event_type}: *{event_data}*\n"
               response += "\n"
           
           response += "Use /pairs to manage your trading pairs or /performance to check your results."
       else:
           response = "📊 *Market Data Analysis*\n\nMarket data is currently being updated. Please try again in a few moments."
           
       self.send_message(chat_id, response)
           
   except Exception as e:
       self.logger.error(f"Error handling data command: {e}")

def _handle_setup_exchange_command(self, message):
   """Handle /setup_exchange command to configure exchange API"""
   try:
       chat_id = message.chat.id
       user = self.get_user_by_telegram_id(str(chat_id))
       
       if not user:
           self.send_message(chat_id, "❌ You need to register first. Use /register to get started.")
           return
           
       # Get API key repository to check if user already has API keys
       existing_keys = None
       if self.api_key_repository:
           existing_keys = self.api_key_repository.get_user_api_keys(user.id, exchange="binance")
       
       setup_message = (
           "🔑 *Exchange API Setup*\n\n"
       )
       
       if existing_keys:
           setup_message += (
               "You already have Binance API credentials configured.\n\n"
               "Would you like to update your existing API keys?\n"
               "Type 'yes' to proceed or 'no' to cancel."
           )
           
           # Set state for API key update
           self.user_states[chat_id] = {
               'state': 'awaiting_update_confirmation',
               'data': {'user_id': user.id}
           }
       else:
           setup_message += (
               "To connect your Binance account, you'll need to provide your API credentials.\n\n"
               "1. Log in to your Binance account\n"
               "2. Go to API Management\n"
               "3. Create a new API key with trading permissions\n"
               "4. Copy the API key and secret\n\n"
               "Ready to proceed? Type 'yes' to continue or click the button below."
           )
           
           # Set state for new API key setup
           self.user_states[chat_id] = {
               'state': 'awaiting_setup_confirmation',
               'data': {'user_id': user.id}
           }
       
       # Create inline keyboard for setup
       markup = types.InlineKeyboardMarkup()
       markup.add(
           types.InlineKeyboardButton("Set Up Exchange", callback_data="setup_exchange")
       )
       
       self.send_message(chat_id, setup_message, reply_markup=markup)
           
   except Exception as e:
       self.logger.error(f"Error handling setup exchange command: {e}")

def _handle_callback_query(self, call):
   """
   Handle callback queries from inline keyboards
   
   Args:
       call: Callback query object
   """
   try:
       chat_id = call.message.chat.id
       data = call.data
       user = self.get_user_by_telegram_id(str(chat_id))
       
       if not user:
           self.bot.answer_callback_query(call.id, "You need to register first. Use /register to get started.")
           return
           
       # Answer callback to remove loading indicator
       self.bot.answer_callback_query(call.id)
       
       # Process callback data
       if data.startswith("risk_"):
           risk_level = data.split("_")[1]
           
           # Get UserTradingManager service
           trading_manager = UserTradingManager(self.db)
           
           # Set the risk level
           success = trading_manager.set_risk_level(user.id, risk_level)
           
           if success:
               response = f"🛡️ Risk level has been set to *{risk_level.title()}*"
               
               # Add explanations based on risk level
               if risk_level == "low":
                   response += "\n\nLow risk means smaller position sizes and more conservative strategies."
               elif risk_level == "medium":
                   response += "\n\nMedium risk is the default balanced approach."
               elif risk_level == "high":
                   response += "\n\nHigh risk allows larger position sizes and more aggressive strategies."
           else:
               response = "❌ Failed to update risk level. Please try again later."
               
           self.send_message(chat_id, response)
           
       elif data.startswith("mode_"):
           mode = data.split("_")[1]
           
           # Get UserTradingManager service
           trading_manager = UserTradingManager(self.db)
           
           # Set the trading mode
           success = trading_manager.set_trading_mode(user.id, mode)
           
           if success:
               response = f"🔄 Trading mode has been set to *{mode.upper()}*"
               
               # Add warnings for live mode
               if mode == "live":
                   response += "\n\n⚠️ **WARNING: LIVE TRADING ACTIVATED** ⚠️\nYour bot will now execute trades using real funds."
           else:
               response = "❌ Failed to update trading mode. Please try again later."
               
           self.send_message(chat_id, response)
           
       elif data.startswith("pair_"):
           action = data.split("_")[1]
           pairs_manager = PairsManager(self.db)
           
           if action == "enable":
               self.send_message(chat_id, "Please enter the symbol to enable:")
               self.user_states[chat_id] = {"state": "awaiting_pair_enable", "data": {"user_id": user.id}}
           elif action == "disable":
               self.send_message(chat_id, "Please enter the symbol to disable:")
               self.user_states[chat_id] = {"state": "awaiting_pair_disable", "data": {"user_id": user.id}}
           elif action == "enable_all":
               success = pairs_manager.enable_all_pairs(user.id)
               if success:
                   self.send_message(chat_id, "✅ All trading pairs have been enabled")
               else:
                   self.send_message(chat_id, "❌ Failed to enable all pairs. Please try again later.")
           elif action == "disable_all":
               success = pairs_manager.disable_all_pairs(user.id)
               if success:
                   self.send_message(chat_id, "❌ All trading pairs have been disabled")
               else:
                   self.send_message(chat_id, "❌ Failed to disable all pairs. Please try again later.")
               
       elif data.startswith("strategy_"):
           action = data.split("_")[1]
           strategy_manager = StrategyManager(self.db)
           
           if action == "enable":
               # Get available strategies
               available_strategies = strategy_manager.get_available_strategies()
               
               # Create inline keyboard with available strategies
               markup = types.InlineKeyboardMarkup(row_width=2)
               for strategy in available_strategies:
                   markup.add(types.InlineKeyboardButton(
                       strategy, callback_data=f"strategy_enable_{strategy}"
                   ))
               
               self.send_message(chat_id, "Please select a strategy to enable:", reply_markup=markup)
           elif action == "disable":
               # Get user's active strategies
               active_strategies, _ = strategy_manager.get_user_strategies(user.id)
               
               if active_strategies:
                   # Create inline keyboard with active strategies
                   markup = types.InlineKeyboardMarkup(row_width=2)
                   for strategy in active_strategies:
                       markup.add(types.InlineKeyboardButton(
                           strategy, callback_data=f"strategy_disable_{strategy}"
                       ))
                   
                   self.send_message(chat_id, "Please select a strategy to disable:", reply_markup=markup)
               else:
                   self.send_message(chat_id, "❌ You don't have any active strategies to disable.")
           elif action == "adjust":
               # Get user's active strategies
               active_strategies, _ = strategy_manager.get_user_strategies(user.id)
               
               if active_strategies:
                   # Create inline keyboard with active strategies
                   markup = types.InlineKeyboardMarkup(row_width=2)
                   for strategy in active_strategies:
                       markup.add(types.InlineKeyboardButton(
                           strategy, callback_data=f"strategy_adjust_{strategy}"
                       ))
                   
                   self.send_message(chat_id, "Please select a strategy to adjust allocation:", reply_markup=markup)
               else:
                   self.send_message(chat_id, "❌ You don't have any active strategies to adjust.")
           elif "enable_" in action:
               # Enable specific strategy
               strategy_name = action.replace("enable_", "")
               success = strategy_manager.enable_strategy(user.id, strategy_name)
               
               if success:
                   self.send_message(chat_id, f"✅ Strategy *{strategy_name}* has been enabled")
               else:
                   self.send_message(chat_id, f"❌ Failed to enable strategy. Please try again later.")
           elif "disable_" in action:
               # Disable specific strategy
               strategy_name = action.replace("disable_", "")
               success = strategy_manager.disable_strategy(user.id, strategy_name)
               
               if success:
                   self.send_message(chat_id, f"❌ Strategy *{strategy_name}* has been disabled")
               else:
                   self.send_message(chat_id, f"❌ Failed to disable strategy. Please try again later.")
           elif "adjust_" in action:
               # Set up state for strategy adjustment
               strategy_name = action.replace("adjust_", "")
               self.user_states[chat_id] = {
                   "state": "awaiting_strategy_allocation",
                   "data": {"user_id": user.id, "strategy": strategy_name}
               }
               
               self.send_message(chat_id, f"Please enter allocation percentage for *{strategy_name}* (1-100):")
               
       elif data.startswith("alert_"):
           alert_type = data.replace("alert_", "")
           
           # Get notification manager
           notification_manager = NotificationManager(self.db)
           
           # Toggle alert status
           success = notification_manager.toggle_notification(user.id, alert_type)
           
           if success:
               # Format alert type for display
               display_name = alert_type.replace("_", " ").title()
               self.send_message(chat_id, f"🔔 {display_name} notifications have been toggled")
           else:
               self.send_message(chat_id, "❌ Failed to update notification settings. Please try again later.")
               
       elif data.startswith("setup_"):
           action = data.split("_")[1]
           if action == "exchange":
               self.user_states[chat_id] = {"state": "awaiting_api_key", "data": {"user_id": user.id}}
               self.send_message(chat_id, "Please enter your Binance API key:")
           
   except Exception as e:
       self.logger.error(f"Error handling callback query: {str(e)}", exc_info=True)
       self.send_message(chat_id, "❌ An error occurred while processing your request. Please try again later.")

def _handle_text_message(self, message):
   """
   Handle text messages for conversation flow
   """
   try:
       chat_id = message.chat.id
       text = message.text

       # Log the received message for debugging
       logger.debug(f"Received text message from {chat_id}: '{text}'")
   except Exception as e:
       logger.error(f"Error accessing message properties: {str(e)}")
       return
   except Exception as e:
       logger.error(f"Error accessing message properties: {str(e)}")
       return

   try:
       
       # Check if user is in a specific state
       if chat_id in self.user_states:
           state = self.user_states[chat_id]['state']
           data = self.user_states[chat_id]['data']
           
           if state == 'awaiting_email':
               # Validate email
               if '@' in text and '.' in text:
                   data['email'] = text
                   self.user_states[chat_id]['state'] = 'awaiting_confirmation'
                   
                   confirm_message = (
                       f"📧 Email address received: *{text}*\n\n"
                       f"Is this correct? (yes/no)"
                   )
                   
                   self.send_message(chat_id, confirm_message)
               else:
                   self.send_message(chat_id, "❌ Invalid email format. Please enter a valid email address:")
                   
           elif state == 'awaiting_confirmation':
               if text.lower() in ['yes', 'y']:
                   # Process registration
                   email = data.get('email', '')
                   telegram_id = str(message.from_user.id)
                   
                   # Register user in database if user repository available
                   user_id = None
                   if self.user_repository:
                       try:
                           user = self.user_repository.create_user(
                               telegram_id=telegram_id,
                               email=email,
                               first_name=message.from_user.first_name,
                               last_name=message.from_user.last_name,
                               username=message.from_user.username
                           )
                           if user:
                               user_id = user.id
                               data['user_id'] = user_id
                       except Exception as e:
                           logger.error(f"Error creating user: {str(e)}", exc_info=True)
                   
                   # Update success message to continue with API key setup
                   success_message = (
                       "✅ *Registration Step 1 Complete!*\n\n"
                       f"Your account has been created with email: *{email}*\n\n"
                       f"Let's set up your exchange API keys now.\n\n"
                       f"Please enter your Binance API key:"
                   )
                   
                   self.send_message(chat_id, success_message)
                   
                   # Update state to await API key
                   self.user_states[chat_id]['state'] = 'awaiting_api_key'
                   
               elif text.lower() in ['no', 'n']:
                   # Restart registration
                   self.user_states[chat_id]['state'] = 'awaiting_email'
                   self.user_states[chat_id]['data'] = {}
                   
                   self.send_message(chat_id, "Please enter your email address:")
                   
               else:
                   self.send_message(chat_id, "Please respond with 'yes' or 'no':")
           
           elif state == 'awaiting_api_key':
               # Store API key
               data['api_key'] = text
               self.user_states[chat_id]['state'] = 'awaiting_api_secret'
               
               self.send_message(chat_id, "Great! Now please enter your Binance API secret:")
               
           elif state == 'awaiting_api_secret':
               # Store API secret
               data['api_secret'] = text
               
               # Store the API credentials securely if API key repository available
               success = False
               if self.api_key_repository and 'user_id' in data:
                   try:
                       key_id = self.api_key_repository.save_api_key(
                           user_id=data['user_id'],
                           exchange="binance",
                           api_key=data['api_key'],
                           api_secret=data['api_secret']
                       )
                       success = bool(key_id)
                   except Exception as e:
                       self.logger.error(f"Error saving API key: {str(e)}", exc_info=True)
               
               # Customize message based on success
               if success:
                   status_message = "🎉 *API Keys Saved Successfully!*\n\n"
               else:
                   status_message = "⚠️ *Note: API Keys couldn't be securely stored at this time*\n\n"
               
               complete_message = (
                   f"{status_message}"
                   "Your trading bot is now configured with your Binance account.\n\n"
                   "• Use /status to check your account status\n"
                   "• Use /risk to set your risk level\n"
                   "• Use /mode to choose between paper and live trading\n"
                   "• Use /pairs to select trading pairs\n\n"
                   "Happy trading! 📈"
               )
               
               self.send_message(chat_id, complete_message)
               
               # Clear user state
               del self.user_states[chat_id]
           
           elif state == 'awaiting_setup_confirmation':
               if text.lower() in ['yes', 'y']:
                   self.send_message(chat_id, "Please enter your Binance API key:")
                   self.user_states[chat_id]['state'] = 'awaiting_api_key'
               else:
                   self.send_message(chat_id, "You can set up your exchange connection later using the /setup_exchange command.")
                   del self.user_states[chat_id]
           
           elif state == 'awaiting_update_confirmation':
               if text.lower() in ['yes', 'y']:
                   self.send_message(chat_id, "Please enter your new Binance API key:")
                   self.user_states[chat_id]['state'] = 'awaiting_api_key'
               else:
                   self.send_message(chat_id, "API key update cancelled. Your existing keys will continue to be used.")
                   del self.user_states[chat_id]
           
           elif state == 'awaiting_pair_enable':
               # Process pair enable request
               symbol = text.strip().upper()
               
               # Enable trading pair
               pairs_manager = PairsManager(self.db)
               
               success = pairs_manager.enable_pair(data.get('user_id'), symbol)
               
               if success:
                   self.send_message(chat_id, f"✅ Trading pair *{symbol}* has been enabled.")
               else:
                   self.send_message(chat_id, f"❌ Failed to enable trading pair. Please check the symbol and try again.")
               
               # Clear user state
               del self.user_states[chat_id]
           
           elif state == 'awaiting_pair_disable':
               # Process pair disable request
               symbol = text.strip().upper()
               
               # Disable trading pair
               pairs_manager = PairsManager(self.db)
               
               success = pairs_manager.disable_pair(data.get('user_id'), symbol)
               
               if success:
                   self.send_message(chat_id, f"❌ Trading pair *{symbol}* has been disabled.")
               else:
                   self.send_message(chat_id, f"❌ Failed to disable trading pair. Please check the symbol and try again.")
               
               # Clear user state
               del self.user_states[chat_id]
           
           elif state == 'awaiting_strategy_allocation':
               # Process strategy adjustment
               try:
                   allocation = int(text.strip())
                   strategy = data.get('strategy', '')
                   
                   if 1 <= allocation <= 100:
                       # Adjust strategy allocation
                       strategy_manager = StrategyManager(self.db)
                       
                       success = strategy_manager.set_strategy_allocation(
                           data.get('user_id'), 
                           strategy, 
                           allocation
                       )
                       
                       if success:
                           self.send_message(chat_id, f"✅ Strategy *{strategy}* allocation has been set to *{allocation}%*.")
                       else:
                           self.send_message(chat_id, f"❌ Failed to adjust strategy allocation. Please try again later.")
                   else:
                       self.send_message(chat_id, "❌ Allocation must be between 1 and 100%. Please enter a valid percentage:")
                       return
               except ValueError:
                   self.send_message(chat_id, "❌ Please enter a valid number for the allocation percentage:")
                   return
               
               # Clear user state
               del self.user_states[chat_id]
           
       else:
           # Check if message is "data" which caused errors in logs
           if text.lower() == "data":
               self._handle_data_command(message)
           else:
               # Default response for unsolicited messages
               help_message = (
                   "I'm not sure what you're asking. Here are some commands you can use:\n\n"
                   "/help - Show all available commands\n"
                   "/status - Check your account status\n"
                   "/register - Create a new account"
               )
               
               self.send_message(chat_id, help_message)
           
   except Exception as e:
       self.logger.error(f"Error handling text message: '{message.text}'", exc_info=True)