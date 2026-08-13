import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

class DatabaseManager:
    """
    A reusable class for managing SQLite database operations.
    Handles connection, cursor creation, and CRUD operations safely.
    """

    def __init__(self, db_path: str):
        """
        Initialize the database manager with a path to the SQLite file.
        
        Args:
            db_path: Path to the .db file (e.g., 'data.db' or ':memory:')
        """
        self.db_path = db_path

    @contextmanager
    def _get_connection(self):
        """
        Context manager for handling database connections.
        Automatically commits on success, rolls back on error, and closes connection.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_table(self, table_name: str, columns: Dict[str, str], 
                     primary_key: Optional[str] = None, 
                     unique_constraints: Optional[List[str]] = None):
        """
        Create a table if it does not exist.
        
        Args:
            table_name: Name of the table.
            columns: Dict mapping column names to SQL types (e.g., {'id': 'INTEGER', 'name': 'TEXT'}).
            primary_key: Name of the column to set as PRIMARY KEY.
            unique_constraints: List of column names to set as UNIQUE.
        """
        col_defs = []
        for name, dtype in columns.items():
            definition = f"{name} {dtype}"
            if name == primary_key:
                definition += " PRIMARY KEY AUTOINCREMENT"
            if unique_constraints and name in unique_constraints:
                definition += " UNIQUE"
            col_defs.append(definition)
        
        cols_sql = ", ".join(col_defs)
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({cols_sql})"
        
        with self._get_connection() as conn:
            conn.execute(query)

    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Insert a single record into the table.
        
        Args:
            table_name: Name of the table.
            data: Dictionary mapping column names to values.
            
        Returns:
            The row ID of the inserted record.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            return cursor.lastrowid

    def insert_many(self, table_name: str, data_list: List[Dict[str, Any]]) -> int:
        """
        Insert multiple records efficiently.
        
        Args:
            table_name: Name of the table.
            data_list: List of dictionaries containing record data.
            
        Returns:
            Number of rows inserted.
        """
        if not data_list:
            return 0
            
        columns = ", ".join(data_list[0].keys())
        placeholders = ", ".join("?" * len(data_list[0]))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        values = [tuple(item.values()) for item in data_list]
        
        with self._get_connection() as conn:
            cursor = conn.executemany(query, values)
            return cursor.rowcount

    def select(self, table_name: str, columns: List[str] = None, 
               where: Optional[str] = None, params: Optional[Tuple] = None,
               order_by: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Read records from the table.
        
        Args:
            table_name: Name of the table.
            columns: List of columns to select (default: all).
            where: WHERE clause string (e.g., "age > ? AND name = ?").
            params: Tuple of values for the WHERE clause placeholders.
            order_by: Column name to sort by.
            limit: Maximum number of rows to return.
            
        Returns:
            List of dictionaries representing rows.
        """
        cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {cols} FROM {table_name}"
        
        conditions = []
        if where:
            conditions.append(f"WHERE {where}")
        if order_by:
            conditions.append(f"ORDER BY {order_by}")
        if limit:
            conditions.append(f"LIMIT {limit}")
            
        if conditions:
            query += " " + " ".join(conditions)
            
        with self._get_connection() as conn:
            cursor = conn.execute(query, params or ())
            # Convert sqlite3.Row objects to dictionaries
            return [dict(row) for row in cursor.fetchall()]

    def update(self, table_name: str, data: Dict[str, Any], 
               where: str, params: Tuple) -> int:
        """
        Update existing records.
        
        Args:
            table_name: Name of the table.
            data: Dictionary of columns and new values to update.
            where: WHERE clause string (e.g., "id = ?").
            params: Tuple of values for the WHERE clause.
            
        Returns:
            Number of rows affected.
        """
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        
        # Combine update values and where parameters
        all_params = tuple(data.values()) + params
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, all_params)
            return cursor.rowcount

    def delete(self, table_name: str, where: str, params: Tuple) -> int:
        """
        Delete records from the table.
        
        Args:
            table_name: Name of the table.
            where: WHERE clause string (e.g., "id = ?").
            params: Tuple of values for the WHERE clause.
            
        Returns:
            Number of rows deleted.
        """
        query = f"DELETE FROM {table_name} WHERE {where}"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount

    def execute_raw(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query (use with caution).
        
        Args:
            query: SQL query string.
            params: Optional parameters for the query.
            
        Returns:
            List of dictionaries for SELECT queries, otherwise empty list.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(query, params or ())
            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cursor.fetchall()]
            return []   