"""LangGraph-based text-to-SQL agent for the Chinook database."""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from database import ChinookDatabase

# Load environment variables
load_dotenv()

class AgentState(BaseModel):
    """State for the text-to-SQL agent."""
    messages: List[Any] = Field(default_factory=list)
    user_query: str = ""
    sql_query: str = ""
    sql_results: List[Dict[str, Any]] = Field(default_factory=list)
    final_response: str = ""
    error_message: str = ""
    
    class Config:
        arbitrary_types_allowed = True

class TextToSQLAgent:
    def __init__(self):
        """Initialize the text-to-SQL agent."""
        # Initialize the database
        self.db = ChinookDatabase()
        
        # Initialize the LLM
        self.llm = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0
        )
        
        # Get schema information
        self.schema_info = self.db.get_schema_info()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Define the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("generate_sql", self._generate_sql_node)
        workflow.add_node("execute_sql", self._execute_sql_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("handle_error", self._handle_error_node)
        
        # Define the flow
        workflow.set_entry_point("generate_sql")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "generate_sql",
            self._should_execute_sql,
            {
                "execute": "execute_sql",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "execute_sql",
            self._should_generate_response,
            {
                "respond": "generate_response",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    def _generate_sql_node(self, state: AgentState) -> Dict[str, Any]:
        """Generate SQL query from natural language."""
        system_prompt = f"""You are a SQL expert working with the Chinook music database. 
        
Generate ONLY a valid SQLite query to answer the user's question. 
Do not include any explanation, markdown formatting, or additional text.
Only return the SQL query itself.

If the question cannot be answered using the available database tables, respond with exactly: "IRRELEVANT_QUERY"

Database Schema:
{self.schema_info}

Rules:
1. Only generate queries using SELECT statements
2. Use proper JOIN syntax when needed
3. Be careful with column names and table names (case-sensitive)
4. Limit results to reasonable numbers (use LIMIT if needed)
5. If the query is irrelevant to the music database, return "IRRELEVANT_QUERY"
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state.user_query)
        ]
        
        response = self.llm.invoke(messages)
        sql_query = response.content.strip()
        
        return {
            "sql_query": sql_query,
            "messages": state.messages + [HumanMessage(content=state.user_query), response]
        }
    
    def _execute_sql_node(self, state: AgentState) -> Dict[str, Any]:
        """Execute the generated SQL query."""
        try:
            if state.sql_query == "IRRELEVANT_QUERY":
                return {
                    "error_message": "This query is not relevant to the music database.",
                    "sql_results": []
                }
            
            # Validate the query first
            is_valid, validation_message = self.db.validate_query(state.sql_query)
            if not is_valid:
                return {
                    "error_message": f"Invalid SQL query: {validation_message}",
                    "sql_results": []
                }
            
            # Execute the query
            results = self.db.execute_query(state.sql_query)
            
            return {
                "sql_results": results,
                "error_message": ""
            }
        
        except Exception as e:
            return {
                "error_message": f"Error executing SQL: {str(e)}",
                "sql_results": []
            }
    
    def _generate_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Generate natural language response from SQL results."""
        system_prompt = """You are a helpful assistant that explains SQL query results in natural language.

Given the user's original question and the SQL results, provide a clear, concise answer.
Focus on directly answering their question using the data provided.

If there are no results, mention that no data was found matching their criteria.
Be conversational and helpful in your response."""
        
        # Format the SQL results for the prompt
        results_text = "SQL Query Results:\n"
        if state.sql_results:
            if len(state.sql_results) <= 10:
                for i, row in enumerate(state.sql_results, 1):
                    results_text += f"{i}. {row}\n"
            else:
                # Show first 5 and last 5 with count
                for i, row in enumerate(state.sql_results[:5], 1):
                    results_text += f"{i}. {row}\n"
                results_text += f"... ({len(state.sql_results) - 10} more rows)\n"
                for i, row in enumerate(state.sql_results[-5:], len(state.sql_results) - 4):
                    results_text += f"{i}. {row}\n"
        else:
            results_text += "No results found."
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User question: {state.user_query}\n\n{results_text}")
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "final_response": response.content,
            "messages": state.messages + [response]
        }
    
    def _handle_error_node(self, state: AgentState) -> Dict[str, Any]:
        """Handle errors and provide appropriate response."""
        if state.sql_query == "IRRELEVANT_QUERY" or "not relevant" in state.error_message.lower():
            final_response = "I don't know the answer to that question. I can only help with queries related to the music database (artists, albums, tracks, customers, sales, etc.)."
        else:
            final_response = "I don't know the answer to that question."
        
        return {"final_response": final_response}
    
    def _should_execute_sql(self, state: AgentState) -> str:
        """Determine if SQL should be executed."""
        if state.sql_query == "IRRELEVANT_QUERY":
            return "error"
        return "execute"
    
    def _should_generate_response(self, state: AgentState) -> str:
        """Determine if response should be generated."""
        if state.error_message:
            return "error"
        return "respond"
    
    def query(self, user_input: str) -> str:
        """Process a user query and return a natural language response."""
        initial_state = AgentState(user_query=user_input)
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return final_state["final_response"]
    
    def close(self):
        """Close database connection."""
        self.db.close()

def main():
    """Interactive demo of the text-to-SQL agent."""
    agent = TextToSQLAgent()
    
    print("🎵 Chinook Music Database Query Agent")
    print("Ask questions about artists, albums, tracks, customers, and sales!")
    print("Type 'quit' to exit.\n")
    
    try:
        while True:
            user_input = input("Your question: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_input:
                continue
            
            response = agent.query(user_input)
            print(f"Answer: {response}\n")
    
    except KeyboardInterrupt:
        print("\nGoodbye!")
    
    finally:
        agent.close()

if __name__ == "__main__":
    main()