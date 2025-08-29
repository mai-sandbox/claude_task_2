from agent import setup_chinook_db, get_schema_info

def test_database_setup():
    """Test the database setup without API calls"""
    print("Setting up Chinook database...")
    
    # Test database setup
    conn = setup_chinook_db()
    print("✓ Database setup successful")
    
    # Test schema extraction
    schema = get_schema_info(conn)
    print("✓ Schema extraction successful")
    print("\nFirst 1000 characters of schema:")
    print(schema[:1000])
    
    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_artists FROM Artist")
    result = cursor.fetchone()
    print(f"\n✓ Database query test: Found {result[0]} artists")
    
    cursor.execute("SELECT COUNT(*) as total_tracks FROM Track")  
    result = cursor.fetchone()
    print(f"✓ Database query test: Found {result[0]} tracks")
    
    cursor.execute("SELECT Name FROM Artist LIMIT 5")
    artists = cursor.fetchall()
    print(f"\n✓ Sample artists: {[artist[0] for artist in artists]}")

if __name__ == "__main__":
    test_database_setup()