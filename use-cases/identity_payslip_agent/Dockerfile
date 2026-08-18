# Custom Dockerfile - the AgentKit CLI manages only files carrying its
# AUTO-GENERATED header; this file is intentionally header-less so the CLI
# leaves it alone.
#
# Hermetic build: all Python deps are vendored in wheels/ (linux/amd64, cp312
# - see README "Vendored wheels"). The BytePlus Code Pipeline environment has
# no pypi egress, so a plain `uv pip install -r requirements.txt` in the
# generated Dockerfile fails ~20s into the cloud build. No `# syntax=`
# directive and a provider-hosted base image, because cloud builds can't
# reach Docker Hub either.
FROM agentkit-prod-public-ap-southeast-1.cr.bytepluses.com/base/py-simple:python3.12-bookworm-slim-latest

ENV PYTHONPATH=/app/wheels PYTHONUNBUFFERED=1
WORKDIR /app
COPY wheels/ ./wheels/
COPY . .

# The runtime probes :8000 for readiness - agent.py serves there (PORT env).
EXPOSE 8000
CMD ["python", "agent.py"]
