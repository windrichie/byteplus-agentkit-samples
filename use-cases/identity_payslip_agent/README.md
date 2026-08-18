# Identity Payslip Agent

An HR self-service assistant with exactly **one tool** (`get_payslip`), built to
demonstrate BytePlus **AgentKit Agent Identity & Policy** end to end:

- **入站 Inbound authn**: users log in to an Identity **user pool** (OIDC) and
  call the agent with the resulting **id_token**. The platform JWT authorizer
  at the gateway verifies it against the pool's **JWKS** — no token, forged
  token, or expired token → **401 before any request reaches the agent**.
- **出站 Outbound authz**: inside the tool, the agent calls the Identity
  **CheckPermission** PDP, which evaluates a **Cedar** policy — alice (in the
  policy) gets the payslip; bob (a valid user, not in the policy) can chat
  freely but the tool call is denied (**403**).

Authentication ≠ authorization: rows 1–2 of the demo come free from the
gateway config; rows 3–4 are one Cedar policy + one gated tool.

## The acceptance matrix

| # | Case | Mechanism | Expected |
|---|------|-----------|----------|
| 1 | bare call, no token | gateway JWT authorizer | **401** |
| 2 | expired id_token (60 s TTL client) | gateway JWT authorizer | **401** |
| 3 | alice logs in (in Cedar policy) | CheckPermission → permit | **200 + payslip** |
| 4 | bob logs in (not in policy) | CheckPermission → deny | chat OK, tool **403** |

## Architecture

```
alice/bob ──password──▶ Identity user pool ──id_token (JWT)──┐
                                                             ▼
                                     AgentKit gateway (custom_jwt authorizer,
                                     verifies signature/issuer/expiry/aud
                                     against pool JWKS) ── bad token ──▶ 401
                                                             ▼ good token
                                     Runtime: agent.py (VeADK + deepseek)
                                       └── tool get_payslip(employee_id)
                                             └── CheckPermission PDP
                                                 Cedar policy in namespace
                                                 "payslip-hw":
                                                   permit(principal == user::"<alice-sub>",
                                                          action == action::"invoke",
                                                          resource == tool::"get_payslip");
                                                   ├── alice → ALLOW → payslip JSON
                                                   └── bob   → DENY  → 403 JSON
```

## Files

| File | Purpose |
|------|---------|
| `agent.py` | VeADK agent + `AgentkitSimpleApp`; verifies the Bearer token (or trusts platform-forwarded identity), gates `get_payslip` with CheckPermission |
| `identity_utils.py` | Shared helpers: IDApi client, `check_permission` (fail-closed), user-pool auth (`initiate_auth` + SECRET_HASH), `PoolJwtVerifier` (PyJWT + JWKS) |
| `setup_identity.py` | Idempotent provisioning: pool, two app clients (one with 60 s token TTL), alice/bob users, Cedar namespace + policy; ends with a live PDP smoke check (alice=ALLOW, bob=DENY) |
| `probe_permission.py` | Cedar dialect discovery tool: position-isolation sweep of principal/action/resource entity types against the live PDP |
| `demo.py` | Runs the 4-row acceptance matrix against a local or deployed agent |
| `gen_deploy_config.py` | Expands `agentkit.yaml` (template with `${VAR}` placeholders) into git-ignored `agentkit.local.yaml` |
| `agentkit.yaml` / `Dockerfile` | Deploy config template (custom_jwt inbound) + hermetic image build |
| `deploy_expect.sh` | best-effort expect script for the CLI's interactive prompts (flaky — answering manually is more reliable) |
| `SUBMISSION.md` / `screenshots/` | Console-step walkthrough of the whole setup + the 4-row demo, with the console screenshots |

## Quickstart (local)

```bash
uv venv && uv pip install . --native-tls   # --native-tls behind corp VPN
cp .env.example .env                        # fill in BYTEPLUS AK/SK + MODEL_AGENT_API_KEY

# 1. Provision Identity (pool, clients, users, namespace, Cedar policy).
#    Writes .env.identity; self-verifies alice=ALLOW / bob=DENY at the end.
set -a && source .env && set +a
uv run --no-sync python setup_identity.py

# 2. Run the agent
uv run --no-sync python agent.py            # serves on :8000 (PORT env to override)

# 3. Run the acceptance matrix (in another shell)
uv run --no-sync python demo.py --row 1     # no token -> 401 payload
uv run --no-sync python demo.py --row 2     # expired token -> 401 payload (waits ~65 s)
uv run --no-sync python demo.py --row 3     # alice -> payslip
uv run --no-sync python demo.py --row 4     # bob -> chat OK, tool 403
```

Locally the 401s arrive as a JSON payload in the response body (the local
server has no gateway in front); deployed, rows 1–2 are real transport-level
401s from the gateway authorizer.

## Deploy to AgentKit Runtime

```bash
# 1. Vendor the linux/amd64 wheels (cloud builders have no pypi egress)
uv lock --native-tls
uv export --frozen --no-hashes --native-tls -o /tmp/lock.txt
# drop crcmod (source-only, can't cross-build; only needed by tos uploads)
grep -v "^crcmod==" /tmp/lock.txt > /tmp/lock2.txt && mv /tmp/lock2.txt /tmp/lock.txt
uv pip install --no-deps --native-tls \
  --python-platform x86_64-unknown-linux-gnu --python-version 3.12 \
  --target wheels -r /tmp/lock.txt

# 2. Generate the deploy config (resolves ${VAR} from .env + .env.identity)
uv run --no-sync python gen_deploy_config.py     # writes agentkit.local.yaml

# 3. Build + deploy in one shot (the new CLI splits build/deploy; `launch`
#    does both). Answer "Yes" when it asks "Continue without enabling
#    services?" — the prompt cancels on non-TTY stdin, so run it yourself.
set -a && source .env && set +a
~/.agentkit/agentkit launch --config-file agentkit.local.yaml

# 4. Run the matrix against the deployed endpoint
uv run --no-sync python demo.py --base-url https://<runtime-endpoint> --row 1
```

Deployed instance (from `agentkit launch` on 2026-08-18): runtime
`r-yet4n3p43kx9ixqlbyua` (`identity_payslip_agent-momi0yhe`), endpoint
`https://sui6hlpmntvaq86nqld8o.apigateway-ap-southeast-1.apigw-byteplus.com`.
All four matrix rows verified against it; SUBMISSION.md Part C reproduces
them step by step with `agentkit invoke run` + `curl`.

The `custom_jwt` settings in `agentkit.yaml` attach the platform JWT
authorizer to the runtime's gateway — that **is** the inbound half of the
homework; no agent code changes are needed for rows 1–2.

**What the gateway forwards** (from runtime logs): with `custom_jwt`, the
gateway passes the original `authorization` header through to the container
intact, plus platform metadata (`x-forward-consumer`, `x-user-account-id`,
`x-agent-resource-*`, tracing headers). There is no forwarded-sub header —
so the agent's `via=jwks-self-verify` path is the one that runs, verifying
the token itself against the pool JWKS.

## Gotchas (learned the hard way)

1. **Cedar entity types must match the CheckPermission request's `Type`
   fields verbatim.** The docs show `permit(principal == user::"alice",
   action == Action::"invoke", resource == agent::"trip_agent")` — capitalized
   `Action::` is what the console / Permission Gateway PEP sends. The raw SDK
   `check_permission` sends `Type: "action"` (lowercase), so the policy must
   say `action::"invoke"`. `probe_permission.py` finds the dialect
   empirically: a wildcard `permit(principal, action, resource)` first
   (structural sanity), then one constrained position at a time.
2. **JWT `sub` == user pool `uid`** (verified on minted tokens), so policies
   can key principals on either — this sample uses `sub`.
3. **The 0.52.5 CLI** wants `agentkit.yaml` at the project root (schema:
   `common.agent_name`, `launch_types.cloud.*`), does **not** interpolate
   `${VAR}`, and its deploy prompt cancels on non-TTY stdin — hence
   `gen_deploy_config.py` and `deploy_expect.sh`.
4. **Never commit `runtime_envs` with real keys** (an older sample in this
   repo does — don't copy that). The template + generated
   `agentkit.local.yaml` (git-ignored) keeps secrets out of git.
5. **aiohttp must stay at 3.12.x** (`[tool.uv] override-dependencies`):
   3.13+ rejects the Ark edge's duplicate `Server:` header and every model
   call dies with 400.
6. **Cloud builds have no pypi egress** — vendor the full wheel closure into
   `wheels/` (git-ignored, ~700 MB) and set `PYTHONPATH=/app/wheels`. The
   custom `Dockerfile` intentionally has no AUTO-GENERATED header so the CLI
   leaves it alone.
7. **`CheckPermission` fails closed** in `identity_utils.py`: any PDP error
   (network, signing, namespace) becomes DENY, never ALLOW.

## Security notes

- `.env`, `.env.identity`, `agentkit.local.yaml`, `wheels/` are git-ignored.
  `agentkit.yaml` (committed) contains only placeholders.
- alice/bob passwords are generated by `setup_identity.py` (or taken from
  `ALICE_PASSWORD`/`BOB_PASSWORD` env) and stored only in `.env.identity`.
- The agent never logs token values — only header *names* and token claims
  after verification.
