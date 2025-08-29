import sqlite3
import requests
from typing import TypedDict, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    messages: List[BaseMessage]
    user_query: str
    sql_query: str
    query_result: List[Dict[str, Any]]
    final_response: str

class SQLQuery(BaseModel):
    """Structured output for SQL query generation"""
    sql: str = Field(description="The SQL query to execute against the Chinook database")
    reasoning: str = Field(description="Brief explanation of why this SQL query answers the user's question")

class DatabaseManager:
    def __init__(self):
        self.db = None
        self.schema_info = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize in-memory SQLite database with Chinook data"""
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        
        # Download and execute Chinook schema
        schema_url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        try:
            with open("chinook_schema.sql", "r", encoding="utf-8") as f:
                schema_sql = f.read()
        except FileNotFoundError:
            response = requests.get(schema_url)
            schema_sql = response.text
        
        cursor = self.db.cursor()
        cursor.executescript(schema_sql)
        self.db.commit()
        
        # Extract schema information for prompts
        self._extract_schema_info()
    
    def _extract_schema_info(self):
        """Extract table and column information for prompt context"""
        cursor = self.db.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_info = {}
        for table in tables:
            table_name = table[0]
            
            # Get column information for each table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            schema_info[table_name] = {
                'columns': [(col[1], col[2]) for col in columns],  # (name, type)
                'sample_data': self._get_sample_data(table_name)
            }
        
        self.schema_info = schema_info
    
    def _get_sample_data(self, table_name: str, limit: int = 3):
        """Get sample data from table for better context"""
        cursor = self.db.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
            return [dict(row) for row in cursor.fetchall()]
        except:
            return []
    
    def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        cursor = self.db.cursor()
        try:
            cursor.execute(sql_query)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_schema_context(self) -> str:
        """Generate schema context for LLM prompts"""
        context = "Chinook Database Schema:\n\n"
        
        for table_name, info in self.schema_info.items():
            context += f"Table: {table_name}\n"
            context += "Columns:\n"
            for col_name, col_type in info['columns']:
                context += f"  - {col_name} ({col_type})\n"
            
            if info['sample_data']:
                context += f"Sample data (first 3 rows):\n"
                for i, row in enumerate(info['sample_data'][:3], 1):
                    context += f"  Row {i}: {row}\n"
            context += "\n"
        
        return context

# Initialize database manager
db_manager = DatabaseManager()

# Initialize LLM
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")

def generate_sql_node(state: State) -> Dict[str, Any]:
    """Generate SQL query from natural language question"""
    user_query = state["messages"][-1].content
    
    schema_context = db_manager.get_schema_context()
    
    system_prompt = f"""You are a text-to-SQL expert for the Chinook music database. 

{schema_context}

Your task:
1. Convert the user's natural language question into a precise SQL query
2. Only answer questions that can be answered using this database schema
3. If the question is irrelevant or cannot be answered with this database, respond with "I don't know"

Rules:
- Use proper SQLite syntax
- Join tables when necessary to get complete information
- Use appropriate WHERE clauses for filtering
- Use aggregate functions (COUNT, SUM, AVG, etc.) when needed
- Always use proper table aliases for clarity
- Return meaningful column names

Generate ONLY a SQL query that answers the user's question."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_query)
    ]
    
    structured_model = model.with_structured_output(SQLQuery)
    response = structured_model.invoke(messages)
    
    # Check if the query is relevant
    if "I don't know" in response.reasoning or "irrelevant" in response.reasoning.lower():
        return {
            "sql_query": "",
            "messages": state["messages"] + [AIMessage(content="I don't know the answer to that question based on the Chinook database.")]
        }
    
    return {
        "sql_query": response.sql,
        "user_query": user_query,
        "messages": state["messages"] + [AIMessage(content=f"Generated SQL: {response.sql}")]
    }

def execute_sql_node(state: State) -> Dict[str, Any]:
    """Execute the generated SQL query"""
    if not state.get("sql_query"):
        return {"query_result": []}
    
    results = db_manager.execute_query(state["sql_query"])
    
    return {
        "query_result": results,
        "messages": state["messages"] + [AIMessage(content=f"Query executed. Found {len(results)} results.")]
    }

def generate_response_node(state: State) -> Dict[str, Any]:
    """Generate natural language response from SQL results"""
    if not state.get("query_result"):
        return {"final_response": "I don't know the answer to that question."}
    
    user_query = state["user_query"]
    sql_query = state["sql_query"]
    results = state["query_result"]
    
    # Check for SQL errors
    if results and "error" in results[0]:
        return {"final_response": "I don't know the answer to that question based on the available data."}
    
    system_prompt = """You are a helpful assistant that converts SQL query results into natural language responses.

Given:
1. User's original question
2. SQL query that was executed 
3. Results from the database

Generate a clear, concise natural language answer that directly addresses the user's question.

Rules:
- Be conversational and natural
- Include specific data points from the results
- Format numbers appropriately (e.g., currency, counts)
- If there are no results, say "I don't have that information"
- Keep responses focused and relevant"""
    
    results_text = f"Results ({len(results)} rows):\n"
    for i, row in enumerate(results[:10], 1):  # Limit to first 10 rows
        results_text += f"Row {i}: {row}\n"
    
    if len(results) > 10:
        results_text += f"... and {len(results) - 10} more rows"
    
    prompt = f"""User Question: {user_query}

SQL Query: {sql_query}

{results_text}

Generate a natural language response:"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt)
    ]
    
    response = model.invoke(messages)
    final_answer = response.content
    
    return {
        "final_response": final_answer,
        "messages": state["messages"] + [AIMessage(content=final_answer)]
    }

def should_execute_sql(state: State) -> str:
    """Conditional edge to determine if SQL should be executed"""
    if state.get("sql_query") and state["sql_query"].strip():
        return "execute_sql"
    else:
        return "end"

# Build the graph
workflow = StateGraph(State)

# Add nodes
workflow.add_node("generate_sql", generate_sql_node)
workflow.add_node("execute_sql", execute_sql_node)
workflow.add_node("generate_response", generate_response_node)

# Add edges
workflow.add_edge(START, "generate_sql")
workflow.add_conditional_edges(
    "generate_sql",
    should_execute_sql,
    {
        "execute_sql": "execute_sql",
        "end": END
    }
)
workflow.add_edge("execute_sql", "generate_response")
workflow.add_edge("generate_response", END)

# Compile graph
graph = workflow.compile()
app = graph