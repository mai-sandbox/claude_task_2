import sqlite3
import requests
from typing import List, Dict, Any

class ChinookDatabase:
    def __init__(self):
        self.conn = None
        self.schema_info = None
        
    def initialize_database(self) -> None:
        """Download Chinook SQL and create in-memory database"""
        url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            sql_content = response.text
            
            self.conn = sqlite3.connect(":memory:")
            self.conn.executescript(sql_content)
            self.conn.commit()
            
            self._extract_schema_info()
            
        except Exception as e:
            raise Exception(f"Failed to initialize database: {str(e)}")
    
    def _extract_schema_info(self) -> None:
        """Extract detailed schema information for SQL generation"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            foreign_keys = cursor.fetchall()
            
            schema_info[table] = {
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "primary_key": bool(col[5])
                    }
                    for col in columns
                ],
                "foreign_keys": [
                    {
                        "column": fk[3],
                        "referenced_table": fk[2],
                        "referenced_column": fk[4]
                    }
                    for fk in foreign_keys
                ]
            }
        
        self.schema_info = schema_info
    
    def get_schema_description(self) -> str:
        """Get detailed schema description for prompt"""
        if not self.schema_info:
            return "Database not initialized"
        
        description = "Database Schema for Chinook Music Store:\n\n"
        
        for table_name, table_info in self.schema_info.items():
            description += f"Table: {table_name}\n"
            description += "Columns:\n"
            
            for col in table_info["columns"]:
                pk_indicator = " (PRIMARY KEY)" if col["primary_key"] else ""
                null_indicator = " NOT NULL" if col["not_null"] else ""
                description += f"  - {col['name']}: {col['type']}{pk_indicator}{null_indicator}\n"
            
            if table_info["foreign_keys"]:
                description += "Foreign Keys:\n"
                for fk in table_info["foreign_keys"]:
                    description += f"  - {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}\n"
            
            description += "\n"
        
        description += """
Key Relationships:
- Artists have Albums
- Albums have Tracks
- Tracks belong to Genres and MediaTypes
- Customers place Invoices
- Invoices contain InvoiceLines for Tracks
- Employees can be assigned to Customers
- Playlists contain Tracks via PlaylistTrack junction table
"""
        
        return description
    
    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results as list of dictionaries"""
        if not self.conn:
            raise Exception("Database not initialized")
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
            
        except sqlite3.Error as e:
            raise Exception(f"SQL execution error: {str(e)}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()