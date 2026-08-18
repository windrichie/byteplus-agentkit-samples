"""Shared Agent Identity helpers for the payslip homework sample.

Three pieces, all talking to BytePlus Agent Identity (veIdentity) in
ap-southeast-1:

1. `id_api_client()`      - management client (byteplussdkid), signed with
                            BYTEPLUS_ACCESS_KEY / SECRET_KEY. Used to provision
                            the user pool / users / namespace / policy and to
                            call CheckPermission (the Cedar PDP).
2. `initiate_auth()`      - USER_PASSWORD_AUTH against a user pool, minting
                            real id/access tokens for a user (how the demo gets
                            tokens for alice and bob without a browser).
3. `PoolJwtVerifier`      - local JWT verification against the pool's JWKS
                            (signature + issuer + expiry + client). The
                            in-agent fallback for "who is calling" when the
                            platform gateway does not forward verified claims.

Endpoint/URL conventions verified against the sibling sample
`inbound_auth_jwt/` (adapted from the official workshop notebook).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import string

import requests

REGION = os.getenv("BYTEPLUS_REGION", "ap-southeast-1")
ID_ENDPOINT = f"id.{REGION}.bytepluses.com"


# ---------------------------------------------------------------------------
# Management client (byteplussdkid)
# ---------------------------------------------------------------------------

def id_api_client():
    """A byteplussdkid.IDApi signed with the BytePlus AK/SK from the env."""
    import byteplussdkcore
    import byteplussdkid

    configuration = byteplussdkcore.Configuration()
    configuration.region = REGION
    configuration.ak = os.environ["BYTEPLUS_ACCESS_KEY"]
    configuration.sk = os.environ["BYTEPLUS_SECRET_KEY"]
    return byteplussdkid.IDApi(byteplussdkcore.ApiClient(configuration))


def check_permission(
    *,
    namespace: str,
    principal_id: str,
    resource_id: str,
    principal_type: str = "user",
    operation_type: str = "action",
    operation_id: str = "invoke",
    resource_type: str = "tool",
) -> bool:
    """Ask the Identity Cedar PDP: may <principal> do <operation> on <resource>?

    Mirrors veadk.integrations.ve_identity.IdentityClient.check_permission
    (which wraps the Volcengine SDK); here we use the BytePlus SDK directly.
    Returns True on permit, False on deny OR on any API failure (fail closed).
    """
    import byteplussdkid

    client = id_api_client()
    request = byteplussdkid.CheckPermissionRequest(
        namespace_name=namespace,
        principal={"Type": principal_type, "Id": principal_id},
        operation={"Type": operation_type, "Id": operation_id},
        resource={"Type": resource_type, "Id": resource_id},
    )
    try:
        response = client.check_permission(request)
    except Exception as exc:  # fail closed: an PDP error must not grant access
        print(f"[identity] CheckPermission error (denying): {exc}")
        return False
    allowed = bool(getattr(response, "allowed", False))
    print(
        f"[identity] CheckPermission ns={namespace} "
        f"user={principal_id} {operation_id} {resource_type}:{resource_id} "
        f"-> {'ALLOW' if allowed else 'DENY'}"
    )
    return allowed


# ---------------------------------------------------------------------------
# User-pool token minting (InitiateAuth, USER_PASSWORD_AUTH)
# ---------------------------------------------------------------------------

def pool_auth_base_url(pool_id: str) -> str:
    return f"https://userpool-{pool_id}.userpool.auth.{ID_ENDPOINT}"


def discovery_url_for(pool_id: str) -> str:
    return f"{pool_auth_base_url(pool_id)}/.well-known/openid-configuration"


def initiate_auth(
    *,
    pool_id: str,
    client_id: str,
    username: str,
    password: str,
    client_secret: str | None = None,
) -> dict:
    """Mint tokens for a pool user via USER_PASSWORD_AUTH.

    Returns the AuthenticationResult dict (AccessToken / IdToken /
    RefreshToken / ExpiresIn ...). Raises on HTTP error.
    """
    auth_parameters = {"USERNAME": username, "PASSWORD": password}
    if client_secret:
        digest = hmac.new(
            client_secret.encode(), f"{username}{client_id}".encode(), hashlib.sha256
        ).digest()
        auth_parameters["SECRET_HASH"] = base64.b64encode(digest).decode()

    response = requests.post(
        f"{pool_auth_base_url(pool_id)}/api/v1/InitiateAuth",
        json={
            "AuthFlow": "USER_PASSWORD_AUTH",
            "AuthParameters": auth_parameters,
            "ClientId": client_id,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["Result"]["AuthenticationResult"]


def decode_jwt_payload(token: str) -> dict:
    """Decode WITHOUT verification (display/debug only)."""
    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload + padding).decode())
    except Exception:
        return {}


def generate_password(length: int = 16) -> str:
    """Pool password policy: upper + lower + digit + special."""
    chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    chars += [
        secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*")
        for _ in range(length - 4)
    ]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


# ---------------------------------------------------------------------------
# Local JWT verification (in-agent fallback for caller identity)
# ---------------------------------------------------------------------------

class PoolJwtVerifier:
    """Verify pool-issued JWTs against the pool JWKS.

    Checks signature, issuer, expiry; accepts the token when `aud` OR
    `client_id` is one of the allowed app clients (id tokens carry `aud`,
    access tokens Cognito-style carry `client_id`).
    """

    def __init__(self, discovery_url: str, allowed_clients: list[str]):
        import jwt  # PyJWT

        metadata = requests.get(discovery_url, timeout=10).json()
        self.issuer = metadata["issuer"]
        self._jwks = jwt.PyJWKClient(metadata["jwks_uri"])
        self.allowed_clients = set(allowed_clients)

    def verify(self, token: str) -> dict:
        """Return the verified claims, or raise (PyJWT exceptions)."""
        import jwt  # PyJWT

        signing_key = self._jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            issuer=self.issuer,
            options={"verify_aud": False},  # aud shape differs id vs access token
        )
        token_client = claims.get("aud") or claims.get("client_id")
        if isinstance(claims.get("aud"), list):
            ok = bool(set(claims["aud"]) & self.allowed_clients)
        else:
            ok = token_client in self.allowed_clients
        if not ok:
            raise jwt.InvalidTokenError(f"client {token_client!r} not allowed")
        return claims
