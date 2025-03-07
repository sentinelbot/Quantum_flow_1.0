# exchange/binance/websocket.py
import logging
import json
import threading
import websocket
from typing import Dict, List, Any, Callable

logger = logging.getLogger(__name__)

class BinanceWebsocket:
    """
    Binance websocket client
    """
    def __init__(self, wss_url: str):
        self.wss_url = wss_url
        self.connections = {}
        self.callbacks = {}
        self.running = True
        
    def start_kline_socket(self, symbol: str, interval: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Start a websocket connection for kline data
        
        Args:
            symbol: Trading pair symbol (lowercase)
            interval: Kline interval (e.g., '1m', '5m', '1h')
            callback: Function to call when data is received
            
        Returns:
            bool: True if successful, False otherwise
        """
        stream_name = f"{symbol.lower()}@kline_{interval}"
        return self._start_socket(stream_name, callback)
        
    def start_ticker_socket(self, symbol: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Start a websocket connection for ticker data
        
        Args:
            symbol: Trading pair symbol (lowercase)
            callback: Function to call when data is received
            
        Returns:
            bool: True if successful, False otherwise
        """
        stream_name = f"{symbol.lower()}@ticker"
        return self._start_socket(stream_name, callback)
        
    def start_depth_socket(self, symbol: str, callback: Callable[[Dict[str, Any]], None], update_speed: str = '1000ms') -> bool:
        """
        Start a websocket connection for depth (order book) data
        
        Args:
            symbol: Trading pair symbol (lowercase)
            callback: Function to call when data is received
            update_speed: Update speed ('1000ms' or '100ms')
            
        Returns:
            bool: True if successful, False otherwise
        """
        stream_name = f"{symbol.lower()}@depth@{update_speed}"
        return self._start_socket(stream_name, callback)
        
    def start_trade_socket(self, symbol: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Start a websocket connection for trade data
        
        Args:
            symbol: Trading pair symbol (lowercase)
            callback: Function to call when data is received
            
        Returns:
            bool: True if successful, False otherwise
        """
        stream_name = f"{symbol.lower()}@trade"
        return self._start_socket(stream_name, callback)
        
    def _start_socket(self, stream_name: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        Start a websocket connection
        
        Args:
            stream_name: Stream name
            callback: Function to call when data is received
            
        Returns:
            bool: True if successful, False otherwise
        """
        if stream_name in self.connections:
            logger.warning(f"Socket already started for {stream_name}")
            return True
            
        try:
            url = f"{self.wss_url}/{stream_name}"
            
            # Register callback
            self.callbacks[stream_name] = callback
            
            # Create websocket connection
            ws = websocket.WebSocketApp(
                url,
                on_message=lambda ws, msg: self._on_message(stream_name, msg),
                on_error=lambda ws, err: self._on_error(stream_name, err),
                on_close=lambda ws, close_code, close_msg: self._on_close(stream_name, close_code, close_msg),
                on_open=lambda ws: self._on_open(stream_name)
            )
            
            # Start connection thread
            thread = threading.Thread(target=ws.run_forever)
            thread.daemon = True
            thread.start()
            
            # Store connection
            self.connections[stream_name] = {
                'ws': ws,
                'thread': thread
            }
            
            logger.info(f"Started websocket for {stream_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting websocket for {stream_name}: {str(e)}")
            return False
            
    def stop_socket(self, stream_name: str) -> bool:
        """
        Stop a websocket connection
        
        Args:
            stream_name: Stream name
            
        Returns:
            bool: True if successful, False otherwise
        """
        if stream_name not in self.connections:
            logger.warning(f"Socket not found for {stream_name}")
            return False
            
        try:
            # Close websocket
            self.connections[stream_name]['ws'].close()
            
            # Remove from connections
            del self.connections[stream_name]
            
            # Remove callback
            if stream_name in self.callbacks:
                del self.callbacks[stream_name]
                
            logger.info(f"Stopped websocket for {stream_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping websocket for {stream_name}: {str(e)}")
            return False
            
    def _on_message(self, stream_name: str, message: str) -> None:
        """
        Handle websocket message
        """
        try:
            data = json.loads(message)
            
            # Call callback
            if stream_name in self.callbacks:
                self.callbacks[stream_name](data)
            else:
                logger.warning(f"No callback found for {stream_name}")
                
        except Exception as e:
            logger.error(f"Error processing message for {stream_name}: {str(e)}")
            
    def _on_error(self, stream_name: str, error: str) -> None:
        """
        Handle websocket error
        """
        logger.error(f"Websocket error for {stream_name}: {error}")
        
        # Attempt to reconnect
        if self.running and stream_name in self.connections:
            logger.info(f"Attempting to reconnect {stream_name}")
            callback = self.callbacks.get(stream_name)
            self.stop_socket(stream_name)
            
            if callback:
                self._start_socket(stream_name, callback)
                
    def _on_close(self, stream_name: str, close_code: int, close_msg: str) -> None:
        """
        Handle websocket close
        """
        logger.info(f"Websocket closed for {stream_name}: {close_code} {close_msg}")
        
        # Attempt to reconnect if unexpected close
        if self.running and stream_name in self.connections:
            logger.info(f"Attempting to reconnect {stream_name}")
            callback = self.callbacks.get(stream_name)
            self.stop_socket(stream_name)
            
            if callback:
                self._start_socket(stream_name, callback)
                
    def _on_open(self, stream_name: str) -> None:
        """
        Handle websocket open
        """
        logger.info(f"Websocket opened for {stream_name}")
        
    def close_all(self) -> None:
        """
        Close all websocket connections
        """
        self.running = False
        
        for stream_name in list(self.connections.keys()):
            self.stop_socket(stream_name)
            
        logger.info("Closed all websocket connections")
