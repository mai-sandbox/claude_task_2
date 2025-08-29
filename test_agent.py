#!/usr/bin/env python3

import os
from agent import app

def test_agent():
    """Test the text-to-SQL agent with sample questions"""
    
    test_questions = [
        "How many artists are in the database?",
        "What are the top 5 most expensive tracks?",
        "Which customers are from the USA?",
        "What is the weather like today?",  # Should respond with "I don't know"
        "Show me all genres available in the database"
    ]
    
    print("Testing Text-to-SQL Agent")
    print("=" * 50)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\nTest {i}: {question}")
        print("-" * 30)
        
        try:
            # Invoke the agent
            result = app.invoke({
                "messages": [{"role": "user", "content": question}]
            })
            
            # Extract the final response
            if result and "messages" in result:
                final_message = result["messages"][-1]
                if hasattr(final_message, 'content'):
                    print(f"Response: {final_message.content}")
                else:
                    print(f"Response: {final_message}")
            else:
                print(f"Unexpected result format: {result}")
                
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_agent()