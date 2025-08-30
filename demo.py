#!/usr/bin/env python3
"""
Interactive demo for the Text-to-SQL Agent
"""
import os
from text_to_sql_agent import TextToSQLAgent

def main():
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
        print("⚠️  OpenAI API key not found!")
        print("Please set your OPENAI_API_KEY in the .env file")
        print("Example: OPENAI_API_KEY=sk-...")
        return

    print("🎵 Chinook Database Text-to-SQL Agent")
    print("=" * 50)
    print("Ask questions about the music database!")
    print("Type 'quit' to exit.")
    print()

    try:
        agent = TextToSQLAgent()
        print("✅ Agent initialized successfully!")
        print()
        
        # Run example queries first
        example_queries = [
            "How many customers are there?",
            "What are the top 5 best-selling tracks?",
            "Which artist has the most albums?",
        ]
        
        print("📋 Running example queries:")
        print("-" * 30)
        
        for query in example_queries:
            print(f"❓ {query}")
            try:
                response = agent.query(query)
                print(f"🤖 {response}")
                print()
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
        
        # Interactive mode
        print("🔄 Interactive mode - Enter your questions:")
        print("-" * 40)
        
        while True:
            user_input = input("❓ Your question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
                
            if not user_input:
                continue
                
            try:
                response = agent.query(user_input)
                print(f"🤖 {response}")
                print()
            except Exception as e:
                print(f"❌ Error: {e}")
                print()
                
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        print("Make sure your OpenAI API key is valid and you have internet connection.")

if __name__ == "__main__":
    main()