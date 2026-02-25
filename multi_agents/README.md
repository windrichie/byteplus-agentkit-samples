# Multi Agents - Multi-Agent Collaboration System

This is a multi-agent collaboration example built with BytePlus VeADK and AgentKit, demonstrating how to handle complex tasks through hierarchical orchestration and specialized sub-agents.

## Overview

This example builds an intelligent customer service system to showcase a typical multi-agent collaboration scenario.

## Core Features

- **Hierarchical Architecture**: A main agent is responsible for task distribution, while sub-agents handle specific execution.
- **Three Collaboration Modes**: Sequential execution, Parallel execution, and Loop optimization.
- **Specialized Division of Labor**: Specialized capabilities for pre-processing, information retrieval, response optimization, etc.
- **Tool Integration**: External tools such as Web search and knowledge base retrieval.

## Agent Capabilities

```text
User Request
    ↓
Customer Service Agent (Main Customer Service Agent)
    └── Sequential Service Agent
        ├── Pre-process Agent
        │   └── Analyzes user needs and extracts key information
        ├── Parallel Get Info Agent
        │   ├── RAG Search Agent (Built-in Knowledge Base Search)
        │   └── Web Search Agent (optional)
        │       └── web_search (Search Tool)
        └── Loop Refine Response Agent
            ├── Judge Agent
            └── Refine Agent
```

### Core Components

| Component | Description |
| - | - |
| **Main Agent** | [agent.py](agent.py) - The main customer service agent, responsible for overall scheduling. |
| **Sub-Agents** | [sub_agents/](sub_agents) - Specialized workflow sub-agents. |
| **- Sequential** | [sequential_agent.py](sub_agents/sequential_agent.py) - Runs the workflow in sequence (pre-process → info → refine). |
| **- Parallel** | [parallel_agent.py](sub_agents/parallel_agent.py) - Retrieves information (knowledge base, optional web). |
| **- Loop** | [loop_agent.py](sub_agents/loop_agent.py) - Evaluates and rewrites responses. |
| **Prompts** | [prompts.py](prompts.py) - System instructions for each agent. |
| **Test Client** | [client.py](client.py) - SSE streaming client for testing. |

### Code Highlights

**Root Agent** ([agent.py](agent.py)):

```python
customer_service_agent = Agent(
    name="customer_service_agent",
    description="Intelligent customer service that answers questions based on user needs",
    instruction=CUSTOMER_SERVICE_AGENT_PROMPT,
    sub_agents=[sequential_service_agent]
)
```

**Sequential Agent** ([sub_agents/sequential_agent.py](sub_agents/sequential_agent.py)):

```python
sequential_service_agent = SequentialAgent(
    name="sequential_service_agent",
    description="Executes a workflow step-by-step based on user needs",
    instruction=SEQUENTIAL_SERVICE_AGENT_PROMPT,
    sub_agents=[pre_process_agent, parallel_get_info_agent, loop_refine_response_agent]
)
```

**Parallel Agent** ([sub_agents/parallel_agent.py](sub_agents/parallel_agent.py)):

```python
parallel_get_info_agent = ParallelAgent(
    name="parallel_get_info_agent",
    description="Executes sub-tasks in parallel to quickly obtain relevant information",
    instruction=PARALLEL_GET_INFO_AGENT_PROMPT,
    sub_agents=[rag_search_agent]  # include web_search_agent to fetch web results
)
```

**Loop Agent** ([sub_agents/loop_agent.py](sub_agents/loop_agent.py)):

```python
loop_refine_response_agent = LoopAgent(
    name="loop_refine_response_agent",
    description="Coordinates customer service response processing and receives the final optimized result",
    instruction=LOOP_REFINE_RESPONSE_AGENT_PROMPT,
    sub_agents=[judge_agent, refine_agent],
    tools=[exit_tool],
    max_iterations=1
)
```

## Directory Structure

```bash
multi_agents/
├── agent.py                      # Main Agent application entry point
├── client.py                     # Test client (SSE streaming)
├── prompts.py                    # System instructions for each agent
├── sub_agents/                   # Sub-agent definitions
│   ├── __init__.py
│   ├── sequential_agent.py       # Sequential execution agent
│   ├── parallel_agent.py         # Parallel execution agent
│   └── loop_agent.py             # Loop optimization agent
├── config.yaml.example
├── config.yaml                   # Local config (safe to share; no secrets)
├── .env.example
├── .env                          # Local credentials (do not commit)
├── requirements.txt              # Python dependency list (required for agentkit deployment)
├── pyproject.toml                # Project configuration (for uv dependency management)
├── agentkit.yaml                 # AgentKit deployment configuration (auto-generated after running `agentkit config`)
├── Dockerfile                    # Docker image build file (auto-generated after running `agentkit config`)
└── README.md                     # Project documentation
```

## Local Execution

### Prerequisites

**1. Enable BytePlus ModelArk**

- Visit the [BytePlus ModelArk Console](https://console.byteplus.com/ark) and create an API key.

**2. Prepare BytePlus AK/SK**

- Refer to the [User Guide](https://docs.byteplus.com/en/docs/byteplus-platform/docs-creating-an-accesskey) to get your AK/SK.

### Dependency Installation

#### 1. Install uv Package Manager

```bash
# macOS / Linux (official installation script)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use Homebrew (macOS)
brew install uv
```

#### 2. Initialize Project Dependencies

```bash
cd multi_agents
```

You can use `pip` to install the project dependencies:

```bash
pip install -r requirements.txt
```

Alternatively, use `uv` to install the dependencies:

```bash
# If you don't have a `uv` virtual environment, create one first
uv venv --python 3.12

# Use `pyproject.toml` to manage dependencies
uv sync

# Use `requirements.txt` to manage dependencies
uv pip install -r requirements.txt

# Activate the virtual environment
source .venv/bin/activate
```

### Configuration

Create `config.yaml` (copy from `config.yaml.example`) for non-secret configuration, and create `.env` (copy from `.env.example`) for credentials:

```bash
cp config.yaml.example config.yaml
cp .env.example .env
```

Run commands from the `multi_agents` directory so `config.yaml` and `.env` are auto-loaded.

### Debugging Methods

#### Method 1: Command-Line Testing (Recommended)

```bash
# Start the Agent service
uv run agent.py
# The service will listen on http://0.0.0.0:8000

# Open a new terminal and run the test client
# Edit client.py base_url/api_key if needed.
uv run client.py
```

**Execution Effect**:

```bash
data: {... "author":"customer_service_agent", ...}
data: {... "author":"pre_process_agent", ...}
data: {... "author":"rag_search_agent", ...}
data: {... "author":"judge_agent", ...}
data: {... "author":"refine_agent", ...}
```

#### Method 2: Using the VeADK Web Debugging Interface

```bash
# Go to the parent directory
cd ..

# Start the VeADK Web interface
veadk web

# Access in your browser: http://127.0.0.1:8000
```

The web interface allows you to visualize the multi-agent collaboration flow and execution trace.

## AgentKit Deployment

### Prerequisites

**Important Note**: Before running this example, authorize dependent services in the [BytePlus AgentKit console](https://console.byteplus.com/agentkit/region:agentkit+ap-southeast-1/auth).

**1. Enable BytePlus ModelArk**

**2. Prepare BytePlus AK/SK**

### AgentKit Cloud Deployment

If you do not want to bundle credentials into the app package, keep `.env` local only and set credentials as AgentKit runtime env vars/secrets instead.

```bash
cd multi_agents

# Configure deployment parameters
agentkit config \
--cloud_provider byteplus \
--region ap-southeast-1 \
--agent_name customer_service_agent \
--entry_point 'agent.py' \
--launch_type cloud

# Launch the cloud service
agentkit launch

# Test the deployed Agent
agentkit invoke 'I want to buy a phone for gaming. Can you recommend a model for me?'
```

## Example Prompts

### Scenario 1: Simple Greeting

```text
User: Hello, what can you help me with?
Agent: Hello! I am an intelligent customer service assistant. I can help you with:

      1. Product consultation and recommendations
      2. Order inquiries and processing
      3. Technical support and problem-solving
      4. Other pre-sales and after-sales services

      How can I help you today?
```

### Scenario 2: Product Consultation (Parallel Search)

```text
User: I want to buy a phone for gaming. Can you recommend a model for me?

Agent Execution Flow:
1. [Pre-process Agent] Extracts key information:
   - Need: Phone
   - Purpose: Gaming
   - Goal: Model recommendation

2. [Sequential Service Agent] Starts the workflow

3. [Parallel Get Info Agent] Retrieves information in parallel:
   └── [RAG Search Agent] Searches the built-in knowledge base

   Note: web_search_agent is optional and disabled by default. You can enable it in sub_agents/parallel_agent.py.

4. [Loop Refine Response Agent] Optimizes the response:
   ├── [Judge Agent] Evaluates the initial response
   │   Rating: Content is accurate but not friendly enough
   └── [Refine Agent] Rewrites the response
       Optimization: Adds polite language and structuring

Agent: Based on your graphics processing needs, I recommend the following specifications:
        Product Name: Star Smart Phone Pro
        Price: 4999 RMB
        Core Configuration: Snapdragon 8 Gen3 (high-performance processor, suitable for gaming), 5000mAh (large battery for long gaming sessions)
        Other Benefits: Supports 12-month interest-free installments
```

### Scenario 3: Order Issue (Full Flow)

```text
User: When will my order 12345 be shipped? I've been waiting for 3 days.

Agent Execution Flow:
1. [Pre-process Agent] Extracts information:
   - Order Number: 12345
   - Issue: Shipping time
   - Emotion: Anxious (waited 3 days)

2. [Sequential Service Agent] Starts the workflow

3. [Parallel Get Info Agent] Queries in parallel:
   └── [RAG Search Agent] Looks up the built-in sample order and policy data
      Result: Order has been shipped, tracking number SF123456; package is in transit, estimated delivery tomorrow

4. [Loop Refine Response Agent] Optimizes the response:
   ├── [Judge Agent] Evaluation: Information is complete but lacks an apology
   └── [Refine Agent] Rewrites: Adds an apology and reassurance

Agent: I am very sorry for the delay!

      I have checked the latest status of your order 12345:

      ✓ The order was shipped yesterday
      ✓ Tracking Number: SF123456 (SF Express)
      ✓ Current Status: In transit
      ✓ Estimated Delivery: Tomorrow (December 9th)

      You can track the logistics details on the SF Express official website or WeChat mini-program.
      If you have any other questions, I am here to help!
```

## Effect Demonstration

## Technical Points

### Three Collaboration Modes

#### 1. Sequential Agent

**Features**:

- Sub-agents execute in sequence.
- The next agent can use the result of the previous one.
- Suitable for task chains with dependencies.

**Use Cases**:

- Information gathering → Analysis → Response (this example)
- Data acquisition → Cleaning → Processing
- Planning → Execution → Verification

#### 2. Parallel Agent

**Features**:

- Sub-agents execute simultaneously without blocking each other.
- Improves execution efficiency.
- Suitable for independent sub-tasks.

**Use Cases**:

- Querying multiple data sources simultaneously (this example)
- Calling multiple APIs in parallel
- Multi-dimensional information gathering

#### 3. Loop Agent

**Features**:

- Executes sub-agents in a loop until a condition is met.
- Supports setting a maximum number of iterations.
- Suitable for tasks that require optimization and refinement.

**Use Cases**:

- Response quality optimization (this example)
- Code debugging and fixing
- Iterative planning

### Implementation Principles

**Sequential Execution**:

```python
from veadk.agents.sequential_agent import SequentialAgent

agent = SequentialAgent(
    sub_agents=[agent1, agent2, agent3]  # Execute in order
)
```

**Parallel Execution**:

```python
from veadk.agents.parallel_agent import ParallelAgent

agent = ParallelAgent(
    sub_agents=[agent1, agent2]  # Execute in parallel
)
```

**Loop Execution**:

```python
from veadk.agents.loop_agent import LoopAgent

agent = LoopAgent(
    sub_agents=[judge_agent, refine_agent],
    max_iterations=3,  # Loop at most 3 times
    tools=[exit_tool]  # Tool to exit early
)
```

### Specialized Division of Labor

| Agent | Responsibility | Features |
| - | - | - |
| **Customer Service** | General Dispatcher | Understands user intent, dispatches tasks |
| **Pre-process** | Pre-processing | Extracts key information, standardizes input |
| **Sequential Service** | Workflow Control | Coordinates sequential execution of sub-agents |
| **Parallel Get Info** | Information Retrieval | Searches multiple data sources in parallel |
| **RAG Search** | Knowledge Base Retrieval | Queries internal documents and data |
| **Web Search** | Web Search | Queries the latest information from the internet |
| **Loop Refine** | Quality Control | Cyclically optimizes response quality |
| **Judge** | Evaluation | Assesses response quality, provides suggestions for improvement |
| **Refine** | Rewriting | Optimizes response content based on evaluation |

### Tool Integration

**Web Search Tool** (optional, [sub_agents/parallel_agent.py](sub_agents/parallel_agent.py)):

```python
from veadk.tools.builtin_tools.web_search import web_search

web_search_agent = Agent(
    name="web_search_agent",
    description="Searches for relevant information from the internet",
    instruction=WEB_SEARCH_AGENT_PROMPT,
    tools=[web_search],
)
```

**Exit Loop Tool** ([sub_agents/loop_agent.py](https://github.com/volcengine/agentkit-samples/blob/main/02-use-cases/beginner/multi_agents/sub_agents/loop_agent.py#L18-L23)):

```python
def exit_tool(tool_context: ToolContext) -> str:
    tool_context.actions.end_of_agent = True
    return {}
```

## Extension Directions

### 1. Add More Specialized Agents

- **Sentiment Analysis Agent**: Identifies user emotions and adjusts response style.
- **Order Processing Agent**: Automatically handles returns, exchanges, and inquiries.
- **Technical Support Agent**: Answers technical questions and provides solutions.

### 2. Integrate More Tools

- **Database Query**: Directly query order and user information.
- **Email Notification**: Send confirmation emails.
- **Ticketing System**: Automatically create and update tickets.

### 3. Optimize Collaboration Strategies

- **Dynamic Task Allocation**: Select the appropriate agent based on the task type.
- **Intelligent Routing**: Distribute tasks based on load balancing.
- **Result Aggregation**: Intelligently merge results from multiple agents.

## References

- [VeADK Official Documentation](https://volcengine.github.io/veadk-python/)
- [AgentKit Development Guide](https://volcengine.github.io/agentkit-sdk-python/)
- [BytePlus ModelArk Console](https://console.byteplus.com/ark)

## License

This project is licensed under the Apache 2.0 License.
