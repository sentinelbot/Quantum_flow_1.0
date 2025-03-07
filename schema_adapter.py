import logging
import os
import json
from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)

class SchemaAdapter:
    """
    Utility class to handle schema differences and enable graceful operation
    with incomplete database schemas.
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.column_cache = {}
        self.logger = logging.getLogger(__name__)
    
    def has_column(self, table_name, column_name):
        """
        Check if a column exists in a table
        
        Args:
            table_name: Name of the table to check
            column_name: Name of the column to look for
            
        Returns:
            bool: True if column exists, False otherwise
        """
        cache_key = f"{table_name}.{column_name}"
        
        # Return cached result if available
        if cache_key in self.column_cache:
            return self.column_cache[cache_key]
            
        # Check database schema
        try:
            session = self.db.get_session()
            inspector = inspect(self.db.engine)
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            result = column_name in columns
            self.column_cache[cache_key] = result
            return result
        except Exception as e:
            self.logger.error(f"Error checking column existence: {str(e)}")
            return False
        finally:
            session.close()
            
    def safe_query(self, model_class, filters=None):
        """
        Build a query that works regardless of schema differences
        
        Args:
            model_class: SQLAlchemy model class
            filters: Dictionary of filters to apply
            
        Returns:
            SQLAlchemy query object or None if error
        """
        try:
            session = self.db.get_session()
            query = session.query(model_class)
            
            if filters:
                for column, value in filters.items():
                    # Check if column exists before filtering on it
                    if self.has_column(model_class.__tablename__, column):
                        query = query.filter(getattr(model_class, column) == value)
            
            return query
        except Exception as e:
            self.logger.error(f"Error building safe query: {str(e)}")
            return None
            
    def validate_and_fix_schema(self):
        """Validate the database schema and fix any issues"""
        conn = None
        try:
            # Get a connection to the database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Get all expected tables from schema definition
            expected_tables = self._get_expected_tables()
            
            # Check for each expected table
            for table_name, table_definition in expected_tables.items():
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """, (table_name,))
                
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    # Create the missing table
                    self.logger.warning(f"Table {table_name} is missing. Creating it now.")
                    create_table_query = self._generate_create_table_query(table_name, table_definition)
                    cursor.execute(create_table_query)
                    self.logger.info(f"Created missing table: {table_name}")
                else:
                    # Table exists, check for missing columns
                    expected_columns = table_definition.get('columns', {})
                    for column_name, column_def in expected_columns.items():
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.columns 
                                WHERE table_schema = 'public' 
                                AND table_name = %s
                                AND column_name = %s
                            );
                        """, (table_name, column_name))
                        
                        column_exists = cursor.fetchone()[0]
                        
                        if not column_exists:
                            # Add the missing column
                            self.logger.warning(f"Column {column_name} is missing in table {table_name}. Adding it now.")
                            add_column_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};"
                            cursor.execute(add_column_query)
                            self.logger.info(f"Added missing column: {table_name}.{column_name}")
            
            # Commit all changes
            conn.commit()
            # Clear column cache after schema changes
            self.column_cache = {}
            self.logger.info("Schema validation and fixing completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error validating and fixing schema: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.db.release_connection(conn)
                
    def _generate_create_table_query(self, table_name, table_definition):
        """Generate a CREATE TABLE query from the table definition"""
        columns = table_definition.get('columns', {})
        constraints = table_definition.get('constraints', [])
        
        column_defs = []
        for column_name, column_def in columns.items():
            column_defs.append(f"{column_name} {column_def}")
        
        query = f"CREATE TABLE {table_name} (\n"
        query += ",\n".join(column_defs)
        
        if constraints:
            query += ",\n" + ",\n".join(constraints)
        
        query += "\n);"
        return query
        
    def _get_expected_tables(self):
        """Get the expected tables and their definitions from configuration"""
        # This method should return a dictionary with table names as keys
        # and their definitions (columns and constraints) as values
        # You can load this from a JSON file or define it programmatically
        schema_file_path = os.path.join(os.path.dirname(__file__), '../config/database_schema.json')
        
        try:
            with open(schema_file_path, 'r') as schema_file:
                return json.load(schema_file)
        except Exception as e:
            self.logger.error(f"Error loading schema definition: {str(e)}")
            # Return a minimal schema definition as fallback
            return {
                "users": {
                    "columns": {
                        "id": "SERIAL PRIMARY KEY",
                        "email": "VARCHAR(255) NOT NULL UNIQUE",
                        "telegram_id": "VARCHAR(255) UNIQUE",
                        "is_active": "BOOLEAN DEFAULT true",
                        "is_admin": "BOOLEAN DEFAULT false",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    }
                },
                "user_trading_settings": {
                    "columns": {
                        "id": "SERIAL PRIMARY KEY",
                        "user_id": "INTEGER NOT NULL",
                        "trading_mode": "VARCHAR(10) NOT NULL DEFAULT 'paper'",
                        "risk_level": "VARCHAR(10) NOT NULL DEFAULT 'medium'",
                        "is_paused": "BOOLEAN DEFAULT false",
                        "max_open_positions": "INTEGER DEFAULT 5",
                        "max_position_size": "DECIMAL(10,5) DEFAULT 0.1",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    },
                    "constraints": [
                        "CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)",
                        "CONSTRAINT unique_user_id UNIQUE (user_id)"
                    ]
                },
                "fee_transactions": {
                    "columns": {
                        "id": "SERIAL PRIMARY KEY",
                        "trade_id": "INTEGER NOT NULL",
                        "user_id": "INTEGER NOT NULL",
                        "referrer_id": "INTEGER",
                        "profit_amount": "DECIMAL(20,10) NOT NULL",
                        "fee_amount": "DECIMAL(20,10) NOT NULL",
                        "fee_rate": "DECIMAL(10,5) NOT NULL",
                        "referral_amount": "DECIMAL(20,10) NOT NULL DEFAULT 0",
                        "admin_amount": "DECIMAL(20,10) NOT NULL",
                        "admin_wallet": "VARCHAR(255)",
                        "transaction_status": "VARCHAR(20) DEFAULT 'pending'",
                        "transaction_hash": "VARCHAR(255)",
                        "notes": "TEXT",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                    }
                }
                # Add other tables as needed
            }

    def refresh_schema_cache(self):
        """
        Clear the column cache to force re-checking of schema
        Useful after schema changes have been made
        """
        self.column_cache = {}
        self.logger.info("Schema cache has been refreshed")
        
    def get_existing_tables(self):
        """
        Get a list of all existing tables in the database
        
        Returns:
            list: List of table names
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE';
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        except Exception as e:
            self.logger.error(f"Error getting existing tables: {str(e)}")
            return []
        finally:
            if conn:
                self.db.release_connection(conn)
                
    def get_table_columns(self, table_name):
        """
        Get all columns for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            dict: Dictionary with column names as keys and their data types as values
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = %s;
            """, (table_name,))
            
            columns = {}
            for row in cursor.fetchall():
                column_name, data_type, is_nullable, default = row
                columns[column_name] = {
                    'data_type': data_type,
                    'is_nullable': is_nullable,
                    'default': default
                }
            
            return columns
        except Exception as e:
            self.logger.error(f"Error getting table columns: {str(e)}")
            return {}
        finally:
            if conn:
                self.db.release_connection(conn)