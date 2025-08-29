"""
LangGraph-based Text-to-SQL Agent for Chinook Database
"""
import sqlite3
import re
from typing import List, Dict, Any, TypedDict
from pydantic import BaseModel, Field
import requests

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState


class SQLQuery(BaseModel):
    """Structured output for SQL generation"""
    sql_query: str = Field(description="The generated SQL query")
    confidence: str = Field(description="High/Medium/Low confidence in the query")
    explanation: str = Field(description="Brief explanation of what the query does")


class TextToSQLState(TypedDict):
    """State for the text-to-SQL agent"""
    messages: List[BaseMessage]
    user_query: str
    sql_query: str
    sql_result: Any
    final_answer: str


class ChinookDatabase:
    """Manages the in-memory Chinook SQLite database"""
    
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self._setup_database()
    
    def _setup_database(self):
        """Download and setup the Chinook database"""
        try:
            response = requests.get("https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql")
            response.raise_for_status()
            sql_script = response.text
            
            # Execute the SQL script to create and populate the database
            self.cursor.executescript(sql_script)
            self.conn.commit()
            
        except Exception as e:
            print(f"Error setting up database: {e}")
            raise
    
    def execute_query(self, query: str) -> List[Dict]:
        """Execute a SQL query and return results"""
        try:
            # Security check - only allow SELECT statements
            if not query.strip().upper().startswith('SELECT'):
                return {"error": "Only SELECT queries are allowed"}
            
            self.cursor.execute(query)
            columns = [description[0] for description in self.cursor.description]
            rows = self.cursor.fetchall()
            
            # Convert to list of dictionaries
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_schema_info(self) -> str:
        """Get detailed schema information for the database"""
        schema_info = []
        
        # Get all table names
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = self.cursor.fetchall()
        
        for (table_name,) in tables:
            schema_info.append(f"\n--- {table_name.upper()} TABLE ---")
            
            # Get column information
            self.cursor.execute(f"PRAGMA table_info({table_name});")
            columns = self.cursor.fetchall()
            
            for column in columns:
                col_name, col_type, not_null, default, pk = column[1], column[2], column[3], column[4], column[5]
                pk_info = " (PRIMARY KEY)" if pk else ""
                null_info = " NOT NULL" if not_null else ""
                default_info = f" DEFAULT {default}" if default else ""
                schema_info.append(f"  {col_name}: {col_type}{pk_info}{null_info}{default_info}")
            
            # Get sample data (first 3 rows)
            self.cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            sample_rows = self.cursor.fetchall()
            if sample_rows:
                schema_info.append("  Sample data:")
                for row in sample_rows:
                    schema_info.append(f"    {row}")
        
        return "\n".join(schema_info)


# Initialize database
db = ChinookDatabase()

# Initialize the model
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# Get schema information for the prompt
SCHEMA_INFO = db.get_schema_info()

SYSTEM_PROMPT = f"""You are a text-to-SQL expert for the Chinook music database. Your job is to convert natural language questions into accurate SQL queries.

IMPORTANT CONSTRAINTS:
- ONLY answer questions that can be answered using the Chinook database
- If a question cannot be answered with the available data, respond with "I don't know the answer to that question"
- NEVER discuss topics outside of the database content
- Only generate SELECT queries (no INSERT, UPDATE, DELETE)

DATABASE SCHEMA:
{SCHEMA_INFO}

The database contains information about:
- Artists and their albums
- Music tracks with genres and media types
- Customers and their purchases (invoices)
- Employees and their relationships
- Playlists and playlist tracks

When generating SQL:
1. Use proper table joins when needed
2. Be careful with column names and table relationships
3. Consider using LIMIT for queries that might return many rows
4. Use appropriate WHERE clauses to filter results
"""


def sql_generation_node(state: TextToSQLState) -> Dict[str, Any]:
    """Generate SQL query from user input"""
    user_query = state["user_query"]
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Convert this question to a SQL query: {user_query}")
    ]
    
    # Use structured output for reliable SQL generation
    structured_llm = model.with_structured_output(SQLQuery)
    result = structured_llm.invoke(messages)
    
    # Check if the query is relevant
    if "don't know" in result.explanation.lower() or result.confidence == "Low":
        return {
            "sql_query": "",
            "messages": state["messages"] + [AIMessage(content="I don't know the answer to that question.")]
        }
    
    return {
        "sql_query": result.sql_query,
        "messages": state["messages"] + [AIMessage(content=f"Generated SQL: {result.sql_query}")]
    }


def sql_execution_node(state: TextToSQLState) -> Dict[str, Any]:
    """Execute the generated SQL query"""
    if not state["sql_query"]:
        return {"sql_result": None}
    
    result = db.execute_query(state["sql_query"])
    
    return {
        "sql_result": result,
        "messages": state["messages"] + [AIMessage(content=f"Query executed, got {len(result) if isinstance(result, list) else 'error'} results")]
    }


def response_generation_node(state: TextToSQLState) -> Dict[str, Any]:
    """Generate natural language response based on SQL results"""
    if not state["sql_result"]:
        return {"final_answer": "I don't know the answer to that question."}
    
    if isinstance(state["sql_result"], dict) and "error" in state["sql_result"]:
        return {"final_answer": "I encountered an error processing your query."}
    
    # Generate natural language response
    messages = [
        SystemMessage(content="""You are a helpful assistant that explains database query results in natural language.
        
        Rules:
        - Provide clear, concise answers based on the data
        - If no results are found, say so politely
        - Don't hallucinate information not in the results
        - Keep responses focused and relevant"""),
        HumanMessage(content=f"""
        User question: {state['user_query']}
        SQL query used: {state['sql_query']}
        Results: {state['sql_result']}
        
        Please provide a natural language answer to the user's question based on these results.
        """)
    ]
    
    response = model.invoke(messages)
    
    return {
        "final_answer": response.content,
        "messages": state["messages"] + [AIMessage(content=response.content)]
    }


def should_execute_sql(state: TextToSQLState) -> str:
    """Determine if we should execute the SQL query"""
    if state["sql_query"]:
        return "execute_sql"
    else:
        return "generate_response"


# Build the graph
graph_builder = StateGraph(TextToSQLState)

# Add nodes
graph_builder.add_node("generate_sql", sql_generation_node)
graph_builder.add_node("execute_sql", sql_execution_node)
graph_builder.add_node("generate_response", response_generation_node)

# Add edges
graph_builder.add_edge(START, "generate_sql")
graph_builder.add_conditional_edges(
    "generate_sql",
    should_execute_sql,
    {
        "execute_sql": "execute_sql",
        "generate_response": "generate_response"
    }
)
graph_builder.add_edge("execute_sql", "generate_response")
graph_builder.add_edge("generate_response", END)

# Compile and export
graph = graph_builder.compile()
app = graph


def run_query(user_question: str) -> str:
    """Convenience function to run a single query"""
    initial_state = {
        "messages": [HumanMessage(content=user_question)],
        "user_query": user_question,
        "sql_query": "",
        "sql_result": None,
        "final_answer": ""
    }
    
    result = app.invoke(initial_state)
    return result["final_answer"]


if __name__ == "__main__":
    # Test queries
    test_queries = [
        "How many artists are in the database?",
        "What are the top 5 genres by number of tracks?",
        "Who are the customers from Brazil?",
        "What is the weather like today?"  # Should return "I don't know"
    ]
    
    print("Testing Text-to-SQL Agent:")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\nQ: {query}")
        answer = run_query(query)
        print(f"A: {answer}")
        print("-" * 30)