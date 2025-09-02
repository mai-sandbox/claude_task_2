import sqlite3
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool


class DatabaseSchema:
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._schema_info = None
        
    def create_in_memory_db(self, sql_file_path: str):
        """Create an in-memory SQLite database from SQL file"""
        conn = sqlite3.connect(":memory:")
        with open(sql_file_path, 'r') as file:
            sql_content = file.read()
        conn.executescript(sql_content)
        return conn
    
    def get_schema_info(self, conn: sqlite3.Connection) -> str:
        """Extract detailed schema information from the database"""
        if self._schema_info:
            return self._schema_info
            
        schema_info = []
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            schema_info.append(f"\nTable: {table_name}")
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name, col_type, not_null, default, pk = col[1], col[2], col[3], col[4], col[5]
                pk_str = " (PRIMARY KEY)" if pk else ""
                not_null_str = " NOT NULL" if not_null else ""
                default_str = f" DEFAULT {default}" if default else ""
                schema_info.append(f"  - {col_name}: {col_type}{pk_str}{not_null_str}{default_str}")
            
            # Get foreign key information
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            fks = cursor.fetchall()
            for fk in fks:
                schema_info.append(f"  - FOREIGN KEY {fk[3]} REFERENCES {fk[2]}({fk[4]})")
        
        self._schema_info = "\n".join(schema_info)
        return self._schema_info


class TextToSQLAgent:
    def __init__(self):
        self.conn = None
        self.schema = DatabaseSchema()
        self.model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
        
    def setup_database(self):
        """Initialize the in-memory database with Chinook data"""
        self.conn = self.schema.create_in_memory_db("chinook.sql")
        
    @tool
    def execute_sql_query(query: str) -> str:
        """Execute SQL query against the Chinook database and return results.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            Query results as formatted string or error message
        """
        # Access the agent instance through a global or pass it properly
        agent_instance = globals().get('current_agent_instance')
        if not agent_instance or not agent_instance.conn:
            return "Error: Database connection not available"
            
        try:
            cursor = agent_instance.conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                return "Query executed successfully but returned no results."
            
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            # Format results nicely
            formatted_results = []
            formatted_results.append(" | ".join(column_names))
            formatted_results.append("-" * len(" | ".join(column_names)))
            
            for row in results[:10]:  # Limit to first 10 rows
                formatted_results.append(" | ".join(str(cell) if cell is not None else "NULL" for cell in row))
            
            if len(results) > 10:
                formatted_results.append(f"... ({len(results) - 10} more rows)")
                
            return "\n".join(formatted_results)
            
        except Exception as e:
            return f"SQL Error: {str(e)}"
    
    def create_agent(self):
        """Create the LangGraph agent with SQL capabilities"""
        if not self.conn:
            self.setup_database()
            
        # Get schema information for the prompt
        schema_info = self.schema.get_schema_info(self.conn)
        
        # Set global reference for the tool to access
        globals()['current_agent_instance'] = self
        
        system_prompt = f"""You are a text-to-SQL agent that helps users query the Chinook database.

The Chinook database contains information about a music store with the following schema:
{schema_info}

Your task is to:
1. Convert natural language questions into SQL queries
2. Execute the SQL queries against the database
3. Provide natural language responses based on the query results

Important guidelines:
- Only answer questions that can be answered using the database
- If a question is irrelevant or cannot be answered with the available data, respond with "I don't know the answer to that question."
- Always use proper SQL syntax for SQLite
- Be precise and helpful in your natural language responses
- Limit results to reasonable amounts (use LIMIT when appropriate)

Remember: Your purpose is ONLY to convert text requests to SQL and generate responses in natural language based on database results."""

        agent = create_react_agent(
            model=self.model,
            tools=[self.execute_sql_query],
            prompt=system_prompt
        )
        
        return agent


def create_app():
    """Create and return the LangGraph application"""
    sql_agent = TextToSQLAgent()
    sql_agent.setup_database()
    agent = sql_agent.create_agent()
    return agent


# Export the compiled graph as 'app' for deployment
app = create_app()

if __name__ == "__main__":
    # Test the agent
    agent = create_app()
    
    test_queries = [
        "How many customers are there?",
        "What are the top 5 best-selling albums?",
        "Show me all genres in the database",
        "What is the weather like today?",  # Should respond with "I don't know"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = agent.invoke({"messages": [HumanMessage(content=query)]})
            print(f"Response: {result['messages'][-1].content}")
        except Exception as e:
            print(f"Error: {e}")