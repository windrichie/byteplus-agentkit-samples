"""Tools that let a VeADK agent drive the codex runtime of an AgentKit sandbox.

Two transports, selected with SANDBOX_BACKEND:

    cli (default) - shell out to the `agentkit` CLI (must be installed and
        authenticated on the host; local dev).
    sdk - talk to the AgentKit tools API + session endpoint directly via the
        agentkit SDK (BYTEPLUS_ACCESS_KEY / BYTEPLUS_SECRET_KEY env vars);
        no CLI binary needed - this is what runs inside AgentKit Runtime.

Three tools are exposed to the agent:

    codex_write_code  — one-shot (or repair-round) implementation by codex
    run_in_sandbox    — run an arbitrary shell command in the task dir (tests…)
download_project  - pull the task dir to ./output/; when TOS_BUCKET is
                        set, also upload the tarball to TOS and return a
                        presigned download URL (cloud runs have no reachable
                        filesystem, so the URL is what the user gets)

Security model: the model API key is baked into the sandbox *tool* at creation
(`agentkit sandbox create --model-api-key …`); every session then gets
CODEX_API_KEY injected by the platform. Neither this agent nor any command
line ever carries a model key.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import uuid

# ---------------------------------------------------------------------------
# Configuration (env-driven; see .env.example)
# ---------------------------------------------------------------------------

PROVIDER = os.getenv("AGENTKIT_PROVIDER", "byteplus")
# NOTE: when running under pyenv/uv, the Python env's bin/ dir leads PATH for
# child processes — if the *Python* agentkit SDK is installed too, plain
# "agentkit" can resolve to the wrong CLI (no `--provider` flag). Set
# AGENTKIT_CLI to the absolute path of the Go CLI in that case.
AGENTKIT_CLI = os.getenv("AGENTKIT_CLI", "agentkit")
# Transport: "cli" shells out to the agentkit CLI (local dev default); "sdk"
# talks to the AgentKit tools API + session endpoint directly via the agentkit
# SDK - no CLI binary needed, which is what makes AgentKit Runtime deploys work.
SANDBOX_BACKEND = os.getenv("SANDBOX_BACKEND", "cli")
TOOL_ID = os.getenv("SANDBOX_TOOL_ID", "")
SESSION_ID = os.getenv("SANDBOX_SESSION_ID", "agent")
WORK_ROOT = os.getenv("SANDBOX_WORK_ROOT", "/home/gem/work")
OUTPUT_ROOT = os.getenv("OUTPUT_DIR", "./output")
CODEX_TIMEOUT_S = int(os.getenv("CODEX_TIMEOUT_S", "900"))
_CMD_GRACE_S = 120  # extra time for CLI polling on top of in-sandbox timeout

# Cloud delivery: AgentKit Runtime has no "send files to the user" feature, so
# when TOS_BUCKET is set, download_project additionally uploads the tarball to
# TOS and returns a presigned download URL (creds: the same BYTEPLUS_* AK/SK
# the SDK backend uses; they sign TOS as well).
TOS_BUCKET = os.getenv("TOS_BUCKET", "")
TOS_REGION = os.getenv("TOS_REGION") or os.getenv("BYTEPLUS_REGION", "ap-southeast-1")
TOS_ENDPOINT = os.getenv("TOS_ENDPOINT", "") or f"tos-{TOS_REGION}.bytepluses.com"
TOS_KEY_PREFIX = os.getenv("TOS_KEY_PREFIX", "codex-factory/")
TOS_URL_EXPIRES_S = int(os.getenv("TOS_URL_EXPIRES_S", "86400"))

_TAIL_CHARS = 4000  # keep tool responses small; codex output can be long


class SandboxError(RuntimeError):
    """Raised when the agentkit CLI or the remote command fails."""


def _require_tool_id() -> str:
    if not TOOL_ID:
        raise SandboxError(
            "SANDBOX_TOOL_ID is not set. Create a CodeEnv sandbox tool first: "
            "agentkit sandbox create --tool-type CodeEnv --tool-name <name> "
            "--cpu 2 --model-api-key <your-model-key>  (see README.md)"
        )
    return TOOL_ID


def _cli(args: list[str], timeout_s: int) -> dict:
    """Run `agentkit --provider <p> sandbox <args>` and return parsed JSON."""
    cmd = [AGENTKIT_CLI, "--provider", PROVIDER, "sandbox", *args]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_s, check=False
        )
    except FileNotFoundError as exc:
        raise SandboxError(f"agentkit CLI not found: {AGENTKIT_CLI}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SandboxError(f"CLI timed out after {timeout_s}s: {' '.join(cmd)}") from exc
    if proc.returncode != 0:
        raise SandboxError(f"CLI failed ({' '.join(cmd)}): {proc.stderr.strip()}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SandboxError(f"CLI returned non-JSON output: {proc.stdout[:500]}") from exc
    if isinstance(payload, dict) and payload.get("success") is False:
        raise SandboxError(f"sandbox call failed: {payload.get('message')}")
    return payload


def _shell(command: str, timeout_s: int) -> dict:
    """Run a command in the sandbox session; return the `data` payload."""
    if SANDBOX_BACKEND == "sdk":
        return _SDK_BACKEND.shell(command, timeout_s)
    payload = _cli(
        [
            "shell",
            "--tool-id",
            _require_tool_id(),
            "--session-id",
            SESSION_ID,
            "--command",
            command,
        ],
        timeout_s,
    )
    return payload.get("data", {})


def _fetch_file(remote_path: str, local_path: str, timeout_s: int = 300) -> None:
    """Pull one file from the sandbox session to a local path."""
    if SANDBOX_BACKEND == "sdk":
        _SDK_BACKEND.fetch_file(remote_path, local_path, timeout_s)
        return
    _cli(
        [
            "scp",
            f"sandbox:{remote_path}",
            local_path,
            "--tool-id",
            _require_tool_id(),
            "--session-id",
            SESSION_ID,
        ],
        timeout_s,
    )


# ---------------------------------------------------------------------------
# SDK backend (for AgentKit Runtime: no agentkit CLI binary in the container)
#
# Session control plane via `agentkit.sdk.tools.AgentkitToolsClient` (signed
# with BYTEPLUS_ACCESS_KEY / BYTEPLUS_SECRET_KEY env vars - or
# ~/.agentkit/config.yaml locally). The created session returns an endpoint
# URL whose query string embeds the authorization, so subsequent exec/file
# calls are plain HTTPS with no signing. Route shapes mirror the CLI's own
# implementations (agentkit.toolkit.cli.sandbox.*).
# ---------------------------------------------------------------------------

_SESSION_TTL_S = int(os.getenv("SANDBOX_TTL_S", "28800"))
_READY_TIMEOUT_S = 120


def _route_url(endpoint: str, route: str) -> str:
    """Append `route` to the endpoint's path, keeping its auth query string."""
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(endpoint.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, f"{path}{route}", parts.query, parts.fragment))


class _SdkBackend:
    def __init__(self) -> None:
        self._endpoint: str | None = None  # cached session endpoint

    def _client(self):
        from agentkit.sdk.tools.client import AgentkitToolsClient

        return AgentkitToolsClient()

    def _ensure_endpoint(self) -> str:
        import time

        if self._endpoint:
            return self._endpoint

        from agentkit.sdk.tools import types as t

        client = self._client()
        listed = client.list_sessions(
            t.ListSessionsRequest(tool_id=_require_tool_id(), page_size=100)
        )
        for info in listed.session_infos or []:
            if info.user_session_id == SESSION_ID and info.endpoint:
                self._endpoint = info.endpoint
                return self._endpoint

        created = client.create_session(
            t.CreateSessionRequest(
                tool_id=_require_tool_id(),
                user_session_id=SESSION_ID,
                ttl=_SESSION_TTL_S,
                ttl_unit="second",
            )
        )
        # Poll until the session is ready (endpoint can lag session creation).
        deadline = time.time() + _READY_TIMEOUT_S
        endpoint, status = created.endpoint, None
        while time.time() < deadline:
            got = client.get_session(
                t.GetSessionRequest(session_id=created.session_id, tool_id=_require_tool_id())
            )
            endpoint, status = got.endpoint or endpoint, got.status
            if status == "ready" and endpoint:
                break
            time.sleep(3)
        if not endpoint:
            raise SandboxError(
                f"sandbox session not ready after {_READY_TIMEOUT_S}s (status={status})"
            )
        self._endpoint = endpoint
        return self._endpoint

    def shell(self, command: str, timeout_s: int) -> dict:
        import requests

        url = _route_url(self._ensure_endpoint(), "/v1/shell/exec")
        body = {"id": "", "exec_dir": "", "command": command}
        try:
            resp = requests.post(url, json=body, timeout=timeout_s)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            # Stale session (TTL expiry etc.) - refresh the endpoint once.
            self._endpoint = None
            url = _route_url(self._ensure_endpoint(), "/v1/shell/exec")
            resp = requests.post(url, json=body, timeout=timeout_s)
            resp.raise_for_status()
            payload = resp.json()
        data = payload.get("data") or {}
        return {"output": data.get("output", ""), "exit_code": data.get("exit_code")}

    def fetch_file(self, remote_path: str, local_path: str, timeout_s: int) -> None:
        import requests

        url = _route_url(self._ensure_endpoint(), "/v1/file/download")
        with requests.get(
            url,
            params={"path": remote_path, "change_policy": "abort"},
            stream=True,
            timeout=timeout_s,
        ) as resp:
            resp.raise_for_status()
            with open(local_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        fh.write(chunk)


_SDK_BACKEND = _SdkBackend()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:40].strip("-") or "task") + "-" + uuid.uuid4().hex[:6]


# Directories codex commonly creates that should never be listed/downloaded
# (a .venv alone can be thousands of files).
_EXCLUDES = (".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules")
_FIND_PRUNE = " -o ".join(f"-path ./{d} -prune" for d in _EXCLUDES)
_TAR_EXCLUDES = " ".join(f"--exclude={d}" for d in _EXCLUDES)


def _tail(text: str, chars: int = _TAIL_CHARS) -> str:
    return text if len(text) <= chars else f"…[truncated {len(text) - chars} chars]\n{text[-chars:]}"


# ---------------------------------------------------------------------------
# Agent tools
# ---------------------------------------------------------------------------


def codex_write_code(task_brief: str, task_slug: str = "") -> dict:
    """Ask the codex runtime inside the AgentKit cloud sandbox to implement a
    coding task. Codex plans, writes, and self-runs the code in the isolated
    sandbox — nothing executes on the local machine.

    Pass the SAME task_slug again for a repair round (codex then continues in
    the existing directory, e.g. to fix failing tests).

    Args:
        task_brief: Precise implementation brief: what to build, which files,
            and how to verify (test command). Include failure output when this
            is a repair round.
        task_slug: Short kebab-case task name for the sandbox working
            directory. Leave empty to auto-generate one.

    Returns:
        dict with task_slug, workdir, exit_code, codex output tail, and the
        list of files codex created.
    """
    slug = task_slug or _slugify(task_brief)
    workdir = f"{WORK_ROOT}/{slug}"

    _shell(f"mkdir -p {shlex.quote(workdir)} && cd {shlex.quote(workdir)} && git init -q", 120)

    run = _shell(
        f"cd {shlex.quote(workdir)} && timeout {CODEX_TIMEOUT_S} codex exec {shlex.quote(task_brief)}",
        CODEX_TIMEOUT_S + _CMD_GRACE_S,
    )
    files = _shell(
        f"cd {shlex.quote(workdir)} && find . {_FIND_PRUNE} -o -type f -print | sort | head -100",
        60,
    )
    return {
        "task_slug": slug,
        "workdir": workdir,
        "exit_code": run.get("exit_code"),
        "codex_output_tail": _tail(run.get("output", "")),
        "files": files.get("output", "").strip().splitlines(),
    }


def run_in_sandbox(command: str, task_slug: str, timeout_s: int = 300) -> dict:
    """Run a shell command inside the sandbox task directory — typically the
    project's test suite or build (e.g. `python -m pytest -q`, `npm test`).

    Args:
        command: Shell command to run inside the task directory.
        task_slug: Task directory returned by codex_write_code.
        timeout_s: Max seconds to wait for the command.

    Returns:
        dict with exit_code and the command output tail.
    """
    workdir = f"{WORK_ROOT}/{task_slug}"
    data = _shell(
        f"cd {shlex.quote(workdir)} && timeout {int(timeout_s)} bash -lc {shlex.quote(command)}",
        int(timeout_s) + _CMD_GRACE_S,
    )
    return {
        "task_slug": task_slug,
        "exit_code": data.get("exit_code"),
        "output_tail": _tail(data.get("output", "")),
    }


def _publish_tarball_to_tos(local_tar: str, task_slug: str) -> dict:
    """Upload the tarball to TOS and presign a download URL.

    Uses the same BYTEPLUS_* AK/SK as the SDK backend (TOS accepts them).
    enable_crc=False because crcmod is deliberately not vendored (source-only
    dist, can't be cross-built for the image; see README).
    """
    import tos  # lazy: part of the veadk dependency closure
    from tos.enum import HttpMethodType

    ak = os.environ["BYTEPLUS_ACCESS_KEY"]
    sk = os.environ["BYTEPLUS_SECRET_KEY"]
    key = f"{TOS_KEY_PREFIX}{task_slug}/{task_slug}.tgz"
    client = tos.TosClientV2(
        ak, sk, TOS_ENDPOINT, TOS_REGION, enable_crc=False,
        socket_timeout=120,
    )
    try:
        client.put_object_from_file(TOS_BUCKET, key, local_tar)
        presigned = client.pre_signed_url(
            HttpMethodType.Http_Method_Get, TOS_BUCKET, key,
            expires=TOS_URL_EXPIRES_S,
        )
    finally:
        client.close()
    return {
        "share": {
            "url": presigned.signed_url,
            "object_key": key,
            "bucket": TOS_BUCKET,
            "expires_s": TOS_URL_EXPIRES_S,
            "note": "presigned URL - download with curl/browser before it expires",
        }
    }


def download_project(task_slug: str) -> dict:
    """Download the finished project from the sandbox to the local
    ./output/<task_slug>/ directory.

    The task dir is tarred sandbox-side (excluding .git/.venv/caches — a venv
    would otherwise be thousands of files), pulled down with
    `agentkit sandbox scp`, and extracted locally.

    Args:
        task_slug: Task directory returned by codex_write_code.

    Returns:
        dict with local_path and the list of downloaded files; in cloud mode
        (TOS_BUCKET set) also a `share` dict with a presigned download URL.
    """
    workdir = f"{WORK_ROOT}/{task_slug}"
    local_dir = os.path.join(OUTPUT_ROOT, task_slug)
    os.makedirs(local_dir, exist_ok=True)

    tarball = f"/tmp/{task_slug}.tgz"
    _shell(
        f"cd {shlex.quote(workdir)} && tar czf {shlex.quote(tarball)} {_TAR_EXCLUDES} .",
        120,
    )
    local_tar = os.path.join(OUTPUT_ROOT, f"{task_slug}.tgz")
    try:
        _fetch_file(tarball, local_tar, 300)
        # cloud delivery first: upload needs local_tar, the extract below
        # works either way (gives the agent a file listing to report)
        shared = _publish_tarball_to_tos(local_tar, task_slug) if TOS_BUCKET else None
        proc = subprocess.run(
            ["tar", "xzf", local_tar, "-C", local_dir],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise SandboxError(f"failed to extract {local_tar}: {proc.stderr.strip()}")
    finally:
        if os.path.exists(local_tar):
            os.remove(local_tar)
        try:
            _shell(f"rm -f {shlex.quote(tarball)}", 60)
        except SandboxError:
            pass

    listing = subprocess.run(
        ["find", local_dir, "-type", "f"],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "task_slug": task_slug,
        "local_path": os.path.abspath(local_dir),
        "files": sorted(line.strip() for line in listing.stdout.splitlines() if line.strip()),
        **(shared or {}),
    }
