#!/bin/bash
# Refresh the Shopizer admin JWT in the nginx gateway config (tokens last 7 days).
TOKEN=$(curl -s -X POST http://127.0.0.1:8081/api/v1/private/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin@shopizer.com","password":"password"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))')
if [ -n "$TOKEN" ]; then
  sed -i "s|proxy_set_header Authorization \"Bearer [^\"]*\";|proxy_set_header Authorization \"Bearer $TOKEN\";|" /etc/nginx/conf.d/shopizer-gw.conf
  nginx -t && systemctl reload nginx
fi
