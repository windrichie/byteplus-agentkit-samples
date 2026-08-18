"""Discover which Cedar dialect the CheckPermission PDP actually evaluates.

A wildcard permit(principal, action, resource) already ALLOWs, so the
plumbing works; this probe isolates WHICH entity position mismatches by
constraining one position at a time, then composes the winners into a final
policy and verifies alice=ALLOW / bob=DENY.

    python probe_permission.py
"""

from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.identity")

import byteplussdkid  # noqa: E402

from identity_utils import check_permission, id_api_client  # noqa: E402

NAMESPACE = os.environ.get("PERMISSION_NAMESPACE", "payslip-hw")
ALICE_SUB = os.environ["ALICE_SUB"]
BOB_SUB = os.environ["BOB_SUB"]
TOOL = "get_payslip"
PROPAGATION_S = 5

# Single-position probes: (label, cedar constraint for that position or None)
PRINCIPAL_VARIANTS = [
    ("user::sub", f'principal == user::"{ALICE_SUB}"'),
    ("user::username", 'principal == user::"alice"'),
    ("User::sub", f'principal == User::"{ALICE_SUB}"'),
]
ACTION_VARIANTS = [
    ('Action::"invoke"', 'action == Action::"invoke"'),
    ('action::"invoke"', 'action == action::"invoke"'),
]
RESOURCE_VARIANTS = [
    ("tool::get_payslip", f'resource == tool::"{TOOL}"'),
    ("Tool::get_payslip", f'resource == Tool::"{TOOL}"'),
]


def make_policy(client, name: str, cedar: str) -> None:
    client.create_policy(
        byteplussdkid.CreatePolicyRequest(
            namespace_name=NAMESPACE, policy_name=name,
            policy=cedar, description="temporary dialect probe",
        )
    )
    time.sleep(PROPAGATION_S)


def drop_policy(client, name: str) -> None:
    try:
        client.delete_policy(
            byteplussdkid.DeletePolicyRequest(namespace_name=NAMESPACE, policy_name=name)
        )
    except Exception as exc:
        print(f"  WARNING: cleanup of {name} failed: {exc}")


def probe_one(client, name: str, cedar: str) -> bool:
    print(f"  policy: {cedar}")
    make_policy(client, name, cedar)
    allowed = check_permission(namespace=NAMESPACE, principal_id=ALICE_SUB,
                               resource_id=TOOL)
    print(f"  -> alice allowed: {allowed}")
    drop_policy(client, name)
    return allowed


def sweep(client, title: str, variants: list[tuple[str, str]]) -> str | None:
    """Constrain one position, wildcard the rest. Return winning constraint."""
    print(f"\n== {title} ==")
    winner = None
    for i, (label, constraint) in enumerate(variants):
        clauses = {"principal": "principal", "action": "action", "resource": "resource"}
        position = constraint.split(" ")[0]
        clauses[position] = constraint
        cedar = f'permit({clauses["principal"]}, {clauses["action"]}, {clauses["resource"]});'
        if probe_one(client, f"probe-sweep-{title[:3]}-{i}", cedar):
            print(f"  WINNER: {label}")
            winner = constraint
        if winner:
            break
    if not winner:
        print(f"  no {title} variant matched")
    return winner


def main() -> int:
    client = id_api_client()

    principal = sweep(client, "principal position", PRINCIPAL_VARIANTS)
    action = sweep(client, "action position", ACTION_VARIANTS)
    resource = sweep(client, "resource position", RESOURCE_VARIANTS)

    print("\n== summary ==")
    print(f"  principal: {principal or 'NO MATCH'}")
    print(f"  action:    {action or 'NO MATCH'}")
    print(f"  resource:  {resource or 'NO MATCH'}")
    if not all([principal, action, resource]):
        print("\nAt least one position never matched - inspect the namespace"
              " in the Identity console to see what entities it expects.")
        return 1

    cedar = f"permit(\n    {principal},\n    {action},\n    {resource}\n);"
    print(f"\n== combined policy ==\n{cedar}")
    make_policy(client, "probe-combined", cedar)
    alice = check_permission(namespace=NAMESPACE, principal_id=ALICE_SUB,
                             resource_id=TOOL)
    bob = check_permission(namespace=NAMESPACE, principal_id=BOB_SUB,
                           resource_id=TOOL)
    drop_policy(client, "probe-combined")
    print(f"  alice allowed: {alice} (expect True)")
    print(f"  bob allowed:   {bob} (expect False)")
    if alice and not bob:
        print("\nDIALECT FOUND - update CEDAR_POLICY_TEMPLATE in setup_identity.py to:")
        print(cedar)
        return 0
    print("\nCombined policy misbehaves despite individual matches - unexpected.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
