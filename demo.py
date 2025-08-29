"""Demo script for the text-to-SQL agent."""

import os
from text_to_sql_agent import TextToSQLAgent

def test_agent():
    """Test the agent with sample queries."""
    print("🎵 Testing Chinook Text-to-SQL Agent")
    print("=" * 50)
    
    try:
        agent = TextToSQLAgent()
        
        # Test queries
        test_queries = [
            "How many artists are in the database?",
            "What are the top 5 bestselling tracks?", 
            "Which genres are most popular?",
            "What is the weather today?",  # Irrelevant query
            "Show me albums by Pink Floyd",
            "What countries have the most customers?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{i}. Query: {query}")
            try:
                response = agent.query(query)
                print(f"   Response: {response}")
            except Exception as e:
                print(f"   Error: {str(e)}")
        
        agent.close()
        
    except Exception as e:
        print(f"Failed to initialize agent: {str(e)}")
        print("\nNote: Make sure you have a valid ANTHROPIC_API_KEY in your .env file")

if __name__ == "__main__":
    test_agent()