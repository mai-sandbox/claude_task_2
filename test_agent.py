#!/usr/bin/env python3

import os
from agent import create_app
from langchain_core.messages import HumanMessage

def test_agent():
    # Check if we have the necessary API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("Warning: ANTHROPIC_API_KEY not set. Please set it to test the agent.")
        return
    
    print("Creating text-to-SQL agent...")
    agent = create_app()
    
    test_queries = [
        "How many customers are there in the database?",
        "What are the names of all the artists in the database?",
        "Show me the top 5 albums by number of tracks",
        "What genres are available in the music store?",
        "What is the weather like today?",  # Should respond with "I don't know"
        "Tell me about your favorite movie",  # Should respond with "I don't know"
    ]
    
    print("\nTesting the agent with various queries...\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        print("-" * 50)
        
        try:
            result = agent.invoke({"messages": [HumanMessage(content=query)]})
            response = result['messages'][-1].content
            print(f"Response: {response}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    test_agent()