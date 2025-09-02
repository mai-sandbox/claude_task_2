#!/usr/bin/env python3
"""
Test script for the text-to-SQL agent
"""

from agent import app
from langchain_core.messages import HumanMessage


def test_agent():
    """Test the agent with various questions"""
    
    test_questions = [
        "Who are the top 5 customers by total purchases?",
        "What are the most popular music genres?",
        "List all albums by AC/DC",
        "What's the weather like today?",  # Should be rejected
        "How many tracks are in the database?",
        "Tell me about machine learning",  # Should be rejected
    ]
    
    print("=== Testing Text-to-SQL Agent ===\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"Test {i}: {question}")
        print("-" * 50)
        
        try:
            # Run the agent
            result = app.invoke({"messages": [HumanMessage(content=question)]})
            
            # Print the final response
            if result.get("messages"):
                final_message = result["messages"][-1]
                print(f"Response: {final_message.content}")
            else:
                print("No response generated")
            
            # Print additional debug info
            if result.get("sql_query"):
                print(f"SQL Query: {result['sql_query']}")
            if result.get("error_message"):
                print(f"Error: {result['error_message']}")
            
        except Exception as e:
            print(f"Error running agent: {e}")
        
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_agent()