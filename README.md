# LangGraph Text-to-SQL Agent for Chinook Database

A LangGraph-based text-to-SQL agent that generates SQL queries, executes them against the Chinook SQLite database, and provides natural language responses.

## Features

- **Natural Language to SQL**: Converts user questions into valid SQL queries
- **Database Execution**: Runs queries against the Chinook music database
- **Natural Language Response**: Converts SQL results back into human-readable answers
- **Error Handling**: Gracefully handles invalid queries and irrelevant questions
- **Interactive Interface**: Command-line interface for easy interaction

## Architecture

The agent uses LangGraph to create a workflow with three main nodes:

1. **SQL Generation Node**: Uses GPT-4o-mini to convert natural language to SQL
2. **SQL Execution Node**: Executes the SQL query against an in-memory SQLite database
3. **Response Generation Node**: Converts query results into natural language

## Database Schema

The Chinook database contains 11 tables representing a music store:

- **Artist**: Music artists
- **Album**: Albums by artists
- **Track**: Individual songs with genre, media type, and pricing
- **Customer**: Customer information
- **Employee**: Employee records
- **Invoice**: Customer purchases
- **InvoiceLine**: Individual items in purchases
- **Genre**: Music genres
- **MediaType**: Audio formats (MP3, AAC, etc.)
- **Playlist**: User playlists
- **PlaylistTrack**: Track assignments to playlists

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key in `.env`:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Interactive Mode
Run the interactive interface:
```bash
python interactive_sql_agent.py
```

### Programmatic Usage
```python
from text_to_sql_agent import create_text_to_sql_agent

agent = create_text_to_sql_agent()

result = agent.invoke({
    "user_query": "What are the top 5 best-selling artists?",
    "sql_query": "",
    "sql_result": "",
    "natural_language_response": "",
    "error": ""
})

print(result["natural_language_response"])
```

### Example Queries

- "What are the top 5 best-selling artists by total sales?"
- "How many customers are from each country?"
- "What is the most popular music genre?"
- "Show me all albums by Led Zeppelin"
- "What are the longest tracks in the database?"

## Error Handling

The agent handles several types of errors:

- **Invalid SQL**: Returns an error message when SQL generation fails
- **Irrelevant Questions**: Returns "I don't know" for non-database questions
- **Empty Results**: Handles cases where queries return no data
- **Database Errors**: Catches and reports SQL execution errors

## Files

- `text_to_sql_agent.py`: Main agent implementation
- `interactive_sql_agent.py`: Interactive command-line interface
- `debug_agent.py`: Debugging utilities
- `requirements.txt`: Python dependencies
- `chinook_schema.sql`: Chinook database schema and data

## Dependencies

- `langgraph>=0.2.28`: Graph-based workflow framework
- `langchain>=0.3.0`: LLM integration framework
- `langchain-openai>=0.2.0`: OpenAI integration
- `python-dotenv>=1.0.0`: Environment variable management

## License

This project uses the Chinook Database, which is licensed under the MIT License.
