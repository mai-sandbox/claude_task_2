#!/usr/bin/env python3

from text_to_sql_agent import TextToSQLAgent
import os

def main():
    """Main function to test the text-to-SQL agent"""
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set your OPENAI_API_KEY environment variable")
        return
    
    try:
        # Initialize the agent
        print("Initializing Text-to-SQL Agent...")
        agent = TextToSQLAgent()
        print("Agent initialized successfully!")
        
        # Test queries
        test_queries = [
            "How many customers are there in total?",
            "What are the top 5 best-selling tracks?",
            "Which artist has the most albums?",
            "What is the average price of tracks?",
            "Show me all employees and their titles",
            "What is the weather like today?",  # Irrelevant query
            "How many invoices were created in 2009?"
        ]
        
        print("\n" + "="*50)
        print("Testing Text-to-SQL Agent")
        print("="*50)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\nQuery {i}: {query}")
            print("-" * 40)
            
            try:
                response = agent.query(query)
                print(f"Response: {response}")
            except Exception as e:
                print(f"Error processing query: {e}")
        
        # Interactive mode
        print("\n" + "="*50)
        print("Interactive Mode (type 'quit' to exit)")
        print("="*50)
        
        while True:
            try:
                user_input = input("\nEnter your question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                    
                if not user_input:
                    continue
                    
                response = agent.query(user_input)
                print(f"\nResponse: {response}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        # Clean up
        agent.close()
        print("\nThank you for using the Text-to-SQL Agent!")
        
    except Exception as e:
        print(f"Failed to initialize agent: {e}")

if __name__ == "__main__":
    main()