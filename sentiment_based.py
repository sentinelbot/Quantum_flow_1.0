# strategies/sentiment_based.py
import logging
import time
from typing import Dict, List, Any, Optional

from exchange.abstract_exchange import TradeSignal
from strategies.base_strategy import BaseStrategy
from analysis.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

class SentimentBasedStrategy(BaseStrategy):
    """
    Sentiment-based trading strategy
    
    Uses sentiment analysis from news and social media to make trading decisions
    """
    def __init__(self, exchange, user, risk_manager, config: Dict[str, Any]):
        super().__init__('sentiment_based', exchange, user, risk_manager, config)
        
        # Get parameters
        params = config.get('parameters', {})
        self.sentiment_threshold_positive = params.get('sentiment_threshold_positive', 0.6)
        self.sentiment_threshold_negative = params.get('sentiment_threshold_negative', 0.4)
        self.news_impact_time_hours = params.get('news_impact_time_hours', 24)
        self.volatility_adjustment = params.get('volatility_adjustment', True)
        self.take_profit_percent = params.get('take_profit_percent', 3.0)
        self.stop_loss_percent = params.get('stop_loss_percent', 2.0)
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Sentiment cache
        self.sentiment_data = {}
        self.last_sentiment_update = 0
        self.sentiment_update_interval = 3600  # 1 hour
        
        # Set update interval
        self.update_interval = 300  # 5 minutes
        
    def _update(self) -> None:
        """
        Update sentiment data
        """
        current_time = time.time()
        
        # Check if sentiment update is needed
        if current_time - self.last_sentiment_update < self.sentiment_update_interval:
            return
            
        try:
            # Update sentiment for all symbols
            for symbol in self.symbols:
                asset = symbol.split('/')[0]  # Extract asset from pair
                
                # Get sentiment data
                sentiment = self.sentiment_analyzer.get_asset_sentiment(asset)
                
                # Store sentiment data
                self.sentiment_data[asset] = {
                    'score': sentiment.get('score', 0.5),
                    'volume': sentiment.get('volume', 0),
                    'timestamp': current_time
                }
                
                logger.info(f"Updated sentiment for {asset}: score={sentiment.get('score', 0.5):.2f}, volume={sentiment.get('volume', 0)}")
                
            # Update last sentiment update time
            self.last_sentiment_update = current_time
            
        except Exception as e:
            logger.error(f"Error updating sentiment data: {str(e)}")
            
    def _generate_signals(self) -> List[TradeSignal]:
        """
        Generate trading signals based on sentiment analysis
        
        Returns:
            List[TradeSignal]: List of trade signals
        """
        signals = []
        
        try:
            # Check each symbol
            for symbol in self.symbols:
                asset = symbol.split('/')[0]  # Extract asset from pair
                
                # Skip if no sentiment data
                if asset not in self.sentiment_data:
                    continue
                    
                sentiment_info = self.sentiment_data[asset]
                sentiment_score = sentiment_info['score']
                sentiment_volume = sentiment_info['volume']
                
                # Skip if sentiment volume is too low
                if sentiment_volume < 10:
                    continue
                    
                # Get current price
                ticker = self.exchange.get_ticker(symbol)
                if not ticker or 'price' not in ticker:
                    continue
                    
                current_price = ticker['price']
                
                # Generate signals based on sentiment
                if sentiment_score >= self.sentiment_threshold_positive:
                    # Positive sentiment: Buy signal
                    take_profit = self.calculate_take_profit_price(current_price, 'buy')
                    stop_loss = self.calculate_stop_loss_price(current_price, 'buy')
                    
                    signal = TradeSignal(
                        symbol=symbol,
                        side='buy',
                        price=current_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        order_type='limit'
                    )
                    
                    signals.append(signal)
                    logger.info(f"Sentiment BUY signal for {symbol} at {current_price} (sentiment: {sentiment_score:.2f})")
                    
                elif sentiment_score <= self.sentiment_threshold_negative:
                    # Negative sentiment: Sell signal
                    take_profit = self.calculate_take_profit_price(current_price, 'sell')
                    stop_loss = self.calculate_stop_loss_price(current_price, 'sell')
                    
                    signal = TradeSignal(
                        symbol=symbol,
                        side='sell',
                        price=current_price,
                        take_profit=take_profit,
                        stop_loss=stop_loss,
                        order_type='limit'
                    )
                    
                    signals.append(signal)
                    logger.info(f"Sentiment SELL signal for {symbol} at {current_price} (sentiment: {sentiment_score:.2f})")
                    
        except Exception as e:
            logger.error(f"Error generating sentiment signals: {str(e)}")
            
        return signals