import os
import sqlite3
from typing import Dict, Any, TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()


class AgentState(TypedDict):
    user_query: str
    sql_query: str
    sql_result: str
    natural_language_response: str
    error: str


def load_chinook_database():
    """Load the Chinook database into an in-memory SQLite database"""
    conn = sqlite3.connect(":memory:")
    
    with open("chinook_schema.sql", "r") as f:
        sql_script = f.read()
    
    conn.executescript(sql_script)
    return conn


def get_database_schema():
    """Get a readable description of the database schema"""
    return """
    The Chinook database contains the following tables:
    
    1. **Album** (AlbumId, Title, ArtistId) - Music albums
    2. **Artist** (ArtistId, Name) - Music artists
    3. **Customer** (CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId) - Customer information
    4. **Employee** (EmployeeId, LastName, FirstName, Title, ReportsTo, BirthDate, HireDate, Address, City, State, Country, PostalCode, Phone, Fax, Email) - Employee information
    5. **Genre** (GenreId, Name) - Music genres
    6. **Invoice** (InvoiceId, CustomerId, InvoiceDate, BillingAddress, BillingCity, BillingState, BillingCountry, BillingPostalCode, Total) - Customer invoices
    7. **InvoiceLine** (InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity) - Individual items on invoices
    8. **MediaType** (MediaTypeId, Name) - Types of media (MP3, AAC, etc.)
    9. **Playlist** (PlaylistId, Name) - Music playlists
    10. **PlaylistTrack** (PlaylistId, TrackId) - Tracks in playlists
    11. **Track** (TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice) - Individual music tracks
    
    Key relationships:
    - Albums belong to Artists
    - Tracks belong to Albums and have Genres and MediaTypes
    - Customers make Purchases (Invoices) containing InvoiceLines for Tracks
    - Employees can be support representatives for Customers
    - Tracks can be in multiple Playlists
    """


def generate_sql_node(state: AgentState) -> Dict[str, Any]:
    """Generate SQL query from natural language query"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    schema_info = get_database_schema()
    
    prompt = f"""You are a SQL expert. Convert the following natural language question into a valid SQLite query.

Database Schema:
{schema_info}

Question: {state["user_query"]}

Rules:
1. Only generate SELECT statements - no INSERT, UPDATE, or DELETE
2. Use proper SQLite syntax
3. Join tables when necessary to answer the question
4. If the question cannot be answered with the available data, return "CANNOT_ANSWER"
5. Return ONLY the SQL query, no explanation

SQL Query:"""

    response = llm.invoke([HumanMessage(content=prompt)])
    sql_query = response.content.strip()
    
    # Clean up markdown formatting if present
    if sql_query.startswith("```sql"):
        sql_query = sql_query[6:]  # Remove ```sql
    if sql_query.endswith("```"):
        sql_query = sql_query[:-3]  # Remove ```
    sql_query = sql_query.strip()
    
    if sql_query == "CANNOT_ANSWER":
        return {
            "sql_query": "",
            "error": "Question cannot be answered with the available database"
        }
    
    return {"sql_query": sql_query}


def execute_sql_node(state: AgentState) -> Dict[str, Any]:
    """Execute SQL query against the Chinook database"""
    if state.get("error") or not state.get("sql_query"):
        return {"sql_result": ""}
    
    try:
        conn = load_chinook_database()
        cursor = conn.cursor()
        
        cursor.execute(state["sql_query"])
        results = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        
        conn.close()
        
        if not results:
            return {"sql_result": "No results found"}
        
        formatted_results = []
        for row in results:
            row_dict = dict(zip(column_names, row))
            formatted_results.append(row_dict)
        
        return {"sql_result": str(formatted_results)}
        
    except Exception as e:
        return {"error": f"SQL execution error: {str(e)}"}


def generate_response_node(state: AgentState) -> Dict[str, Any]:
    """Generate natural language response from SQL results"""
    if state.get("error"):
        return {"natural_language_response": "I don't know the answer to that question."}
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = f"""You are a helpful assistant that converts SQL query results into natural language responses.

Original question: {state["user_query"]}
SQL query used: {state["sql_query"]}
Query results: {state["sql_result"]}

Convert the query results into a natural, conversational response that directly answers the user's question.
Be concise but informative. If there are no results, say you don't know the answer.

Response:"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return {"natural_language_response": response.content}


def should_continue(state: AgentState) -> str:
    """Determine if we should continue processing or end"""
    if state.get("error"):
        return "generate_response"
    return "execute_sql"


def create_text_to_sql_agent():
    """Create and return the LangGraph text-to-SQL agent"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("generate_response", generate_response_node)
    
    # Add edges
    workflow.add_edge(START, "generate_sql")
    workflow.add_conditional_edges(
        "generate_sql",
        should_continue,
        {
            "execute_sql": "execute_sql",
            "generate_response": "generate_response"
        }
    )
    workflow.add_edge("execute_sql", "generate_response")
    workflow.add_edge("generate_response", END)
    
    return workflow.compile()


def main():
    """Test the text-to-SQL agent"""
    agent = create_text_to_sql_agent()
    
    # Test queries
    test_queries = [
        "What are the top 5 best-selling artists by total sales?",
        "How many customers are from each country?",
        "What is the most popular music genre?",
        "What are the weather conditions today?",  # Should return "don't know"
    ]
    
    for query in test_queries:
        print(f"\n🤔 Question: {query}")
        print("=" * 50)
        
        result = agent.invoke({
            "user_query": query,
            "sql_query": "",
            "sql_result": "",
            "natural_language_response": "",
            "error": ""
        })
        
        print(f"💬 Answer: {result['natural_language_response']}")
        
        if result.get("sql_query"):
            print(f"🔍 SQL Used: {result['sql_query']}")


if __name__ == "__main__":
    main()