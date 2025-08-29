#!/usr/bin/env python3

"""
Simple test script to verify the text-to-SQL agent functionality
"""

from text_to_sql_agent import TextToSQLAgent
import os

def test_database_initialization():
    """Test that database initializes correctly"""
    print("Testing database initialization...")
    agent = TextToSQLAgent()
    
    if agent.db.conn is None:
        agent.db.initialize_database()
    
    schema = agent.db.get_schema_description()
    print("✅ Database initialized successfully")
    print(f"Schema contains {len(agent.db.schema_info)} tables")
    agent.close()

def test_sample_queries():
    """Test sample queries"""
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Skipping LLM tests.")
        print("Set your API key in .env file to test the full workflow.")
        return
    
    print("\nTesting sample queries...")
    agent = TextToSQLAgent()
    
    test_queries = [
        "How many artists are in the database?",
        "Show me all albums by AC/DC",
        "What is the weather today?",  # Should be irrelevant
        "List the top 5 most expensive tracks"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        try:
            response = agent.query(query)
            print(f"💬 Response: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    agent.close()

def main():
    print("🧪 Testing Text-to-SQL Agent")
    print("=" * 40)
    
    try:
        test_database_initialization()
        test_sample_queries()
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()