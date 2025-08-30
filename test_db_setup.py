#!/usr/bin/env python3
"""
Test script to verify database setup works correctly
"""
import sqlite3
from text_to_sql_agent import setup_database, get_database_schema

def test_database_setup():
    """Test that the database is set up correctly"""
    print("🔧 Testing database setup...")
    
    try:
        # Setup database
        conn = setup_database()
        print("✅ Database created successfully")
        
        # Test basic queries
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
        
        # Test sample queries
        test_queries = [
            ("SELECT COUNT(*) FROM Artist", "Artists count"),
            ("SELECT COUNT(*) FROM Album", "Albums count"), 
            ("SELECT COUNT(*) FROM Track", "Tracks count"),
            ("SELECT COUNT(*) FROM Customer", "Customers count"),
            ("SELECT COUNT(*) FROM Invoice", "Invoices count"),
        ]
        
        print("\n📊 Sample data counts:")
        print("-" * 25)
        
        for query, description in test_queries:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"  {description}: {count}")
        
        # Test schema extraction
        print("\n🏗️  Testing schema extraction...")
        schema = get_database_schema(conn)
        schema_lines = schema.split('\n')
        print(f"✅ Schema extracted successfully ({len(schema_lines)} lines)")
        
        # Show first few tables in schema
        print("\n📋 Schema preview (first 3 tables):")
        print("-" * 40)
        current_table_count = 0
        for line in schema_lines:
            if line.startswith("Table:"):
                current_table_count += 1
                if current_table_count > 3:
                    print("...")
                    break
            if current_table_count <= 3:
                print(line)
        
        conn.close()
        print("\n✅ Database test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_database_setup()