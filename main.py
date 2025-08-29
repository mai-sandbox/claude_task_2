#!/usr/bin/env python3

import sys
from text_to_sql_agent import TextToSQLAgent

def main():
    """Main application entry point"""
    print("🎵 Chinook Music Store SQL Agent")
    print("Ask questions about artists, albums, tracks, customers, and sales!")
    print("Type 'exit' or 'quit' to exit.\n")
    
    agent = TextToSQLAgent()
    
    try:
        while True:
            try:
                user_input = input("❓ Your question: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("🤔 Thinking...")
                response = agent.query(user_input)
                print(f"💬 {response}\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
    
    finally:
        agent.close()

if __name__ == "__main__":
    main()