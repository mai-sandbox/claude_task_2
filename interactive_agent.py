"""
Interactive Text-to-SQL Agent for Chinook Database
Run this script to interact with the agent in real-time
"""

import os
from dotenv import load_dotenv
from text_to_sql_agent import TextToSQLAgent

def main():
    """Interactive demo of the text-to-SQL agent."""
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return
    
    # Create the agent
    print("Initializing Text-to-SQL Agent...")
    try:
        agent = TextToSQLAgent(api_key)
        print("✅ Agent initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        return
    
    print("\n" + "="*60)
    print("🎵 Welcome to the Chinook Database Text-to-SQL Agent! 🎵")
    print("="*60)
    print("You can ask questions about:")
    print("• Artists, Albums, and Tracks")
    print("• Customers and their purchases")
    print("• Employees and sales")
    print("• Music genres and media types")
    print("• Invoices and sales data")
    print("\nType 'quit', 'exit', or 'bye' to stop.")
    print("Type 'help' for example questions.")
    print("-" * 60)
    
    while True:
        try:
            question = input("\n🤔 Your question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'bye', 'q']:
                print("\n👋 Thanks for using the Text-to-SQL Agent!")
                break
            
            if question.lower() == 'help':
                print("\n📝 Example questions you can ask:")
                print("• How many customers are there?")
                print("• What are the top 10 selling tracks?")
                print("• Which artist has the most albums?")
                print("• Show me customers from Canada")
                print("• What's the total revenue for 2009?")
                print("• Which employee made the most sales?")
                print("• What are the different music genres?")
                continue
            
            if not question:
                print("Please enter a question!")
                continue
            
            print("\n🔍 Processing your question...")
            answer = agent.query(question)
            print(f"\n💡 Answer: {answer}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Thanks for using the Text-to-SQL Agent!")
            break
        except Exception as e:
            print(f"\n❌ Error processing question: {e}")
    
    # Clean up
    agent.close()

if __name__ == "__main__":
    main()