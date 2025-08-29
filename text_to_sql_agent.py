import sqlite3
import requests
from typing import Dict, Any, List, Tuple
import os
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict
import json

class AgentState(TypedDict):
    user_query: str
    sql_query: str
    sql_result: List[Dict[str, Any]]
    final_response: str
    error: str

class TextToSQLAgent:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4",
            api_key=openai_api_key,
            temperature=0
        )
        self.db_connection = None
        self.schema_info = ""
        self._setup_database()
        
    def _setup_database(self):
        """Fetch Chinook database and create in-memory SQLite database"""
        print("Fetching Chinook database...")
        
        # Fetch the SQL file
        url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        response = requests.get(url)
        
        if response.status_code == 200:
            sql_content = response.text
            
            # Create in-memory database
            self.db_connection = sqlite3.connect(":memory:")
            self.db_connection.row_factory = sqlite3.Row  # Enable column access by name
            
            # Execute the SQL to create tables and insert data
            cursor = self.db_connection.cursor()
            cursor.executescript(sql_content)
            self.db_connection.commit()
            
            # Extract schema information
            self._extract_schema_info()
            print("Database setup complete!")
        else:
            raise Exception(f"Failed to fetch Chinook database: {response.status_code}")
    
    def _extract_schema_info(self):
        """Extract detailed schema information for the LLM prompt"""
        cursor = self.db_connection.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_parts = []
        for table in tables:
            table_name = table[0]
            
            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            # Get sample data (first 3 rows)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            sample_data = cursor.fetchall()
            
            # Build schema description
            table_info = f"\nTable: {table_name}\n"
            table_info += "Columns:\n"
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_nullable = "NOT NULL" if col[3] else "NULL"
                is_pk = "PRIMARY KEY" if col[5] else ""
                table_info += f"  - {col_name} ({col_type}) {is_nullable} {is_pk}\n"
            
            if sample_data:
                table_info += "\nSample data:\n"
                for row in sample_data:
                    table_info += f"  {dict(row)}\n"
            
            schema_parts.append(table_info)
        
        self.schema_info = "\n".join(schema_parts)
    
    def generate_sql(self, state: AgentState) -> AgentState:
        """Generate SQL query from natural language"""
        user_query = state["user_query"]
        
        prompt = f"""You are a SQL expert. Convert the following natural language question into a SQL query for the Chinook music database.

Database Schema:
{self.schema_info}

Rules:
1. Only use tables and columns that exist in the schema above
2. Generate valid SQLite syntax
3. If the question cannot be answered with the available data, respond with "CANNOT_ANSWER"
4. Be precise and efficient in your queries
5. Use appropriate JOINs when needed
6. Handle case-insensitive searches appropriately

User Question: {user_query}

SQL Query (return only the query, no explanation):"""

        try:
            response = self.llm.invoke(prompt)
            sql_query = response.content.strip()
            
            # Check if the query is answerable
            if "CANNOT_ANSWER" in sql_query.upper():
                state["error"] = "Query cannot be answered with available data"
                return state
            
            # Clean up the SQL query
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            state["sql_query"] = sql_query
            
        except Exception as e:
            state["error"] = f"Error generating SQL: {str(e)}"
        
        return state
    
    def execute_sql(self, state: AgentState) -> AgentState:
        """Execute the generated SQL query"""
        if state.get("error"):
            return state
        
        sql_query = state.get("sql_query", "")
        if not sql_query:
            state["error"] = "No SQL query to execute"
            return state
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(sql_query)
            
            # Fetch results
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            state["sql_result"] = [dict(row) for row in results]
            
        except Exception as e:
            state["error"] = f"SQL execution error: {str(e)}"
        
        return state
    
    def generate_response(self, state: AgentState) -> AgentState:
        """Generate natural language response from SQL results"""
        if state.get("error"):
            state["final_response"] = "I don't know the answer to that question."
            return state
        
        user_query = state["user_query"]
        sql_query = state["sql_query"]
        results = state["sql_result"]
        
        if not results:
            state["final_response"] = "No results found for your query."
            return state
        
        prompt = f"""Based on the SQL query results, provide a clear and natural language answer to the user's question.

User's Question: {user_query}
SQL Query Used: {sql_query}
Query Results: {json.dumps(results, indent=2)}

Provide a concise, helpful answer based on the data. If there are multiple results, summarize them appropriately. Be specific with numbers, names, and details from the results.

Natural Language Response:"""

        try:
            response = self.llm.invoke(prompt)
            state["final_response"] = response.content.strip()
        except Exception as e:
            state["final_response"] = f"Error generating response: {str(e)}"
        
        return state
    
    def should_continue(self, state: AgentState) -> str:
        """Determine if processing should continue"""
        if state.get("error"):
            return "generate_response"
        if not state.get("sql_query"):
            return "generate_sql"
        if not state.get("sql_result") and "sql_result" not in state:
            return "execute_sql"
        return "generate_response"
    
    def create_graph(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("generate_sql", self.generate_sql)
        workflow.add_node("execute_sql", self.execute_sql)
        workflow.add_node("generate_response", self.generate_response)
        
        # Define the flow
        workflow.set_entry_point("generate_sql")
        workflow.add_conditional_edges(
            "generate_sql",
            self.should_continue,
            {
                "execute_sql": "execute_sql",
                "generate_response": "generate_response"
            }
        )
        workflow.add_edge("execute_sql", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def query(self, user_question: str) -> str:
        """Main method to process user queries"""
        app = self.create_graph()
        
        initial_state = AgentState(
            user_query=user_question,
            sql_query="",
            sql_result=[],
            final_response="",
            error=""
        )
        
        result = app.invoke(initial_state)
        return result["final_response"]

def main():
    # Example usage
    import os
    
    # You need to set your OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set your OPENAI_API_KEY environment variable")
        return
    
    agent = TextToSQLAgent(api_key)
    
    # Example queries
    test_queries = [
        "How many customers are there in total?",
        "What are the top 5 best-selling albums?",
        "Which artists have sold the most tracks?",
        "What is the average price of tracks?",
        "Show me customers from Brazil",
        "What is the weather like today?"  # This should return "I don't know"
    ]
    
    print("Text-to-SQL Agent Ready!")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\nQ: {query}")
        response = agent.query(query)
        print(f"A: {response}")
        print("-" * 30)

if __name__ == "__main__":
    main()