import sqlite3
import requests
from typing import Dict, Any, Annotated, Sequence
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import ToolMessage


class AgentState(BaseModel):
    """State for the agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]


def setup_chinook_database() -> sqlite3.Connection:
    """Download and set up the Chinook SQLite database in memory"""
    # Download the SQL script
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response = requests.get(url)
    sql_script = response.text
    
    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    
    # Execute the SQL script to create tables and insert data
    conn.executescript(sql_script)
    
    return conn


def get_database_schema() -> str:
    """Get the database schema information for the prompt"""
    schema_info = """
    The Chinook database contains the following tables:
    
    1. Album (AlbumId, Title, ArtistId)
    2. Artist (ArtistId, Name)
    3. Customer (CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId)
    4. Employee (EmployeeId, LastName, FirstName, Title, ReportsTo, BirthDate, HireDate, Address, City, State, Country, PostalCode, Phone, Fax, Email)
    5. Genre (GenreId, Name)
    6. Invoice (InvoiceId, CustomerId, InvoiceDate, BillingAddress, BillingCity, BillingState, BillingCountry, BillingPostalCode, Total)
    7. InvoiceLine (InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)
    8. MediaType (MediaTypeId, Name)
    9. Playlist (PlaylistId, Name)
    10. PlaylistTrack (PlaylistId, TrackId)
    11. Track (TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice)
    
    Key relationships:
    - Albums are linked to Artists
    - Tracks belong to Albums, have MediaTypes and Genres
    - Customers make Invoices, which contain InvoiceLines for specific Tracks
    - Employees can be support representatives for Customers
    - Playlists contain multiple Tracks through PlaylistTrack junction table
    """
    return schema_info


@tool
def execute_sql_query(query: str) -> str:
    """Execute SQL query against the Chinook database and return results"""
    try:
        # Set up database connection
        conn = setup_chinook_database()
        cursor = conn.cursor()
        
        # Execute the query
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Format results
        if not results:
            return "No results found."
        
        # Create formatted output
        output = f"Query: {query}\n\nResults:\n"
        output += " | ".join(column_names) + "\n"
        output += "-" * (len(" | ".join(column_names))) + "\n"
        
        for row in results[:10]:  # Limit to first 10 rows
            output += " | ".join(str(cell) if cell is not None else "NULL" for cell in row) + "\n"
        
        if len(results) > 10:
            output += f"\n... and {len(results) - 10} more rows"
        
        conn.close()
        return output
        
    except Exception as e:
        return f"Error executing query: {str(e)}"


def should_continue(state: AgentState):
    """Determine if we should continue to tools or end"""
    last_message = state.messages[-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "end"


def call_model(state: AgentState):
    """Call the LLM with the current messages"""
    system_prompt = f"""You are a text-to-SQL agent for the Chinook music database. Your role is to:

1. Convert natural language questions into SQL queries
2. Execute those queries against the database
3. Provide natural language answers based on the results

{get_database_schema()}

IMPORTANT GUIDELINES:
- Only answer questions that can be answered using the Chinook database
- If a query is irrelevant or cannot be answered using the database, respond with "I don't know the answer to that question"
- Always use proper SQL syntax for SQLite
- Be precise with table and column names
- Limit results to reasonable numbers (e.g., LIMIT 10) when appropriate
- Always explain what data you found in natural language

When you need to query the database, use the execute_sql_query tool with a proper SQL query."""
    
    model = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
    model_with_tools = model.bind_tools([execute_sql_query])
    
    # Add system message to the conversation
    messages = [AIMessage(content=system_prompt)] + state.messages
    response = model_with_tools.invoke(messages)
    
    return {"messages": [response]}


def call_tools(state: AgentState):
    """Execute tools called by the model"""
    last_message = state.messages[-1]
    tool_messages = []
    
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "execute_sql_query":
            result = execute_sql_query.invoke({"query": tool_call["args"]["query"]})
            tool_messages.append(
                ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"]
                )
            )
    
    return {"messages": tool_messages}


def create_text_to_sql_agent():
    """Create the text-to-SQL agent using LangGraph StateGraph"""
    
    # Create state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", call_tools)
    
    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    workflow.add_edge("tools", "agent")
    
    # Compile the graph
    return workflow.compile()


# Create the agent instance for deployment
app = create_text_to_sql_agent()

if __name__ == "__main__":
    # Test the agent locally
    test_queries = [
        "What are the top 5 best-selling artists by total sales?",
        "How many tracks are there in the Jazz genre?",
        "What is the weather like today?",  # Should respond with "I don't know"
        "Which customers are from the USA?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*50}")
        print(f"Test Query {i}: {query}")
        print('='*50)
        
        response = app.invoke({
            "messages": [HumanMessage(content=query)]
        })
        
        # Print the final response
        final_message = response["messages"][-1]
        print(f"Response: {final_message.content}")