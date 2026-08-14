#!/usr/bin/env python3
"""Send a prompt to the Shop Ops Copilot (/run_sse) and print a readable trace:
tool calls (name + args), then the agent's final answer.

Usage:
  python3 ask_copilot.py "your question" [session_id] [base_url]

Defaults: session_id=demo, base_url=http://127.0.0.1:8000 (local dev server).
For the cloud runtime use `agentkit invoke shop-ops-copilot -m "..."` instead.
"""
import json
import sys
import urllib.request
import uuid

PROMPT = sys.argv[1] if len(sys.argv) > 1 else "List our products with prices and stock."
SESSION = sys.argv[2] if len(sys.argv) > 2 else "demo"
BASE = (sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:8000").rstrip("/")

# Ensure the session exists (fresh id each run avoids state bleed between runs)
if SESSION == "demo":
    SESSION = "demo-" + uuid.uuid4().hex[:8]
req = urllib.request.Request(
    f"{BASE}/apps/shop_ops_copilot/users/ops/sessions/{SESSION}",
    data=b"{}", headers={"Content-Type": "application/json"})
urllib.request.urlopen(req, timeout=15)

payload = {
    "app_name": "shop_ops_copilot",
    "user_id": "ops",
    "session_id": SESSION,
    "new_message": {"role": "user", "parts": [{"text": PROMPT}]},
    "streaming": False,
}
req = urllib.request.Request(
    f"{BASE}/run_sse", data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Accept": "text/event-stream"})

final_text = []
with urllib.request.urlopen(req, timeout=300) as r:
    for raw in r:
        line = raw.decode().strip()
        if not line.startswith("data:"):
            continue
        try:
            evt = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        for part in (evt.get("content") or {}).get("parts") or []:
            if "functionCall" in part:
                fc = part["functionCall"]
                print(f"\n>>> TOOL CALL: {fc.get('name')}({json.dumps(fc.get('args', {}))[:200]})")
            elif "functionResponse" in part:
                fr = part["functionResponse"]
                print(f"<<< TOOL RESP: {fr.get('name')} -> {json.dumps(fr.get('response', {}))[:200]}")
            elif part.get("text"):
                final_text.append(part["text"])

print("\n===== ANSWER =====")
print("".join(final_text) if final_text else "(no text answer)")
