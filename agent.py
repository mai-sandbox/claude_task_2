import sqlite3
import requests
import os
from dotenv import load_dotenv
from typing import TypedDict, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel

# Load environment variables
load_dotenv()


class SQLQuery(BaseModel):
    query: str
    explanation: str


class State(TypedDict):
    messages: List[BaseMessage]
    sql_query: str
    sql_result: str
    schema_info: str


def setup_chinook_db():
    """Download and setup the Chinook SQLite database in memory"""
    # Download the SQL script
    response = requests.get("https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql")
    sql_script = response.text
    
    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.executescript(sql_script)
    
    return conn


def get_schema_info(conn):
    """Get detailed schema information for the database"""
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    schema_info = "Database Schema Information:\n\n"
    
    for table in tables:
        table_name = table[0]
        schema_info += f"Table: {table_name}\n"
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            is_pk = col[5]
            not_null = col[3]
            pk_indicator = " (PRIMARY KEY)" if is_pk else ""
            null_indicator = " NOT NULL" if not_null else ""
            schema_info += f"  - {col_name}: {col_type}{pk_indicator}{null_indicator}\n"
        
        # Get foreign key information
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        fks = cursor.fetchall()
        
        for fk in fks:
            from_col = fk[3]
            to_table = fk[2]
            to_col = fk[4]
            schema_info += f"  - {from_col} -> {to_table}.{to_col} (FOREIGN KEY)\n"
        
        schema_info += "\n"
    
    return schema_info


# Initialize database connection (global for this example)
db_conn = setup_chinook_db()
SCHEMA_INFO = get_schema_info(db_conn)

# Initialize the model
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
sql_model = model.with_structured_output(SQLQuery)


def generate_sql_node(state: State) -> dict:
    """Generate SQL query from natural language question"""
    
    user_question = state["messages"][-1].content
    
    system_prompt = f"""You are a SQL expert working with a music store database called Chinook.

{SCHEMA_INFO}

Your task is to convert natural language questions into SQL queries. Follow these rules:
1. Only generate queries that can be answered using the database schema above
2. If the question cannot be answered with the available data, return an empty query string
3. Use proper SQL syntax and table/column names exactly as shown in the schema
4. Provide a brief explanation of what the query does
5. Focus only on SELECT queries for data retrieval

Question: {user_question}"""
    
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_question)]
    result = sql_model.invoke(messages)
    
    return {
        "sql_query": result.query,
        "messages": state["messages"] + [AIMessage(content=f"Generated SQL: {result.query}\nExplanation: {result.explanation}")]
    }


def execute_sql_node(state: State) -> dict:
    """Execute the generated SQL query"""
    
    if not state["sql_query"]:
        return {
            "sql_result": "No query to execute - question cannot be answered with available data",
            "messages": state["messages"] + [AIMessage(content="I don't know the answer to that question based on the available data.")]
        }
    
    try:
        cursor = db_conn.cursor()
        cursor.execute(state["sql_query"])
        results = cursor.fetchall()
        
        # Get column names for better formatting
        column_names = [description[0] for description in cursor.description]
        
        if not results:
            result_text = "No results found"
        else:
            # Format results as a readable string
            result_text = f"Columns: {', '.join(column_names)}\n"
            result_text += f"Results ({len(results)} rows):\n"
            for row in results[:10]:  # Limit to first 10 rows for readability
                result_text += f"  {row}\n"
            if len(results) > 10:
                result_text += f"  ... and {len(results) - 10} more rows"
        
        return {
            "sql_result": result_text,
            "messages": state["messages"] + [AIMessage(content=f"SQL executed successfully. Found {len(results)} results.")]
        }
        
    except Exception as e:
        error_msg = f"SQL Error: {str(e)}"
        return {
            "sql_result": error_msg,
            "messages": state["messages"] + [AIMessage(content="I encountered an error executing the SQL query.")]
        }


def generate_response_node(state: State) -> dict:
    """Generate natural language response based on SQL results"""
    
    if "don't know" in state["messages"][-1].content.lower():
        return {
            "messages": state["messages"] + [AIMessage(content="I don't know the answer to that question.")]
        }
    
    user_question = None
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    system_prompt = f"""You are a helpful assistant that provides natural language answers based on SQL query results.

Original question: {user_question}
SQL Query: {state["sql_query"]}
Query Results: {state["sql_result"]}

Provide a clear, natural language answer to the original question based on the query results.
Be concise and focus only on answering the question. Do not explain the SQL or database structure.
If there were no results, explain that no data was found for the query.
If there was an error, simply say you don't know the answer."""
    
    messages = [SystemMessage(content=system_prompt)]
    result = model.invoke(messages)
    
    return {
        "messages": state["messages"] + [AIMessage(content=result.content)]
    }


# Build the graph
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("generate_sql", generate_sql_node)
graph_builder.add_node("execute_sql", execute_sql_node)
graph_builder.add_node("generate_response", generate_response_node)

# Add edges
graph_builder.add_edge(START, "generate_sql")
graph_builder.add_edge("generate_sql", "execute_sql")
graph_builder.add_edge("execute_sql", "generate_response")
graph_builder.add_edge("generate_response", END)

# Compile the graph
graph = graph_builder.compile()
app = graph