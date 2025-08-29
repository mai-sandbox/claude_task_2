"""
LangGraph-based text-to-SQL agent for the Chinook database.
"""

import sqlite3
import re
import requests
from typing import Dict, Any, TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State of the SQL agent."""
    messages: Annotated[list, add_messages]
    query: str
    sql_query: str
    sql_result: str
    schema_info: str
    error: str


class SQLAgent:
    """A text-to-SQL agent using LangGraph."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize the SQL agent."""
        self.llm = ChatOpenAI(api_key=api_key, model=model, temperature=0)
        self.db_connection = None
        self.schema_info = ""
        self._setup_database()
        
    def _setup_database(self):
        """Fetch Chinook database SQL and set up in-memory database."""
        print("Setting up Chinook database...")
        
        # Fetch the SQL file
        url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        response = requests.get(url)
        response.raise_for_status()
        sql_content = response.text
        
        # Create in-memory database
        self.db_connection = sqlite3.connect(":memory:")
        cursor = self.db_connection.cursor()
        
        # Execute the SQL to create tables and insert data
        cursor.executescript(sql_content)
        self.db_connection.commit()
        
        # Extract schema information
        self.schema_info = self._get_schema_info()
        print("Database setup complete!")
        
    def _get_schema_info(self) -> str:
        """Extract detailed schema information from the database."""
        cursor = self.db_connection.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_parts = []
        for table in tables:
            table_name = table[0]
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Get sample data (first 3 rows)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = cursor.fetchall()
            
            schema_part = f"\nTable: {table_name}\n"
            schema_part += "Columns:\n"
            for col in columns:
                schema_part += f"  - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''} {'NOT NULL' if col[3] else ''}\n"
            
            if sample_data:
                schema_part += f"Sample data (first 3 rows):\n"
                col_names = [col[1] for col in columns]
                schema_part += f"  {' | '.join(col_names)}\n"
                for row in sample_data:
                    schema_part += f"  {' | '.join(str(x) if x is not None else 'NULL' for x in row)}\n"
            
            schema_parts.append(schema_part)
        
        return "\n".join(schema_parts)
    
    def _generate_sql_node(self, state: AgentState) -> Dict[str, Any]:
        """Node to generate SQL query from natural language."""
        query = state["query"]
        
        system_prompt = f"""You are a SQL expert working with a SQLite database called Chinook.

Database Schema:
{self.schema_info}

Your task is to convert the user's natural language question into a valid SQL query.

Rules:
1. Only generate SELECT queries - no INSERT, UPDATE, or DELETE
2. If the question cannot be answered with the available data, return "NO_ANSWER"
3. Return only the SQL query, nothing else
4. Use proper SQL syntax for SQLite
5. Be precise with table and column names
6. Use JOINs when necessary to get complete information

Example:
User: "How many customers are there?"
SQL: SELECT COUNT(*) FROM Customer

User: "Who are the top 5 customers by total purchases?"
SQL: SELECT c.FirstName, c.LastName, SUM(i.Total) as TotalSpent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId ORDER BY TotalSpent DESC LIMIT 5
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate SQL for: {query}")
        ]
        
        response = self.llm.invoke(messages)
        sql_query = response.content.strip()
        
        # Check if the query is relevant
        if sql_query == "NO_ANSWER":
            return {
                "sql_query": "",
                "error": "Question cannot be answered with the available database"
            }
        
        return {"sql_query": sql_query, "error": ""}
    
    def _execute_sql_node(self, state: AgentState) -> Dict[str, Any]:
        """Node to execute the SQL query."""
        sql_query = state["sql_query"]
        
        if not sql_query or state.get("error"):
            return {"sql_result": "", "error": state.get("error", "")}
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(sql_query)
            results = cursor.fetchall()
            
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            # Format results
            if not results:
                sql_result = "No results found."
            else:
                result_lines = [" | ".join(column_names)]
                result_lines.append("-" * len(result_lines[0]))
                for row in results:
                    result_lines.append(" | ".join(str(x) if x is not None else "NULL" for x in row))
                sql_result = "\n".join(result_lines)
            
            return {"sql_result": sql_result, "error": ""}
            
        except Exception as e:
            return {"sql_result": "", "error": f"SQL execution error: {str(e)}"}
    
    def _generate_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Node to generate natural language response."""
        query = state["query"]
        sql_query = state["sql_query"]
        sql_result = state["sql_result"]
        error = state.get("error", "")
        
        if error:
            if "cannot be answered" in error:
                response = "I don't know the answer to that question. I can only help with questions that can be answered using the Chinook music database."
            else:
                response = "I don't know the answer to that question."
        else:
            system_prompt = """You are a helpful assistant that explains SQL query results in natural language.

Your task is to:
1. Take the user's question, the SQL query, and the results
2. Provide a clear, natural language answer based on the results
3. Be concise but informative
4. If there are no results, explain that clearly
5. Don't mention the SQL query or technical details unless specifically asked

Keep your response focused and helpful."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"""
User Question: {query}
SQL Query: {sql_query}
Query Results: {sql_result}

Provide a natural language answer to the user's question based on these results.
""")
            ]
            
            response_msg = self.llm.invoke(messages)
            response = response_msg.content
        
        # Add the final response to messages
        messages = state.get("messages", [])
        messages.append(AIMessage(content=response))
        
        return {"messages": messages}
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue or end."""
        if state.get("error") and "cannot be answered" in state["error"]:
            return "generate_response"
        elif state.get("error"):
            return "generate_response"
        elif state.get("sql_query") and not state.get("sql_result"):
            return "execute_sql"
        elif state.get("sql_result"):
            return "generate_response"
        else:
            return "execute_sql"
    
    def build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("generate_sql", self._generate_sql_node)
        workflow.add_node("execute_sql", self._execute_sql_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # Add edges
        workflow.add_edge(START, "generate_sql")
        workflow.add_conditional_edges("generate_sql", self._should_continue)
        workflow.add_conditional_edges("execute_sql", self._should_continue)
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def query_database(self, user_question: str) -> str:
        """Main method to query the database with natural language."""
        graph = self.build_graph()
        
        initial_state = {
            "messages": [HumanMessage(content=user_question)],
            "query": user_question,
            "sql_query": "",
            "sql_result": "",
            "schema_info": self.schema_info,
            "error": ""
        }
        
        result = graph.invoke(initial_state)
        
        # Return the last AI message
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                return msg.content
        
        return "I don't know the answer to that question."


def main():
    """Example usage of the SQL Agent."""
    import os
    
    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set the OPENAI_API_KEY environment variable")
        return
    
    # Create agent
    agent = SQLAgent(api_key)
    
    # Example queries
    example_queries = [
        "How many customers are there?",
        "Who are the top 5 customers by total purchases?",
        "What are the most popular music genres?",
        "Which artists have the most albums?",
        "What is the weather like today?",  # This should return "I don't know"
        "How many tracks are there in the Rock genre?"
    ]
    
    print("SQL Agent is ready! Here are some example queries:\n")
    
    for query in example_queries:
        print(f"Question: {query}")
        response = agent.query_database(query)
        print(f"Answer: {response}\n")
        print("-" * 50 + "\n")


if __name__ == "__main__":
    main()