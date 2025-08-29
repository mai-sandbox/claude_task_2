# Chinook Text-to-SQL Agent

A LangGraph-based text-to-SQL agent that converts natural language questions into SQL queries, executes them against the Chinook music database, and provides natural language responses.

## Features

- **Natural Language to SQL**: Converts user questions into valid SQLite queries
- **In-memory Database**: Uses the Chinook SQLite database loaded in memory
- **Smart Query Validation**: Validates SQL queries before execution
- **Contextual Responses**: Provides natural language answers based on query results
- **Irrelevant Query Handling**: Politely declines questions outside the music domain

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Anthropic API key in `.env`:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Usage

### Interactive Mode
```bash
python text_to_sql_agent.py
```

### Demo Script
```bash
python demo.py
```

### Programmatic Usage
```python
from text_to_sql_agent import TextToSQLAgent

agent = TextToSQLAgent()
response = agent.query("How many artists are in the database?")
print(response)
agent.close()
```

## Database Schema

The Chinook database contains the following tables:
- **Artist**: Music artists
- **Album**: Albums by artists  
- **Track**: Individual songs/tracks
- **Genre**: Music genres
- **MediaType**: File formats (MP3, AAC, etc.)
- **Playlist**: User-created playlists
- **Customer**: Customer information
- **Employee**: Employee records
- **Invoice**: Purchase transactions
- **InvoiceLine**: Individual items in purchases

## Example Queries

- "How many artists are in the database?"
- "What are the top 5 bestselling tracks?"
- "Which albums were released by Pink Floyd?"
- "What countries have the most customers?"
- "Show me the most popular music genres"

## Architecture

The agent uses LangGraph to create a workflow with these nodes:
1. **SQL Generation**: Converts natural language to SQL
2. **Query Execution**: Runs SQL against the database
3. **Response Generation**: Creates natural language responses
4. **Error Handling**: Manages invalid or irrelevant queries

## Files

- `text_to_sql_agent.py`: Main agent implementation
- `database.py`: Database utilities and schema management
- `demo.py`: Demo script with sample queries
- `chinook_database.sql`: SQLite database schema and data
- `requirements.txt`: Python dependencies
