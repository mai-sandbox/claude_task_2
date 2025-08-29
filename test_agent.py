from agent import app
from langchain_core.messages import HumanMessage

def test_agent():
    """Test the text-to-SQL agent with sample queries"""
    
    # Test 1: Valid music-related query
    print("=== Test 1: Artists and Albums ===")
    result = app.invoke({"messages": [HumanMessage(content="How many albums does each artist have?")]})
    print("Final response:", result["messages"][-1].content)
    print()
    
    # Test 2: Customer-related query
    print("=== Test 2: Customer Information ===")
    result = app.invoke({"messages": [HumanMessage(content="Which customers are from the USA?")]})
    print("Final response:", result["messages"][-1].content)
    print()
    
    # Test 3: Irrelevant query
    print("=== Test 3: Irrelevant Query ===")
    result = app.invoke({"messages": [HumanMessage(content="What's the weather like today?")]})
    print("Final response:", result["messages"][-1].content)
    print()
    
    # Test 4: Track information
    print("=== Test 4: Track Information ===")
    result = app.invoke({"messages": [HumanMessage(content="What are the top 5 longest tracks?")]})
    print("Final response:", result["messages"][-1].content)

if __name__ == "__main__":
    test_agent()