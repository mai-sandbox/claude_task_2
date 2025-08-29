# LangGraph Text-to-SQL Agent

A sophisticated text-to-SQL agent built with LangGraph that can answer natural language questions about the Chinook music database.

## Features

- **🧠 Smart SQL Generation**: Converts natural language questions to accurate SQL queries
- **🗄️ In-Memory Database**: Automatically fetches and sets up the Chinook SQLite database
- **📊 Schema-Aware**: Uses detailed database schema information for better SQL generation
- **🔍 Query Execution**: Safely executes SELECT queries against the database
- **📝 Natural Language Responses**: Converts query results back to natural language
- **❌ Error Handling**: Gracefully handles invalid queries and irrelevant questions
- **🔄 LangGraph Workflow**: Robust state management with conditional node routing

## Architecture

The agent uses a LangGraph workflow with three main nodes:

1. **SQL Generation Node**: Takes user question and generates appropriate SQL
2. **SQL Execution Node**: Executes the SQL query against the database
3. **Response Generation Node**: Creates natural language response from results

## Files

- `sql_agent.py` - Main agent implementation (uses OpenAI)
- `sql_agent_claude.py` - Claude version of the agent (uses Anthropic)
- `demo_agent.py` - Demonstration script that works without API keys
- `test_agent.py` - Test script for validation
- `requirements.txt` - Python dependencies

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. For OpenAI version, set your API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

3. For Claude version, set your Anthropic API key:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

## Usage

### With API Key (Full Agent)

```bash
# OpenAI version
python sql_agent.py

# Claude version  
python sql_agent_claude.py
```

### Demo Mode (No API Key Required)

```bash
python demo_agent.py
```

### Testing

```bash
python test_agent.py
```

## Example Queries

The agent can handle questions like:

- "How many customers are there?"
- "Who are the top 5 customers by total purchases?"
- "What are the most popular music genres?"
- "Which artists have the most albums?"
- "How many tracks are there in the Rock genre?"
- "What are the longest tracks?"

For irrelevant questions (e.g., "What's the weather?"), the agent responds: "I don't know the answer to that question. I can only help with questions that can be answered using the Chinook music database."

## Database

The agent automatically fetches the Chinook database from:
`https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql`

The database contains 11 tables with information about:
- Artists, Albums, Tracks
- Customers, Employees, Invoices
- Genres, Media Types, Playlists

## Safety Features

- Only allows SELECT queries (no INSERT/UPDATE/DELETE)
- Validates queries before execution
- Handles SQL execution errors gracefully
- Filters out non-database related questions

## LangGraph Implementation

The agent demonstrates key LangGraph concepts:

- **StateGraph**: Manages workflow state across nodes
- **Conditional Edges**: Route based on execution results
- **State Management**: Maintains context throughout the workflow
- **Error Recovery**: Handles failures at each node
- **Message Passing**: Structured communication between nodes

This implementation showcases how to build production-ready agentic systems with LangGraph for complex, multi-step tasks.