import sqlite3
import requests
from typing import Dict, Any, List, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

class State:
    messages: Annotated[List[BaseMessage], add_messages]
    sql_query: str = ""
    sql_result: List[Dict[str, Any]] = []
    database_schema: str = ""
    user_question: str = ""
    final_answer: str = ""

def setup_database() -> sqlite3.Connection:
    """Create in-memory SQLite database and load Chinook data"""
    conn = sqlite3.connect(":memory:")
    
    # Read and execute the Chinook SQL file
    with open("chinook.sql", "r", encoding="utf-8") as f:
        sql_script = f.read()
    
    conn.executescript(sql_script)
    return conn

def get_database_schema(conn: sqlite3.Connection) -> str:
    """Get detailed database schema information"""
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    schema_info = []
    for table in tables:
        table_name = table[0]
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        table_info = f"Table: {table_name}\n"
        table_info += "Columns:\n"
        for col in columns:
            col_name, col_type, not_null, default_val, pk = col[1], col[2], col[3], col[4], col[5]
            pk_str = " (PRIMARY KEY)" if pk else ""
            not_null_str = " NOT NULL" if not_null else ""
            default_str = f" DEFAULT {default_val}" if default_val else ""
            table_info += f"  - {col_name}: {col_type}{pk_str}{not_null_str}{default_str}\n"
        
        # Get foreign key information
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            table_info += "Foreign Keys:\n"
            for fk in foreign_keys:
                table_info += f"  - {fk[3]} -> {fk[2]}.{fk[4]}\n"
        
        schema_info.append(table_info)
    
    return "\n".join(schema_info)

def text_to_sql_node(state: State) -> Dict[str, Any]:
    """Convert natural language query to SQL"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # Extract user question from messages
    user_question = ""
    for msg in state.messages:
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert SQL query generator for the Chinook database. 

Database Schema:
{database_schema}

Rules:
1. Generate ONLY the SQL query, no explanations
2. Use proper SQLite syntax
3. Be precise with table and column names
4. If the question cannot be answered with this database, return "IRRELEVANT_QUERY"
5. Only answer questions related to music, customers, employees, invoices, playlists, tracks, albums, artists, genres, and media types
6. Use appropriate JOINs when needed
7. Limit results to reasonable numbers (use LIMIT clause when appropriate)

Generate a SQL query for this question: {user_question}"""),
        ("human", "{user_question}")
    ])
    
    response = llm.invoke(prompt.format_messages(
        database_schema=state.database_schema,
        user_question=user_question
    ))
    
    sql_query = response.content.strip()
    
    return {
        "sql_query": sql_query,
        "user_question": user_question,
        "messages": [AIMessage(content=f"Generated SQL: {sql_query}")]
    }

def execute_sql_node(state: State) -> Dict[str, Any]:
    """Execute SQL query against the database"""
    if state.sql_query == "IRRELEVANT_QUERY":
        return {
            "sql_result": [],
            "final_answer": "I don't know the answer. This question is not related to the music database or cannot be answered with the available data."
        }
    
    conn = setup_database()
    
    try:
        cursor = conn.cursor()
        cursor.execute(state.sql_query)
        
        # Get column names
        column_names = [description[0] for description in cursor.description] if cursor.description else []
        
        # Fetch results
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        result = []
        for row in rows:
            result.append(dict(zip(column_names, row)))
        
        conn.close()
        
        return {
            "sql_result": result,
            "messages": [AIMessage(content=f"Query executed successfully. Found {len(result)} results.")]
        }
        
    except sqlite3.Error as e:
        conn.close()
        return {
            "sql_result": [],
            "final_answer": f"I encountered an error executing the SQL query: {str(e)}. Please rephrase your question."
        }

def generate_response_node(state: State) -> Dict[str, Any]:
    """Generate natural language response based on SQL results"""
    if state.final_answer:  # If there's already a final answer (error or irrelevant)
        return {"messages": [AIMessage(content=state.final_answer)]}
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant that converts SQL query results into natural language responses.

Given the user's original question and the SQL query results, provide a clear, conversational answer.

Rules:
1. Be conversational and natural
2. Include specific numbers, names, and details from the results
3. If no results found, say so politely
4. Format the response in a readable way
5. Don't mention SQL queries or technical details
6. Focus on answering the user's original question

User Question: {user_question}
SQL Results: {sql_result}

Provide a natural language answer:"""),
        ("human", "Please answer my question based on the data.")
    ])
    
    # Format SQL results for the prompt
    if not state.sql_result:
        sql_result_str = "No results found"
    else:
        sql_result_str = "\n".join([str(row) for row in state.sql_result[:10]])  # Limit to first 10 rows
        if len(state.sql_result) > 10:
            sql_result_str += f"\n... and {len(state.sql_result) - 10} more results"
    
    response = llm.invoke(prompt.format_messages(
        user_question=state.user_question,
        sql_result=sql_result_str
    ))
    
    final_answer = response.content
    
    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)]
    }

def should_continue(state: State) -> str:
    """Determine if we should continue processing"""
    if state.sql_query == "IRRELEVANT_QUERY":
        return "generate_response"
    return "execute_sql"

class TextToSQLAgent:
    def __init__(self):
        self.conn = setup_database()
        self.database_schema = get_database_schema(self.conn)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(State)
        
        # Add nodes
        workflow.add_node("text_to_sql", text_to_sql_node)
        workflow.add_node("execute_sql", execute_sql_node)
        workflow.add_node("generate_response", generate_response_node)
        
        # Add edges
        workflow.add_edge(START, "text_to_sql")
        workflow.add_conditional_edges(
            "text_to_sql",
            should_continue,
            {
                "execute_sql": "execute_sql",
                "generate_response": "generate_response"
            }
        )
        workflow.add_edge("execute_sql", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def query(self, question: str) -> str:
        """Process a user question and return a natural language response"""
        initial_state = State(
            messages=[HumanMessage(content=question)],
            database_schema=self.database_schema
        )
        
        result = self.graph.invoke(initial_state)
        return result["final_answer"]

def main():
    """Example usage of the TextToSQLAgent"""
    agent = TextToSQLAgent()
    
    # Example queries
    example_queries = [
        "How many customers are in the database?",
        "What are the top 5 best-selling tracks?",
        "Which artist has the most albums?",
        "What is the total revenue from invoices in 2009?",
        "List all genres in the database",
        "What is the weather like today?",  # Irrelevant query
    ]
    
    print("Text-to-SQL Agent Demo")
    print("=" * 50)
    
    for query in example_queries:
        print(f"\nQuestion: {query}")
        print("-" * 30)
        response = agent.query(query)
        print(f"Answer: {response}")

if __name__ == "__main__":
    main()