# LangGraph Text-to-SQL Agent

A LangGraph-based text-to-SQL agent that converts natural language questions into SQL queries, executes them against the Chinook SQLite database, and provides natural language responses.

## Features

- **Natural Language to SQL**: Converts user questions into SQL queries using GPT-4
- **In-Memory Database**: Creates and populates Chinook database in SQLite memory
- **Schema-Aware**: Includes detailed database schema information in prompts for accurate SQL generation
- **Safety Filtering**: Rejects irrelevant queries and only answers music database-related questions  
- **Natural Language Responses**: Converts SQL results back to conversational answers
- **LangGraph Workflow**: Uses LangGraph's state management and conditional routing

## Database Schema

The agent works with the Chinook database containing:
- **Artists** (275 records) - Music artists
- **Albums** (347 records) - Album information  
- **Tracks** (3,503 records) - Individual songs
- **Customers** (59 records) - Customer information
- **Invoices** (412 records) - Purchase transactions
- **Employees** - Staff information
- **Genres** - Music genres
- **Playlists** - User playlists
- **MediaTypes** - File formats

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set OpenAI API Key**:
   Update the `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. **Test Database Setup** (optional):
   ```bash
   python test_db_setup.py
   ```

## Usage

### Interactive Demo
```bash
python demo.py
```

### Programmatic Usage
```python
from text_to_sql_agent import TextToSQLAgent

agent = TextToSQLAgent()
response = agent.query("How many customers are there?")
print(response)
```

## Example Queries

The agent can answer questions like:
- "How many customers are in the database?"
- "What are the top 5 best-selling tracks?"  
- "Which artist has the most albums?"
- "What is the total revenue from invoices in 2009?"
- "List all genres in the database"
- "Show me customers from Canada"

## Architecture

The agent uses a LangGraph workflow with three main nodes:

1. **Text-to-SQL Node**: Converts natural language to SQL using schema context
2. **Execute SQL Node**: Runs queries against the in-memory database  
3. **Generate Response Node**: Creates natural language answers from results

### Conditional Routing
- Irrelevant queries are filtered out and receive "I don't know" responses
- Valid queries proceed through the full SQL execution pipeline

## Safety Features

- Only processes music database-related queries
- Rejects questions outside the domain scope  
- Handles SQL execution errors gracefully
- Limits result sets to prevent overwhelming responses

## Files

- `text_to_sql_agent.py` - Main agent implementation
- `demo.py` - Interactive demo script
- `test_db_setup.py` - Database setup verification
- `chinook.sql` - Downloaded Chinook database schema and data
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (API keys)

## Requirements

- Python 3.8+
- OpenAI API key
- Internet connection for initial setup
