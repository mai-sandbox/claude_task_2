#!/usr/bin/env python3

from database import ChinookDatabase

def test_database_setup():
    """Test that the database setup works correctly."""
    print("Testing Chinook database setup...")
    
    try:
        db = ChinookDatabase()
        print("✓ Database initialized successfully")
        
        # Test schema extraction
        schema = db.get_schema_info()
        print("✓ Schema information extracted")
        print(f"Schema length: {len(schema)} characters")
        
        # Test a simple query
        results = db.execute_query("SELECT COUNT(*) FROM Artist;")
        artist_count = results[0][0]
        print(f"✓ Query executed successfully: {artist_count} artists found")
        
        # Test column names extraction
        column_names = db.get_column_names("SELECT Name FROM Artist LIMIT 1;")
        print(f"✓ Column names extracted: {column_names}")
        
        # Show first few artists as example
        artists = db.execute_query("SELECT ArtistId, Name FROM Artist LIMIT 5;")
        print("\nFirst 5 artists:")
        for artist in artists:
            print(f"  {artist[0]}: {artist[1]}")
        
        db.close()
        print("\n✓ All database tests passed!")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_database_setup()