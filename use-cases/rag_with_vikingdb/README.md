# VikingDB - Intelligent Q&A for Document Knowledge Base

This is a RAG (Retrieval-Augmented Generation) example built with BytePlus VeADK and VikingDB, demonstrating how to implement intelligent Q&A for a document knowledge base through vector retrieval.

Forked from original sample: https://github.com/bytedance/agentkit-samples/tree/main/02-use-cases/beginner/vikingdb

## Overview

This example shows how to use VikingDB to build a document knowledge base and create a professional Q&A system based on real document content.

## Core Features

- Directly import documents without manual slicing.
- Automatically build vector indexes.
- Enhance answer accuracy with semantic retrieval.
- Support composite queries from multiple document sources.

## Agent Capabilities

```text
User Query
    ↓
Agent (Knowledge Q&A)
    ↓
VikingDB Retrieval
    ├── Vector Index Query
    ├── Document Content Retrieval
    └── Relevance Ranking
    ↓
LLM Generates Answer
```

### Core Components

| Component | Description |
| - | - |
| **Agent Service** | agent.py - The main application that integrates KnowledgeBase, VikingDB, LongTermMemory, and MCP Tools. |
| **Knowledge Base** | VikingDB vector database, storing document vector indexes. |
| **Document Sources** | product_info.txt, service_policy.txt, outlet_locations.txt, warranty_terms.txt, troubleshooting_guide.txt, repair_guide.txt (generated locally during setup). |
| **MCP Toolset** | OpenStreetMap MCP - Used for geocoding and calculating distances to the nearest repair outlets. |
| **Agent Prompts** | prompts.py - Centralized system prompt for the professional support agent. |
| **Project Configuration** | pyproject.toml - Dependency management (uv tool). |
| **Short-term Memory** | Maintains session context (local storage). |
| **Long-term Memory** | VikingDB-backed long-term memory (`viking_mem`) for persisting user context across sessions. |

### Code Features

**Knowledge Base Creation** (setup_kb.py, run once):

```python
kb = KnowledgeBase(
    backend="viking",
    backend_config={
        "index": os.getenv("DATABASE_VIKING_COLLECTION"),
        "tos_config": NormalTOSConfig(
            bucket=os.getenv("DATABASE_TOS_BUCKET"),
            region=os.getenv("DATABASE_TOS_REGION"),
            endpoint=os.getenv("DATABASE_TOS_ENDPOINT"),
        ),
    },
)
```

**Agent Configuration** (agent.py):

```python
# Initialize Knowledge Base
kb = KnowledgeBase(backend="viking", index=os.getenv("DATABASE_VIKING_COLLECTION"))

# Initialize Long-term Memory
ltm = LongTermMemory(backend="viking_mem", index=os.getenv("DATABASE_VIKINGMEM_COLLECTION"))

# Create agent with tools and memory
root_agent = Agent(
    name="rag_vikingdb_agent",
    knowledgebase=kb,
    tools=tools,
    instruction=SUPPORT_AGENT_PROMPT,
    long_term_memory=ltm
)
```

## Directory Structure

```text
rag_with_vikingdb/
├── agent.py           # Agent application entry point (integrates VikingDB & MCP)
├── setup_kb.py        # One-time knowledge base initialization
├── prompts.py         # System prompts for the agent
├── config.yaml.example
├── config.yaml        # Local config (do not commit secrets)
├── requirements.txt   # Python dependency list
├── pyproject.toml     # Project configuration (uv dependency management)
└── README.md          # Project documentation
```

## Local Execution

### Prerequisites

**1. Enable BytePlus ModelArk:**

- Visit the [BytePlus ModelArk Console](https://console.byteplus.com/ark)
- Activate the model service.

**2. Enable VikingDB:**

- Visit the [VikingDB Console](https://console.byteplus.com/vikingdb)
- Create a knowledge base/Collection. Refer to [this documentation](https://docs.byteplus.com/en/docs/VikingDB/Create_Collection)

**3. Enable Object Storage (TOS):**

- VikingDB needs to upload local files to TOS, so you need to activate the object storage service.
- Visit the [TOS Console](https://console.byteplus.com/tos)

**4. Prepare BytePlus AK/SK:**

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
# Enter the project directory
cd rag_with_vikingdb
```

Use the `uv` tool to install project dependencies:

```bash
# If you don't have a `uv` virtual environment, create one first
uv venv --python 3.12

# Use `pyproject.toml` to manage dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

### Environment Setup

Create a `config.yaml` file (copy from `config.yaml.example`) and fill in your BytePlus keys, ModelArk settings, and database config:

```bash
cp config.yaml.example config.yaml
```

**Important Notes for BytePlus Users:**

1.  **Credential Names**: The underlying SDK for viking knowledge base backend currently expects `VOLCENGINE_ACCESS_KEY` and `VOLCENGINE_SECRET_KEY` even when using BytePlus. Ensure you set these in your `.env` or `config.yaml`.
2.  **Cloud Provider**: You MUST set the environment variable `CLOUD_PROVIDER=byteplus`. This tells the SDK to use the BytePlus-specific endpoints (`bytepluses.com`) instead of the default Volcengine ones.
3.  **MCP Tool Integration**: To use the location-based repair outlet features, set `MCP_TOOL_URL` and `MCP_TOOL_API_KEY`.
4.  **Long-term Memory**: Set `DATABASE_VIKINGMEM_COLLECTION` to use a separate VikingDB collection for user session memory.

Additional Notes:
- This example assumes your VikingDB collection is in **CN‑HK** and your TOS bucket is created in **CN‑HK** as well.
- If your collection is in a different region, update both `database.viking.region` and `database.tos.region` to the same region.
- The setup script uploads files to TOS using `database.tos.endpoint`.
- Make sure `database.viking.collection` in `config.yaml` matches the collection name you created.
- If you see "The specified bucket does not exist" from VikingDB, ensure the bucket is in the same region and project as your VikingDB collection.

### One-time Knowledge Base Setup

Run this once to create the VikingDB knowledge base from the local demo documents:

```bash
export CLOUD_PROVIDER=byteplus
export DATABASE_VIKING_COLLECTION=<your_vikingdb_collection>
export DATABASE_TOS_BUCKET=<your_cn_hk_tos_bucket>
```

The remaining settings (ModelArk, VikingDB base URL/region, TOS endpoint/region, and BytePlus AK/SK) are loaded automatically from `config.yaml`.

```bash
uv run setup_kb.py
```

If you update the source documents or change `DATABASE_VIKING_COLLECTION`, re-run this command.

### Debugging Methods

#### Method 1: Use VeADK Web Debugging Interface

```bash
# Go to the parent directory
cd ..

# Start the VeADK Web interface
veadk web

# Visit in your browser: http://127.0.0.1:8000
```

The web interface provides a graphical dialogue testing environment, supporting real-time viewing of retrieval results and debugging information.

#### Method 2: Command-line Testing

```bash
# Start the Agent service
uv run agent.py
# The service will listen on http://0.0.0.0:8000
```

**Important Note**: When inserting documents into VikingDB for the first time, it needs to build a vector index (takes about 2-5 minutes). The first run may result in an error; please wait for the index to be built and try again.

## AgentKit Deployment

### Prerequisites

**Important Note**: Before running this example, authorize all dependent services in the [BytePlus AgentKit console](https://console.byteplus.com/agentkit/region:agentkit+ap-southeast-1/auth).

**1. Enable BytePlus ModelArk**

**2. Enable VikingDB**

**3. Enable TOS**

**4. Prepare BytePlus AK/SK**

### AgentKit Cloud Deployment

If you do not want to bundle credentials in `config.yaml`, set them as AgentKit runtime env vars/secrets instead and keep `config.yaml` out of the package.

```bash
# Enter the rag_with_vikingdb directory

# Configure deployment parameters. Ensure `config.yaml` is present in the app package.
agentkit config \
--cloud_provider byteplus \
--region ap-southeast-1 \
--agent_name vikingdb_agent \
--entry_point 'agent.py' \
--launch_type cloud

# Start the cloud service
agentkit launch

# Test the deployed Agent
agentkit invoke 'What is the price of the High-Performance Laptop Pro?'

# Or use client.py to connect to the cloud service
# You need to edit client.py, changing the base_url and api_key on lines 14 and 15 to the runtime_endpoint and runtime_apikey fields generated in agentkit.yaml.
# Modify the request content in client.py on line 56 as needed.
uv run client.py
```

## Example Prompts

### Product Information Query

**Retrieval-based answers from product_info.txt**:

```text
User: What is the price of the High-Performance Laptop Pro?
Agent: According to the product list, the price of the High-Performance Laptop (Laptop Pro) is 8999 yuan.

User: What is the cheapest product here?
Agent: The cheapest product is the Tablet Air, priced at 2999 yuan.
```

### After-Sales Service Query

**Data retrieval from service_policy.txt**:

```text
User: What is your return and exchange policy?
Agent: According to the after-sales service policy, we support no-reason returns within 7 days of purchase and exchanges for quality issues within 15 days.

User: How long is the warranty for the laptop?
Agent: All electronic products come with a 1-year free warranty.
```

### Contextual Query

**Continuous Q&A reusing previous context:**

```text
User: What about the SmartPhone X?
Agent: The price of the SmartPhone X is 4999 yuan.
```

### Composite Query

**Comprehensive query across documents:**

```text
User: I want to buy a device for both work and entertainment. What do you recommend, and what is the after-sales support?
Agent: I recommend the Tablet Air. It is thin, portable, and suitable for both work and entertainment, priced at 2999. For after-sales support, we offer a 1-year free warranty and support 7-day no-reason returns.
```

### Location-Based Service Query (MCP Integration)

**Finding nearest outlets using OpenStreetMap MCP:**

```text
User: My laptop screen is cracked. Where can I get it fixed?
Agent: I'm sorry to hear about your laptop. We have several repair centers in Singapore. To suggest the nearest one, could you please tell me your current location or a nearby landmark?

User: I am at Orchard Road.
Agent: Based on your location at Orchard Road, the nearest outlet is our flagship store in Funan Mall (about 1.2km away). Other nearby options include Sim Lim Square (2.5km) and Plaza Singapura (0.8km). Would you like the full address and opening hours for any of these?
```

### Troubleshooting and Repair Query

**Checklists and repair processes from troubleshooting_guide.txt and repair_guide.txt:**

```text
User: My SmartPhone Ultra is draining battery very fast. What should I do?
Agent: For fast battery drain on your smartphone, please try the following:
1. Reduce screen brightness.
2. Close unused background apps.
3. Check for battery-intensive processes in settings.
If the issue persists, you can bring it to any of our outlets. Would you like to book a repair appointment?
```

## Effect Demonstration

## Technical Points

### VikingDB Knowledge Base

- **Storage Method**: Vector database (`backend="viking"`)
- **Document Import**: Supports direct import of multiple files.
- **Automatic Indexing**: Automatically builds vector indexes (requires 2-5 minutes for the first time).
- **Retrieval Method**: Vector retrieval based on semantic similarity.
- **Applicable Scenarios**: Document knowledge bases, professional Q&A, RAG applications.

### Long-term Memory (LTM)

- **Storage Backend**: `viking_mem` (using VikingDB).
- **Functionality**: Persists user session history and context across multiple interactions and server restarts.
- **Context Retrieval**: Automatically retrieves relevant past conversation context to provide more personalized and consistent responses.

### RAG Workflow

1. **Document Preparation**: Write document content to files.
2. **Vectorization**: KnowledgeBase automatically converts documents into vectors.
3. **Storage**: Vectors are stored in VikingDB.
4. **Retrieval**: Retrieve relevant document snippets when a user queries.
5. **Generation**: LLM generates an answer based on the retrieved content.

### AgentKit Integration

```python
from agentkit.apps import AgentkitAgentServerApp

agent_server_app = AgentkitAgentServerApp(
    agent=root_agent,
    short_term_memory=short_term_memory,
)
```

## FAQ

None.

## Code License

This project is licensed under the Apache 2.0 License.
