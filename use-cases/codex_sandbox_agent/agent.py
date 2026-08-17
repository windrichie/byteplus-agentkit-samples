"""One-shot code factory — a VeADK dispatcher agent that drives the codex
runtime of an AgentKit CodeEnv sandbox.

Architecture:
    User → this agent (VeADK, local)
             ├── Model calls → BytePlus ModelArk (deepseek by default)
             └── Tool calls  → agentkit CLI → AgentKit CodeEnv sandbox
                                  └── codex CLI writes & runs the code in the
                                      isolated cloud sandbox; artifacts are
                                      pulled back to ./output/ via scp

The model key used by codex inside the sandbox is baked into the sandbox tool
at creation time (`agentkit sandbox create --model-api-key …`) — this agent
never sees it.

Configuration is env-driven (see .env.example):
    MODEL_NAME / MODEL_AGENT_API_BASE / MODEL_AGENT_API_KEY  dispatcher model
    SANDBOX_TOOL_ID              CodeEnv sandbox tool id (required)
    SANDBOX_SESSION_ID           sandbox session name (default: agent)
    CODEX_TIMEOUT_S              per-codex-run timeout (default: 900)
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# Behind TLS-intercepting corporate networks, certifi's bundle doesn't trust
# the corp root CA and ModelArk calls fail with CERTIFICATE_VERIFY_FAILED.
# truststore makes Python use the OS trust store (same fix as uv --native-tls).
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

from veadk import Agent, Runner
from veadk.memory.short_term_memory import ShortTermMemory

from agentkit.apps import AgentkitAgentServerApp

from sandbox_codex import codex_write_code, download_project, run_in_sandbox

logger = logging.getLogger(__name__)

app_name = "code_factory_dispatcher"

INSTRUCTION = """You are a coding-task orchestrator. You turn natural-language coding
requests into working, tested code by driving a codex runtime that lives in an
isolated AgentKit cloud sandbox. You never write or run code yourself — codex
does, inside the sandbox.

Workflow for every coding request:
1. Rewrite the request into a precise implementation brief for codex: what to
   build, which files to create, and how to verify it (exact test/build
   command). Then call codex_write_code with that brief.
2. Call run_in_sandbox with the verification command (e.g. `python -m pytest
   -q`) for the same task_slug.
3. If verification fails, call codex_write_code AGAIN with the same task_slug
   and a repair brief that includes the failing output. At most 3 total
   rounds.
4. When verification passes (or rounds are exhausted), call download_project
   and report: what was built, the test command + result, the download
   location, and the notable files. The tool result contains either a
   local_path (local run) or a share.url (cloud run) - report whichever you
   get; if it's a URL, tell the user it expires and to download soon. If it
   still fails after 3 rounds, download anyway and say so honestly.

Rules:
- Keep the same task_slug across all rounds of one request.
- Codex often creates a Python .venv in the task dir; the sandbox's default
  `python` does NOT see its packages. Run tests with the venv interpreter,
  e.g. `.venv/bin/python -m pytest -q`.
- Prefer Python-standard-library-only solutions unless the user asks
  otherwise; the sandbox may not have every third-party package installed.
- Keep your final answer short: outcome, tests, download path or URL."""

agent: Agent = Agent(
    name=app_name,
    model_name=os.getenv("MODEL_NAME", "deepseek-v3-2-251201"),
    model_api_base=os.getenv("MODEL_AGENT_API_BASE"),
    model_api_key=os.getenv("MODEL_AGENT_API_KEY"),
    description="One-shot code factory: dispatches coding tasks to a codex runtime in an AgentKit sandbox",
    instruction=INSTRUCTION,
    tools=[codex_write_code, run_in_sandbox, download_project],
)

runner = Runner(agent=agent, app_name=app_name)
root_agent = agent

agent_server_app = AgentkitAgentServerApp(
    agent=agent,
    short_term_memory=ShortTermMemory(backend="local"),
)

if __name__ == "__main__":
    agent_server_app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
