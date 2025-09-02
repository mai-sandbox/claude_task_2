import sqlite3
import requests
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict


class DatabaseState(TypedDict):
    messages: List[BaseMessage]
    query: str
    sql_query: str
    sql_result: List[Dict]
    final_response: str
    error: str


class TextToSQLAgent:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)
        self.db_connection = None
        self.schema_info = ""
        self._setup_database()
        self._build_graph()

    def _setup_database(self):
        """Download Chinook database and set up in-memory SQLite database"""
        chinook_url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
        
        response = requests.get(chinook_url)
        sql_script = response.text
        
        self.db_connection = sqlite3.connect(":memory:")
        cursor = self.db_connection.cursor()
        
        cursor.executescript(sql_script)
        self.db_connection.commit()
        
        self._extract_schema_info()

    def _extract_schema_info(self):
        """Extract detailed schema information for the LLM prompt"""
        cursor = self.db_connection.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = "CHINOOK DATABASE SCHEMA:\n\n"
        
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            
            schema_info += f"Table: {table}\n"
            schema_info += "Columns:\n"
            for col in columns:
                col_name, col_type, not_null, default, pk = col[1], col[2], col[3], col[4], col[5]
                schema_info += f"  - {col_name} ({col_type})"
                if pk:
                    schema_info += " [PRIMARY KEY]"
                if not_null:
                    schema_info += " [NOT NULL]"
                schema_info += "\n"
            
            cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
            sample_data = cursor.fetchall()
            if sample_data:
                schema_info += f"Sample data: {sample_data[:2]}\n"
            
            schema_info += "\n"
        
        self.schema_info = schema_info

    def _generate_sql(self, state: DatabaseState) -> Dict[str, Any]:
        """Generate SQL query from natural language"""
        user_query = state["messages"][-1].content
        
        prompt = f"""You are a SQL query generator for the Chinook music database. 
        Convert the user's natural language question into a valid SQL query.

{self.schema_info}

User Question: {user_query}

Rules:
1. Only generate SQL queries that can be answered using the Chinook database
2. If the question cannot be answered using this database, return "CANNOT_ANSWER"
3. Return only the SQL query, no explanation
4. Use proper SQL syntax for SQLite
5. Be precise with table and column names as shown in the schema
6. Use JOINs when necessary to get complete information

SQL Query:"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            sql_query = response.content.strip()
            
            if sql_query == "CANNOT_ANSWER":
                return {**state, "error": "I don't know the answer. This question cannot be answered using the Chinook music database."}
                
            return {**state, "sql_query": sql_query}
        except Exception as e:
            return {**state, "error": f"Error generating SQL: {str(e)}"}

    def _execute_sql(self, state: DatabaseState) -> Dict[str, Any]:
        """Execute the generated SQL query"""
        if state["error"]:
            return state
            
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(state["sql_query"])
            
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                result.append(dict(zip(columns, row)))
            
            return {**state, "sql_result": result}
        except Exception as e:
            return {**state, "error": f"SQL execution error: {str(e)}"}

    def _generate_response(self, state: DatabaseState) -> Dict[str, Any]:
        """Generate natural language response from SQL results"""
        if state["error"]:
            return {**state, "final_response": state["error"]}
            
        user_query = state["messages"][-1].content
        
        if not state["sql_result"]:
            return {**state, "final_response": "I found no results for your query in the Chinook database."}
        
        prompt = f"""You are a helpful assistant that converts SQL query results into natural language responses.

User Question: {user_query}
SQL Query Used: {state["sql_query"]}
Query Results: {state["sql_result"]}

Rules:
1. Provide a clear, natural language answer to the user's question
2. Use the data from the SQL results to support your answer
3. Be concise but informative
4. If there are multiple results, summarize appropriately
5. Use proper formatting for readability

Natural Language Response:"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            final_response = response.content.strip()
            return {**state, "final_response": final_response}
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            return {**state, "error": error_msg, "final_response": error_msg}

    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(DatabaseState)
        
        workflow.add_node("generate_sql", self._generate_sql)
        workflow.add_node("execute_sql", self._execute_sql)
        workflow.add_node("generate_response", self._generate_response)
        
        workflow.set_entry_point("generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        workflow.add_edge("execute_sql", "generate_response")
        workflow.add_edge("generate_response", END)
        
        self.graph: CompiledStateGraph = workflow.compile()

    def query(self, user_input: str) -> str:
        """Process a user query and return natural language response"""
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "query": "",
            "sql_query": "",
            "sql_result": [],
            "final_response": "",
            "error": ""
        }
        
        result = self.graph.invoke(initial_state)
        return result["final_response"]

    def close(self):
        """Close database connection"""
        if self.db_connection:
            self.db_connection.close()


def main():
    """Example usage of the TextToSQLAgent"""
    agent = TextToSQLAgent()
    
    try:
        test_queries = [
            "How many albums are there in total?",
            "What are the top 5 best-selling artists by number of tracks sold?",
            "Which genres are most popular based on sales?",
            "What's the weather like today?",  # This should return "I don't know"
            "Show me all customers from Canada"
        ]
        
        print("Text-to-SQL Agent Demo")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\nUser: {query}")
            response = agent.query(query)
            print(f"Agent: {response}")
            
    finally:
        agent.close()


if __name__ == "__main__":
    main()