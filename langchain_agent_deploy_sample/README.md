# Session 1 - Adapting a Standard LangChain Agent for AgentKit

## Overview

This workshop demonstrates how to take a standard LangChain-based agent and make a lightweight adaptation with the AgentKit Python SDK, so it can be deployed to the Volcengine AgentKit platform with one command.

### Agent Adaptation Guide

We will compare `langchain_agent.py` (the original implementation) and `agent.py` (the AgentKit-adapted version). The adaptation only requires **3 minimal changes**:

1. **Import the SDK and initialize the app**

   ```python
   # Import AgentKit SDK
   from agentkit.apps import AgentkitSimpleApp

   # Initialize the app instance
   app = AgentkitSimpleApp()
   ```

2. **Mark the entrypoint function**
   Use the `@app.entrypoint` decorator to mark your main business logic function.

   ```python
   @app.entrypoint
   async def run(payload: dict, headers: dict):
       # Your business logic...
   ```

3. **Return using the standard protocol**
   Change outputs that were previously printed to stdout into `yield`-ed JSON event data in the standard format.

   ```python
   # Native LangChain: print(chunk)
   # AgentKit adaptation:
   yield json.dumps(event_data)
   ```

These changes are non-intrusive: your existing Chain definition, Tool definition, and Prompt logic do not need to be modified.

## Key Features

1. **Build a LangChain Agent**: Build a tool-calling ReAct agent using the LangChain 1.0 standard pattern.
2. **Fast AgentKit adaptation**: Convert a local agent into a production-ready microservice via the SDK, without changing core Chain logic.
3. **One-click cloud deployment**: Use AgentKit CLI to package code, build images, and sync environment variables automatically.

## Agent Capabilities

This agent provides the following basic capabilities:

- **Automated reasoning**: Based on the ReAct pattern, it analyzes the user query and plans tool calls.
- **Tool calling**:
  - `get_word_length`: compute the length of a word.
  - `add_numbers`: add two numbers.
- **Streaming responses**: Supports the SSE protocol and streams intermediate thoughts and final results.

## Project Structure

```bash
session1/
├── agent.py               # AgentKit-adapted agent app (core file)
├── langchain_agent.py     # Original LangChain script (for comparison)
├── local_client.py        # Local streaming client for testing
├── agentkit.yaml          # Deployment config
├── .env                   # Environment variables (synced automatically on deploy)
└── README.md              # Documentation
```

## Run Locally

### Prerequisites

1. **Install dependencies**

   ```bash
   uv sync
   source .venv/bin/activate
   ```

2. **Configure environment variables**

   ```bash
   cp .env.sample .env
   # Edit .env and fill in required values such as OPENAI_API_KEY

   # Volcengine access credentials (required)
   export VOLCENGINE_ACCESS_KEY=<Your Access Key>
   export VOLCENGINE_SECRET_KEY=<Your Secret Key>
   ```

### Debugging

**Option 1: Run the native script** (validate agent logic)

```bash
uv run langchain_agent.py
```

**Option 2: Run the AgentKit service** (simulate production-like behavior)

```bash
# Start the service (listens on port 8000)
uv run agent.py

# In a new terminal, run the client test
uv run client.py
```

## Deploy with AgentKit

Deployment is fully automated and supports automatic syncing of environment variables from `.env`.

### 1. Initialize configuration

```bash
agentkit config
```

This command guides you through selecting workspace, image registry, etc., and generates `agentkit.yaml`.

### 2. Launch to production

```bash
agentkit launch
```

> **Important**: `agentkit launch` automatically reads the `.env` file in your project root and injects all environment variables into the cloud Runtime environment. This means you **do not** need to configure sensitive values like `OPENAI_API_KEY` or `MODEL_NAME` manually in the console. The CLI syncs the environment for you to keep cloud runtime consistent with your local setup.

### 3. Test online

After deployment, you can invoke the cloud agent directly with the CLI:

```bash
# <URL> is the service endpoint printed by the launch command
agentkit invoke 'Hello, can you calculate 10 + 20 and tell me the length of the word "AgentKit"?'
```

## Example Prompts

- "What is the length of the word 'Volcengine'?"
- "Calculate 123 + 456."
- "Hello, can you calculate 10 + 20 and tell me the length of the word 'AgentKit'?"
- "Tell me a fun fact about Python." (This agent is not a general-knowledge bot; it will try to use tools or refuse.)

## What It Looks Like

- **Local script**: Prints the ReAct thought chain to the terminal, showing reasoning steps and the final result.
- **HTTP service**: The client receives streaming SSE events, including `on_llm_chunk` (LLM thought stream), `on_tool_start` (tool call start), `on_tool_end` (tool call end), etc., for a richer interactive experience.

## FAQ

- **Q: Why does it say the API key is invalid?**
  - A: Make sure `OPENAI_API_KEY` (or your model provider API key) in `.env` is correct, and `OPENAI_API_BASE` matches your provider (for example Volcengine Ark or OpenAI).

- **Q: Why don’t environment variables take effect during deployment?**
  - A: Confirm that `.env` is located in the project root directory where you run `agentkit launch`. The CLI automatically discovers and syncs that file.

- **Q: Why can’t the agent answer general knowledge questions?**
  - A: This sample focuses on demonstrating tool-calling and does not include a general knowledge base. To answer general questions, extend the toolset or connect a knowledge base.

## License

This project is licensed under the Apache 2.0 License.

