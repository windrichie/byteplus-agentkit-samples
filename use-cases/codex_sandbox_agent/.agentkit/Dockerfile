# No `# syntax=` directive and a provider-hosted base, so cloud builds
# (which can't reach Docker Hub) work. The base also ships `uv`.
FROM agentkit-prod-public-ap-southeast-1.cr.bytepluses.com/base/py-simple:python3.12-bookworm-slim-latest

# Hermetic build: all Python deps are vendored in wheels/ (linux/amd64, cp312
# - see README "Vendored wheels"). The BytePlus Code Pipeline environment has
# no pypi egress, so the image installs nothing from the network.
ENV PYTHONPATH=/app/wheels PYTHONUNBUFFERED=1
WORKDIR /app
COPY wheels/ ./wheels/
COPY . .

# The runtime probes :8000 for readiness - agent.py serves there (PORT env).
EXPOSE 8000
CMD ["python", "agent.py"]
