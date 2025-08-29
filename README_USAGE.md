# LangGraph Text-to-SQL Agent

This is a LangGraph-based text-to-SQL agent that converts natural language questions into SQL queries, executes them against the Chinook SQLite database, and provides natural language responses.

## Features

- **Schema-aware SQL generation**: Uses detailed database schema information to generate accurate SQL queries
- **In-memory Chinook database**: Automatically downloads and sets up the Chinook music database
- **Natural language responses**: Converts query results back to human-readable answers
- **Error handling**: Gracefully handles irrelevant queries and SQL errors
- **LangGraph architecture**: Uses a 3-node workflow for clean separation of concerns

## Architecture

The agent follows a 3-node LangGraph workflow:

1. **generate_sql**: Converts natural language to SQL using schema-aware prompting
2. **execute_sql**: Executes the SQL query against the database  
3. **generate_response**: Converts query results to natural language

## Database Schema

The Chinook database contains:
- **Artist**: Music artists (275 total)
- **Album**: Albums by artists (347 total) 
- **Track**: Individual songs (3,503 total)
- **Customer**: Store customers (59 total)
- **Employee**: Store employees (8 total)
- **Invoice**: Purchase records
- **Genre**: Music genres (25 total)
- **MediaType**: File formats
- **Playlist**: User-created playlists

## Usage

1. Set your Anthropic API key in `.env`:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

2. Run the agent:
   ```python
   from agent import app
   from langchain_core.messages import HumanMessage
   
   result = app.invoke({
       "messages": [HumanMessage(content="How many albums does each artist have?")]
   })
   print(result["messages"][-1].content)
   ```

## Example Queries

**Valid queries the agent can handle:**
- "How many albums does each artist have?"
- "Which customers are from the USA?"
- "What are the top 5 longest tracks?"
- "Show me all rock albums"
- "Who are the top spending customers?"

**Invalid queries (will respond with "I don't know"):**
- "What's the weather like today?"
- "How do I cook pasta?"
- "What's the latest news?"

## Files

- `agent.py`: Main LangGraph agent implementation
- `langgraph.json`: LangGraph configuration
- `test_db_setup.py`: Database setup verification
- `test_agent.py`: Full agent testing (requires valid API key)

## Dependencies

- langgraph
- langchain-anthropic
- langchain-core
- python-dotenv
- requests
- sqlite3 (built-in)