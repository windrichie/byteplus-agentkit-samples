# Simple Image + Video Generation Agent

This sample demonstrates how to build a minimal Agent with VeADK that can:

- Generate images via the built-in `image_generate` tool
- Generate videos via the built-in `video_generate` tool
- Run locally as an HTTP service and deploy to BytePlus AgentKit Runtime

## How It Works

The agent is defined in [agent.py](file:///Users/bytedance/Documents/mygarage/agentkit/byteplus-agentkit-samples/use-cases/simple_image_video_gen/agent.py):

- Tools: `image_generate`, `video_generate`
- Agent server: `AgentkitAgentServerApp` (listens on port `8000` by default)

## Local Run

### 1) Install dependencies

```bash
cd use-cases/simple_image_video_gen

uv venv --python 3.12
source .venv/bin/activate
uv sync
```

### 2) Configure credentials

Set your ModelArk key and base URL (BytePlus):

```bash
export MODEL_AGENT_API_KEY=<your_modelark_api_key>
export MODEL_AGENT_API_BASE=https://ark.ap-southeast.bytepluses.com/api/v3/
export MODEL_AGENT_NAME=deepseek-v3-2-251201
```

### 3) Start the server

```bash
uv run agent.py
```

The service listens on `http://0.0.0.0:8000`.

## Deploy to BytePlus AgentKit Runtime

### 1) Configure AgentKit credentials

Option A: Global config

```bash
agentkit config --global --set byteplus.access_key=<your_ak>
agentkit config --global --set byteplus.secret_key=<your_sk>
```

Option B: Environment variables

```bash
export BYTEPLUS_ACCESS_KEY=<your_ak>
export BYTEPLUS_SECRET_KEY=<your_sk>
```

### 2) Configure and deploy

```bash
cd use-cases/simple_image_video_gen

agentkit config \
  --cloud_provider byteplus \
  --region ap-southeast-1 \
  --agent_name quick_video_create_agent \
  --entry_point 'agent.py' \
  --launch_type cloud

agentkit launch
```

### 3) Test the deployed agent

Use the AgentKit console runtime endpoint and API key, or run:

```bash
agentkit invoke '{"prompt":"Generate an image of a cyberpunk city at night, then turn it into a short video."}'
```

