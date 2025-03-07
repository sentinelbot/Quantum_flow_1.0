"""
Binance Exchange Implementation
"""

import logging
import time
import hmac
import hashlib
import requests
from typing import Dict, List, Optional, Any
import json
import uuid
import websocket
import threading

from exchange.abstract_exchange import AbstractExchange, TradeResult, TradingSignal
from security.api_key_manager import ApiKeyManager
from services.user_trading_manager import UserTradingManager

logger = logging.getLogger(__name__)

class BinanceExchange(AbstractExchange):
    """
    Binance Exchange API implementation
    """
    
    BASE_URL = "https://api.binance.com"
    BASE_URL_V3 = "https://api.binance.com/api/v3"
    WS_URL = "wss://stream.binance.com:9443/ws"
    
    def __init__(self, api_key: str, api_secret: str, user=None, db=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.user = user
        self.db = db
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })
        self.ws = None
        self.ws_thread = None
        self.running = False
        self.initialized = False
        self.logger = logger
        
    def initialize(self) -> bool:
        """
        Initialize the exchange connection
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Verify API keys first
            if not self.verify_api_keys():
                return False
                
            # Test connection and permissions
            result = self._make_request("GET", "/api/v3/account", {}, signed=True)
            if 'balances' in result:
                self.initialized = True
                logger.info("Binance exchange initialized successfully")
                return True
            else:
                logger.error("Failed to initialize Binance exchange: Invalid API response")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize Binance exchange: {str(e)}")
            return False
    
    def verify_api_keys(self) -> bool:
        """
        Verify that the API keys are valid and have correct permissions
        """
        key_manager = ApiKeyManager()
        is_valid, error = key_manager.verify_binance_keys(self.api_key, self.api_secret)
        if not is_valid:
            logger.error(f"Binance API key verification failed: {error}")
            return False
        logger.info("Binance API keys verified successfully")
        return True
    
    def close(self) -> None:
        """
        Close the exchange connection
        """
        try:
            self.initialized = False
            if self.ws:
                self.running = False
                self.ws.close()
                if self.ws_thread:
                    self.ws_thread.join(timeout=2)
            logger.info("Binance exchange connection closed")
        except Exception as e:
            logger.error(f"Error closing Binance exchange connection: {str(e)}")
    
    def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance
        
        Returns:
            Dict mapping asset symbols to amounts
        """
        if not self.initialized:
            logger.error("Binance exchange not initialized")
            return {}
        
        try:
            result = self._make_request("GET", "/api/v3/account", {}, signed=True)
            balances = {}
            for asset in result.get('balances', []):
                free = float(asset.get('free', 0))
                locked = float(asset.get('locked', 0))
                total = free + locked
                if total > 0:
                    balances[asset.get('asset')] = total
            return balances
        except Exception as e:
            logger.error(f"Error getting account balance: {str(e)}")
            return {}
    
    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Current price or None if unavailable
        """
        try:
            result = self._make_request("GET", "/api/v3/ticker/price", {'symbol': symbol})
            if 'price' in result:
                return float(result['price'])
            return None
        except Exception as e:
            logger.error(f"Error getting ticker price for {symbol}: {str(e)}")
            return None
    
    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, List]:
        """
        Get orderbook for a symbol
        
        Args:
            symbol: Trading pair symbol
            limit: Number of price levels to retrieve
            
        Returns:
            Orderbook with bids and asks
        """
        try:
            result = self._make_request("GET", "/api/v3/depth", {
                'symbol': symbol,
                'limit': limit
            })
            return {
                'bids': [[float(bid[0]), float(bid[1])] for bid in result.get('bids', [])],
                'asks': [[float(ask[0]), float(ask[1])] for ask in result.get('asks', [])]
            }
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {str(e)}")
            return {'bids': [], 'asks': []}
    
    def get_historical_klines(self, symbol: str, interval: str, 
                             start_time: Optional[int] = None, 
                             end_time: Optional[int] = None,
                             limit: int = 500) -> List[Dict]:
        """
        Get historical candlestick data
        
        Args:
            symbol: Trading pair symbol
            interval: Timeframe interval (e.g., '1m', '1h', '1d')
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Maximum number of candles
            
        Returns:
            List of candlestick data
        """
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            if start_time:
                params['startTime'] = start_time
            if end_time:
                params['endTime'] = end_time
                
            result = self._make_request("GET", "/api/v3/klines", params)
            
            # Convert to more usable format
            klines = []
            for k in result:
                klines.append({
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': k[6],
                    'quote_volume': float(k[7]),
                    'trades': k[8],
                    'taker_buy_base': float(k[9]),
                    'taker_buy_quote': float(k[10])
                })
            return klines
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {str(e)}")
            return []
    
    def execute_trade(self, signal):
        """Execute a trade based on the given signal"""
        try:
            # Validate required signal properties
            required_props = ['symbol', 'side', 'quantity']
            for prop in required_props:
                if not hasattr(signal, prop) or getattr(signal, prop) is None:
                    self.logger.error(f"Missing required signal property: {prop}")
                    return None
            
            # Determine trading mode from user settings
            trading_manager = UserTradingManager(self.db)
            settings = trading_manager.get_trading_settings(self.user.id)
            
            trading_mode = settings.get('trading_mode', 'paper') if settings else 'paper'
            
            if trading_mode == 'paper':
                # Paper trading - simulate execution
                return self._execute_paper_trade(signal)
            else:
                # Live trading - actual execution
                return self._execute_live_trade(signal)
        
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return None
    
    def _execute_paper_trade(self, signal):
        """Simulate a trade execution for paper trading"""
        try:
            # Generate a unique order ID
            order_id = f"paper-{uuid.uuid4()}"
            
            # Fetch current market price if no specific price provided
            current_price = self.get_ticker_price(signal.symbol) if not hasattr(signal, 'price') or signal.price is None else signal.price
            
            # Create a mock trade result
            trade_result = TradeResult(
                trade_id=order_id,
                symbol=signal.symbol,
                side=signal.side,
                price=current_price,
                quantity=signal.quantity,
                timestamp=int(time.time() * 1000),
                success=True
            )
            
            self.logger.info(f"Paper trade executed: {signal.symbol} {signal.side} {signal.quantity} @ {current_price}")
            return trade_result
        
        except Exception as e:
            self.logger.error(f"Error executing paper trade: {e}")
            return None
    
    def _execute_live_trade(self, signal):
        """Execute a live trade on Binance"""
        try:
            # Prepare API request
            endpoint = f"{self.BASE_URL}/api/v3/order"
            timestamp = int(time.time() * 1000)
            
            # Order parameters
            params = {
                'symbol': signal.symbol.replace('/', ''),  # Remove / from trading pair
                'side': signal.side.upper(),
                'type': 'LIMIT' if hasattr(signal, 'price') and signal.price else 'MARKET',
                'timeInForce': 'GTC' if hasattr(signal, 'price') and signal.price else None,
                'quantity': signal.quantity,
            }
            
            # Add price for limit orders
            if hasattr(signal, 'price') and signal.price:
                params['price'] = signal.price
            
            # Add optional parameters if available
            if hasattr(signal, 'stop_loss') and signal.stop_loss:
                params['stopPrice'] = signal.stop_loss
            
            if hasattr(signal, 'client_order_id') and signal.client_order_id:
                params['newClientOrderId'] = signal.client_order_id
            
            # Add timestamp and generate signature
            params['timestamp'] = timestamp
            params['signature'] = self._generate_signature(params)
            
            # Make API request
            headers = {'X-MBX-APIKEY': self.api_key}
            response = self.session.post(endpoint, headers=headers, data=params)
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                
                # Create trade result
                trade_result = TradeResult(
                    trade_id=str(result['orderId']),
                    symbol=result['symbol'],
                    side=result['side'],
                    price=float(result.get('price', 0)),
                    quantity=float(result['executedQty']),
                    timestamp=result['transactTime'],
                    success=True
                )
                
                self.logger.info(f"Live trade executed: {signal.symbol} {signal.side} {signal.quantity}")
                return trade_result
            else:
                self.logger.error(f"API error: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            self.logger.error(f"Error executing live trade: {e}")
            return None
    
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an open order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self._make_request("DELETE", "/api/v3/order", {
                'symbol': symbol,
                'orderId': order_id
            }, signed=True)
            
            return 'orderId' in result
        except Exception as e:
            logger.error(f"Error canceling order: {str(e)}")
            return False
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open orders
        
        Args:
            symbol: Trading pair symbol (optional)
            
        Returns:
            List of open orders
        """
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol
                
            result = self._make_request("GET", "/api/v3/openOrders", params, signed=True)
            return result
        except Exception as e:
            logger.error(f"Error getting open orders: {str(e)}")
            return []
    
    def get_order_status(self, symbol: str, order_id: str) -> Optional[Dict]:
        """
        Get status of a specific order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            Order status or None if not found
        """
        try:
            result = self._make_request("GET", "/api/v3/order", {
                'symbol': symbol,
                'orderId': order_id
            }, signed=True)
            
            return result
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            return None
    
    def _generate_signature(self, params: Dict) -> str:
        """
        Generate signature for authenticated requests
        
        Args:
            params: Request parameters
            
        Returns:
            HMAC SHA256 signature
        """
        query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Dict, signed: bool = False) -> Dict:
        """
        Make HTTP request to Binance API
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether request requires signature
            
        Returns:
            Response JSON
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
            
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, data=params)
            elif method == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    def start_websocket_stream(self, symbols: List[str], callback: Any):
        """
        Start a WebSocket stream for given symbols
        
        Args:
            symbols: List of trading symbols to stream
            callback: Function to handle incoming WebSocket messages
        """
        try:
            # Prepare WebSocket connection
            self.running = True
            
            # Create WebSocket streams for each symbol
            streams = [f"{symbol.lower()}@trade" for symbol in symbols]
            stream_url = f"{self.WS_URL}/{'/'.join(streams)}"
            
            def on_message(ws, message):
                """Handle incoming WebSocket messages"""
                if self.running:
                    try:
                        data = json.loads(message)
                        callback(data)
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
            
            def on_error(ws, error):
                """Handle WebSocket errors"""
                logger.error(f"WebSocket error: {error}")
                self.running = False
            
            def on_close(ws, close_status_code, close_msg):
                """Handle WebSocket closure"""
                logger.info("WebSocket connection closed")
                self.running = False
            
            def on_open(ws):
                """Handle WebSocket connection open"""
                logger.info("WebSocket connection established")
            
            # Create and start WebSocket connection
            self.ws = websocket.WebSocketApp(
                stream_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"Error starting WebSocket stream: {e}")
            self.running = False
    
    def stop_websocket_stream(self):
        """
        Stop the active WebSocket stream
        """
        try:
            self.running = False
            if self.ws:
                self.ws.close()
            
            if self.ws_thread:
                self.ws_thread.join(timeout=2)
                
            logger.info("WebSocket stream stopped")
        except Exception as e:
            logger.error(f"Error stopping WebSocket stream: {e}")
    
    def calculate_position_size(self, symbol: str, risk_percentage: float, stop_loss_price: float) -> float:
        """
        Calculate optimal position size based on account balance and risk management
        
        Args:
            symbol: Trading pair symbol
            risk_percentage: Maximum percentage of account to risk on trade
            stop_loss_price: Stop loss price for the trade
            
        Returns:
            Optimal position size in base asset
        """
        try:
            # Get account balance
            balances = self.get_account_balance()
            
            # Get current ticker price
            current_price = self.get_ticker_price(symbol)
            
            if not current_price or 'USDT' not in balances:
                logger.error("Unable to calculate position size")
                return 0
            
            # Calculate total account value in USDT
            total_account_value = balances.get('USDT', 0)
            
            # Calculate risk amount
            risk_amount = total_account_value * (risk_percentage / 100)
            
            # Calculate position size
            # Risk amount = Position Size * (Entry Price - Stop Loss Price)
            position_size = risk_amount / abs(current_price - stop_loss_price)
            
            return position_size
        
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0