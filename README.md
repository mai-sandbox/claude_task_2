# LangGraph Text-to-SQL Agent

A LangGraph-based agent that converts natural language questions into SQL queries, executes them against the Chinook music database, and provides natural language responses.

## Features

- **Natural Language to SQL**: Converts user questions into valid SQL queries
- **Database Validation**: Validates queries are relevant to the music database
- **Smart Execution**: Safely executes SQL queries against the Chinook database
- **Natural Responses**: Generates conversational responses from query results
- **Error Handling**: Gracefully handles invalid queries and database errors

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure OpenAI API Key**:
   Add your OpenAI API key to the `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Test Database Setup**:
   ```bash
   python test_database.py
   ```

## Usage

Run the interactive agent:
```bash
python main.py
```

## Example Queries

The agent can answer questions about:
- **Artists**: "Who are the top 10 artists by number of albums?"
- **Albums**: "What albums does AC/DC have?"
- **Tracks**: "Show me the longest tracks in the database"
- **Sales**: "What are the total sales by country?"
- **Customers**: "Which customer has spent the most money?"

## Architecture

- **database.py**: Handles Chinook database setup and SQL execution
- **text_to_sql_agent.py**: LangGraph workflow for text-to-SQL conversion
- **main.py**: Interactive command-line interface

The agent uses a LangGraph workflow with these steps:
1. **Validate Query**: Check if query is relevant to music database
2. **Generate SQL**: Convert natural language to SQL
3. **Execute SQL**: Run query against database
4. **Generate Response**: Create natural language response from results

## Database Schema

The Chinook database contains tables for:
- Artists, Albums, Tracks
- Customers, Employees
- Invoices, Invoice Lines
- Playlists, Playlist Tracks
- Media Types, Genres
