import sqlite3
import requests
from typing import Dict, Any, List
from typing_extensions import TypedDict
from pydantic import BaseModel
import os

# Check if we can use the LangGraph agent or fallback to simple version
try:
    from langgraph.graph import StateGraph, START, END
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGGRAPH_AVAILABLE = True
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not found. The full agent won't work.")
        LANGGRAPH_AVAILABLE = False
        
except ImportError:
    print("LangGraph not installed. Using simple version.")
    LANGGRAPH_AVAILABLE = False


class State(TypedDict):
    messages: List[Any]
    query: str
    sql_query: str
    sql_result: List[Dict]
    natural_response: str
    schema_info: str


def setup_database() -> sqlite3.Connection:
    """Download Chinook database and create in-memory SQLite database."""
    # Download the SQL file
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response = requests.get(url)
    sql_content = response.text
    
    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Execute the SQL to create tables and insert data
    cursor.executescript(sql_content)
    conn.commit()
    
    return conn


def get_schema_info(conn: sqlite3.Connection) -> str:
    """Get detailed schema information for all tables."""
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_info = "DATABASE SCHEMA INFORMATION:\n\n"
    
    for table in tables:
        table_name = table[0]
        schema_info += f"Table: {table_name}\n"
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            is_nullable = "NOT NULL" if col[3] else "NULL"
            is_pk = "PRIMARY KEY" if col[5] else ""
            schema_info += f"  - {col_name} ({col_type}) {is_nullable} {is_pk}\n"
        
        schema_info += "\n"
    
    return schema_info


# Initialize database
db_conn = setup_database()
schema_info = get_schema_info(db_conn)


def simple_text_to_sql(user_query: str) -> str:
    """Simple rule-based text-to-SQL converter for demonstration."""
    query_lower = user_query.lower()
    
    # Common queries for demonstration
    if "top" in query_lower and "artist" in query_lower and "album" in query_lower:
        return """
        SELECT ar.Name, COUNT(al.AlbumId) as album_count
        FROM Artist ar
        JOIN Album al ON ar.ArtistId = al.ArtistId
        GROUP BY ar.ArtistId, ar.Name
        ORDER BY album_count DESC
        LIMIT 5;
        """
    elif "genre" in query_lower and ("popular" in query_lower or "most" in query_lower):
        return """
        SELECT g.Name, COUNT(t.TrackId) as track_count
        FROM Genre g
        JOIN Track t ON g.GenreId = t.GenreId
        GROUP BY g.GenreId, g.Name
        ORDER BY track_count DESC
        LIMIT 10;
        """
    elif "revenue" in query_lower and ("2009" in query_lower or "total" in query_lower):
        return """
        SELECT SUM(Total) as total_revenue, 
               MIN(InvoiceDate) as first_invoice,
               MAX(InvoiceDate) as last_invoice
        FROM Invoice;
        """
    elif ("customer" in query_lower and ("country" in query_lower or "location" in query_lower)) or ("countries" in query_lower and "customer" in query_lower):
        return """
        SELECT Country, COUNT(*) as customer_count
        FROM Customer
        GROUP BY Country
        ORDER BY customer_count DESC
        LIMIT 10;
        """
    else:
        return "SELECT 'IRRELEVANT_QUERY' as result;"


def execute_sql_query(sql_query: str) -> List[Dict]:
    """Execute SQL query and return results."""
    try:
        cursor = db_conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description] if cursor.description else []
        
        # Convert to list of dictionaries
        result_dicts = []
        for row in results:
            result_dicts.append(dict(zip(column_names, row)))
        
        return result_dicts
        
    except Exception as e:
        print(f"SQL execution error: {str(e)}")
        return []


def generate_natural_response(user_query: str, sql_results: List[Dict]) -> str:
    """Generate natural language response from SQL results."""
    # Check if query was irrelevant
    if sql_results and len(sql_results) == 1 and sql_results[0].get("result") == "IRRELEVANT_QUERY":
        return "I don't know the answer to that question. I can only answer questions about the music database including artists, albums, tracks, customers, and sales data."
    
    # Check if no results
    if not sql_results:
        return "I don't know the answer to that question based on the available data."
    
    # Simple response generation based on query type
    query_lower = user_query.lower()
    
    if "top" in query_lower and "artist" in query_lower and "album" in query_lower:
        response = "Here are the top artists with the most albums:\n"
        for i, result in enumerate(sql_results, 1):
            response += f"{i}. {result['Name']}: {result['album_count']} albums\n"
        return response.strip()
    
    elif "genre" in query_lower and ("popular" in query_lower or "most" in query_lower):
        response = "Here are the most popular music genres by track count:\n"
        for i, result in enumerate(sql_results, 1):
            response += f"{i}. {result['Name']}: {result['track_count']} tracks\n"
        return response.strip()
    
    elif "revenue" in query_lower and ("2009" in query_lower or "total" in query_lower):
        result = sql_results[0]
        revenue = result['total_revenue']
        first_date = result['first_invoice']
        last_date = result['last_invoice']
        if revenue is None:
            return "No revenue data found."
        return f"The total revenue is ${revenue:.2f} (data from {first_date} to {last_date})"
    
    elif ("customer" in query_lower and ("country" in query_lower or "location" in query_lower)) or ("countries" in query_lower and "customer" in query_lower):
        response = "Here are the countries with the most customers:\n"
        for i, result in enumerate(sql_results, 1):
            response += f"{i}. {result['Country']}: {result['customer_count']} customers\n"
        return response.strip()
    
    else:
        return f"Found {len(sql_results)} results: {sql_results}"


def query_database_simple(user_question: str) -> str:
    """Simple version without LangGraph for testing."""
    print(f"Processing question: {user_question}")
    
    # Generate SQL
    sql_query = simple_text_to_sql(user_question)
    print(f"Generated SQL: {sql_query.strip()}")
    
    # Execute SQL
    sql_results = execute_sql_query(sql_query)
    print(f"SQL Results: {sql_results}")
    
    # Generate response
    response = generate_natural_response(user_question, sql_results)
    return response


if LANGGRAPH_AVAILABLE:
    # Full LangGraph implementation (same as agent.py but with API key check)
    class SQLQuery(BaseModel):
        query: str
        reasoning: str

    model = ChatAnthropic(model="claude-3-5-sonnet-20241022")

    def sql_generation_node(state: State) -> Dict[str, Any]:
        """Generate SQL query from natural language input."""
        user_query = state["query"]
        
        system_prompt = f"""You are a SQL expert. Convert natural language questions into SQL queries for the Chinook database.

{state["schema_info"]}

IMPORTANT RULES:
1. Only answer questions that can be answered using the database schema above
2. If the question cannot be answered with the available data, respond with a query that returns no results
3. Use proper SQL syntax for SQLite
4. Always use table and column names exactly as shown in the schema
5. Be precise with your queries - avoid overly broad or complex joins unless necessary

Generate a SQL query to answer this question: {user_query}

If the question is not relevant to the music database or cannot be answered, generate: SELECT 'IRRELEVANT_QUERY' as result;"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Question: {user_query}")
        ]
        
        structured_llm = model.with_structured_output(SQLQuery)
        result = structured_llm.invoke(messages)
        
        return {
            "sql_query": result.query,
            "messages": state["messages"] + [HumanMessage(content=f"Generated SQL: {result.query}")]
        }

    def sql_execution_node(state: State) -> Dict[str, Any]:
        """Execute the generated SQL query."""
        sql_query = state["sql_query"]
        
        try:
            cursor = db_conn.cursor()
            cursor.execute(sql_query)
            results = cursor.fetchall()
            
            # Get column names
            column_names = [description[0] for description in cursor.description] if cursor.description else []
            
            # Convert to list of dictionaries
            result_dicts = []
            for row in results:
                result_dicts.append(dict(zip(column_names, row)))
            
            return {
                "sql_result": result_dicts,
                "messages": state["messages"] + [HumanMessage(content=f"Query executed successfully. Found {len(result_dicts)} results.")]
            }
            
        except Exception as e:
            return {
                "sql_result": [],
                "messages": state["messages"] + [HumanMessage(content=f"SQL execution error: {str(e)}")]
            }

    def response_generation_node(state: State) -> Dict[str, Any]:
        """Generate natural language response from SQL results."""
        user_query = state["query"]
        sql_query = state["sql_query"]
        sql_results = state["sql_result"]
        
        # Check if query was irrelevant
        if sql_results and len(sql_results) == 1 and sql_results[0].get("result") == "IRRELEVANT_QUERY":
            return {
                "natural_response": "I don't know the answer to that question. I can only answer questions about the music database including artists, albums, tracks, customers, and sales data.",
                "messages": state["messages"] + [HumanMessage(content="Query was irrelevant to the database.")]
            }
        
        # Check if no results
        if not sql_results:
            return {
                "natural_response": "I don't know the answer to that question based on the available data.",
                "messages": state["messages"] + [HumanMessage(content="No results found.")]
            }
        
        system_prompt = f"""Convert the SQL query results into a natural, conversational response.

Original question: {user_query}
SQL query used: {sql_query}
Results: {sql_results}

Provide a clear, concise answer based on the data. If there are multiple results, summarize appropriately. Only use the information from the SQL results - don't add external knowledge."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="Please provide a natural language response based on the query results.")
        ]
        
        response = model.invoke(messages)
        
        return {
            "natural_response": response.content,
            "messages": state["messages"] + [HumanMessage(content=f"Generated response: {response.content}")]
        }

    # Build the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("sql_generation", sql_generation_node)
    graph_builder.add_node("sql_execution", sql_execution_node)
    graph_builder.add_node("response_generation", response_generation_node)
    graph_builder.add_edge(START, "sql_generation")
    graph_builder.add_edge("sql_generation", "sql_execution")
    graph_builder.add_edge("sql_execution", "response_generation")
    graph_builder.add_edge("response_generation", END)

    graph = graph_builder.compile()
    app = graph

    def query_database(user_question: str) -> str:
        """Main function to query the database with natural language using LangGraph."""
        initial_state = {
            "messages": [],
            "query": user_question,
            "sql_query": "",
            "sql_result": [],
            "natural_response": "",
            "schema_info": schema_info
        }
        
        result = app.invoke(initial_state)
        return result["natural_response"]
else:
    # Fallback to simple version
    query_database = query_database_simple
    app = None


if __name__ == "__main__":
    # Test the agent
    test_questions = [
        "Who are the top 5 artists with the most albums?",
        "What are the most popular music genres?",
        "How much revenue did the company make in 2009?",
        "Which countries have the most customers?",
        "What is the weather like today?"  # Irrelevant question
    ]
    
    print(f"Using {'LangGraph' if LANGGRAPH_AVAILABLE else 'Simple'} implementation")
    print("=" * 60)
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        print(f"Answer: {query_database(question)}")
        print("-" * 50)