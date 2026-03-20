# veADK Migration Notes (Image Scoring Sample)

This document summarizes the minimal changes required to migrate the [Google ADK image‑scoring sample](https://github.com/google/adk-samples/tree/main/python/agents/image-scoring) to veADK + AgentKit, and why a small adapter tool is used for image generation.

## Goal

Keep the original multi-agent workflow intact (prompt → image generation → scoring → loop check), while swapping the runtime and model backends to veADK/AgentKit with minimal code changes.

## What Changed (Minimal Surface Area)

### 1) Agent framework imports

Replaced Google ADK agents with veADK equivalents for orchestration:

- `SequentialAgent` → `veadk.agents.sequential_agent.SequentialAgent`
- `LoopAgent` → `veadk.agents.loop_agent.LoopAgent`
- `Agent` → `veadk.Agent`

The flow and prompt content are unchanged.

## 2) Model configuration

Google ADK used GCP/Vertex defaults. veADK requires BytePlus ModelArk configuration via environment variables.

Centralized in [config.py](config.py):

- `MODEL_AGENT_NAME`
- `MODEL_AGENT_API_BASE`
- `MODEL_AGENT_API_KEY`

## 3) Image generation backend

Google ADK used Imagen (via `google.genai`) directly within the tool. In the original code, this tool would:
- Call the Imagen API to get image bytes.
- Save the image bytes to Google Cloud Storage (GCS).
- Save the bytes as an ADK artifact.

The veADK version uses `veadk.tools.builtin_tools.image_generate`, which calls Seedream. This requires a different approach because Seedream returns a publicly accessible image URL rather than raw bytes, and we don't need to manually upload to GCS.

To bridge this gap while preserving the rest of the workflow, a thin adapter tool was added in [image_generation_tool.py](sub_agents/image/tools/image_generation_tool.py) to:

- call the built-in veADK `image_generate`
- extract the first image URL from the Seedream tool response
- optionally download the bytes from that URL and save them as an artifact (to keep parity with ADK artifact usage)
- store the URL into `tool_context.state` (replacing the GCS URI) for downstream scoring

## 4) AgentKit server entrypoint

Added [agent.py](agent.py) to serve the agent via AgentKit:

- uses `AgentkitAgentServerApp`
- injects `ShortTermMemory`

## Did we minimize changes?

Yes. The workflow, prompts, policy logic, scoring structure, and session state usage were preserved. Changes were limited to:
- framework imports (Google ADK → veADK)
- model configuration to use BytePlus ModelArk
- a small adapter for image generation
- AgentKit server wrapper

## Why use `image_generation_tool.py` instead of directly using `image_generate`?
You can technically attach `image_generate` directly as a tool, but the sample needs two behaviors that the built‑in tool alone does not guarantee:

1) **Artifact compatibility**  
   The scoring flow expects an artifact to be available (or at least a placeholder). The adapter downloads the generated image and stores it with `save_artifact` when possible.

2) **Consistent URL extraction**  
   The built-in tool returns a generic response format. The adapter normalizes the response and stores the image URL in state (`generated_image_url_*`) so downstream agents have a stable field to read.

This mirrors the Google sample: Google ADK already has access to Imagen through SDK calls, but they still wrapped it in a custom `generate_images` tool to:

- add consistent artifact storage
- enforce a fixed output structure for downstream tools
- integrate storage (GCS) and session state

So the adapter exists to preserve the same integration points, but backed by veADK’s built‑in image generation instead of Google’s Imagen client.

## Local Test Steps

These steps mirror the patterns used in [simple_image_video_gen](../use-cases/simple_image_video_gen/agent.py) and [multi_agents](../multi_agents/agent.py).

1) Install dependencies

```bash
cd /Users/bytedance/Documents/mygarage/agentkit/byteplus-agentkit-samples/migrate-from-adk

uv venv --python 3.12
source .venv/bin/activate
uv sync
```

2) Configure ModelArk credentials (BytePlus)

```bash
export MODEL_AGENT_API_KEY=<your_modelark_api_key>
export MODEL_AGENT_API_BASE=https://ark.ap-southeast.bytepluses.com/api/v3/
export MODEL_AGENT_NAME=deepseek-v3-2-251201
```

3) Start the AgentKit server

```bash
uv run agent.py
```

The service listens on `http://0.0.0.0:8000`.

## AgentKit Cloud Deployment

These steps mirror the deployment guidance used across the sample repo (see [tiktok_ref_video_gen](../use-cases/tiktok_ref_video_gen/README.md)).

### Step 0: Install AgentKit CLI

```bash
pip install 'agentkit-sdk-python>=0.5.1'
```

### Step 1: Configure BytePlus credentials

```bash
agentkit config --global --set byteplus.access_key=<your_ak>
agentkit config --global --set byteplus.secret_key=<your_sk>
```

### Step 2: Enter the project directory

```bash
cd /Users/bytedance/Documents/mygarage/agentkit/byteplus-agentkit-samples/migrate-from-adk/image_scoring
```

### Step 3: Configure the deployment

```bash
agentkit config \
  --agent_name image_scoring \
  --entry_point 'agent.py' \
  --cloud_provider byteplus \
  --region ap-southeast-1 \
  --launch_type cloud
```

If you do not want to bundle API keys into the package, set them as runtime env vars or in the AgentKit console:

```bash
agentkit config --set runtime_envs.MODEL_AGENT_API_KEY=<your_key>
agentkit config --set runtime_envs.MODEL_AGENT_API_BASE=https://ark.ap-southeast.bytepluses.com/api/v3/
agentkit config --set runtime_envs.MODEL_AGENT_NAME=deepseek-v3-2-251201
```

### Step 4: Deploy

```bash
agentkit launch
```

### Step 5: Test the deployed agent

Use the AgentKit Console to open the runtime and send a prompt, or invoke via CLI:

```bash
agentkit invoke '{"prompt": "Generate a high-quality image of a minimalist watch for a premium brand"}'
```
