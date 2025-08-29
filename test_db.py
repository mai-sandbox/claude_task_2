import sqlite3
import requests

def setup_database() -> sqlite3.Connection:
    """Download Chinook database and create in-memory SQLite database."""
    # Download the SQL file
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    print("Downloading Chinook database...")
    response = requests.get(url)
    sql_content = response.text
    
    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Execute the SQL to create tables and insert data
    print("Setting up database...")
    cursor.executescript(sql_content)
    conn.commit()
    print("Database setup complete!")
    
    return conn

def get_schema_info(conn: sqlite3.Connection) -> str:
    """Get detailed schema information for all tables."""
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_info = "DATABASE SCHEMA INFORMATION:\n\n"
    
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
            is_pk = "PRIMARY KEY" if col[5] else ""
            schema_info += f"  - {col_name} ({col_type}) {is_nullable} {is_pk}\n"
        
        schema_info += "\n"
    
    return schema_info

if __name__ == "__main__":
    # Test database setup
    conn = setup_database()
    
    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_artists FROM Artist;")
    result = cursor.fetchone()
    print(f"Total artists in database: {result[0]}")
    
    cursor.execute("SELECT COUNT(*) as total_albums FROM Album;")
    result = cursor.fetchone()
    print(f"Total albums in database: {result[0]}")
    
    # Test the query we want to answer
    cursor.execute("""
    SELECT ar.Name, COUNT(al.AlbumId) as album_count
    FROM Artist ar
    JOIN Album al ON ar.ArtistId = al.ArtistId
    GROUP BY ar.ArtistId, ar.Name
    ORDER BY album_count DESC
    LIMIT 5;
    """)
    
    results = cursor.fetchall()
    print("\nTop 5 artists with most albums:")
    for artist, count in results:
        print(f"- {artist}: {count} albums")
    
    print("\nSchema info (first 1000 chars):")
    schema = get_schema_info(conn)
    print(schema[:1000] + "..." if len(schema) > 1000 else schema)