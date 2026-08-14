#!/usr/bin/env bash
# Raw MCP handshake against the MCP Gateway: initialize -> initialized ->
# tools/list -> tools/call (one public op + one admin op through the hosted
# outbound credential). No agent involved — this isolates the gateway layer.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'EOF'
import json, urllib.request

env = {}
for line in open('.env.local'):
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        env[k] = v.strip('"')

URL, KEY = env['MCP_GATEWAY_URL'], env['MCP_GATEWAY_API_KEY']

def call(payload):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={
        'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read().decode() or '{}')

s, d = call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-03-26", "capabilities": {},
    "clientInfo": {"name": "verify-script", "version": "0.1"}}})
print(f"initialize        -> {s}  server: {d['result']['serverInfo']['name']}")

s, _ = call({"jsonrpc": "2.0", "method": "notifications/initialized"})
print(f"initialized notif -> {s}")

s, d = call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
tools = [t['name'] for t in d['result']['tools']]
print(f"tools/list        -> {s}  {len(tools)} tools: {', '.join(sorted(tools))}")

for i, (name, args) in enumerate([
        ("list_products", {"count": 3}),          # public storefront op
        ("list_customers", {"count": 3})], 3):    # admin op — needs outbound credential
    s, d = call({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                 "params": {"name": name, "arguments": args}})
    text = d['result']['content'][0]['text']
    preview = json.loads(text)['_body'] if text.startswith('{') else text
    print(f"tools/call {name:<16} -> {s}  {json.dumps(preview)[:140]}")
EOF
