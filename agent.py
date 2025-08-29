import sqlite3
import requests
from typing import Dict, Any, List
from typing_extensions import TypedDict
from pydantic import BaseModel
import re

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


class State(TypedDict):
    messages: List[Any]
    query: str
    sql_query: str
    sql_result: List[Dict]
    natural_response: str
    schema_info: str


class SQLQuery(BaseModel):
    query: str
    reasoning: str


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
        
        # Get foreign key information
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        fks = cursor.fetchall()
        for fk in fks:
            schema_info += f"  - FOREIGN KEY: {fk[3]} -> {fk[2]}.{fk[4]}\n"
        
        schema_info += "\n"
    
    return schema_info


# Initialize database and model
db_conn = setup_database()
schema_info = get_schema_info(db_conn)
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

# Add nodes
graph_builder.add_node("sql_generation", sql_generation_node)
graph_builder.add_node("sql_execution", sql_execution_node)
graph_builder.add_node("response_generation", response_generation_node)

# Add edges
graph_builder.add_edge(START, "sql_generation")
graph_builder.add_edge("sql_generation", "sql_execution")
graph_builder.add_edge("sql_execution", "response_generation")
graph_builder.add_edge("response_generation", END)

# Compile the graph
graph = graph_builder.compile()
app = graph


def query_database(user_question: str) -> str:
    """Main function to query the database with natural language."""
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


if __name__ == "__main__":
    # Test the agent
    test_questions = [
        "Who are the top 5 artists with the most albums?",
        "What are the most popular music genres?",
        "How much revenue did the company make in 2009?",
        "What is the weather like today?"  # Irrelevant question
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        print(f"Answer: {query_database(question)}")
        print("-" * 50)