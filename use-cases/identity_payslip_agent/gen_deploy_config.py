"""Expand agentkit.yaml (${VAR} placeholders) into agentkit.local.yaml.

The 0.52.5+ CLI does not interpolate env vars in the config file, and secrets
must never live in committed files — so the committed agentkit.yaml is a
template, and this script resolves the placeholders from .env + .env.identity
(both git-ignored) into agentkit.local.yaml (also git-ignored):

    uv run --no-sync python gen_deploy_config.py
    agentkit deploy --config-file agentkit.local.yaml
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).parent
TEMPLATE = HERE / "agentkit.yaml"
OUT = HERE / "agentkit.local.yaml"


class MissingVarsError(Exception):
    pass


MARKER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand(text: str) -> str:
    # Only expand dollar-brace markers that name real env vars; leave the
    # CLI's own {{account_id}} / {{timestamp}} macros untouched.
    missing = sorted({m for m in MARKER.findall(text) if m not in os.environ})
    if missing:
        raise MissingVarsError(
            "missing env vars: " + ", ".join(missing)
            + " — source .env and .env.identity (run setup_identity.py first)"
        )
    return MARKER.sub(lambda match: os.environ[match.group(1)], text)


def main() -> int:
    load_dotenv(HERE / ".env")
    load_dotenv(HERE / ".env.identity")
    try:
        rendered = expand(TEMPLATE.read_text())
    except MissingVarsError as exc:
        print(f"error: {exc}")
        return 1
    OUT.write_text(rendered)
    print(f"wrote {OUT.name} (git-ignored; contains resolved secrets - do not commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
