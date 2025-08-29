# LangGraph Text-to-SQL Agent for Chinook Database

A LangGraph-based agent that converts natural language questions into SQL queries, executes them against the Chinook music database, and provides natural language responses.

## Features

- **Text-to-SQL Conversion**: Converts natural language questions into proper SQL queries
- **Chinook Database**: Uses the complete Chinook music database (275 artists, 347 albums, 3503 tracks)
- **In-Memory Database**: Automatically downloads and sets up the database in memory
- **Natural Language Responses**: Provides clear, conversational responses based on query results
- **Query Validation**: Only answers questions that can be answered using the available database
- **Deployment Ready**: Built with LangGraph for easy deployment and scaling

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment Variables**:
   Create a `.env` file and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

3. **Test Database Setup**:
   ```bash
   python test_database.py
   ```

## Usage

### Using the Agent Directly

```python
from agent import app

# Ask a question
result = app.invoke({
    "messages": [{"role": "user", "content": "How many artists are in the database?"}]
})

# Get the response
final_message = result["messages"][-1]
print(final_message.content)
```

### Running Tests

Test the complete agent workflow:
```bash
python test_agent.py
```

Test just the database functionality:
```bash
python test_database.py  
```

## Database Schema

The Chinook database contains the following tables:

- **Artist** - Music artists (275 records)
- **Album** - Music albums (347 records)  
- **Track** - Individual songs (3,503 records)
- **Genre** - Music genres
- **MediaType** - File formats (MP3, AAC, etc.)
- **Playlist** & **PlaylistTrack** - User playlists
- **Customer** - Customer information
- **Employee** - Employee data
- **Invoice** & **InvoiceLine** - Purchase transactions

## Example Questions

The agent can answer questions like:

- "How many artists are in the database?"
- "What are the top 5 most expensive tracks?"
- "Which customers are from Canada?"
- "Show me all rock albums"
- "What's the total revenue from invoices?"
- "Which employee has sold the most?"

For questions outside the database scope, the agent will respond: "I don't know the answer to that question."

## Deployment

This agent is built for deployment using the LangGraph platform:

1. The `langgraph.json` file configures the deployment
2. The `agent.py` file exports the compiled graph as `app`
3. All dependencies are specified in `requirements.txt`

## Architecture

- **LangGraph**: Orchestrates the agent workflow
- **Anthropic Claude**: Powers the natural language understanding and generation
- **SQLite**: In-memory database for fast query execution
- **Pydantic**: Type validation and structured data handling

The agent follows these steps:
1. Receives a natural language question
2. Determines if it can be answered using the Chinook database
3. Generates appropriate SQL query
4. Executes the query using the `execute_sql_query` tool
5. Converts results back to natural language response
