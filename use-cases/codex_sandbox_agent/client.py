"""Local test client for the code-factory dispatcher agent.

Usage:
    uv run --no-sync client.py "Build a Python CLI that converts Markdown to HTML, with pytest tests"

Starts a session against the agent server, streams SSE events, and prints a
readable trace (tool calls + final text). Codex rounds can take many minutes,
so the HTTP timeout is generous. Plain HTTP/JSON — no ADK imports, so it is
robust across google-adk versions.
"""

import json
import os
import sys
import uuid

import httpx

APP_NAME = "code_factory_dispatcher"
BASE_URL = os.getenv("AGENT_BASE_URL", "http://127.0.0.1:8000")
API_KEY = "agentkit test key"
USER_ID = "agentkit_user"
# Fresh session per run — the server 409s on a duplicate session id.
SESSION_ID = f"session-{uuid.uuid4().hex[:8]}"

DEFAULT_PROMPT = (
    "Build a small Python CLI that converts a Markdown file to HTML "
    "(headings, bold, italic, code blocks, links), with pytest tests."
)

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def create_session() -> str:
    resp = httpx.post(
        f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}",
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return SESSION_ID


def render_event(data: dict) -> None:
    """Print tool calls and text parts from one SSE event."""
    content = data.get("content") or {}
    for part in content.get("parts") or []:
        if "functionCall" in part:
            fc = part["functionCall"]
            args = json.dumps(fc.get("args", {}))[:200]
            print(f"\n>>> tool call: {fc.get('name')}({args})")
        elif "functionResponse" in part:
            print("<<< tool response received")
        elif part.get("text"):
            print(part["text"], end="", flush=True)


def run(prompt: str) -> None:
    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": create_session(),
        "new_message": {"role": "user", "parts": [{"text": prompt}]},
        "streaming": True,
    }
    with httpx.stream(
        "POST",
        f"{BASE_URL}/run_sse",
        json=payload,
        headers=HEADERS,
        timeout=1800,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data:"):
                continue
            try:
                render_event(json.loads(line[len("data:"):]))
            except (json.JSONDecodeError, AttributeError):
                continue


if __name__ == "__main__":
    user_prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT
    print(f"[prompt] {user_prompt}\n")
    run(user_prompt)
    print()
