# One-Shot Code Factory - VeADK Agent × AgentKit Sandbox (codex runtime)

**Story:** *"Describe the code you want; get back a working, tested mini-project -
without anything ever executing on your machine."* A thin **dispatcher agent**
(VeADK) turns your natural-language request into a precise brief, hands it to the
**codex runtime inside an AgentKit CodeEnv sandbox**, runs the resulting test
suite in the same sandbox, sends failure output back to codex for repair rounds,
and finally delivers the finished project - to `./output/` on a local run, or as
a **presigned download link in chat** when deployed to AgentKit Runtime.

```
you ──prompt──▶ dispatcher agent (VeADK; local OR AgentKit Runtime)
                  model: BytePlus ModelArk (deepseek-v4-pro by default)
                  │
                  ├─ tool: codex_write_code(brief)  ─┐
                  ├─ tool: run_in_sandbox(cmd)       ├─ agentkit SDK ──▶ CodeEnv sandbox
                  └─ tool: download_project(slug)   ─┘        (BytePlus ap-southeast-1)
                                                                  │
                                                          codex CLI writes + runs
                                                          the code; pytest runs in
                                                          the same isolated env
                                                                  │
                  ◀────────── finished project: ./output/<task>/ (local run)
                              or TOS upload -> download link in chat (cloud run)
```

**Why this is interesting**

- **Isolation**: generated code is untrusted by definition - here it is written,
  executed, and tested entirely inside the cloud sandbox. Your laptop only ever
  receives the finished files.
- **Key hygiene**: the model key used by codex is **baked into the sandbox tool
  at creation** (`--model-api-key`). The platform injects it into sessions as
  `CODEX_API_KEY`; the agent and every command line stay key-free.
- **The repair loop is emergent**: three small tools + one instruction - the
  agent itself decides to run tests and send failures back to codex. No loop
  code anywhere.

## What one prompt produces (real example)

Run against the deployed AgentKit Runtime (console online-test), with this
prompt:

> Build a small Python CLI called **md2html** that converts Markdown files to
> self-contained HTML pages. Support headings, bold, italic, inline code,
> fenced code blocks, and links. Give the output an aesthetic, polished,
> modern look - nice typography and colours, with the CSS embedded in the
> generated file. Add pytest tests for every feature. Finally, create a demo
> Markdown file (content of your choice, complex enough to exercise
> everything), run the CLI on it end to end, and produce `demo.html`.

What happened, end to end:

1. `codex_write_code(brief)` - codex planned and implemented the project in an
   isolated task dir inside the sandbox (and self-ran the demo conversion).
2. `run_in_sandbox(".venv/bin/python -m pytest -q")` - the dispatcher verified
   independently: **44 tests, all green** (39 test functions, some parametrized).
3. `download_project(md2html)` - sandbox-side tarball -> upload to TOS ->
   **presigned download link posted in the chat reply** (valid 24h).
4. `curl <link>` -> `md2html.tgz` -> unzip locally. The project runs as-is.

What came back in the archive (72KB) - **shipped in this repo at
[`examples/md2html/`](examples/md2html/) so you can inspect it without
running anything** (open `examples/md2html/demo.html` in a browser; the
shipped files regenerate `demo.html` byte-identically via
`python3 -m md2html demo.md`):

```
md2html/
├── md2html/            ← proper package: converter.py, cli.py, styles.py
├── tests/              ← 44 pytest cases (formatting, links, code, escaping…)
├── demo.md             ← codex-authored demo exercising every feature
├── demo.html           ← the conversion output: self-contained page with
│                          embedded CSS (system font stack, indigo accents)
├── README.md           ← written by codex, usage + features
└── pyproject.toml      ← zero third-party deps - pure stdlib
```

Notable behaviors the agent got right on its own: HTML-escaping user input
(no injection), embedding the stylesheet so `demo.html` is a single portable
file, and staying stdlib-only (a rule from the agent instruction).

A full run takes ~5-10 minutes (codex writes, runs, and self-checks the code).
Keep that in mind with gateways that enforce short request timeouts.

## Layout

```
codex_sandbox_agent/
├── README.md            ← this file
├── agent.py             ← VeADK dispatcher agent (instruction + server)
├── sandbox_codex.py     ← the 3 tools: CLI + SDK backends (shell / fetch / tar / TOS)
├── client.py            ← local test client (SSE stream, readable tool trace)
├── pyproject.toml       ← pinned, verified dependency combo
├── .env.example         ← required env vars
├── examples/md2html/    ← real output of one prompt (see showcase section)
├── wheels/              ← vendored linux/amd64 deps for hermetic cloud builds (git-ignored)
└── .agentkit/           ← AgentKit Runtime deploy scaffold (agentkit.yaml + Dockerfile)
```

## How it works: 3 tools, 1 instruction

The agent instruction (see `agent.py`) fixes a simple protocol:

1. `codex_write_code(brief)` - fresh task dir `work/<slug>`, `git init`, then
   `codex exec "<brief>"` (codex plans, writes, and usually self-runs).
2. `run_in_sandbox("<test command>", slug)` - the dispatcher verifies
   independently instead of trusting codex's self-report.
3. On failure: `codex_write_code(repair brief with the failing output, same
   slug)` - codex continues in the same directory. Max 3 rounds.
4. `download_project(slug)` - sandbox-side tarball (excluding `.git`, `.venv`,
   caches), then either extract to `./output/<slug>/` (local) or upload to TOS
   and return a presigned URL (cloud).

## Run it locally - step by step

**Prerequisites**

1. **agentkit CLI** installed and authenticated for BytePlus -
   `~/.agentkit/config.yaml` with `byteplus.access_key` / `secret_key` and
   `defaults.cloud_provider: byteplus`. Verify: `agentkit --provider byteplus
   whoami`.
2. Python 3.12+ and `uv`.
3. A BytePlus ModelArk API key with access to the dispatcher model.

**Step 1 - create the sandbox tool (one time).** The CodeEnv tool comes with
the codex CLI preinstalled; baking your model key in *at creation* is what
makes later sessions key-free:

```bash
agentkit --provider byteplus sandbox create \
  --tool-type CodeEnv --tool-name codex-one-shot --cpu 2 \
  --model-api-key <your-modelark-api-key> --json
# -> note the tool_id (t-...) in the output
```

Verified behavior (2026-08-17): codex CLI 0.139.0 preconfigured for
`byteplus_model_square` (base URL `https://ark.ap-southeast.bytepluses.com/api/v3`,
`approval_policy="never"`, `sandbox_mode="danger-full-access"` - fully
unattended), sessions receive `CODEX_API_KEY` from the tool config.

> **Cost note:** a sandbox tool provisions cloud compute **while it exists** -
> delete it when done (`sandbox delete --tool-id t-... --force`, see Cleanup).

**Step 2 - configure `.env`.**

```bash
cp .env.example .env
# fill in: MODEL_AGENT_API_KEY, SANDBOX_TOOL_ID, AGENTKIT_CLI (absolute path!)
```

**Step 3 - install and start the agent.**

```bash
uv venv && uv pip install . --native-tls   # --native-tls behind corp VPN
uv run --no-sync agent.py                  # serves :8000 (PORT env to change)
```

**Step 4 - send a task from a second terminal.**

```bash
uv run --no-sync client.py "Build a small Python CLI that converts Markdown to HTML, with pytest tests"
# custom port: AGENT_BASE_URL=http://127.0.0.1:8001 uv run --no-sync client.py "..."
```

The client prints a live trace: `>>> tool call: codex_write_code(...)`,
`run_in_sandbox(.venv/bin/python -m pytest -q)`, possibly a repair round, then
`download_project(...)` and the final summary with the local path
(`./output/<task>/`).

## Deploy to AgentKit Runtime (BytePlus) - step by step

The same agent runs as a managed runtime; the console's online-test (or the
`agentkit invoke` CLI) becomes the front end, and finished projects come back
as TOS download links. The deploy scaffold lives in `.agentkit/`.

**Step 1 - scaffold (already committed here; for a new project).**

```bash
agentkit --provider byteplus deploy config -n codex-factory -r ap-southeast-1 -p default
```

**Step 2 - declare runtime envs** in `.agentkit/agentkit.yaml`. Four groups:

- dispatcher model: `MODEL_NAME`, `MODEL_AGENT_API_BASE`, `MODEL_AGENT_API_KEY`
- sandbox transport: `SANDBOX_BACKEND=sdk` (no agentkit CLI inside the
  runtime image - the SDK talks to the tools API + session endpoint directly),
  `SANDBOX_TOOL_ID`, `SANDBOX_SESSION_ID`, `OUTPUT_DIR=/tmp/output`
- credentials the SDK signs with: `AGENTKIT_CLOUD_PROVIDER`, `BYTEPLUS_REGION`,
  `BYTEPLUS_ACCESS_KEY`, `BYTEPLUS_SECRET_KEY`
- cloud file delivery: `TOS_BUCKET`, `TOS_REGION`, `TOS_URL_EXPIRES_S`

Secrets use `${VAR:?message}` guards - they resolve from your shell at deploy
time, never from the file.

**Step 3 - vendor the wheels (why: the cloud builder has no pypi egress).** A
plain `RUN uv pip install -r requirements.txt` in the Dockerfile fails ~20s
into the cloud build with an opaque `Cloud build did not succeed`. Fix: ship
the full linux/amd64 cp312 closure in `wheels/` (git-ignored, ~637MB unpacked /
~120MB in the build context) and set `PYTHONPATH=/app/wheels` - the build
touches no network. Regenerate with:

```bash
uv lock                                      # then edit: aiohttp==3.12.15, drop crcmod
uv export --frozen --no-hashes -o /tmp/lock.txt
uv pip install --no-deps --native-tls \
  --python-platform x86_64-unknown-linux-gnu --python-version 3.12 \
  --target wheels -r /tmp/lock.txt
```

- **aiohttp** must be pinned `==3.12.15` in the lock (gotcha 8) - otherwise
  uv resolves 3.13+.
- **crcmod** (tos dependency) is source-only and can't be cross-built on a
  mac; it's dropped from the lock. Safe here: veadk imports `tos` lazily and
  uploads run with `enable_crc=False`.

**Step 4 - build the image (no secrets needed; iterate freely).**

```bash
agentkit --provider byteplus deploy build
```

**Step 5 - apply (needs the secret envs).**

```bash
set -a && source .env && set +a
agentkit --provider byteplus deploy apply
# -> Ready - runtime r-... @ https://<api-gateway-url>
```

**Step 6 - talk to it.**

```bash
agentkit --provider byteplus invoke codex_sandbox_agent -m "..."
# or the BytePlus console -> AgentKit -> runtime -> online test
```

Notes from our deployment (runtime `r-yet1cflv5sx9ixql84jw`, image
`agentkit/codex_sandbox_agent:20260817-162624`):

- The endpoint answers `401 key_auth:missing_api_key` to bare curl - always
  invoke through the CLI or console, which resolve endpoint + auth.
- Full tasks run 5-10+ minutes; gateways with short request timeouts may cut
  long runs. A no-tool smoke (`"Reply with exactly: runtime smoke OK"`)
  verifies boot + model connectivity in seconds.
- The runtime needs egress to ModelArk (model calls), the sandbox session
  endpoint, and TOS (artifact upload) - all public endpoints, no VPC setup
  needed.

### Cloud file delivery (TOS + presigned URL)

AgentKit Runtime has no "send files to the user" feature - a cloud
`download_project` would park the tarball in the runtime's `/tmp/output`,
which nobody can reach. Fix: when `TOS_BUCKET` is set, `download_project`
additionally uploads the tarball to TOS and returns a **presigned download
URL** that the agent reports in chat. It reuses the `BYTEPLUS_*` AK/SK already
injected for the SDK backend (TOS accepts the same keys). Default: the
platform-managed bucket (`agentkit-platform-<account-id>`, the same one
`deploy build` auto-ensures) under a `codex-factory/` prefix; point
`TOS_BUCKET`/`TOS_KEY_PREFIX` anywhere you like. URLs expire after
`TOS_URL_EXPIRES_S` (default 24h).

> Alternative considered: `sandbox create --tos-bucket/--tos-mount` mounts a
> TOS bucket into sandbox sessions (platform-native, no runtime code) - but it
> requires recreating the sandbox tool and still gives no in-chat link. The
> presigned-URL approach works with the existing tool and delivers the link
> straight into the conversation. Both can coexist.

## Example prompts

| Prompt | What it exercises |
|---|---|
| The md2html prompt above | the full happy path: brief -> code -> demo run -> tests -> download link (see "What one prompt produces") |
| "Write a URL-shortener Flask app with an in-memory store and tests" | third-party deps; codex creates a sandbox `.venv` |
| "Implement Dijkstra's algorithm with a CLI and property-based tests" | algorithmic task, test-driven repair round likely |
| "The md2html project from earlier should also support tables - fix it in the same task dir" | repair/extend round on an existing `task_slug` |
| "Scaffold a tiny static site and start a server" | then `agentkit sandbox web` to preview it live |

## Gotchas (all hit during development)

1. **Two `agentkit` CLIs can coexist.** If the *Python* agentkit SDK is also
   installed, a pyenv/uv Python process prepends its own `bin/` to PATH for
   child processes - so `subprocess` finds the Python CLI (no `--provider`
   flag) instead of the Go CLI. Set `AGENTKIT_CLI` to the Go CLI's absolute
   path (see `.env.example`).
2. **codex refuses non-git directories.** Sessions inherit
   `trust_level = "trusted"` only for `/home/gem`; per-task dirs need
   `git init -q` (the tools do this for you).
3. **The sandbox's default `python` is not codex's venv.** Codex typically
   creates `.venv/` in the task dir to install pytest etc. Run tests as
   `.venv/bin/python -m pytest -q` (the agent instruction says so).
4. **Never `scp` a task dir raw.** Codex's `.venv` + caches are thousands of
   files; `download_project` tars sandbox-side with excludes first.
5. **Bake the model key at tool creation.** There is no per-`shell` env
   injection; `--model-api-key` on `sandbox create` (or `--model-api-key` on
   `sandbox exec` session creation) is the supported path.
6. **Corp-VPN TLS interception breaks the dispatcher's model calls.**
   `CERTIFICATE_VERIFY_FAILED` against `ark.ap-southeast.bytepluses.com`
   means certifi's bundle doesn't trust the corp root CA. `agent.py` injects
   `truststore` (OS trust store - same fix as `uv --native-tls`, which you
   also need for installs). Relatedly, `uv run` re-syncs and fails the same
   way - use `uv run --no-sync` after the initial install.
7. **veadk/ADK version drift** - `veadk-python==1.1.1` +
   `agentkit-sdk-python==0.8.1` is the combo verified here (unpinned installs
   pulled an ADK needing extra deps).
8. **The Ark ap-southeast edge sends TWO `Server:` headers**
   (`feilian-agw` + `istio-envoy`) and **aiohttp ≥ 3.13 rejects duplicate
   singleton headers** (RFC 9110 hardening) - every model call dies with
   `400 Duplicate 'Server' header found`. Pinned `aiohttp<3.13`.
9. **BytePlus cloud builds have no pypi egress** - `uv pip install` in the
   Dockerfile fails ~20s in with an opaque `Cloud build did not succeed`.
   Vendor wheels in the context instead (see the deploy steps). Note
   `agentkit deploy build` runs *without* your secret envs - you can iterate
   on builds autonomously; only `deploy apply` needs them.
10. **The cloud context archiver only partially respects `.dockerignore`**
   (e.g. it included `output/` despite the entry) - keep the build context
   clean manually; `.env`/`.venv` are excluded by built-in rules.

## Cleanup

```bash
# tear down the AgentKit Runtime deployment (stops runtime charges)
agentkit --provider byteplus destroy codex_sandbox_agent

# delete just the session (keeps the tool; state in the session is lost)
agentkit --provider byteplus sandbox delete --tool-id t-... --session-id agent --force

# delete the whole sandbox tool (stops sandbox charges)
agentkit --provider byteplus sandbox delete --tool-id t-... --force
```

Deletion is irreversible - download anything you need first (`./output/` is
local, so finished projects are already safe).

## License

Apache 2.0
