# analysis/sentiment_analyzer.py
import logging
import time
import random
from typing import Dict, List, Any, Optional
import json
import re
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Sentiment analysis system for cryptocurrency assets
    """
    def __init__(self):
        # Cache for sentiment data
        self.sentiment_cache = {}
        self.last_update = {}
        self.cache_expiry = 3600  # 1 hour
        
        # Mock data for demonstration (in a real implementation, this would use APIs)
        self.mock_sentiment_data = {}
        self._initialize_mock_data()
        
        logger.info("Sentiment analyzer initialized")
        
    def _initialize_mock_data(self) -> None:
        """
        Initialize mock sentiment data for demonstration
        """
        assets = ['BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 'LINK', 'UNI']
        
        for asset in assets:
            self.mock_sentiment_data[asset] = {
                'score': random.uniform(0.3, 0.7),
                'volume': random.randint(100, 1000),
                'sources': {
                    'twitter': random.uniform(0.2, 0.8),
                    'reddit': random.uniform(0.2, 0.8),
                    'news': random.uniform(0.2, 0.8)
                },
                'keywords': [
                    {'word': 'bullish', 'count': random.randint(10, 100)},
                    {'word': 'bearish', 'count': random.randint(10, 100)},
                    {'word': 'moon', 'count': random.randint(5, 50)},
                    {'word': 'dump', 'count': random.randint(5, 50)},
                    {'word': 'buy', 'count': random.randint(20, 200)},
                    {'word': 'sell', 'count': random.randint(20, 200)}
                ]
            }
            
    def get_asset_sentiment(self, asset: str) -> Dict[str, Any]:
        """
        Get sentiment analysis for an asset
        
        Args:
            asset: Asset symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            Dict[str, Any]: Sentiment data
        """
        try:
            # Check if asset is in cache and if cache is valid
            current_time = time.time()
            cache_valid = (
                asset in self.sentiment_cache and
                asset in self.last_update and
                current_time - self.last_update[asset] < self.cache_expiry
            )
            
            if cache_valid:
                return self.sentiment_cache[asset]
                
            # In a real implementation, this would call external APIs
            # For demonstration, we'll use mock data
            if asset in self.mock_sentiment_data:
                sentiment_data = self._get_mock_sentiment(asset)
            else:
                # Generate random sentiment for unknown assets
                sentiment_data = {
                    'score': random.uniform(0.3, 0.7),
                    'volume': random.randint(10, 100),
                    'sources': {
                        'twitter': random.uniform(0.2, 0.8),
                        'reddit': random.uniform(0.2, 0.8),
                        'news': random.uniform(0.2, 0.8)
                    },
                    'keywords': []
                }
                
            # Update cache
            self.sentiment_cache[asset] = sentiment_data
            self.last_update[asset] = current_time
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Error getting sentiment for {asset}: {str(e)}")
            return {
                'score': 0.5,  # Neutral
                'volume': 0,
                'sources': {},
                'keywords': []
            }
            
    def _get_mock_sentiment(self, asset: str) -> Dict[str, Any]:
        """
        Get mock sentiment data for demonstration
        
        Args:
            asset: Asset symbol
            
        Returns:
            Dict[str, Any]: Mock sentiment data
        """
        base_data = self.mock_sentiment_data.get(asset, {
            'score': 0.5,
            'volume': 0,
            'sources': {},
            'keywords': []
        })
        
        # Add some randomness to simulate changing sentiment
        sentiment_change = random.uniform(-0.1, 0.1)
        volume_change = random.randint(-50, 50)
        
        # Ensure score stays between 0 and 1
        new_score = max(0, min(1, base_data['score'] + sentiment_change))
        new_volume = max(0, base_data['volume'] + volume_change)
        
        # Update sources with random changes
        new_sources = {}
        for source, score in base_data.get('sources', {}).items():
            new_sources[source] = max(0, min(1, score + random.uniform(-0.05, 0.05)))
            
        # Create sentiment data
        sentiment_data = {
            'score': new_score,
            'volume': new_volume,
            'sources': new_sources,
            'keywords': base_data.get('keywords', []),
            'timestamp': int(time.time())
        }
        
        return sentiment_data
        
    def get_market_news(self, asset: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent market news
        
        Args:
            asset: Asset symbol (optional)
            limit: Maximum number of news items
            
        Returns:
            List[Dict[str, Any]]: News items
        """
        try:
            # In a real implementation, this would call a news API
            # For demonstration, we'll generate mock news
            news = []
            
            current_time = int(time.time())
            
            # Generate generic news items
            generic_news = [
                "Market Analysis: Bitcoin Shows Signs of Recovery",
                "Ethereum Gas Fees Drop to 6-Month Low",
                "Analysts Predict Bull Run in Coming Months",
                "Major Exchange Adds Support for New Assets",
                "Regulatory Concerns Impact Crypto Markets",
                "Institutional Investors Increase Crypto Holdings",
                "DeFi Protocols See Surge in Total Value Locked",
                "NFT Sales Reach New Heights",
                "Central Bank Digital Currencies Gain Traction",
                "Crypto Mining Difficulty Adjusts After Price Movements"
            ]
            
            # Generate asset-specific news items
            asset_news = {
                'BTC': [
                    "Bitcoin Hashrate Reaches All-Time High",
                    "Bitcoin Mining Difficulty Adjustment Expected Next Week",
                    "On-Chain Metrics Show Strong Bitcoin Accumulation",
                    "Bitcoin Exchange Reserves Continue to Decline",
                    "Bitcoin Lightning Network Capacity Grows by 20%"
                ],
                'ETH': [
                    "Ethereum Staking Rewards Analysis",
                    "Ethereum Layer 2 Solutions Gain Adoption",
                    "Ethereum Gas Optimization Strategies",
                    "Ethereum Foundation Announces Grants",
                    "Ethereum EIP-1559 Burns Over 1 Million ETH"
                ],
                'BNB': [
                    "Binance Coin Used for Ecosystem Expansion",
                    "BNB Chain Introduces New Scaling Solution",
                    "BNB Burn Event Scheduled for Next Week",
                    "BNB Chain DApps Surpass 1 Million Users",
                    "BNB Chain Integrates with Major Payment Provider"
                ]
            }
            
            # Select news items based on asset
            if asset and asset in asset_news:
                news_items = asset_news[asset]
                remaining = limit - len(news_items)
                if remaining > 0:
                    news_items.extend(generic_news[:remaining])
            else:
                news_items = generic_news[:limit]
                
            # Create news objects
            for i, title in enumerate(news_items):
                # Generate random timestamp within the last 24 hours
                random_time = current_time - random.randint(0, 86400)
                
                # Generate random sentiment score
                sentiment_score = random.uniform(0.3, 0.7)
                
                news.append({
                    'id': f"news_{i}",
                    'title': title,
                    'summary': f"This is a summary of the news about {title.lower()}.",
                    'source': random.choice(['CoinDesk', 'CoinTelegraph', 'Bloomberg', 'Reuters', 'CryptoNews']),
                    'url': f"https://example.com/news/{i}",
                    'timestamp': random_time,
                    'sentiment_score': sentiment_score
                })
                
            # Sort by timestamp (newest first)
            news.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return news[:limit]
            
        except Exception as e:
            logger.error(f"Error getting market news: {str(e)}")
            return []
            
    def get_social_metrics(self, asset: str) -> Dict[str, Any]:
        """
        Get social media metrics for an asset
        
        Args:
            asset: Asset symbol
            
        Returns:
            Dict[str, Any]: Social media metrics
        """
        try:
            # In a real implementation, this would call social media APIs
            # For demonstration, we'll generate mock data
            
            # Generate random metrics
            twitter_followers = random.randint(10000, 1000000)
            twitter_mentions = random.randint(1000, 10000)
            reddit_subscribers = random.randint(5000, 500000)
            reddit_active_users = random.randint(500, 5000)
            
            # Generate random sentiment scores
            twitter_sentiment = random.uniform(0.3, 0.7)
            reddit_sentiment = random.uniform(0.3, 0.7)
            
            # Generate historical data
            historical_data = []
            for i in range(7):  # Last 7 days
                day = int(time.time()) - (6 - i) * 86400
                historical_data.append({
                    'date': day,
                    'twitter_mentions': random.randint(800, 12000),
                    'reddit_posts': random.randint(50, 500),
                    'sentiment_score': random.uniform(0.3, 0.7)
                })
                
            return {
                'twitter': {
                    'followers': twitter_followers,
                    'mentions_24h': twitter_mentions,
                    'sentiment_score': twitter_sentiment
                },
                'reddit': {
                    'subscribers': reddit_subscribers,
                    'active_users': reddit_active_users,
                    'sentiment_score': reddit_sentiment
                },
                'historical_data': historical_data,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error getting social metrics for {asset}: {str(e)}")
            return {
                'twitter': {},
                'reddit': {},
                'historical_data': [],
                'timestamp': int(time.time())
            }
            
    def get_market_fear_greed_index(self) -> Dict[str, Any]:
        """
        Get market fear and greed index
        
        Returns:
            Dict[str, Any]: Fear and greed index data
        """
        try:
            # In a real implementation, this would call an API
            # For demonstration, we'll generate mock data
            
            # Generate random value between 0 (extreme fear) and 100 (extreme greed)
            value = random.randint(20, 80)
            
            # Determine classification
            if value <= 25:
                classification = "Extreme Fear"
            elif value <= 45:
                classification = "Fear"
            elif value <= 55:
                classification = "Neutral"
            elif value <= 75:
                classification = "Greed"
            else:
                classification = "Extreme Greed"
                
            # Generate historical data
            historical_data = []
            for i in range(30):  # Last 30 days
                day = int(time.time()) - (29 - i) * 86400
                # Generate value with some correlation to previous value
                if i > 0:
                    prev_value = historical_data[i-1]['value']
                    new_value = max(0, min(100, prev_value + random.randint(-10, 10)))
                else:
                    new_value = random.randint(20, 80)
                    
                historical_data.append({
                    'date': day,
                    'value': new_value
                })
                
            return {
                'value': value,
                'classification': classification,
                'historical_data': historical_data,
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error getting fear and greed index: {str(e)}")
            return {
                'value': 50,
                'classification': "Neutral",
                'historical_data': [],
                'timestamp': int(time.time())
            }
