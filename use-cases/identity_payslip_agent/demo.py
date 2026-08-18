"""Run the homework acceptance matrix against the payslip agent.

    python demo.py                      # all four rows, local agent on :8000
    python demo.py --row 3              # just one row (recording-friendly)
    python demo.py --base-url https://<runtime-apigw-endpoint>   # deployed

Rows:
  1. no token          -> 401
  2. expired token     -> 401 (short-lived client, waits out the 60s TTL)
  3. alice (permitted) -> 200, payslip data
  4. bob  (denied)     -> chat works, tool call 403

Reads pool/client/user coordinates from .env.identity (written by
setup_identity.py).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.identity")

from identity_utils import decode_jwt_payload, initiate_auth  # noqa: E402

PROMPT = "Show me the payslip for employee E1002, please."


def banner(text: str) -> None:
    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}")


def mint(username: str, password: str, *, shortlived: bool = False) -> str:
    suffix = "SHORTLIVED_" if shortlived else ""
    auth = initiate_auth(
        pool_id=os.environ["IDENTITY_POOL_ID"],
        client_id=os.environ[f"IDENTITY_{suffix}CLIENT_ID"],
        client_secret=os.environ[f"IDENTITY_{suffix}CLIENT_SECRET"],
        username=username,
        password=password,
    )
    token = auth["IdToken"]
    claims = decode_jwt_payload(token)
    print(
        f"minted id_token for {username}: sub={claims.get('sub')} "
        f"exp in {claims.get('exp', 0) - claims.get('iat', 0)}s"
    )
    return token


def invoke(base_url: str, prompt: str, token: str | None = None) -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/invoke",
            headers=headers,
            json={"prompt": prompt},
            timeout=120,
        )
        body = resp.text if len(resp.text) < 1500 else resp.text[:1500] + " …[truncated]"
        return resp.status_code, body
    except requests.RequestException as exc:
        return -1, str(exc)


def show(status: int, body: str) -> None:
    print(f"HTTP {status}")
    try:
        parsed = json.loads(body)
        # AgentkitSimpleApp wraps the entrypoint's return value as a JSON
        # string; unwrap one level so structured results read cleanly.
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except ValueError:
                pass
        print(json.dumps(parsed, indent=2)[:1200] if not isinstance(parsed, str) else parsed)
    except ValueError:
        print(body)


def row1(base_url: str) -> None:
    banner("ROW 1 - bare call, no token (expect 401)")
    status, body = invoke(base_url, PROMPT)
    show(status, body)


def row2(base_url: str, wait: bool = True) -> None:
    banner("ROW 2 - expired token (expect 401)")
    token = mint("alice", os.environ["ALICE_PASSWORD"], shortlived=True)
    claims = decode_jwt_payload(token)
    ttl = max(claims.get("exp", 0) - int(time.time()), 0)
    if wait and ttl > 0:
        print(f"waiting {ttl + 5}s for the token to expire …")
        time.sleep(ttl + 5)
    status, body = invoke(base_url, PROMPT)
    show(status, body)


def row3(base_url: str) -> None:
    banner("ROW 3 - alice is in the Cedar policy (expect 200 + payslip)")
    token = mint("alice", os.environ["ALICE_PASSWORD"])
    status, body = invoke(base_url, PROMPT, token)
    show(status, body)


def row4(base_url: str) -> None:
    banner("ROW 4 - bob is NOT in the policy (expect chat OK, tool 403)")
    token = mint("bob", os.environ["BOB_PASSWORD"])
    print("\n-- 4a. plain chat, no tool needed --")
    status, body = invoke(base_url, "Hi! What can you help me with?", token)
    show(status, body)
    print("\n-- 4b. now ask for a payslip --")
    status, body = invoke(base_url, PROMPT, token)
    show(status, body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("AGENT_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--row", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--no-wait", action="store_true",
                        help="row 2: don't wait for expiry (token already stale)")
    args = parser.parse_args()

    rows = {1: row1, 3: row3, 4: row4}
    print(f"target: {args.base_url}")
    if args.row:
        if args.row == 2:
            row2(args.base_url, wait=not args.no_wait)
        else:
            rows[args.row](args.base_url)
        return 0
    row1(args.base_url)
    row2(args.base_url, wait=not args.no_wait)
    row3(args.base_url)
    row4(args.base_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
