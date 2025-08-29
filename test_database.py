#!/usr/bin/env python3

from agent import db, execute_sql_query

def test_database_setup():
    """Test that the Chinook database is properly set up"""
    
    print("Testing Chinook Database Setup")
    print("=" * 40)
    
    test_queries = [
        ("Count artists", "SELECT COUNT(*) as artist_count FROM Artist"),
        ("Count albums", "SELECT COUNT(*) as album_count FROM Album"), 
        ("Count tracks", "SELECT COUNT(*) as track_count FROM Track"),
        ("Sample artists", "SELECT Name FROM Artist LIMIT 5"),
        ("Sample genres", "SELECT Name FROM Genre LIMIT 5"),
        ("Top tracks by price", "SELECT Name, UnitPrice FROM Track ORDER BY UnitPrice DESC LIMIT 3")
    ]
    
    for description, query in test_queries:
        print(f"\n{description}:")
        print(f"Query: {query}")
        try:
            result = execute_sql_query.func(query)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
    
    print(f"\nDatabase schema info available: {len(db.schema_info)} characters")

if __name__ == "__main__":
    test_database_setup()