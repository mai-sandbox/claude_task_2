#!/usr/bin/env python3

from text_to_sql_agent import create_text_to_sql_agent

def main():
    """Interactive interface for the text-to-SQL agent"""
    print("🎵 Welcome to the Chinook Music Database Query Agent!")
    print("Ask me any question about the music database.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    agent = create_text_to_sql_agent()
    
    while True:
        try:
            user_query = input("💬 Your question: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_query:
                continue
            
            print("\n🤔 Thinking...")
            
            result = agent.invoke({
                "user_query": user_query,
                "sql_query": "",
                "sql_result": "",
                "natural_language_response": "",
                "error": ""
            })
            
            print(f"\n💭 Answer: {result['natural_language_response']}")
            
            if result.get("sql_query"):
                print(f"\n🔍 SQL Query used:")
                print(f"   {result['sql_query']}")
            
            print("\n" + "="*60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again.\n")

if __name__ == "__main__":
    main()