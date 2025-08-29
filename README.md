# Text-to-SQL Agent with LangGraph

A LangGraph-based agent that converts natural language queries into SQL, executes them against the Chinook music store database, and provides natural language responses.

## Features

- **Natural Language Processing**: Converts user questions into SQL queries
- **Database Integration**: Uses the Chinook SQLite database (music store data)
- **LangGraph Workflow**: Implements a multi-step agent workflow
- **Error Handling**: Gracefully handles irrelevant queries and SQL errors
- **In-Memory Database**: Automatically downloads and initializes the Chinook database

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API Key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Run the Agent**:
   ```bash
   python main.py
   ```

4. **Run Tests**:
   ```bash
   python test_agent.py
   ```

## Usage

The agent can answer questions about:
- **Artists**: "Show me all albums by AC/DC"
- **Albums**: "What are the most popular albums?"
- **Tracks**: "List the most expensive tracks"
- **Customers**: "How many customers do we have?"
- **Sales**: "What are the total sales by country?"

### Example Queries

```
❓ Your question: How many artists are in the database?
💬 There are 275 artists in the database.

❓ Your question: Show me albums by Led Zeppelin
💬 Led Zeppelin has several albums including Led Zeppelin I, Led Zeppelin II, Led Zeppelin III, Led Zeppelin IV, Houses Of The Holy, Physical Graffiti, Presence, In Through The Out Door, and Coda.

❓ Your question: What's the weather today?
💬 I don't know the answer to that question. I can only help with queries related to the Chinook music store database, including information about artists, albums, tracks, customers, and sales.
```

## Architecture

The agent follows a LangGraph workflow:

1. **SQL Generation**: Converts natural language to SQL using schema information
2. **SQL Execution**: Runs the query against the Chinook database  
3. **Response Generation**: Creates a natural language response from the results
4. **Error Handling**: Manages irrelevant queries and execution errors

## Database Schema

The Chinook database contains:
- **Artist** - Music artists
- **Album** - Music albums  
- **Track** - Individual songs
- **Genre** - Music genres
- **Customer** - Store customers
- **Invoice** - Sales transactions
- **Employee** - Store employees
- **Playlist** - Music playlists

## Error Handling

- **Irrelevant Queries**: Questions unrelated to the music store return a polite "I don't know" response
- **SQL Errors**: Invalid queries are handled gracefully
- **Connection Issues**: Database initialization errors are caught and reported

## Dependencies

- `langgraph>=0.2.0` - Workflow orchestration
- `langchain>=0.3.0` - LLM integration
- `langchain-openai>=0.2.0` - OpenAI API integration  
- `requests` - HTTP requests for database download
- `python-dotenv>=1.0.0` - Environment variable management
