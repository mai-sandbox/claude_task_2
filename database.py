"""Database utilities for the Chinook database."""

import sqlite3
import os
from typing import Dict, List, Tuple, Any

class ChinookDatabase:
    def __init__(self, sql_file_path: str = "chinook_database.sql"):
        """Initialize the in-memory Chinook database."""
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row  # Enable column access by name
        self.cursor = self.connection.cursor()
        self._initialize_database(sql_file_path)
    
    def _initialize_database(self, sql_file_path: str):
        """Load and execute the Chinook database SQL file."""
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"SQL file not found: {sql_file_path}")
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        self.cursor.executescript(sql_content)
        self.connection.commit()
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries."""
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            raise sqlite3.Error(f"SQL execution error: {str(e)}")
    
    def get_schema_info(self) -> str:
        """Get detailed schema information for all tables."""
        schema_info = []
        
        # Get all table names
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        tables = self.execute_query(tables_query)
        
        for table in tables:
            table_name = table['name']
            schema_info.append(f"\n--- Table: {table_name} ---")
            
            # Get column information
            pragma_query = f"PRAGMA table_info({table_name})"
            columns = self.execute_query(pragma_query)
            
            for col in columns:
                nullable = "NULL" if not col['notnull'] else "NOT NULL"
                pk = " (PRIMARY KEY)" if col['pk'] else ""
                default = f" DEFAULT {col['dflt_value']}" if col['dflt_value'] else ""
                schema_info.append(f"  - {col['name']}: {col['type']} {nullable}{pk}{default}")
            
            # Get foreign key information
            fk_query = f"PRAGMA foreign_key_list({table_name})"
            foreign_keys = self.execute_query(fk_query)
            
            if foreign_keys:
                schema_info.append("  Foreign Keys:")
                for fk in foreign_keys:
                    schema_info.append(f"    - {fk['from']} -> {fk['table']}({fk['to']})")
            
            # Get sample data (first 3 rows)
            sample_query = f"SELECT * FROM {table_name} LIMIT 3"
            try:
                sample_data = self.execute_query(sample_query)
                if sample_data:
                    schema_info.append("  Sample data:")
                    for i, row in enumerate(sample_data, 1):
                        row_str = ", ".join([f"{k}: {v}" for k, v in list(row.items())[:4]])  # Show first 4 columns
                        if len(row) > 4:
                            row_str += "..."
                        schema_info.append(f"    {i}. {row_str}")
            except sqlite3.Error:
                schema_info.append("  Sample data: Unable to fetch")
        
        return "\n".join(schema_info)
    
    def get_table_names(self) -> List[str]:
        """Get all table names in the database."""
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        results = self.execute_query(query)
        return [result['name'] for result in results]
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate a SQL query without executing it."""
        try:
            # Use EXPLAIN to validate the query syntax without executing
            self.cursor.execute(f"EXPLAIN {query}")
            return True, "Query is valid"
        except sqlite3.Error as e:
            return False, str(e)
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()