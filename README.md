# LangGraph Text-to-SQL Agent

A LangGraph-based text-to-SQL agent that converts natural language queries into SQL and executes them against the Chinook SQLite database.

## Features

- **Natural Language to SQL**: Converts user questions into appropriate SQL queries
- **Database Execution**: Executes SQL queries against the Chinook music store database
- **Natural Language Response**: Provides human-readable responses based on query results
- **Schema-Aware**: Uses detailed database schema information to generate accurate queries
- **Scoped Responses**: Only responds to queries that can be answered using the database

## Architecture

The agent consists of:

1. **DatabaseSchema**: Utility class for managing the in-memory SQLite database
2. **TextToSQLAgent**: Main agent class that integrates with LangGraph
3. **LangGraph Integration**: Uses `create_react_agent` for the conversational interface
4. **SQL Execution Tool**: Custom tool for executing SQL queries safely

## Setup

### Prerequisites

- Python 3.8+
- Anthropic API key

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment:
```bash
cp .env.template .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Files

- `agent.py`: Main agent implementation
- `chinook.sql`: Chinook database SQL file (downloaded automatically)
- `langgraph.json`: LangGraph configuration
- `requirements.txt`: Python dependencies
- `test_agent.py`: Test script for the agent

## Database Schema

The Chinook database contains the following tables:

- **Album**: Music albums with artist information
- **Artist**: Musical artists
- **Customer**: Store customers
- **Employee**: Store employees
- **Genre**: Music genres
- **Invoice**: Customer purchases
- **InvoiceLine**: Individual items in invoices
- **MediaType**: Types of media (MP3, AAC, etc.)
- **Playlist**: User-created playlists
- **PlaylistTrack**: Tracks in playlists
- **Track**: Individual music tracks

## Usage

### Basic Usage

```python
from agent import create_app
from langchain_core.messages import HumanMessage

# Create the agent
agent = create_app()

# Query the agent
response = agent.invoke({
    "messages": [HumanMessage(content="How many customers are there?")]
})

print(response['messages'][-1].content)
```

### Test the Agent

Run the test script:

```bash
python test_agent.py
```

### Example Queries

The agent can handle queries like:

- "How many customers are there?"
- "What are the top 5 best-selling albums?"
- "Show me all genres in the database"
- "Which artist has the most albums?"
- "What are the most popular tracks?"

### Non-Database Queries

For queries that cannot be answered using the database (like weather, general knowledge, etc.), the agent will respond with "I don't know the answer to that question."

## Development

### Running Locally

The agent can be run locally for development:

```bash
python agent.py
```

### LangGraph Platform Deployment

The agent is configured for deployment on LangGraph Platform:

1. The `langgraph.json` file defines the deployment configuration
2. The main graph is exported as `app` in `agent.py`
3. Dependencies are listed in `requirements.txt`

## Technical Details

### Database Management

- Uses SQLite in-memory database for fast access
- Automatically creates schema from the Chinook SQL file
- Extracts detailed schema information including foreign keys

### SQL Safety

- Uses parameterized queries where possible
- Limits result sets to prevent overwhelming responses
- Provides clear error messages for invalid SQL

### LangGraph Integration

- Uses `create_react_agent` for tool-calling capabilities
- Implements custom tool for SQL execution
- Follows LangGraph deployment best practices

## Limitations

- Only works with the Chinook database schema
- Requires Anthropic API key
- Limited to SQLite syntax
- Results limited to first 10 rows for readability

## License

This project is for educational and demonstration purposes.
