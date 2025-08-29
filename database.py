import sqlite3
import requests
from typing import Dict, List, Tuple

class ChinookDatabase:
    def __init__(self):
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        """Download Chinook database SQL and set up in-memory database."""
        try:
            response = requests.get(
                "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
            )
            response.raise_for_status()
            sql_content = response.text
            
            self.conn = sqlite3.connect(":memory:")
            self.conn.executescript(sql_content)
            self.conn.commit()
            
        except Exception as e:
            raise Exception(f"Failed to setup Chinook database: {str(e)}")
    
    def get_schema_info(self) -> str:
        """Extract detailed schema information from the database."""
        cursor = self.conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_info = "Database Schema:\n\n"
        
        for table in tables:
            table_name = table[0]
            schema_info += f"Table: {table_name}\n"
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_nullable = "NOT NULL" if col[3] else "NULL"
                is_primary = "PRIMARY KEY" if col[5] else ""
                schema_info += f"  - {col_name}: {col_type} {is_nullable} {is_primary}\n"
            
            # Get foreign key information
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            foreign_keys = cursor.fetchall()
            
            for fk in foreign_keys:
                schema_info += f"  - Foreign Key: {fk[3]} references {fk[2]}({fk[4]})\n"
            
            schema_info += "\n"
        
        return schema_info
    
    def execute_query(self, query: str) -> List[Tuple]:
        """Execute SQL query and return results."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            return results
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")
    
    def get_column_names(self, query: str) -> List[str]:
        """Get column names for a given query."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            column_names = [description[0] for description in cursor.description]
            return column_names
        except Exception as e:
            raise Exception(f"Error getting column names: {str(e)}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()