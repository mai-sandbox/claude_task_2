#!/usr/bin/env python3

import os
import sys
from text_to_sql_agent import TextToSQLAgent

def main():
    print("🎵 Chinook Music Database Text-to-SQL Agent")
    print("=" * 50)
    print("Ask questions about the music database in natural language!")
    print("Examples:")
    print("- How many customers are there?")
    print("- What are the top 5 albums?")
    print("- Which artist has sold the most tracks?")
    print("- Show me customers from Canada")
    print("\nType 'quit' or 'exit' to end the session.")
    print("=" * 50)
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n❌ Error: OPENAI_API_KEY environment variable not set.")
        print("Please set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return 1
    
    try:
        # Initialize the agent
        print("\n🔄 Initializing agent and setting up database...")
        agent = TextToSQLAgent(api_key)
        print("✅ Agent ready!\n")
        
        while True:
            try:
                # Get user input
                user_input = input("\n🔍 Your question: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                # Process the query
                print("\n🤔 Thinking...")
                response = agent.query(user_input)
                print(f"\n💡 Answer: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error processing query: {str(e)}")
                
    except Exception as e:
        print(f"\n❌ Error initializing agent: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())