"""
Demo script to test the Chinook database setup and SQL generation structure
"""
from agent import ChinookDatabase

def main():
    print("Testing Chinook Database Setup")
    print("=" * 50)
    
    # Test database setup
    try:
        db = ChinookDatabase()
        print("✓ Database initialized successfully")
        
        # Test schema info
        print("\n✓ Database schema loaded")
        print(f"Schema info length: {len(db.get_schema_info())} characters")
        
        # Test basic queries
        test_queries = [
            "SELECT COUNT(*) as artist_count FROM Artist",
            "SELECT Name FROM Genre LIMIT 5",
            "SELECT FirstName, LastName, Country FROM Customer WHERE Country = 'Brazil' LIMIT 3",
            "SELECT COUNT(*) as track_count FROM Track"
        ]
        
        print("\nTesting SQL execution:")
        for query in test_queries:
            result = db.execute_query(query)
            if isinstance(result, dict) and "error" in result:
                print(f"❌ Query failed: {query}")
                print(f"   Error: {result['error']}")
            else:
                print(f"✓ Query successful: {query}")
                print(f"   Results: {len(result)} rows")
                if result:
                    print(f"   Sample: {result[0] if len(result) > 0 else 'No data'}")
            print()
            
        # Test invalid query
        print("Testing security (non-SELECT query):")
        result = db.execute_query("INSERT INTO Artist (Name) VALUES ('Test')")
        if isinstance(result, dict) and "error" in result:
            print("✓ Security check working - non-SELECT queries blocked")
        else:
            print("❌ Security issue - non-SELECT query executed")
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
    
    print("\n" + "=" * 50)
    print("Demo completed. To use the full agent, set ANTHROPIC_API_KEY in .env file")

if __name__ == "__main__":
    main()