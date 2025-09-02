"""
LangGraph-based Text-to-SQL Agent for Chinook Database
"""

import os
import sqlite3
from typing import TypedDict, Annotated, List
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    database_schema: str
    sql_query: str
    query_result: str
    final_answer: str

class TextToSQLAgent:
    def __init__(self, openai_api_key: str):
        """Initialize the Text-to-SQL agent with database and LLM setup."""
        self.llm = ChatOpenAI(model="gpt-4", api_key=openai_api_key)
        self.db_connection = None
        self.schema_info = ""
        self._setup_database()
        self._extract_schema()
        self._build_graph()

    def _setup_database(self):
        """Create in-memory SQLite database from Chinook SQL file."""
        self.db_connection = sqlite3.connect(':memory:')
        
        # Read and execute the SQL file
        with open('chinook.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Execute the SQL commands to create tables and insert data
        cursor = self.db_connection.cursor()
        cursor.executescript(sql_content)
        self.db_connection.commit()

    def _extract_schema(self):
        """Extract database schema information for LLM context."""
        cursor = self.db_connection.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_parts = []
        schema_parts.append("CHINOOK DATABASE SCHEMA:")
        schema_parts.append("=" * 50)
        
        for table_name in tables:
            table_name = table_name[0]
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            schema_parts.append(f"\nTable: {table_name}")
            schema_parts.append("-" * (len(table_name) + 7))
            
            for column in columns:
                col_name = column[1]
                col_type = column[2]
                is_pk = " (PRIMARY KEY)" if column[5] else ""
                is_notnull = " NOT NULL" if column[3] else ""
                schema_parts.append(f"  {col_name}: {col_type}{is_notnull}{is_pk}")
            
            # Get sample data (first 3 rows)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
            sample_data = cursor.fetchall()
            if sample_data:
                schema_parts.append("  Sample data:")
                for row in sample_data:
                    schema_parts.append(f"    {row}")
        
        self.schema_info = "\n".join(schema_parts)

    def _generate_sql_query(self, state: AgentState) -> AgentState:
        """Generate SQL query from natural language input."""
        human_query = state["messages"][-1].content
        
        system_prompt = f"""You are a SQL expert. Your task is to convert natural language questions into SQL queries for the Chinook database.

{self.schema_info}

Rules:
1. Generate ONLY valid SQLite SQL queries
2. Use proper table and column names as shown in the schema
3. If the question cannot be answered with the available data, respond with "CANNOT_ANSWER"
4. Keep queries efficient and accurate
5. Use appropriate JOINs when needed
6. Return only the SQL query, no explanations

Human Question: {human_query}
"""
        
        messages = [SystemMessage(content=system_prompt)]
        response = self.llm.invoke(messages)
        
        sql_query = response.content.strip()
        
        # Check if the query is valid
        if sql_query == "CANNOT_ANSWER":
            state["sql_query"] = "CANNOT_ANSWER"
        else:
            # Remove any markdown formatting
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()
            state["sql_query"] = sql_query
        
        return state

    def _execute_sql_query(self, state: AgentState) -> AgentState:
        """Execute the generated SQL query."""
        sql_query = state["sql_query"]
        
        if sql_query == "CANNOT_ANSWER":
            state["query_result"] = "CANNOT_ANSWER"
            return state
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(sql_query)
            results = cursor.fetchall()
            
            # Get column names for better formatting
            column_names = [description[0] for description in cursor.description]
            
            if results:
                # Format results as a readable string
                formatted_results = []
                formatted_results.append(f"Column names: {', '.join(column_names)}")
                formatted_results.append("-" * 50)
                
                for row in results:
                    formatted_results.append(str(row))
                
                state["query_result"] = "\n".join(formatted_results)
            else:
                state["query_result"] = "No results found."
                
        except Exception as e:
            state["query_result"] = f"SQL Error: {str(e)}"
        
        return state

    def _generate_natural_language_response(self, state: AgentState) -> AgentState:
        """Generate natural language response from query results."""
        human_query = state["messages"][-1].content
        sql_query = state["sql_query"]
        query_result = state["query_result"]
        
        if query_result == "CANNOT_ANSWER":
            final_answer = "I don't know the answer to that question. The query cannot be answered using the available database."
            state["final_answer"] = final_answer
            state["messages"].append(AIMessage(content=final_answer))
            return state
        
        system_prompt = f"""You are a helpful assistant that converts SQL query results into natural language answers.

Original Question: {human_query}
SQL Query Used: {sql_query}
Query Results: {query_result}

Your task:
1. Provide a clear, natural language answer to the original question
2. Base your answer strictly on the query results
3. Be concise but informative
4. If there's an SQL error, explain that the query couldn't be executed
5. If no results were found, mention that clearly

Generate a natural language response:"""
        
        messages = [SystemMessage(content=system_prompt)]
        response = self.llm.invoke(messages)
        
        final_answer = response.content.strip()
        state["final_answer"] = final_answer
        state["messages"].append(AIMessage(content=final_answer))
        
        return state

    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue processing."""
        return "continue"

    def _build_graph(self):
        """Build the LangGraph workflow."""
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("generate_sql", self._generate_sql_query)
        workflow.add_node("execute_sql", self._execute_sql_query)
        workflow.add_node("generate_response", self._generate_natural_language_response)
        
        # Add edges
        workflow.add_edge(START, "generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_edge("execute_sql", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # Compile the graph
        memory = MemorySaver()
        self.app = workflow.compile(checkpointer=memory)

    def query(self, question: str, thread_id: str = "default") -> str:
        """Process a natural language question and return the answer."""
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "database_schema": self.schema_info,
            "sql_query": "",
            "query_result": "",
            "final_answer": ""
        }
        
        config = {"configurable": {"thread_id": thread_id}}
        final_state = self.app.invoke(initial_state, config)
        
        return final_state["final_answer"]

    def get_conversation_history(self, thread_id: str = "default") -> List:
        """Get conversation history for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        state = self.app.get_state(config)
        return state.values.get("messages", []) if state.values else []

    def close(self):
        """Close database connection."""
        if self.db_connection:
            self.db_connection.close()


def main():
    """Demo function to test the agent."""
    # You need to set your OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return
    
    # Create the agent
    agent = TextToSQLAgent(api_key)
    
    # Test queries
    test_queries = [
        "How many customers are there in total?",
        "What are the top 5 best-selling tracks?",
        "Which genre has the most tracks?",
        "Who are the customers from Brazil?",
        "What is the average invoice total?",
        "Tell me about quantum physics",  # Should return "I don't know"
    ]
    
    print("Text-to-SQL Agent Demo")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\nQuestion: {query}")
        print("-" * 30)
        answer = agent.query(query)
        print(f"Answer: {answer}")
    
    # Close the database connection
    agent.close()


if __name__ == "__main__":
    main()