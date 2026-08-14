# MCP Gateway service — console configuration steps

Volcengine console → AgentKit → Gateway (网关) → MCP services (MCP 服务).

## 1. Create the MCP service from the API file

1. **Create MCP service** → import mode **API file / HTTP 转 MCP**.
2. Upload `swagger/shopizer-gateway-flat.json` (NOT the non-flat variant — the
   importer rejects `$ref`/`components`; see README Gotcha §1).
3. Backend service (后端服务):
   - Protocol: `http`
   - Domain: `shopizer-api.wind.cloudpeek.xyz` (your DNS → the VM)
   - Port: `8080`
   - The spec's `paths` already carry the full `/api/v1/...` prefix — do NOT add a
     path prefix in the backend config (double-prefix → 404 on every tool call).
4. After creation, the service exposes a **Streamable HTTP** endpoint:
   `https://<id>.apigateway-cn-beijing.volceapi.com/mcp` ← this is `MCP_GATEWAY_URL`.

## 2. Inbound auth ( callers → gateway )

- Enable **API-Key** inbound auth on the service, create a key.
- Callers send `Authorization: Bearer <key>` ← this is `MCP_GATEWAY_API_KEY`.

## 3. Outbound credential ( gateway → legacy app ) — 凭据托管

The legacy app sits behind an nginx gate that requires `X-API-Key`
(see `nginx-shopizer-gw.conf`). Host that key in credential management:

1. 凭据管理 → **新建 API Key**:
   - API Key 名称: `win-shopizer-api-key`
   - API Key 值: the static key nginx expects — charset is restricted to
     `[A-Za-z0-9!@#$%_-]`, so a JWT or `Bearer ` prefix is NOT accepted here.
   - 加密方式: **凭据托管（托管存储）**
   - 参数位置: `Header`
   - 参数名称: `X-API-Key`
   - Prefix: **empty**
2. Attach it as the MCP service's **outbound credential** (出站凭据).
   Every tool call then carries `X-API-Key`; nginx validates it and injects the
   real Shopizer admin JWT (`Authorization: Bearer …`) before proxying to the app.

Resulting trust chain: agent knows only the MCP key; the API key lives in the
gateway's credential hosting; the admin JWT never leaves the VM.

## 4. Verify

```bash
../verify/03-mcp-gateway.sh
# initialize -> 200, tools/list -> 17 tools,
# tools/call list_products (public op) and list_customers (admin op) both return data
```
