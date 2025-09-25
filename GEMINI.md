# Project Overview

This project is a Text-to-SQL multi-agent system built with Python, FastAPI, Pydantic AI, and LangGraph. It exposes a FastAPI endpoint that takes a natural language question, converts it to a SQL query, executes it against a PostgreSQL database, and returns a natural language answer.

The agent is designed with a graph-based approach using LangGraph, allowing for a multi-step process of intent classification, SQL generation, reflection, and execution.

## Key Technologies

*   **Backend Framework:** FastAPI
*   **LLM Orchestration:** LangGraph
*   **Structured Data Generation:** Pydantic AI
*   **Database:** PostgreSQL (asynchronous with `asyncpg`)
*   **Python Version:** >=3.12.7

## Architecture

The application is structured into three main files:

*   `main.py`: The FastAPI entry point, handling API endpoints, dependency injection, and the application lifecycle.
*   `agent.py`: Defines the LangGraph agent, including its state, nodes (intent classification, SQL generation, reflection, execution), and the conditional logic that connects them.
*   `database.py`: Manages all database interactions, including an asynchronous connection pool, schema retrieval, and initial data setup.

# Building and Running

This project uses `uv` for environment and package management.

## 1. Setup PostgreSQL

It is recommended to use Docker to run a local PostgreSQL instance.

**`docker-compose.yml`:**
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:13
    container_name: text-to-sql-db
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
      POSTGRES_DB: text2sql
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Run the database with:
```bash
docker-compose up -d
```

## 2. Environment Variables

Create a `.env` file in the project root:

```
# PostgreSQL connection URL
DATABASE_URL="postgresql://myuser:mypassword@localhost:5432/text2sql"

# OpenAI API Key
OPENAI_API_KEY="sk-..."
```

## 3. Install Dependencies

```bash
# Install uv if you haven't already
pip install uv

# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Create a requirements.txt file
cat << EOF > requirements.txt
fastapi
uvicorn[standard]
langgraph>=0.1.0a0
pydantic-ai
langchain-openai
python-dotenv
langchain
asyncpg
psycopg[binary]
EOF

# Install dependencies
uv pip install -r requirements.txt
```

## 4. Run the Application

You can now send requests to the agent:

```bash
curl -X POST "http://127.0.0.1:8000/agent/invoke" \
-H "Content-Type: application/json" \
-d '{"question": "Who is the manager of the Marketing department?"}'
```

# Development Conventions

*   **Asynchronous Code:** The project uses `async` and `await` extensively for non-blocking I/O, especially for database interactions and the FastAPI endpoints.
*   **Dependency Injection:** FastAPI's `Depends` system is used to provide database connections to the API endpoints.
*   **Configuration:** Application configuration (database URL, API keys) is managed through environment variables loaded from a `.env` file.
*   **Modularity:** The code is separated into logical modules (`main.py`, `agent.py`, `database.py`) based on functionality.
*   **State Management:** The agent's state is explicitly managed within the `GraphState` TypedDict, which is passed between nodes in the LangGraph workflow.

# Mandatory for this folder
All work in this folder must use Sequential Thinking MCP.