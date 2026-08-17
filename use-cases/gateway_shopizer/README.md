# Shop Ops Copilot — Legacy E-commerce Backend × AgentKit Gateway

**Story:** *"AI-enable your existing commerce backend in a day."* A retailer runs a
legacy Shopizer e-commerce backend (Spring Boot, Swagger 2.0, JWT admin auth). Instead
of rewriting it, we put it behind **AgentKit Gateway** and ship an ops/admin copilot
agent (VeADK) that answers questions like *"which products are low on stock?"*,
*"show customer Jane's orders"* — and can even create products — all through the
gateway, with enterprise auth and credentials hosted in the platform.

```
┌────────────┐   chat    ┌──────────────────────────────┐
│   User     ├──────────▶│  Shop Ops Copilot (VeADK)     │
└────────────┘           │  AgentKit Runtime, cn-beijing │
                         └───────┬──────────────┬────────┘
              LLM (proxy key)    │              │  MCP tools (Bearer key)
                                 ▼              ▼
                    ┌────────────────────┐  ┌─────────────────────────┐
                    │  Model Gateway      │  │  MCP Gateway            │
                    │  deepseek-v4-flash  │  │  17 curated tools from  │
                    │  (+ backup model    │  │  Shopizer Swagger       │
                    │   fallback)         │  │  outbound: hosted       │
                    └─────────┬──────────┘  │  credential (X-API-Key) │
                              ▼             └───────────┬─────────────┘
                    Volcengine Ark (real                  ▼
                    key stays hosted)        ┌─────────────────────────────┐
                                             │ nginx gate on VM :8080      │
                                             │  • requires X-API-Key       │
                                             │  • injects admin JWT        │
                                             │  • daily cron refreshes JWT │
                                             └───────────┬─────────────────┘
                                                         ▼
                                            Shopizer container (127.0.0.1:8081)
                                            products / orders / customers / stores
```

The agent's model calls and tool calls **only know gateway endpoints + proxy keys**.
The real LLM supplier key and the legacy app's real credential (admin JWT) are hosted
behind the gateways / at the edge and never reach the agent.

## Homework rubric mapping

| Rubric item | Level | How this sample satisfies it |
|---|---|---|
| Legacy app with industry attributes | 基础 | **Shopizer 3.2.0** (open-source e-commerce: catalog, orders, customers), Docker on a cloud VM, seeded demo data |
| — app protected by API-key auth | 进阶 | **nginx gate** in front of Shopizer: every request needs `X-API-Key`; anonymous → 401 (`verify/02-legacy-app-auth.sh`) |
| Swagger extraction | 基础 | Shopizer serves Swagger 2.0 at `/v2/api-docs`; captured, converted to OpenAPI 3, curated to 17 ops (`swagger/transform_shopizer_spec.py`) |
| — scan code project to auto-generate | 进阶 | (covered by sibling sample / colleague submission; here the app already emitted Swagger) |
| Agent connects via Model Gateway | 基础 | Agent's `model_api_base` = Model Gateway endpoint, `model_api_key` = gateway **proxy key** (`agent/agent.py`) |
| — break primary model → fallback | 进阶 | Backup model configured on the gateway; agent pins ONE model id so failover happens **gateway-side** (see "Fallback demo") |
| Security: credential hosting | 进阶 | Outbound credential (`X-API-Key`) hosted in **凭据托管** on the MCP service; nginx swaps it for the real admin JWT — the JWT never leaves the VM |

## Layout

```
gateway_shopizer/
├── README.md                      ← this file
├── .env.example                   ← required env vars (copy to .env.local)
├── agent/
│   ├── agent.py                   ← VeADK agent (incl. two compat shims — see Gotchas)
│   ├── requirements.txt           ← pinned versions (verified)
│   └── .agentkit/                 ← deploy config (NOT committed — repo-wide convention; regenerate via `agentkit deploy config`)
├── swagger/
│   ├── shopizer-openapi.json      ← raw Swagger 2.0 from the live app (244 paths!)
│   ├── transform_shopizer_spec.py ← curate + sanitize script
│   └── shopizer-gateway-flat.json ← ★ curated 17 ops, fully inlined — THE spec the gateway accepts
├── gateway/
│   ├── mcp-server-config.md       ← console steps (import spec, auth, credentials)
│   ├── nginx-shopizer-gw.conf     ← the API-key + JWT-injection gate (sanitized)
│   └── shopizer-jwt-refresh.sh    ← daily JWT refresh (cron on the VM)
└── verify/
    ├── 01-model-gateway.sh        ← direct chat completion via Model Gateway
    ├── 02-legacy-app-auth.sh      ← 401 without key / 200 with key (incl. admin op)
    ├── 03-mcp-gateway.sh          ← raw MCP handshake + tools/list + tools/call
    └── ask_copilot.py             ← prompt the agent, print tool-call trace + answer
```

## Reproduce

### 0. Prerequisites
- A cloud VM (public IP) with Docker — hosts the "legacy" app.
- AgentKit Gateway enabled (Beta — whitelist) on Volcengine cn-beijing.
- `uv` + Python 3.12 locally; `agentkit` CLI for the cloud deploy.

### 1. Legacy app (Shopizer + nginx API-key gate)
```bash
docker run -d --name shopizer -p 127.0.0.1:8081:8080 --restart unless-stopped \
  shopizerecomm/shopizer:latest
# nginx on :8080 requires X-API-Key and injects the admin JWT — see gateway/nginx-shopizer-gw.conf
# daily cron runs gateway/shopizer-jwt-refresh.sh (Shopizer JWTs live 7 days)
```
Seed data (optional): 4 products (`table1/chair1/chair2/chair3`), categories
Tables/Chairs, one customer. Admin login: `admin@shopizer.com / password`
(Shopizer image default).

### 2. Swagger → gateway-ready spec
```bash
curl -s http://<vm>:8080/v2/api-docs > swagger/shopizer-openapi.json
# convert Swagger 2.0 → OpenAPI 3 (converter.swagger.io), then:
python3 swagger/transform_shopizer_spec.py    # curate 17 ops, sanitize
# then fully inline ALL $refs → shopizer-gateway-flat.json (see Gotchas §1)
```

### 3. MCP Gateway (console) — see `gateway/mcp-server-config.md`
Import `shopizer-gateway-flat.json` → set backend `http://shopizer-api…:8080` →
inbound API-Key auth → **outbound credential** = hosted API key
(header `X-API-Key`). Verify: `verify/03-mcp-gateway.sh`.

### 4. Model Gateway (console)
Create gateway → add model (`deepseek-v4-flash-ga-260731` via Ark) → issue proxy key.
Verify: `verify/01-model-gateway.sh`.

### 5. Run the agent locally
```bash
cp .env.example .env.local   # fill in the 3 keys/URLs
cd agent && uv venv && uv pip install -r requirements.txt --native-tls
uv run agent.py              # serves :8000
python3 ../verify/ask_copilot.py "What products do we sell, with prices and stock?"
```

### 6. Deploy to AgentKit Runtime
```bash
cd agent
export VOLCENGINE_ACCESS_KEY/SECRET_KEY/SESSION_TOKEN   # console STS triple works
set -a; source ../.env.local; set +a
agentkit deploy
agentkit invoke shop-ops-copilot -m "How many products and total stock?"
```

## Fallback demo (进阶) — verified live

Backup model `glm-5-2-260617` is configured on the gateway for primary
`deepseek-v4-flash-ga-260731`. The agent pins exactly ONE model id
(`MODEL_NAME`) — fallback happens gateway-side, not in the SDK.

**Break the primary via the requested model id** (NOT the supplier key — both
models share one Ark Plaza supplier entry, so killing the key/URL kills the
backup too):

1. Runtime config → env var `MODEL_NAME` → a nonexistent id
   (`deepseek-v4-flash-ga-260730`) → release a new version.
2. Runtime logs show the agent passing the wrong id; the agent keeps answering
   in the online test UI (screenshots in `screenshots/fallback-*.png`).
3. Proof of who served: `verify/01-model-gateway.sh` prints the response
   `model` field — `deepseek-v4-flash-ga-260731` for the correct id;
   `MODEL_NAME=deepseek-v4-flash-ga-260730 ./verify/01-model-gateway.sh`
   returns HTTP 200 with `model: glm-5-2-260617` (the backup).
4. Restore: set `MODEL_NAME` back to `deepseek-v4-flash-ga-260731`, release.

## Demo script (ops copilot persona)

| Prompt | Exercises |
|---|---|
| "What products do we sell? Prices and stock in a table." | `list_products`, `get_product_inventory`, `get_store` |
| "Who are our registered customers and where are they located? Any orders yet?" | `list_customers`, `list_orders` |
| "Add 'Walnut Coffee Table', sku table2, $329, qty 150 — check the SKU first, then confirm it's in the catalog." | `check_product_sku_available` → `create_product` → `get_product` (write path!) |
| "How did we do this week — order count and revenue?" | `list_orders` aggregation (honest "no orders" on a fresh store) |

## Gotchas (hard-won)

1. **The MCP importer rejects `$ref`/`components`.** Framework-generated specs
   (Springfox/Springdoc) fail with a generic `InvalidParameter.Config`. You must
   upload a **fully inlined** spec: no `$ref`, no `components`, exactly one response
   per op, JSON/form bodies only, no `type: file`, array params `explode: false`.
   That is what `shopizer-gateway-flat.json` is.
2. **veadk 1.1.1 + google-adk 2.x deadlock.** `TrustedMcpSessionManager` takes a
   non-reentrant asyncio.Lock then calls `super().create_session()` which takes the
   same lock → agent startup hangs at "Initialize MCP session". `agent.py` carries a
   3-line monkeypatch shim.
3. **mcp SDK 1.26 client-side outputSchema validation.** The gateway derives strict
   output schemas from the spec, but the legacy API returns `null` where the schema
   says object → every tool call fails client-side. `agent.py` no-ops
   `_validate_tool_result` (spec-side alternative: strip response schemas).
4. **Outbound credential charset.** The hosted API-key value allows only
   `[A-Za-z0-9!@#$%_-]` — a JWT (dots) or `Bearer ` prefix (space) is rejected. Hence
   the static `X-API-Key` + nginx-side JWT injection.
5. **Shopizer JWTs expire in 7 days** — the VM cron refreshes the injected token
   daily (`shopizer-jwt-refresh.sh`).
6. **Cloud builds can't reach Docker Hub** — the Dockerfile uses the
   provider-hosted base image (scaffolded by `agentkit deploy config`).
7. **Corporate VPN:** CLI needs proxies cleared; `uv pip install` needs `--native-tls`.
