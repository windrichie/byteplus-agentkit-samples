# BytePlus AgentKit Samples

Code samples for building and deploying AI agents on **BytePlus AgentKit** — ByteDance's international cloud platform for running agent workloads (the global counterpart of Volcengine).

> **BytePlus** is the international brand of Volcengine. The same underlying AgentKit platform ships under both names with different API endpoints, model gateways, regions, and SDK packages. This repo targets the **BytePlus (international)** side.

## What is this repo?

These samples are adapted from the official [bytedance/agentkit-samples](https://github.com/bytedance/agentkit-samples/) repository and reworked so they run end-to-end on BytePlus rather than Volcengine. The originals were written for the in-China (Volcengine) stack and were mostly in Chinese. Every sample here has been:

- **Ported to BytePlus endpoints and credentials** — ModelArk gateway (`https://ark.ap-southeast.bytepluses.com/api/v3/`), BytePlus regions (`ap-southeast-1`, `cn-hongkong`), BytePlus TOS object storage, and BytePlus SDK packages (`byteplussdkcore`, `byteplussdkid`, etc.).
- **Switched to BytePlus ModelArk model IDs** — e.g. `deepseek-v3-2-251201`, `doubao-seed-1-6-251015`, `doubao-seedream-4-5-251128`, `doubao-seedance-1-5-pro-251215`.
- **Translated to English** — prompts, agent descriptions, tool docstrings, hook/callback messages, READMEs, and runtime output are all English so the samples are usable by an international audience.
- **Tested to deploy** to BytePlus AgentKit via the `agentkit` CLI.

## Prerequisites

- **Python 3.10+**
- [**uv**](https://docs.astral.sh/uv/) — used for virtualenvs and dependency sync across all samples
- A **BytePlus account** with access to ModelArk, TOS, and AgentKit
- The **AgentKit CLI** (`agentkit` / `ak`):

  ```bash
  pip install 'agentkit-sdk-python>=0.5.3'
  ```

- Configure your BytePlus deploy credentials once (the CLI stores them globally; the runtime itself uses an IAM role, not your AK/SK):

  ```bash
  agentkit config --global --set byteplus.access_key=<your_byteplus_ak>
  agentkit config --global --set byteplus.secret_key=<your_byteplus_sk>
  ```

## Samples

Each folder is an independent, self-contained agent project. Pick one, configure it, run it locally, then deploy.

| Folder | What it demonstrates | Framework |
| --- | --- | --- |
| [`multi_agents/`](./multi_agents) | Multi-agent orchestration patterns — a customer-service agent composed of `SequentialAgent`, `ParallelAgent`, and `LoopAgent` sub-agents. | VeADK |
| [`sandbox_tool_sample/`](./sandbox_tool_sample) | Using VeADK's built-in `run_code` sandbox tool — a Python coding agent that executes code in an isolated environment. | VeADK |
| [`migrate-from-adk/`](./migrate-from-adk) | Migrating a [Google ADK](https://github.com/google/adk-samples) sample (image scoring) to VeADK + AgentKit with minimal changes. See its [README](./migrate-from-adk/README.md) for the diff walkthrough. | VeADK |
| [`langchain_agent_deploy_sample/`](./langchain_agent_deploy_sample) | Deploying a **LangChain** agent (not VeADK) onto AgentKit using `AgentkitSimpleApp`. Shows AgentKit is framework-agnostic. | LangChain |
| [`use-cases/ad_video_gen_seq/`](./use-cases/ad_video_gen_seq) | A sequential 7-agent pipeline that turns a product brief into a finished e-commerce marketing video (market → storyboard → image → image eval → video → video eval → release). Uses Seedream (image) + Seedance (video). | VeADK |
| [`use-cases/codex_sandbox_agent/`](./use-cases/codex_sandbox_agent) | One-shot code factory: a dispatcher agent drives the codex runtime inside an AgentKit CodeEnv sandbox (write -> test -> repair loop), runs locally or deployed to AgentKit Runtime with TOS presigned-link delivery of the finished project. | VeADK |
| [`use-cases/gateway_shopizer/`](./use-cases/gateway_shopizer) | A legacy Shopizer (Java) e-commerce app behind an AgentKit MCP toolset + Model Gateway, so agents can query and operate the existing API. | VeADK |
| [`use-cases/rag_with_vikingdb/`](./use-cases/rag_with_vikingdb) | RAG support agent backed by a VikingDB knowledge base, with long-term memory (VikingMem) and an optional MCP toolset. | VeADK |
| [`use-cases/simple_image_video_gen/`](./use-cases/simple_image_video_gen) | Minimal agent that generates images and turns them into a video — the smallest possible multimedia starting point. | VeADK |
| [`use-cases/tiktok_ref_video_gen/`](./use-cases/tiktok_ref_video_gen) | "Director" agent that downloads a TikTok reference video, analyzes the product, and generates a new product video matching the reference style. | VeADK |
| [`use-cases/video_gen/`](./use-cases/video_gen) | YAML-driven (`AgentBuilder`) story-to-video generation with MCP-based video stitching. | VeADK |

> Framework note: **VeADK** (Volcano Engine Agent Development Kit) is a Google-ADK-compatible agent framework. The BytePlus runtime accepts VeADK agents directly. LangChain and other frameworks are supported through the `AgentkitSimpleApp` entrypoint.

## Common conventions

Every sample follows the same layout, so once you've run one the rest are familiar:

- **`agent.py`** (or `main.py`) — entry point that builds the root agent and wraps it in `AgentkitAgentServerApp`.
- **`config.yaml.example`** — committed template for model/TOS/database config. Copy to `config.yaml` and fill in your values (`config.yaml` is gitignored).
- **`.env`** — local secrets and runtime flags. Never committed (gitignored). Holds your ModelArk API keys, BytePlus AK/SK, bucket names, etc.
- **`.agentkit/agentkit.yaml`** — the AgentKit deploy manifest (see below). Gitignored because it may reference live secrets via `${VAR}`.
- **`pyproject.toml` / `requirements.txt`** — dependencies; use `uv sync` or `uv pip install -r requirements.txt`.
- **`Dockerfile`** — optional; the AgentKit runtime can build from source or a Dockerfile.

### Environment variables

Most samples read the same core env vars. Set them in `.env` (local) or as runtime envs (cloud):

| Variable | Purpose |
| --- | --- |
| `MODEL_AGENT_API_KEY` | ModelArk API key for the reasoning/agent model |
| `MODEL_AGENT_API_BASE` | ModelArk gateway, e.g. `https://ark.ap-southeast.bytepluses.com/api/v3/` |
| `MODEL_AGENT_NAME` | ModelArk model ID, e.g. `deepseek-v3-2-251201` |
| `MODEL_IMAGE_API_KEY` / `MODEL_VIDEO_API_KEY` | Keys for the image (Seedream) and video (Seedance) models, when used |
| `TOS_ENDPOINT` / `DATABASE_TOS_BUCKET` | BytePlus TOS endpoint and bucket for uploads |
| `BYTEPLUS_ACCESS_KEY` / `BYTEPLUS_SECRET_KEY` | BytePlus account credentials (local dev / Viking SDK) |
| `BYTEPLUS_REGION` | BytePlus region, e.g. `ap-southeast-1` |

Each sample's README lists its exact variable set.

## Quick start

Pick a sample — `sandbox_tool_sample` is the simplest — then:

```bash
cd sandbox_tool_sample

# 1. Create a virtualenv and install deps
uv venv --python 3.12
source .venv/bin/activate
uv sync   # or: uv pip install -r requirements.txt

# 2. Configure secrets
cp config.yaml.example config.yaml   # edit model id, api key, etc. (if the sample ships one)
# and/or create a .env with your ModelArk keys + BytePlus credentials

# 3. Run locally
uv run agent.py      # serves on http://0.0.0.0:8000
```

Test the running agent with the AgentKit CLI:

```bash
agentkit invoke '{"prompt": "Write a one-line Monte Carlo estimate of pi."}'
```

## Deploy to BytePlus AgentKit

The `agentkit` CLI (v0.5.3+) is **fully YAML-driven**: the `.agentkit/agentkit.yaml` file is the source of truth for a deployment — region, runtime sizing, environment variables, container registry, TOS, and optional frontend/auth/IM blocks. `agentkit deploy` reads everything from it; no flags are required.

From inside the sample folder:

```bash
# Scaffold the deploy manifest (run once)
agentkit deploy --provider byteplus --region ap-southeast-1 --name <lowercase-app-name>

# Edit .agentkit/agentkit.yaml:
#   - set repo_name to a lowercase CR name
#   - fill in the envs: block with ${VAR} references resolved from your .env
#     (MODEL_AGENT_API_KEY, MODEL_IMAGE_API_KEY, etc.)

# Deploy
agentkit deploy
```

Key points specific to BytePlus:

- **CR repo names must be lowercase** (`[a-z0-9]`, plus `.`/`_`/`-`). The CLI does not normalize case — name it lowercase yourself.
- **Declare each runtime env var explicitly** in the `envs:` block with `${VAR}`. The CLI resolves `${VAR}` from your local `.env` at deploy time; it no longer auto-injects every `.env` variable. The runtime itself runs under an **IAM role** — your BytePlus AK/SK are used for deploy-time resources only, not injected into the runtime.
- **Redeploy after code changes** with `agentkit deploy` (or `agentkit launch` on older CLI versions).

The scaffolded `agentkit.yaml` is heavily commented and covers runtime, `envs:`, infrastructure, and optional frontend/auth/IM blocks — keep it as a reference once generated (it is gitignored by default because it references secrets via `${VAR}`).

## Repository layout

```plaintext
.
├── multi_agents/                     # multi-agent orchestration (seq/parallel/loop)
├── sandbox_tool_sample/              # run_code sandbox tool
├── migrate-from-adk/                 # Google ADK → VeADK migration (image scoring)
├── langchain_agent_deploy_sample/    # LangChain agent on AgentKit
├── use-cases/
│   ├── ad_video_gen_seq/             # sequential marketing-video pipeline
│   ├── rag_with_vikingdb/            # RAG + long-term memory + MCP
│   ├── simple_image_video_gen/       # minimal image→video agent
│   ├── tiktok_ref_video_gen/         # reference-style product video director
│   └── video_gen/                    # YAML-driven story-to-video
└── .gitignore                        # ignores .env, config.yaml, .agentkit/, .tmp/, etc.
```

## Notes for adapting your own samples

If you are porting another sample from [bytedance/agentkit-samples](https://github.com/bytedance/agentkit-samples) to BytePlus, the changes typically required are:

1. **Endpoints** — replace `ark.cn-beijing.volces.com` with `ark.ap-southeast.bytepluses.com`; replace Volcengine TOS/Viking endpoints with their BytePlus (`*.bytepluses.com`) equivalents.
2. **SDK packages** — swap `volcengine-python-sdk` / `volcenginesdkcore` for `byteplussdkcore` and friends where the sample uses a BytePlus service directly.
3. **Model IDs** — keep the same Doubao/Seedream/Seedance family IDs; they resolve on the BytePlus ModelArk gateway.
4. **Credentials** — use BytePlus AK/SK and a BytePlus region. The runtime uses an IAM role, so you usually only need AK/SK for local dev and deploy.
5. **Language** — translate prompts, descriptions, docstrings, and user-facing strings to English so the sample is usable internationally.

## License

Each sample retains its original Apache 2.0 license header. See the `LICENSE` headers in individual files. This repository is provided as-is for reference and is intended to be shared with colleagues and customers.
