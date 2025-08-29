import os
from typing import Dict, Any, List
from dataclasses import dataclass
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from database import ChinookDatabase

load_dotenv()

@dataclass
class AgentState:
    user_query: str
    sql_query: str = ""
    sql_results: List[Dict[str, Any]] = None
    final_response: str = ""
    error: str = ""
    schema_info: str = ""

class TextToSQLAgent:
    def __init__(self):
        self.db = ChinookDatabase()
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("generate_sql", self.generate_sql_node)
        workflow.add_node("execute_sql", self.execute_sql_node)
        workflow.add_node("generate_response", self.generate_response_node)
        workflow.add_node("handle_error", self.handle_error_node)
        
        workflow.set_entry_point("generate_sql")
        
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_conditional_edges(
            "execute_sql",
            self._should_continue_after_sql,
            {
                "generate_response": "generate_response",
                "handle_error": "handle_error"
            }
        )
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    def _should_continue_after_sql(self, state: AgentState) -> str:
        """Decide whether to continue to response generation or handle error"""
        return "handle_error" if state.error else "generate_response"
    
    def generate_sql_node(self, state: AgentState) -> AgentState:
        """Generate SQL query from natural language"""
        if not self.db.conn:
            self.db.initialize_database()
        
        schema_info = self.db.get_schema_description()
        state.schema_info = schema_info
        
        system_prompt = f"""You are a SQL expert specializing in the Chinook music store database.

{schema_info}

Your task is to convert natural language queries into valid SQLite queries for this database.

IMPORTANT RULES:
1. Only generate queries that can be answered using this database schema
2. If the query is unrelated to music, artists, albums, tracks, customers, invoices, or employees, respond with: "IRRELEVANT_QUERY"
3. Return only the SQL query, no explanation
4. Use proper SQLite syntax
5. Use JOINs when accessing related data across tables
6. Be precise with column names and table relationships

Examples:
- "Show me all albums by AC/DC" -> SELECT Album.Title FROM Album JOIN Artist ON Album.ArtistId = Artist.ArtistId WHERE Artist.Name = 'AC/DC'
- "What are the most expensive tracks?" -> SELECT Name, UnitPrice FROM Track ORDER BY UnitPrice DESC LIMIT 10
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Convert this to SQL: {state.user_query}")
        ]
        
        try:
            response = self.llm.invoke(messages)
            sql_query = response.content.strip()
            
            if sql_query == "IRRELEVANT_QUERY":
                state.error = "irrelevant"
            else:
                state.sql_query = sql_query
                
        except Exception as e:
            state.error = f"SQL generation failed: {str(e)}"
        
        return state
    
    def execute_sql_node(self, state: AgentState) -> AgentState:
        """Execute the generated SQL query"""
        if state.error:
            return state
            
        try:
            results = self.db.execute_query(state.sql_query)
            state.sql_results = results
            
        except Exception as e:
            state.error = f"SQL execution failed: {str(e)}"
        
        return state
    
    def generate_response_node(self, state: AgentState) -> AgentState:
        """Generate natural language response from SQL results"""
        if state.error:
            return state
        
        system_prompt = """You are a helpful assistant that explains database query results in natural language.

Given a user's original question and the SQL query results, provide a clear, concise response in natural language.

Rules:
1. Be conversational and friendly
2. Present the data in an organized way
3. If no results, say "No results found for your query"
4. Don't mention the SQL query or technical details
5. Focus on answering the user's original question
"""
        
        results_text = ""
        if not state.sql_results:
            results_text = "No results found."
        elif len(state.sql_results) == 0:
            results_text = "No results found."
        else:
            results_text = f"Found {len(state.sql_results)} results:\n"
            for i, row in enumerate(state.sql_results[:10], 1):
                row_text = ", ".join([f"{k}: {v}" for k, v in row.items()])
                results_text += f"{i}. {row_text}\n"
            
            if len(state.sql_results) > 10:
                results_text += f"... and {len(state.sql_results) - 10} more results"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Original question: {state.user_query}
Query results: {results_text}

Provide a natural language response to the user's question based on these results.
""")
        ]
        
        try:
            response = self.llm.invoke(messages)
            state.final_response = response.content.strip()
            
        except Exception as e:
            state.error = f"Response generation failed: {str(e)}"
        
        return state
    
    def handle_error_node(self, state: AgentState) -> AgentState:
        """Handle errors and provide appropriate responses"""
        if state.error == "irrelevant":
            state.final_response = "I don't know the answer to that question. I can only help with queries related to the Chinook music store database, including information about artists, albums, tracks, customers, and sales."
        else:
            state.final_response = "I don't know the answer to that question."
        
        return state
    
    def query(self, user_input: str) -> str:
        """Main interface to query the agent"""
        initial_state = AgentState(user_query=user_input)
        
        try:
            final_state = self.graph.invoke(initial_state)
            return final_state.final_response
        except Exception as e:
            return "I don't know the answer to that question."
    
    def close(self):
        """Clean up resources"""
        self.db.close()