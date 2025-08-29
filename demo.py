#!/usr/bin/env python3

"""
Demo script showing how the LangGraph text-to-SQL agent works.
This demonstrates the structure and flow without requiring API access.
"""

import sqlite3
import requests
from typing import Dict, Any, List

class DatabaseManager:
    """Manages the in-memory Chinook SQLite database"""
    
    def __init__(self):
        self.db = None
        self.schema_info = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize in-memory SQLite database with Chinook data"""
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        
        # Load the schema file
        try:
            with open("chinook_schema.sql", "r", encoding="utf-8") as f:
                schema_sql = f.read()
        except FileNotFoundError:
            print("Chinook schema file not found. Please run the main agent first.")
            return
        
        cursor = self.db.cursor()
        cursor.executescript(schema_sql)
        self.db.commit()
        
        self._extract_schema_info()
    
    def _extract_schema_info(self):
        """Extract table and column information"""
        cursor = self.db.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_info = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            schema_info[table_name] = {
                'columns': [(col[1], col[2]) for col in columns],
                'sample_data': self._get_sample_data(table_name)
            }
        
        self.schema_info = schema_info
    
    def _get_sample_data(self, table_name: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Get sample data from table"""
        cursor = self.db.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        cursor = self.db.cursor()
        try:
            cursor.execute(sql_query)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            return [{"error": str(e)}]
    
    def show_schema(self):
        """Display database schema information"""
        print("=== Chinook Database Schema ===\n")
        
        for table_name, info in self.schema_info.items():
            print(f"📁 Table: {table_name}")
            print("   Columns:")
            for col_name, col_type in info['columns']:
                print(f"     • {col_name} ({col_type})")
            
            if info['sample_data']:
                print("   Sample data:")
                for i, row in enumerate(info['sample_data'], 1):
                    # Show only first 3 columns to keep it clean
                    sample_cols = list(row.keys())[:3]
                    sample_values = {k: row[k] for k in sample_cols}
                    print(f"     Row {i}: {sample_values}")
            print()

def demo_sql_execution():
    """Demonstrate SQL query execution against the Chinook database"""
    
    print("=== LangGraph Text-to-SQL Agent Demo ===\n")
    
    # Initialize database
    db = DatabaseManager()
    
    # Show schema
    db.show_schema()
    
    print("=== Sample SQL Queries and Results ===\n")
    
    # Sample queries that the agent would generate
    sample_queries = [
        {
            "natural_language": "How many tracks are there in total?",
            "sql": "SELECT COUNT(*) as total_tracks FROM Track;",
            "explanation": "Count all records in the Track table"
        },
        {
            "natural_language": "Who are the top 3 customers by total purchase amount?",
            "sql": """
                SELECT c.FirstName, c.LastName, SUM(i.Total) as TotalSpent
                FROM Customer c
                JOIN Invoice i ON c.CustomerId = i.CustomerId
                GROUP BY c.CustomerId, c.FirstName, c.LastName
                ORDER BY TotalSpent DESC
                LIMIT 3;
            """,
            "explanation": "Join Customer and Invoice tables, sum totals, and get top 3"
        },
        {
            "natural_language": "What are the most popular music genres by number of tracks?",
            "sql": """
                SELECT g.Name as Genre, COUNT(t.TrackId) as TrackCount
                FROM Genre g
                JOIN Track t ON g.GenreId = t.GenreId
                GROUP BY g.GenreId, g.Name
                ORDER BY TrackCount DESC
                LIMIT 5;
            """,
            "explanation": "Join Genre and Track tables, count tracks per genre"
        },
        {
            "natural_language": "Which artist has the most albums?",
            "sql": """
                SELECT ar.Name as Artist, COUNT(al.AlbumId) as AlbumCount
                FROM Artist ar
                JOIN Album al ON ar.ArtistId = al.ArtistId
                GROUP BY ar.ArtistId, ar.Name
                ORDER BY AlbumCount DESC
                LIMIT 1;
            """,
            "explanation": "Join Artist and Album tables, count albums per artist"
        }
    ]
    
    for i, query_info in enumerate(sample_queries, 1):
        print(f"Query {i}: {query_info['natural_language']}")
        print(f"SQL: {query_info['sql'].strip()}")
        print(f"Explanation: {query_info['explanation']}")
        
        # Execute the query
        results = db.execute_query(query_info['sql'])
        
        if results and 'error' not in results[0]:
            print(f"Results ({len(results)} rows):")
            for j, row in enumerate(results[:5], 1):  # Show max 5 rows
                print(f"  {j}. {dict(row)}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more rows")
        else:
            print(f"Error: {results[0].get('error', 'Unknown error')}")
        
        print("\n" + "="*60 + "\n")
    
    # Demonstrate irrelevant query handling
    print("Irrelevant Query Example:")
    print("Natural Language: 'What is the weather like today?'")
    print("Agent Response: 'I don't know the answer to that question based on the Chinook database.'")
    print("Explanation: The agent recognizes this query is unrelated to the music database schema.")

if __name__ == "__main__":
    demo_sql_execution()