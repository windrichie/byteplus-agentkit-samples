#!/usr/bin/env bash
# Verify the legacy app is API-key protected (nginx gate on the VM) and that the
# valid key unlocks both public AND admin endpoints (admin JWT injected by nginx).
# Expect: 401 without key, 401 with wrong key, 200 / 200 with the real key.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env.local; set +a

BASE="${LEGACY_APP_BASE_URL:-http://shopizer-api.wind.cloudpeek.xyz:8080}"
KEY="${LEGACY_APP_API_KEY:?set LEGACY_APP_API_KEY (the X-API-Key nginx expects)}"

check() { # label expect url [key]
  local label="$1" expect="$2" url="$3" key="${4:-}"
  local args=(-s -m 15 -o /dev/null -w "%{http_code}")
  [ -n "$key" ] && args+=(-H "X-API-Key: $key")
  local code
  code=$(curl "${args[@]}" "$url")
  local mark="OK"; [ "$code" = "$expect" ] || mark="FAIL"
  printf "%-4s %-55s expect=%s got=%s\n" "$mark" "$label" "$expect" "$code"
}

check "no key -> public endpoint rejected"        401 "$BASE/api/v1/products?count=1"
check "wrong key -> rejected"                     401 "$BASE/api/v1/products?count=1" "wrong-key"
check "valid key -> public endpoint"              200 "$BASE/api/v1/products?count=1" "$KEY"
check "valid key -> admin endpoint (JWT injected)" 200 "$BASE/api/v1/private/customers?count=1" "$KEY"
