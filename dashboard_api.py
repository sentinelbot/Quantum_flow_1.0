# admin/dashboard_api.py
import logging
import threading
import socket
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from security.auth import authenticate_admin, create_access_token

logger = logging.getLogger(__name__)

class UserResponseModel(BaseModel):
    id: int
    email: str
    status: str
    risk_level: str
    balance: float
    created_at: str
   
class SystemMetricsModel(BaseModel):
    total_users: int
    active_users: int
    total_trades: int
    win_rate: float
    total_profit: float
    system_health: str

class DashboardAPI:
    """
    Dashboard API for QuantumFlow Trading Bot administration
    Provides HTTP endpoints for monitoring and managing the trading system
    """
    def __init__(self, auth_service, user_repository, trade_repository, 
                 analytics_repository, system_monitoring, host="127.0.0.1", port=8080):
        self.auth_service = auth_service
        self.user_repository = user_repository
        self.trade_repository = trade_repository
        self.analytics_repository = analytics_repository
        self.system_monitoring = system_monitoring
        self.host = host
        self.port = port
        self.server = None
        self.app = self._create_app()
        self.server_thread = None
        self.running = False
        self.alternative_ports = [8081, 8082, 8083, 8084, 8085]
        
        logger.info("Dashboard API initialized")
        
    def _create_app(self):
        """Create the FastAPI application with all routes"""
        app = FastAPI(title="QuantumFlow Admin API")
        
        # Add CORS middleware to allow cross-origin requests
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify exact origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        
        @app.post("/token")
        async def login(form_data: OAuth2PasswordRequestForm = Depends()):
            user = authenticate_admin(form_data.username, form_data.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            access_token = create_access_token(data={"sub": user.email})
            return {"access_token": access_token, "token_type": "bearer"}
        
        @app.get("/users", response_model=List[UserResponseModel])
        async def get_users(token: str = Depends(oauth2_scheme)):
            try:
                users = self.user_repository.get_all_users()
                return users
            except Exception as e:
                logger.error(f"Error retrieving users: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving users: {str(e)}"
                )
        
        @app.get("/users/{user_id}")
        async def get_user(user_id: int, token: str = Depends(oauth2_scheme)):
            try:
                user = self.user_repository.get_user_by_id(user_id)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="User not found"
                    )
                return user
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error retrieving user {user_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving user: {str(e)}"
                )
        
        @app.get("/users/active", response_model=List[UserResponseModel])
        async def get_active_users(token: str = Depends(oauth2_scheme)):
            try:
                users = self.user_repository.get_active_users()
                return users
            except Exception as e:
                logger.error(f"Error retrieving active users: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving active users: {str(e)}"
                )
        
        @app.get("/system/metrics", response_model=SystemMetricsModel)
        async def get_system_metrics(token: str = Depends(oauth2_scheme)):
            try:
                # Gather system metrics
                total_users = self.user_repository.count_users()
                active_users = self.user_repository.count_active_users()
                total_trades = self.trade_repository.count_all_trades()
                win_rate = self.analytics_repository.get_overall_win_rate()
                total_profit = self.analytics_repository.get_total_profit()
                system_health = self.system_monitoring.get_health_status()
                
                return {
                    "total_users": total_users,
                    "active_users": active_users,
                    "total_trades": total_trades,
                    "win_rate": win_rate,
                    "total_profit": total_profit,
                    "system_health": system_health
                }
            except Exception as e:
                logger.error(f"Error retrieving system metrics: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving system metrics: {str(e)}"
                )
        
        @app.get("/trades")
        async def get_trades(
            limit: int = 100, 
            offset: int = 0, 
            user_id: Optional[int] = None,
            token: str = Depends(oauth2_scheme)
        ):
            try:
                if user_id:
                    trades = self.trade_repository.get_trades_by_user(user_id, limit, offset)
                else:
                    trades = self.trade_repository.get_all_trades(limit, offset)
                return trades
            except Exception as e:
                logger.error(f"Error retrieving trades: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving trades: {str(e)}"
                )
        
        @app.get("/analytics/summary")
        async def get_analytics_summary(token: str = Depends(oauth2_scheme)):
            try:
                summary = self.analytics_repository.get_summary()
                return summary
            except Exception as e:
                logger.error(f"Error retrieving analytics summary: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving analytics summary: {str(e)}"
                )
        
        @app.get("/system/status")
        async def get_system_status(token: str = Depends(oauth2_scheme)):
            try:
                return self.system_monitoring.get_full_status()
            except Exception as e:
                logger.error(f"Error retrieving system status: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error retrieving system status: {str(e)}"
                )
        
        @app.get("/health")
        async def health_check():
            """Public health check endpoint that doesn't require authentication"""
            return {"status": "ok", "version": "1.0.0"}
        
        return app
    
    def _is_port_available(self, host, port):
        """Check if a port is available by attempting to bind to it"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return True
            except OSError:
                return False
    
    def _find_available_port(self):
        """Find an available port starting with the configured port and fallback to alternatives"""
        # First try the configured port
        if self._is_port_available(self.host, self.port):
            return self.port
        
        logger.warning(f"Port {self.port} is not available. Trying alternative ports.")
        
        # Try alternative ports
        for port in self.alternative_ports:
            if self._is_port_available(self.host, port):
                logger.info(f"Found available port: {port}")
                return port
        
        # If no ports are available, raise an exception
        error_msg = f"No available ports found. Tried {self.port} and {self.alternative_ports}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def start_server(self):
        """Start the dashboard API server in a separate thread with improved error handling"""
        if self.running:
            logger.warning("Dashboard API server is already running")
            return
        
        def run_server():
            try:
                # Find an available port
                port = self._find_available_port()
                logger.info(f"Starting Dashboard API server on {self.host}:{port}")
                
                # Configure Uvicorn with appropriate settings
                config = uvicorn.Config(
                    app=self.app,
                    host=self.host, 
                    port=port,
                    log_level="info",
                    access_log=False,  # Disable access logging for less noise
                )
                server = uvicorn.Server(config)
                server.run()
            except Exception as e:
                logger.error(f"Error in Dashboard API server: {str(e)}")
                self.running = False
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        logger.info("Dashboard API server started")
    
    def stop(self):
        """Stop the dashboard API server"""
        if not self.running:
            logger.warning("Dashboard API server is not running")
            return
        
        # Note: Uvicorn doesn't provide a clean way to stop the server from another thread
        # In a production environment, you might want to use a more sophisticated approach
        # such as sending a shutdown signal or using a process instead of a thread
        
        self.running = False
        logger.info("Dashboard API server stopping (will terminate after current requests complete)")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the Dashboard API server"""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "endpoint_count": len(self.app.routes)
        }