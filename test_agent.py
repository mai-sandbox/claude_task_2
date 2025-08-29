#!/usr/bin/env python3

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agent import app
from langchain_core.messages import HumanMessage

def test_queries():
    """Test the text-to-SQL agent with various queries"""
    
    test_cases = [
        "How many tracks are there in total?",
        "Who are the top 5 customers by total purchase amount?", 
        "What are the most popular music genres by number of tracks?",
        "Which artist has the most albums?",
        "What is the weather like today?",  # Irrelevant query
        "Show me all employees and their managers",
    ]
    
    print("=== Testing Text-to-SQL Agent ===\n")
    
    for i, query in enumerate(test_cases, 1):
        print(f"Test {i}: {query}")
        print("-" * 50)
        
        try:
            # Create initial state with user query
            initial_state = {
                "messages": [HumanMessage(content=query)]
            }
            
            # Run the agent
            result = app.invoke(initial_state)
            
            # Print the final response
            if result.get("final_response"):
                print(f"Response: {result['final_response']}")
            else:
                # Get the last AI message if no final_response
                last_message = result.get("messages", [])[-1]
                if hasattr(last_message, 'content'):
                    print(f"Response: {last_message.content}")
                else:
                    print("No response generated")
            
            print(f"SQL Query: {result.get('sql_query', 'None')}")
            print(f"Results Count: {len(result.get('query_result', []))}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_queries()