# Chinook Music Database Text-to-SQL Agent

A LangGraph-based text-to-SQL agent that converts natural language questions into SQL queries, executes them against the Chinook SQLite database, and returns natural language responses.

## Features

- **Natural Language to SQL**: Converts user questions into valid SQL queries
- **Chinook Database**: Uses the popular Chinook music database with tables for artists, albums, tracks, customers, invoices, etc.
- **LangGraph Workflow**: Implements a structured workflow with SQL generation, execution, and response generation
- **Schema-Aware**: Includes detailed table schema information in prompts for accurate SQL generation
- **Error Handling**: Gracefully handles invalid queries and database errors
- **Interactive CLI**: Command-line interface for easy interaction

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Interactive CLI
```bash
python cli.py
```

### Programmatic Usage
```python
from text_to_sql_agent import TextToSQLAgent

agent = TextToSQLAgent("your-openai-api-key")
response = agent.query("How many customers are there?")
print(response)
```

## Example Queries

- "How many customers are there in total?"
- "What are the top 5 best-selling albums?"
- "Which artists have sold the most tracks?"
- "Show me customers from Brazil"
- "What is the average price of tracks?"

## Database Schema

The agent automatically fetches the Chinook database and extracts schema information including:
- Table structures with column names and types
- Primary keys and foreign keys
- Sample data for context

## Architecture

The agent uses a LangGraph workflow with three main nodes:
1. **SQL Generation**: Converts natural language to SQL using GPT-4
2. **SQL Execution**: Executes the query against the SQLite database
3. **Response Generation**: Converts results back to natural language

## Limitations

- Only answers questions that can be resolved using the Chinook database
- Returns "I don't know" for irrelevant queries
- Requires OpenAI API access
