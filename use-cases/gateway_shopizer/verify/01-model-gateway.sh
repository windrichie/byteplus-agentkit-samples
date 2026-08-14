#!/usr/bin/env bash
# Verify the Model Gateway proxies LLM calls (OpenAI-compatible chat completion).
# Expect: HTTP 200 with a chat completion JSON.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env.local; set +a

BASE="${MODEL_GATEWAY_BASE_URL:-https://si0oek5vkdg5ks57m8l1l.apigateway-cn-beijing.volceapi.com/ark}"
MODEL="${MODEL_NAME:-deepseek-v4-flash-ga-260731}"

echo "== POST $BASE/chat/completions (model: $MODEL)"
curl -s -m 60 -o /tmp/mg_resp.json -w "HTTP %{http_code}\n" -X POST "$BASE/chat/completions" \
  -H "Authorization: Bearer $MODEL_GATEWAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"Reply with exactly: gateway ok\"}]}"
python3 -c "
import json
d = json.load(open('/tmp/mg_resp.json'))
print('model:', d.get('model'))
print('reply:', d['choices'][0]['message']['content'][:120])
"
