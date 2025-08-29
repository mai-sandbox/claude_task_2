import os
from typing import Dict, Any, List, TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import Graph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation

from database import ChinookDatabase

load_dotenv()

class AgentState(TypedDict):
    user_query: str
    schema_info: str
    sql_query: str
    query_results: List[tuple]
    column_names: List[str]
    final_response: str
    error_message: str

class TextToSQLAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.db = ChinookDatabase()
        self.schema_info = self.db.get_schema_info()
        self.graph = self._create_graph()
    
    def _create_graph(self) -> Graph:
        """Create the LangGraph workflow."""
        workflow = Graph()
        
        # Add nodes
        workflow.add_node("validate_query", self._validate_query)
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_error", self._handle_error)
        
        # Add edges
        workflow.add_edge("validate_query", "generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_edge("execute_sql", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "validate_query",
            self._should_continue,
            {
                "continue": "generate_sql",
                "stop": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "execute_sql",
            self._check_sql_execution,
            {
                "success": "generate_response",
                "error": "handle_error"
            }
        )
        
        # Set entry point
        workflow.set_entry_point("validate_query")
        
        return workflow.compile()
    
    def _validate_query(self, state: AgentState) -> AgentState:
        """Validate if the user query is relevant to the database."""
        validation_prompt = f"""
        You are a database query validator. Your task is to determine if a user's query can be answered using the Chinook music database.
        
        Database Schema:
        {self.schema_info}
        
        User Query: {state['user_query']}
        
        Analyze if this query:
        1. Is related to music, artists, albums, tracks, customers, invoices, or employees
        2. Can be answered using the available tables and data
        3. Is a reasonable request for a music database
        
        Respond with only "VALID" if the query can be answered, or "INVALID" if it cannot be answered using this database.
        """
        
        try:
            response = self.llm.invoke([SystemMessage(content=validation_prompt)])
            is_valid = "VALID" in response.content.upper()
            
            if not is_valid:
                state["error_message"] = "I don't know the answer. This query cannot be answered using the music database."
            
            return state
        except Exception as e:
            state["error_message"] = f"Error validating query: {str(e)}"
            return state
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue with SQL generation."""
        return "stop" if state.get("error_message") else "continue"
    
    def _generate_sql(self, state: AgentState) -> AgentState:
        """Generate SQL query from natural language."""
        sql_prompt = f"""
        You are an expert SQL query generator. Convert the user's natural language query into a valid SQL query for the Chinook database.
        
        Database Schema:
        {self.schema_info}
        
        User Query: {state['user_query']}
        
        Rules:
        1. Generate only the SQL query, no explanations
        2. Use proper SQL syntax for SQLite
        3. Use appropriate JOINs when needed
        4. Include LIMIT clauses for potentially large results (max 50 rows)
        5. Use proper column names and table names as shown in the schema
        6. Handle case-sensitive comparisons appropriately
        
        Return only the SQL query:
        """
        
        try:
            response = self.llm.invoke([SystemMessage(content=sql_prompt)])
            sql_query = response.content.strip()
            
            # Clean up the SQL query
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            state["sql_query"] = sql_query.strip()
            return state
        except Exception as e:
            state["error_message"] = f"Error generating SQL: {str(e)}"
            return state
    
    def _execute_sql(self, state: AgentState) -> AgentState:
        """Execute the generated SQL query."""
        try:
            results = self.db.execute_query(state["sql_query"])
            column_names = self.db.get_column_names(state["sql_query"])
            
            state["query_results"] = results
            state["column_names"] = column_names
            return state
        except Exception as e:
            state["error_message"] = f"Error executing SQL query: {str(e)}"
            return state
    
    def _check_sql_execution(self, state: AgentState) -> str:
        """Check if SQL execution was successful."""
        return "error" if state.get("error_message") else "success"
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate natural language response from SQL results."""
        if not state["query_results"]:
            state["final_response"] = "No results were found for your query."
            return state
        
        # Format results for the prompt
        formatted_results = []
        for row in state["query_results"][:10]:  # Limit to first 10 rows for response generation
            row_dict = dict(zip(state["column_names"], row))
            formatted_results.append(row_dict)
        
        response_prompt = f"""
        You are a helpful assistant that explains database query results in natural language.
        
        Original User Query: {state['user_query']}
        
        SQL Query Used: {state['sql_query']}
        
        Query Results (showing first 10 rows):
        {formatted_results}
        
        Total number of results: {len(state['query_results'])}
        
        Please provide a natural language response that:
        1. Directly answers the user's question
        2. Includes specific data from the results
        3. Is conversational and easy to understand
        4. Mentions the total count if relevant
        
        Be concise but informative. Don't mention the SQL query or technical details unless specifically asked.
        """
        
        try:
            response = self.llm.invoke([SystemMessage(content=response_prompt)])
            state["final_response"] = response.content
            return state
        except Exception as e:
            state["error_message"] = f"Error generating response: {str(e)}"
            return state
    
    def _handle_error(self, state: AgentState) -> AgentState:
        """Handle errors and provide appropriate response."""
        if not state.get("error_message"):
            state["final_response"] = "I don't know the answer."
        else:
            state["final_response"] = state["error_message"]
        return state
    
    def process_query(self, user_query: str) -> str:
        """Process a user query and return a natural language response."""
        initial_state = AgentState(
            user_query=user_query,
            schema_info=self.schema_info,
            sql_query="",
            query_results=[],
            column_names=[],
            final_response="",
            error_message=""
        )
        
        try:
            result = self.graph.invoke(initial_state)
            return result["final_response"]
        except Exception as e:
            return f"I don't know the answer. An error occurred: {str(e)}"