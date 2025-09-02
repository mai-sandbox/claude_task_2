import os
import sqlite3
from text_to_sql_agent import load_chinook_database, create_text_to_sql_agent

def debug_database():
    """Debug the database loading"""
    try:
        conn = load_chinook_database()
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables in database: {tables}")
        
        # Test a simple query
        cursor.execute("SELECT COUNT(*) FROM Artist;")
        artist_count = cursor.fetchone()
        print(f"Number of artists: {artist_count[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM Customer;")
        customer_count = cursor.fetchone()
        print(f"Number of customers: {customer_count[0]}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False

def debug_single_query():
    """Debug a single query execution"""
    agent = create_text_to_sql_agent()
    
    result = agent.invoke({
        "user_query": "How many customers are from each country?",
        "sql_query": "",
        "sql_result": "",
        "natural_language_response": "",
        "error": ""
    })
    
    print("Final result:")
    for key, value in result.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    print("=== Database Debug ===")
    if debug_database():
        print("\n=== Query Debug ===")
        debug_single_query()