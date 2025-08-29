from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from database import ChinookDatabase
import os
from dotenv import load_dotenv
import json

load_dotenv()

class TextToSQLState:
    def __init__(self):
        self.user_question: str = ""
        self.generated_sql: str = ""
        self.query_results: List[Dict[str, Any]] = []
        self.natural_language_response: str = ""
        self.error: str = ""
        self.schema_info: str = ""

class TextToSQLAgent:
    def __init__(self, api_key: str = None):
        self.db = ChinookDatabase()
        self.llm = ChatOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model="gpt-4-turbo-preview",
            temperature=0
        )
        self.setup_database()
        
    def setup_database(self):
        """Initialize the Chinook database"""
        if not self.db.setup_database():
            raise Exception("Failed to setup Chinook database")
    
    def text_to_sql_node(self, state: TextToSQLState) -> Dict[str, Any]:
        """Convert natural language question to SQL query"""
        schema_info = self.db.get_schema_description()
        
        system_prompt = f"""You are a SQL expert. Convert the user's natural language question into a valid SQLite query for the Chinook database.

{schema_info}

Rules:
1. Only generate SELECT queries - no INSERT, UPDATE, DELETE, DROP, etc.
2. If the question cannot be answered with the available tables, respond with "NO_ANSWER"
3. Return only the SQL query, nothing else
4. Use proper SQLite syntax
5. Be precise with table and column names
6. Use appropriate JOINs when needed

User Question: {state.user_question}

SQL Query:"""

        try:
            messages = [SystemMessage(content=system_prompt)]
            response = self.llm.invoke(messages)
            
            sql_query = response.content.strip()
            
            if sql_query == "NO_ANSWER" or "NO_ANSWER" in sql_query:
                state.error = "Cannot answer this question with the available data"
                state.generated_sql = ""
            else:
                state.generated_sql = sql_query
                state.schema_info = schema_info
                
        except Exception as e:
            state.error = f"Error generating SQL: {str(e)}"
            
        return {"state": state}
    
    def execute_sql_node(self, state: TextToSQLState) -> Dict[str, Any]:
        """Execute the generated SQL query"""
        if state.error or not state.generated_sql:
            return {"state": state}
            
        try:
            results = self.db.execute_query(state.generated_sql)
            state.query_results = results
        except Exception as e:
            state.error = f"Error executing SQL: {str(e)}"
            
        return {"state": state}
    
    def generate_response_node(self, state: TextToSQLState) -> Dict[str, Any]:
        """Generate natural language response from query results"""
        if state.error:
            state.natural_language_response = "I don't know the answer to that question."
            return {"state": state}
            
        if not state.query_results:
            state.natural_language_response = "No results found for your query."
            return {"state": state}
        
        system_prompt = f"""You are a helpful assistant that explains database query results in natural language.

User's original question: {state.user_question}
SQL query used: {state.generated_sql}
Query results: {json.dumps(state.query_results, indent=2)}

Provide a clear, concise answer to the user's question based on the query results. 
Be conversational and helpful. If there are multiple results, summarize appropriately.
Do not mention SQL queries or technical details unless relevant to the answer."""

        try:
            messages = [SystemMessage(content=system_prompt)]
            response = self.llm.invoke(messages)
            state.natural_language_response = response.content.strip()
        except Exception as e:
            state.natural_language_response = "I don't know the answer to that question."
            
        return {"state": state}
    
    def should_continue(self, state: TextToSQLState) -> str:
        """Determine next step in the workflow"""
        if state.error:
            return "generate_response"
        elif state.generated_sql and not state.query_results:
            return "execute_sql"
        elif state.query_results and not state.natural_language_response:
            return "generate_response"
        else:
            return END
    
    def create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(TextToSQLState)
        
        # Add nodes
        workflow.add_node("text_to_sql", self.text_to_sql_node)
        workflow.add_node("execute_sql", self.execute_sql_node)
        workflow.add_node("generate_response", self.generate_response_node)
        
        # Define edges
        workflow.set_entry_point("text_to_sql")
        workflow.add_conditional_edges(
            "text_to_sql",
            self.should_continue,
            {
                "execute_sql": "execute_sql",
                "generate_response": "generate_response",
                END: END
            }
        )
        workflow.add_conditional_edges(
            "execute_sql",
            self.should_continue,
            {
                "generate_response": "generate_response",
                END: END
            }
        )
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def query(self, question: str) -> str:
        """Process a natural language question and return response"""
        state = TextToSQLState()
        state.user_question = question
        
        workflow = self.create_workflow()
        result = workflow.invoke({"state": state})
        
        return result["state"].natural_language_response
    
    def close(self):
        """Close database connection"""
        self.db.close()