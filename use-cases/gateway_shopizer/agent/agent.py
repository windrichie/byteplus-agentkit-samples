"""Shop Ops Copilot — VeADK agent for the AgentKit Gateway homework.

An enterprise ops/admin copilot for the Shopizer legacy e-commerce backend.

Architecture:
    User → AgentKit Runtime (this agent)
             ├── Model calls → AgentKit **Model Gateway** (proxy key, HA/fallback)
             └── Tool calls  → AgentKit **MCP Gateway** (Shopizer Swagger → MCP,
                               API-key inbound, credential hosting outbound)

Configuration is entirely env-driven (see .env.example):
    MODEL_NAME               LLM id served via the Model Gateway
    MODEL_GATEWAY_BASE_URL   Model Gateway endpoint (OpenAI-compatible base)
    MODEL_GATEWAY_API_KEY    Model Gateway proxy API key
    MCP_GATEWAY_URL          MCP Gateway service/toolset URL (must contain /mcp or /sse)
    MCP_GATEWAY_API_KEY      MCP Gateway API key (optional if service is open)
"""

import logging
import os
import sys

from dotenv import load_dotenv

# Load agent-local .env first, then the project-level .env.local (shared secrets)
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env.local"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from veadk import Agent, Runner
from veadk.memory.short_term_memory import ShortTermMemory

from agentkit.apps import AgentkitAgentServerApp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# VeADK 1.1.1 + google-adk 2.x compatibility shim (deadlock fix)
#
# veadk's TrustedMcpSessionManager.create_session() acquires
# `self._session_lock` and then calls super().create_session() — which in
# google-adk >= 2.x acquires the SAME non-reentrant asyncio.Lock again.
# Result: startup hangs forever at "Initialize MCP session".
# The x-trusted-mcp code path we lose here is only used for Volcengine's
# internal TrustedMCP headers, which the AgentKit MCP Gateway does not need
# (plain Bearer API key). Verified against the live gateway.
# ---------------------------------------------------------------------------
from google.adk.tools.mcp_tool.mcp_session_manager import (
    MCPSessionManager as _ADKMCPSessionManager,
)
from veadk.tools.mcp_tool.trusted_mcp_session_manager import (
    TrustedMcpSessionManager as _TrustedMcpSessionManager,
)

_TrustedMcpSessionManager.create_session = _ADKMCPSessionManager.create_session

# ---------------------------------------------------------------------------
# mcp SDK 1.26 client-side outputSchema validation — disable.
#
# The MCP Gateway derives a strict outputSchema per tool from the legacy app's
# Swagger and wraps responses as {"_body": ...}. But this is a LEGACY app:
# Springfox-generated schemas declare fields as non-null objects/strings that
# the real API routinely returns as null (e.g. product.type, category.parent).
# Every tool call then dies client-side with "Invalid structured content".
# The raw JSON is perfectly usable by the model, so we skip the validation.
# (Spec-side alternative: strip response schemas before gateway import.)
# ---------------------------------------------------------------------------
from mcp.client.session import ClientSession as _MCPClientSession


async def _skip_tool_result_validation(self, name, result):
    return None


_MCPClientSession._validate_tool_result = _skip_tool_result_validation

# ---------------------------------------------------------------------------
# Short-term memory — local backend (no external DB needed for dev)
# ---------------------------------------------------------------------------
short_term_memory = ShortTermMemory(backend="local")

# ---------------------------------------------------------------------------
# Tools — Shopizer MCP toolset via the AgentKit MCP Gateway
# ---------------------------------------------------------------------------
def build_tools() -> list:
    """Attach the MCP Gateway toolset if its URL is configured.

    Kept lazy/optional so the agent still boots (and can be smoke-tested)
    before the MCP service is created.
    """
    mcp_url = os.getenv("MCP_GATEWAY_URL", "").strip()
    if not mcp_url:
        logger.warning("MCP_GATEWAY_URL not set — agent starts WITHOUT Shopizer tools.")
        return []

    from veadk.utils.mcp_utils import get_mcp_params
    from veadk.tools.mcp_tool.trusted_mcp_toolset import TrustedMcpToolset

    mcp_api_key = os.getenv("MCP_GATEWAY_API_KEY", "").strip() or None
    connection_params = get_mcp_params(mcp_url, api_key=mcp_api_key)
    toolset = TrustedMcpToolset(connection_params=connection_params)
    logger.info("Attached Shopizer MCP toolset from %s", mcp_url)
    return [toolset]


# ---------------------------------------------------------------------------
# Shop Ops Copilot
# ---------------------------------------------------------------------------
OPS_COPILOT_INSTRUCTION = """\
You are **Shop Ops Copilot**, an operations assistant for the team running a
Shopizer-based e-commerce store. You speak to store operators, merchandisers
and support leads — not to shoppers.

You access the store's backend exclusively through the MCP tools provided to
you (these map 1:1 to the Shopizer REST API). Never invent data: if you need
numbers, call the tools.

## What you can do
1. **Order operations** — list and filter orders, look up an order by ID,
   report its status, items, totals and history; find orders for a customer.
2. **Sales analysis** — aggregate order data to answer questions like
   "how did we do this week": order count, revenue, average order value,
   best-selling products, status breakdown. When the raw API returns pages,
   paginate until you have enough data, and state the time window you used.
3. **Catalog management** — search/list products and categories, check stock
   (quantity) and prices, and when asked, create or update products
   (name, sku, price, quantity, description). Confirm destructive or
   write operations with a short summary of what you changed.
4. **Customer 360** — look up customers, list their orders, and compute
   simple aggregates (order count, total spend, last order date).

## Guidelines
- Prefer precise answers backed by tool calls over guesses. If a tool call
  fails or returns empty, say so plainly and suggest why.
- Money: report amounts with the store currency when known.
- When listing many records, summarize first (counts, totals), then show a
  compact table of the most relevant rows (max ~10) unless asked for more.
- For "today/this week/this month" questions, state the exact date range you
  used in the answer.
- Some admin APIs require elevated credentials; if a call returns 401/403,
  explain that the operation needs admin authorization.
- Keep answers concise and operational: lead with the answer, then evidence.
"""

agent = Agent(
    name="shop_ops_copilot",
    model_name=os.getenv("MODEL_NAME", "deepseek-v4-flash-ga-260731"),
    model_api_key=os.getenv("MODEL_GATEWAY_API_KEY", ""),
    model_api_base=os.getenv(
        "MODEL_GATEWAY_BASE_URL",
        "https://si0oek5vkdg5ks57m8l1l.apigateway-cn-beijing.volceapi.com/ark",
    ),
    description=(
        "Operations copilot for a Shopizer e-commerce backend: order status, "
        "sales analysis, catalog management and customer 360 — powered by "
        "AgentKit Model Gateway (LLM) and MCP Gateway (legacy API as tools)."
    ),
    instruction=OPS_COPILOT_INSTRUCTION,
    tools=build_tools(),
)

root_agent = agent

runner = Runner(agent=agent, app_name="shop-ops-copilot")

agent_server_app = AgentkitAgentServerApp(
    agent=agent,
    short_term_memory=short_term_memory,
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    logger.info("Starting Shop Ops Copilot on http://0.0.0.0:%s", port)
    agent_server_app.run(host="0.0.0.0", port=port)
