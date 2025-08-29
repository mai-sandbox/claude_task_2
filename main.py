#!/usr/bin/env python3

import sys
from text_to_sql_agent import TextToSQLAgent

def main():
    """Main application entry point."""
    print("Welcome to the Chinook Music Database Text-to-SQL Agent!")
    print("Ask me questions about music, artists, albums, tracks, customers, or sales.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    try:
        agent = TextToSQLAgent()
        
        while True:
            user_query = input("Question: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_query:
                continue
            
            print("\nProcessing your query...\n")
            response = agent.process_query(user_query)
            print(f"Answer: {response}\n")
            print("-" * 80)
            print()
    
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error initializing agent: {str(e)}")
        print("Please make sure you have set your OPENAI_API_KEY in the .env file.")
        sys.exit(1)

if __name__ == "__main__":
    main()