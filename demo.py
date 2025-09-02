#!/usr/bin/env python3
"""
Interactive demo of the text-to-SQL agent
"""

from agent import app
from langchain_core.messages import HumanMessage


def demo():
    """Interactive demo of the text-to-SQL agent"""
    
    print("=== Chinook Database Text-to-SQL Agent ===")
    print("Ask questions about the music database or type 'quit' to exit.")
    print("Examples:")
    print("- 'Who are the top artists by album count?'")
    print("- 'What are the longest tracks?'")
    print("- 'How much revenue did we make in 2009?'")
    print()
    
    while True:
        try:
            question = input("Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            if not question:
                continue
                
            print("\nProcessing your question...")
            print("-" * 40)
            
            # Run the agent
            result = app.invoke({"messages": [HumanMessage(content=question)]})
            
            # Print the response
            if result.get("messages"):
                final_message = result["messages"][-1]
                print(f"\nAnswer: {final_message.content}")
            
            # Show SQL query if generated
            if result.get("sql_query"):
                print(f"\n[SQL Query used: {result['sql_query']}]")
            
            print("\n" + "="*50 + "\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    demo()