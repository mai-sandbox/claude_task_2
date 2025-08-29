import sqlite3
import requests
from typing import List, Dict, Any

class ChinookDatabase:
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def setup_database(self):
        """Fetch Chinook SQL and create in-memory database"""
        sql_url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        
        try:
            response = requests.get(sql_url)
            response.raise_for_status()
            sql_content = response.text
            
            self.connection = sqlite3.connect(":memory:")
            self.cursor = self.connection.cursor()
            
            self.cursor.executescript(sql_content)
            self.connection.commit()
            
            return True
        except Exception as e:
            print(f"Error setting up database: {e}")
            return False
    
    def get_table_schemas(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract detailed table schema information"""
        if not self.connection:
            return {}
            
        schemas = {}
        
        # Get all table names
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = self.cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            
            # Get column information
            self.cursor.execute(f"PRAGMA table_info({table_name});")
            columns = self.cursor.fetchall()
            
            schema_info = []
            for col in columns:
                schema_info.append({
                    'column_name': col[1],
                    'data_type': col[2],
                    'not_null': bool(col[3]),
                    'default_value': col[4],
                    'primary_key': bool(col[5])
                })
            
            schemas[table_name] = schema_info
        
        return schemas
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        if not self.connection:
            return []
            
        try:
            self.cursor.execute(query)
            columns = [description[0] for description in self.cursor.description]
            rows = self.cursor.fetchall()
            
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
    
    def get_schema_description(self) -> str:
        """Get a formatted description of all table schemas"""
        schemas = self.get_table_schemas()
        description = "Database Schema:\n\n"
        
        for table_name, columns in schemas.items():
            description += f"Table: {table_name}\n"
            for col in columns:
                pk = " (PRIMARY KEY)" if col['primary_key'] else ""
                nn = " NOT NULL" if col['not_null'] else ""
                description += f"  - {col['column_name']}: {col['data_type']}{pk}{nn}\n"
            description += "\n"
        
        return description
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()