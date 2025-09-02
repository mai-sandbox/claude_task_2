import sqlite3
import requests
from typing import TypedDict, List
from pydantic import BaseModel, Field

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState


class SQLQueryResponse(BaseModel):
    """Structured response for SQL query generation"""
    query: str = Field(description="The SQL query to execute")
    reasoning: str = Field(description="Brief explanation of the query logic")
    

class TextToSQLState(MessagesState):
    """State for the text-to-SQL agent"""
    query_result: str = ""
    sql_query: str = ""
    error_message: str = ""


class ChinookDB:
    """Chinook database manager"""
    
    def __init__(self):
        self.conn = None
        self.schema_info = ""
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize in-memory database with Chinook data"""
        try:
            # Fetch the Chinook SQL script
            response = requests.get("https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql")
            response.raise_for_status()
            
            # Create in-memory database
            self.conn = sqlite3.connect(":memory:")
            self.conn.executescript(response.text)
            
            # Generate schema information for prompts
            self._generate_schema_info()
            
        except Exception as e:
            raise Exception(f"Failed to initialize Chinook database: {e}")
    
    def _generate_schema_info(self):
        """Generate detailed schema information for LLM prompts"""
        cursor = self.conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_parts = []
        schema_parts.append("=== CHINOOK DATABASE SCHEMA ===\n")
        
        for (table_name,) in tables:
            schema_parts.append(f"\n--- TABLE: {table_name} ---")
            
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_pk = " (PRIMARY KEY)" if col[5] else ""
                not_null = " NOT NULL" if col[3] else ""
                schema_parts.append(f"  {col_name}: {col_type}{is_pk}{not_null}")
            
            # Get foreign keys
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            fks = cursor.fetchall()
            for fk in fks:
                schema_parts.append(f"  {fk[3]} -> {fk[2]}.{fk[4]} (FOREIGN KEY)")
        
        # Add database description
        schema_parts.append("\n=== DATABASE DESCRIPTION ===")
        schema_parts.append("The Chinook database represents a music store with:")
        schema_parts.append("- Artists, Albums, Tracks (music catalog)")
        schema_parts.append("- Genres and MediaTypes (categorization)")
        schema_parts.append("- Customers, Employees (people)")
        schema_parts.append("- Invoices, InvoiceLines (sales)")
        schema_parts.append("- Playlists, PlaylistTracks (user collections)")
        
        self.schema_info = "\n".join(schema_parts)
    
    def execute_query(self, query: str) -> str:
        """Execute SQL query and return results"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            
            # Get column names
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            if not rows:
                return "No results found."
            
            # Format results as a table
            result_parts = []
            if columns:
                result_parts.append(" | ".join(columns))
                result_parts.append("-" * len(" | ".join(columns)))
            
            for row in rows:
                result_parts.append(" | ".join(str(val) if val is not None else "NULL" for val in row))
            
            return "\n".join(result_parts)
            
        except Exception as e:
            return f"SQL Error: {str(e)}"


# Initialize database
db = ChinookDB()

# Initialize model
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")


def generate_sql_node(state: TextToSQLState, config: RunnableConfig) -> dict:
    """Generate SQL query from user question"""
    
    # Get the user's question from messages
    messages = state.get("messages", [])
    if not messages:
        return {"error_message": "No user question provided"}
    
    user_question = messages[-1].content
    
    # System prompt with schema information
    system_prompt = f"""You are a SQL query generator for the Chinook music database.

{db.schema_info}

Your task is to convert natural language questions into valid SQL queries.

IMPORTANT RULES:
1. Only answer questions that can be answered using the Chinook database
2. If a question is irrelevant or cannot be answered from this database, respond with exactly: "I don't know the answer to that question."
3. Generate syntactically correct SQLite queries
4. Use appropriate JOINs when data spans multiple tables
5. Always use proper table aliases for clarity
6. Include LIMIT clauses for potentially large results

Examples of questions you CAN answer:
- "Who are the top 5 customers by total purchases?"
- "What are the most popular genres?"
- "List all albums by The Beatles"
- "What's the total revenue for 2023?"

Examples of questions you CANNOT answer:
- "What's the weather like?"
- "Tell me about machine learning"
- "What should I cook for dinner?"

Generate only the SQL query with a brief explanation."""

    # Create structured output LLM
    structured_llm = model.with_structured_output(SQLQueryResponse)
    
    # Generate SQL query
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_question)
    ]
    
    try:
        response = structured_llm.invoke(messages)
        
        # Check if this is an irrelevant question
        if "don't know" in response.query.lower() or "cannot" in response.query.lower():
            return {
                "messages": [AIMessage(content="I don't know the answer to that question.")],
                "error_message": "Irrelevant question"
            }
        
        return {
            "sql_query": response.query,
            "messages": [AIMessage(content=f"Generated SQL: {response.query}\nReasoning: {response.reasoning}")]
        }
        
    except Exception as e:
        return {
            "error_message": f"Failed to generate SQL: {str(e)}",
            "messages": [AIMessage(content="I don't know the answer to that question.")]
        }


def execute_sql_node(state: TextToSQLState, config: RunnableConfig) -> dict:
    """Execute the generated SQL query"""
    
    sql_query = state.get("sql_query", "")
    if not sql_query or state.get("error_message"):
        return {}  # Skip execution if no query or error
    
    # Execute query
    result = db.execute_query(sql_query)
    
    return {
        "query_result": result
    }


def generate_response_node(state: TextToSQLState, config: RunnableConfig) -> dict:
    """Generate natural language response from query results"""
    
    # Skip if there's an error or no results
    if state.get("error_message") or not state.get("query_result"):
        return {}
    
    messages = state.get("messages", [])
    user_question = messages[0].content if messages else "Unknown question"
    sql_query = state.get("sql_query", "")
    query_result = state.get("query_result", "")
    
    system_prompt = """You are a helpful assistant that explains database query results in natural language.

Given a user question, SQL query, and query results, provide a clear, concise answer in natural language.

Guidelines:
1. Answer the user's original question directly
2. Use the query results to provide specific information
3. If results are empty, say "No results found for your query"
4. Keep responses conversational and informative
5. Don't repeat the SQL query unless specifically asked"""

    response_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""
User Question: {user_question}

SQL Query: {sql_query}

Query Results:
{query_result}

Please provide a natural language answer to the user's question based on these results.
        """)
    ]
    
    try:
        response = model.invoke(response_messages)
        return {
            "messages": [AIMessage(content=response.content)]
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content="I don't know the answer to that question.")]
        }


def should_execute_sql(state: TextToSQLState) -> str:
    """Determine if SQL should be executed"""
    if state.get("error_message") or not state.get("sql_query"):
        return "end"
    return "execute_sql"


def should_generate_response(state: TextToSQLState) -> str:
    """Determine if response should be generated"""
    if state.get("error_message"):
        return "end"
    return "generate_response"


# Build the graph
graph_builder = StateGraph(TextToSQLState)

# Add nodes
graph_builder.add_node("generate_sql", generate_sql_node)
graph_builder.add_node("execute_sql", execute_sql_node)
graph_builder.add_node("generate_response", generate_response_node)

# Add edges
graph_builder.add_edge(START, "generate_sql")
graph_builder.add_conditional_edges(
    "generate_sql",
    should_execute_sql,
    {
        "execute_sql": "execute_sql",
        "end": END
    }
)
graph_builder.add_conditional_edges(
    "execute_sql",
    should_generate_response,
    {
        "generate_response": "generate_response",
        "end": END
    }
)
graph_builder.add_edge("generate_response", END)

# Compile the graph
graph = graph_builder.compile()
app = graph