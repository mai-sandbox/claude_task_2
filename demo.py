#!/usr/bin/env python3

from agent import db, execute_sql_query

def demonstrate_sql_capabilities():
    """Demonstrate the SQL generation and execution capabilities"""
    
    print("🎵 Chinook Database Text-to-SQL Agent Demo 🎵")
    print("=" * 50)
    
    # Sample natural language questions and their corresponding SQL
    demonstrations = [
        {
            "question": "How many artists are in the database?",
            "sql": "SELECT COUNT(*) as artist_count FROM Artist",
            "explanation": "Simple count query to get total number of artists"
        },
        {
            "question": "What are the top 5 most expensive tracks?",
            "sql": "SELECT Name, UnitPrice FROM Track ORDER BY UnitPrice DESC LIMIT 5",
            "explanation": "Query to find tracks with highest unit price"
        },
        {
            "question": "Which rock albums are available?",
            "sql": """SELECT DISTINCT a.Title, ar.Name as Artist 
                     FROM Album a 
                     JOIN Artist ar ON a.ArtistId = ar.ArtistId
                     JOIN Track t ON a.AlbumId = t.AlbumId
                     JOIN Genre g ON t.GenreId = g.GenreId 
                     WHERE g.Name = 'Rock' 
                     LIMIT 10""",
            "explanation": "Complex join to find rock albums using genre information"
        },
        {
            "question": "What are all the available genres?",
            "sql": "SELECT Name FROM Genre ORDER BY Name",
            "explanation": "Simple query to list all music genres"
        },
        {
            "question": "Which customers are from Canada?",
            "sql": "SELECT FirstName, LastName, City FROM Customer WHERE Country = 'Canada'",
            "explanation": "Filter customers by country"
        }
    ]
    
    for i, demo in enumerate(demonstrations, 1):
        print(f"\n📝 Example {i}: {demo['question']}")
        print(f"💡 SQL Translation: {demo['sql'].strip()}")
        print(f"🔍 Explanation: {demo['explanation']}")
        print("📊 Results:")
        
        try:
            result = execute_sql_query.func(demo['sql'].strip())
            print(f"   {result}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print("-" * 50)
    
    print("\n✅ Database Statistics:")
    print(f"   • Artists: {len(db.execute_query('SELECT * FROM Artist'))}")
    print(f"   • Albums: {len(db.execute_query('SELECT * FROM Album'))}")
    print(f"   • Tracks: {len(db.execute_query('SELECT * FROM Track'))}")
    print(f"   • Genres: {len(db.execute_query('SELECT * FROM Genre'))}")
    print(f"   • Customers: {len(db.execute_query('SELECT * FROM Customer'))}")
    
    print("\n🚀 To use the full agent with natural language processing:")
    print("   1. Set up your ANTHROPIC_API_KEY in .env file")
    print("   2. Run: python test_agent.py")
    print("\n💡 The agent will automatically:")
    print("   • Convert natural language to SQL")
    print("   • Execute queries safely")
    print("   • Return natural language responses")
    print("   • Handle irrelevant questions appropriately")

if __name__ == "__main__":
    demonstrate_sql_capabilities()