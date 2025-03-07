"""
Database Management Module for QuantumFlow Trading Bot

This module provides comprehensive database management functionality,
including connection pooling, schema validation, optimization, 
and repository management.
"""

import logging
import os
import time
import subprocess
from typing import Optional, Any, Dict, List
import urllib.parse

import psycopg2
from psycopg2 import pool, extensions, extras
from sqlalchemy import create_engine, text, inspect, Table, Column, Boolean
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()

class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass

class Database:
    """Advanced Database interface for QuantumFlow Trading Bot."""
    
    def __init__(self, db_url, max_connections=30, connection_timeout=60):
        """
        Initialize Database with advanced connection management.
        
        Args:
            db_url (str): Database connection URL
            max_connections (int): Maximum number of database connections
            connection_timeout (int): Connection timeout in seconds
        """
        self.db_url = db_url
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        # Core database components
        self.engine = None
        self.SessionFactory = None
        self.connection_pool = None
        
        # State tracking
        self.initialized = False
        self.repositories = {}
        self.schema_validated = False
        self.column_cache = {}
        
        # Logging configuration
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def connect(self):
        """
        Establish a connection to the database.
        Wrapper method for initialize() to ensure compatibility with existing code.
        
        Returns:
            bool: True if connection successful, False otherwise
        
        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            # Log connection attempt
            self.logger.info(f"Attempting to connect to database: {self.db_url}")
            
            # Call initialize method which handles connection setup
            connection_result = self.initialize()
            
            if connection_result:
                # Perform a connection test to ensure robust connectivity
                if self.test_connection():
                    self.logger.info("Database connection established successfully")
                    return True
                else:
                    self.logger.error("Database connection test failed after initialization")
                    return False
            else:
                self.logger.error("Database initialization failed")
                return False
        
        except DatabaseConnectionError as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during database connection: {e}")
            raise DatabaseConnectionError(f"Could not connect to database: {e}")

    def _parse_connection_url(self, url):
        """
        Robustly parse SQLAlchemy connection URL into connection parameters.

        Args:
            url (str): SQLAlchemy connection URL

        Returns:
            dict: Parsed connection parameters
        """
        try:
            # Use urllib.parse for more robust URL parsing
            parsed_url = urllib.parse.urlparse(url)
            
            # Extract credentials and connection details
            credentials = parsed_url.netloc.split('@')
            
            # Handle cases with and without credentials
            if len(credentials) > 1:
                auth, host_port = credentials
                user_pass = auth.split(':')
                user = user_pass[0]
                password = user_pass[1] if len(user_pass) > 1 else ''
                
                # Parse host and port
                host_port = host_port.split(':')
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 5432
            else:
                host_port = credentials[0].split(':')
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 5432
                user = 'quantumuser'
                password = ''
            
            # Get database name from path
            dbname = parsed_url.path.lstrip('/')
            
            return {
                'host': host or 'localhost',
                'port': port,
                'dbname': dbname or 'quantumflow',
                'user': user,
                'password': password
            }
        except Exception as e:
            self.logger.error(f"Failed to parse connection URL: {e}")
            return {
                'host': 'localhost',
                'port': 5432,
                'dbname': 'quantumflow',
                'user': 'quantumuser',
                'password': ''
            }
    
    def initialize(self):
        """
        Advanced database initialization with robust error handling.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info(f"Initializing database connection to {self.db_url}")
            
            # Parse connection parameters
            conn_params = self._parse_connection_url(self.db_url)
            
            # Create database if not exists
            if not database_exists(self.db_url):
                self.logger.warning("Database does not exist. Creating...")
                create_database(self.db_url)
            
            # Configure SQLAlchemy engine with advanced pooling
            self.engine = create_engine(
                self.db_url,
                pool_size=self.max_connections // 2,  # Half for SQLAlchemy
                max_overflow=self.max_connections // 2,  # Remaining for overflow
                pool_timeout=self.connection_timeout,
                pool_recycle=1800,  # Recycle connections every 30 minutes
                pool_pre_ping=True,  # Test connection health before use
                echo=False  # Set to True for SQL logging
            )
            
            # Create scoped session factory
            self.SessionFactory = scoped_session(sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            ))
            
            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            
            # Configure psycopg2 connection pool
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                1,  # Minimum connections
                self.max_connections,  # Maximum connections
                host=conn_params['host'],
                port=conn_params['port'],
                dbname=conn_params['dbname'],
                user=conn_params['user'],
                password=conn_params['password'],
                application_name="QuantumFlow",
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            
            # Validate and fix schema
            self._validate_and_fix_schema()
            
            # Create essential tables
            self.create_essential_tables()
            
            # Mark as initialized
            self.initialized = True
            self.logger.info("Database initialized successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise DatabaseConnectionError(f"Could not initialize database: {e}")

    def create_essential_tables(self):
        """
        Create essential tables that might be missing from the schema
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create user_trading_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_trading_settings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) UNIQUE,
                    trading_mode VARCHAR(10) NOT NULL DEFAULT 'paper',
                    risk_level VARCHAR(10) NOT NULL DEFAULT 'medium',
                    is_paused BOOLEAN DEFAULT false,
                    max_open_positions INTEGER DEFAULT 5,
                    max_position_size DECIMAL(10,5) DEFAULT 0.1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create fee_transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fee_transactions (
                    id SERIAL PRIMARY KEY,
                    trade_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    referrer_id INTEGER,
                    profit_amount DECIMAL(20,10) NOT NULL,
                    fee_amount DECIMAL(20,10) NOT NULL,
                    fee_rate DECIMAL(10,5) NOT NULL,
                    referral_amount DECIMAL(20,10) NOT NULL DEFAULT 0,
                    admin_amount DECIMAL(20,10) NOT NULL,
                    admin_wallet VARCHAR(255),
                    transaction_status VARCHAR(20) DEFAULT 'pending',
                    transaction_hash VARCHAR(255),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            self.logger.info("Essential tables have been created if they were missing")
            return True
        except Exception as e:
            self.logger.error(f"Error creating essential tables: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def _validate_and_fix_schema(self):
        """
        Advanced schema validation and automatic repair.
        """
        if self.schema_validated:
            return
        
        try:
            inspector = inspect(self.engine)
            
            # Define schema requirements
            schema_requirements = {
                "users": {
                    "is_admin": "Boolean DEFAULT false",
                    "is_active": "Boolean DEFAULT true",
                    "is_paused": "Boolean DEFAULT false",
                    "last_login": "TIMESTAMP",
                    "registration_date": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                },
                # Add more tables as needed
            }
            
            for table_name, columns in schema_requirements.items():
                if inspector.has_table(table_name):
                    current_columns = {col['name'] for col in inspector.get_columns(table_name)}
                    
                    # Identify and add missing columns
                    missing_columns = [
                        (col_name, col_type) 
                        for col_name, col_type in columns.items() 
                        if col_name not in current_columns
                    ]
                    
                    if missing_columns:
                        self._add_missing_columns(table_name, missing_columns)
            
            self.schema_validated = True
            
        except Exception as e:
            self.logger.error(f"Advanced schema validation failed: {e}")
    
    def _add_missing_columns(self, table_name, missing_columns):
        """
        Add missing columns with comprehensive error handling.
        
        Args:
            table_name (str): Name of the table
            missing_columns (list): List of (column_name, column_type) tuples
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for col_name, col_type in missing_columns:
                try:
                    # Comprehensive column addition
                    sql = f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                    """
                    self.logger.info(f"Attempting to add column: {col_name} to {table_name}")
                    cursor.execute(sql)
                    
                    # Verify column addition
                    verify_sql = f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}' AND column_name = '{col_name}'
                    """
                    cursor.execute(verify_sql)
                    if cursor.fetchone():
                        self.logger.info(f"Successfully added column '{col_name}' to table '{table_name}'")
                    else:
                        self.logger.warning(f"Could not verify column '{col_name}' in table '{table_name}'")
                    
                except Exception as col_e:
                    self.logger.error(f"Failed to add column '{col_name}': {col_e}")
            
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Comprehensive column addition failed: {e}")
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_connection(self):
        """
        Get a robust database connection with advanced error handling.
        
        Returns:
            psycopg2 connection
        
        Raises:
            DatabaseConnectionError: If connection cannot be established
        """
        if not self.initialized:
            self.initialize()
        
        try:
            conn = self.connection_pool.getconn()
            
            # Additional connection validation
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            
            return conn
        except Exception as e:
            self.logger.error(f"Connection retrieval failed: {e}")
            raise DatabaseConnectionError(f"Could not get database connection: {e}")
    
    def release_connection(self, conn):
        """
        Safely return connection to the pool.
        
        Args:
            conn: Database connection to release
        """
        try:
            if self.connection_pool:
                self.connection_pool.putconn(conn)
        except Exception as e:
            self.logger.error(f"Failed to release connection: {e}")
    
    def execute_query(self, query, params=None, fetch_all=True):
        """
        Execute a query with comprehensive error handling.
        
        Args:
            query (str): SQL query to execute
            params (dict, optional): Query parameters
            fetch_all (bool): Whether to fetch all results
        
        Returns:
            Query results or number of affected rows
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=extras.DictCursor)
            
            cursor.execute(query, params or {})
            
            if fetch_all:
                result = cursor.fetchall()
                return [dict(row) for row in result]
            else:
                conn.commit()
                return cursor.rowcount
        
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.release_connection(conn)
    
    def full_backup(self, backup_dir=None):
        """
        Perform a comprehensive database backup.
        
        Args:
            backup_dir (str, optional): Custom backup directory
        
        Returns:
            str: Path to backup file
        """
        try:
            # Determine backup directory
            if not backup_dir:
                backup_dir = os.path.join(os.getcwd(), 'database_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Parse connection details
            conn_params = self._parse_connection_url(self.db_url)
            dbname = conn_params['dbname']
            
            # Generate unique backup filename
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f"{dbname}_backup_{timestamp}.sql")
            
            # Construct pg_dump command
            pg_dump_cmd = [
                'pg_dump',
                '-h', conn_params['host'],
                '-p', str(conn_params['port']),
                '-U', conn_params['user'],
                '-d', dbname,
                '-f', backup_file,
                '-F', 'p',  # Plain text format
                '-v'  # Verbose mode
            ]
            
            # Set environment variable for password
            env = os.environ.copy()
            if conn_params['password']:
                env['PGPASSWORD'] = conn_params['password']
            
            # Execute backup
            result = subprocess.run(
                pg_dump_cmd, 
                env=env, 
                capture_output=True, 
                text=True
            )
            
            # Check backup result
            if result.returncode != 0:
                self.logger.error(f"Backup failed: {result.stderr}")
                raise Exception(f"Backup failed: {result.stderr}")
            
            self.logger.info(f"Database backup completed: {backup_file}")
            return backup_file
        
        except Exception as e:
            self.logger.error(f"Backup process failed: {e}")
            raise
    
    def optimize_database(self):
        """
        Comprehensive database optimization routine.
        
        Returns:
            bool: Optimization success status
        """
        try:
            self.logger.info("Starting comprehensive database optimization")
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Perform VACUUM FULL to reclaim space and update statistics
            cursor.execute("VACUUM FULL ANALYZE")
            
            # Reindex all tables to optimize index performance
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'""")
            tables = cursor.fetchall()
            
            for (table,) in tables:
                try:
                    cursor.execute(f"REINDEX TABLE {table}")
                    self.logger.info(f"Reindexed table: {table}")
                except Exception as table_e:
                    self.logger.warning(f"Reindex failed for {table}: {table_e}")
            
            conn.commit()
            cursor.close()
            
            self.logger.info("Database optimization completed successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Database optimization failed: {e}")
            return False
        finally:
            if conn:
                self.release_connection(conn)
    
    def close(self):
        """
        Gracefully close all database connections and resources.
        """
        try:
            self.logger.info("Initiating database connection closure")
            
            # Close connection pool
            if self.connection_pool:
                self.connection_pool.closeall()
                self.connection_pool = None
            
            # Close SQLAlchemy session factory
            if self.SessionFactory:
                self.SessionFactory.remove()# Dispose of SQLAlchemy engine
            if self.engine:
                self.engine.dispose()
            
            # Reset initialization state
            self.initialized = False
            self.repositories.clear()
            
            self.logger.info("All database connections and resources closed successfully")
        
        except Exception as e:
            self.logger.error(f"Error during database connection closure: {e}")
    
    def get_repository(self, repo_name):
        """
        Advanced repository retrieval with dynamic import and caching.
        
        Args:
            repo_name (str): Name of the repository to retrieve
        
        Returns:
            Repository instance
        
        Raises:
            ValueError: If repository cannot be found
        """
        # Check cache first
        if repo_name in self.repositories:
            self.logger.debug(f"Returning cached repository: {repo_name}")
            return self.repositories[repo_name]
        
        self.logger.info(f"Creating repository instance for: {repo_name}")
        
        try:
            # Dynamic repository import based on name
            repository_map = {
                'user': ('database.repository.user_repository', 'UserRepository'),
                'trade': ('database.repository.trade_repository', 'TradeRepository'),
                'position': ('database.repository.position_repository', 'PositionRepository'),
                'analytics': ('database.repository.analytics_repository', 'AnalyticsRepository')
            }
            
            if repo_name not in repository_map:
                raise ValueError(f"Unknown repository: {repo_name}")
            
            # Import the repository dynamically
            module_path, class_name = repository_map[repo_name]
            module = __import__(module_path, fromlist=[class_name])
            repository_class = getattr(module, class_name)
            
            # Instantiate and cache the repository
            self.repositories[repo_name] = repository_class(self)
            
            return self.repositories[repo_name]
        
        except ImportError as e:
            self.logger.error(f"Failed to import repository {repo_name}: {e}")
            raise ValueError(f"Repository {repo_name} could not be imported")
        except AttributeError as e:
            self.logger.error(f"Repository class not found for {repo_name}: {e}")
            raise ValueError(f"Repository class not found for {repo_name}")
    
    def get_session(self):
        """
        Get a thread-local SQLAlchemy session.
        
        Returns:
            SQLAlchemy session
        """
        if not self.initialized:
            self.initialize()
        
        return self.SessionFactory()
    
    def test_connection(self):
        """
        Comprehensive database connection test.
        
        Returns:
            bool: Connection test result
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Perform multiple connection tests
            tests = [
                "SELECT 1 AS connection_test",
                "SELECT current_database()",
                "SELECT version()"
            ]
            
            for test in tests:
                cursor.execute(test)
                result = cursor.fetchone()
                self.logger.debug(f"Connection test passed: {test}")
            
            cursor.close()
            self.release_connection(conn)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Comprehensive connection test failed: {e}")
            return False

# Alias for backward compatibility
DatabaseManager = Database

# Function to get a database connection (for legacy code compatibility)
def get_db_connection():
    """
    Legacy function to get a database connection.
    This is for backward compatibility with older modules.
    
    Returns:
        A database connection
    """
    from config.app_config import AppConfig
    
    config = AppConfig("config/settings.json")
    db_url = f"postgresql://{config.get('database.username')}:{config.get('database.password')}@{config.get('database.host')}:{config.get('database.port')}/{config.get('database.name')}"
    
    db_manager = DatabaseManager(db_url)
    db_manager.initialize()
    return db_manager.get_connection()

# Optional: Logging configuration for database module
def configure_database_logging(log_level=logging.INFO):
    """
    Configure logging for the database module.
    
    Args:
        log_level (int): Logging level (default: logging.INFO)
    """
    logging.getLogger(__name__).setLevel(log_level)

# Export key classes and functions
__all__ = [
    'Database', 
    'DatabaseManager', 
    'Base', 
    'DatabaseConnectionError', 
    'configure_database_logging',
    'get_db_connection'
]