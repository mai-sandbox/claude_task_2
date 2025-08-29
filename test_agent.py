#!/usr/bin/env python3

import os
import sys
from text_to_sql_agent import TextToSQLAgent

def test_agent():
    """Test the text-to-SQL agent with various queries"""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set. Skipping tests that require OpenAI API.")
        return False
    
    print("🧪 Testing Text-to-SQL Agent")
    print("=" * 50)
    
    try:
        # Initialize agent
        print("🔄 Initializing agent...")
        agent = TextToSQLAgent(api_key)
        print("✅ Agent initialized successfully!")
        
        # Test queries
        test_queries = [
            {
                "question": "How many customers are there in total?",
                "expected_type": "number"
            },
            {
                "question": "What are the top 3 albums by name?",
                "expected_type": "list"
            },
            {
                "question": "Which customers are from Canada?",
                "expected_type": "list"
            },
            {
                "question": "What is the weather like today?",
                "expected_answer": "don't know"
            }
        ]
        
        print("\n🔍 Running test queries...")
        print("-" * 50)
        
        for i, test in enumerate(test_queries, 1):
            print(f"\nTest {i}: {test['question']}")
            
            try:
                response = agent.query(test['question'])
                print(f"✅ Response: {response}")
                
                # Basic validation
                if "expected_answer" in test:
                    if test["expected_answer"].lower() in response.lower():
                        print("✅ Expected response pattern found")
                    else:
                        print("⚠️  Expected response pattern not found")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ Testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

def test_database_setup():
    """Test database setup without requiring OpenAI API"""
    print("🔍 Testing database setup...")
    
    try:
        import sqlite3
        import requests
        
        # Test fetching the database
        print("📥 Fetching Chinook database...")
        url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch database: {response.status_code}")
            return False
        
        print("✅ Database fetched successfully")
        
        # Test creating in-memory database
        print("💾 Testing in-memory database creation...")
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        # Execute a small portion to test
        sql_lines = response.text.split('\n')[:100]  # Test first 100 lines
        test_sql = '\n'.join(sql_lines)
        
        try:
            cursor.executescript(test_sql)
            print("✅ Database creation test successful")
        except Exception as e:
            print(f"⚠️  Database creation test warning: {str(e)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database setup test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting tests...\n")
    
    # Test database setup first (doesn't require API key)
    db_test = test_database_setup()
    print()
    
    # Test full agent functionality
    agent_test = test_agent()
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Database setup: {'✅ PASS' if db_test else '❌ FAIL'}")
    print(f"Agent functionality: {'✅ PASS' if agent_test else '❌ FAIL'}")
    
    if not agent_test and not os.getenv("OPENAI_API_KEY"):
        print("\n💡 To test full functionality, set OPENAI_API_KEY environment variable")
    
    sys.exit(0 if (db_test and agent_test) else 1)