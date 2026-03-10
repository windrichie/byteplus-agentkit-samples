# TikTok Reference Product Video Generator

An AgentKit use-case that automatically generates TikTok Shop product videos (≤30 seconds) by studying a reference TikTok video and applying its style, pacing, and structure to your own product.

## Overview

Provide a reference TikTok URL, a product image, and optional customization instructions — the agent handles the rest: downloading and analyzing the reference video, studying the product, planning a storyboard, generating scene keyframes and video clips, and stitching everything into a final polished video uploaded to TOS.

```text
User Input (reference URL + product image + instructions)
    ↓
Director Agent
    ├── download_tiktok_video     — Download reference video
    ├── upload_to_tos             — Host files on TOS (for AI model access)
    ├── analyze_reference_video   — VLM: extract style, pacing, hook strategy
    ├── analyze_product_image     — VLM: identify product & scene suggestions
    ├── [Storyboard Planning]     — Agent designs 3–4 scenes
    ├── image_generate            — Seedream: generate per-scene keyframes
    ├── video_generate            — Seedance: animate each keyframe
    ├── file_download             — Download clips locally for assembly
    └── mergeVideos (MCP)         — Stitch clips → upload final video to TOS
```

## Core Features

- **Reference Video Analysis**: Uses a vision model to deeply analyze the reference TikTok — hook strategy, camera movements, pacing, lighting, and scene structure.
- **Product-Aware Storyboarding**: Analyzes the product image and adapts the reference video's style into a 3–4 scene storyboard tailored to the product.
- **Reference-Based Image Generation**: Uses Seedream's `single_image_to_single` mode to generate scene keyframes that faithfully preserve the product's appearance.
- **Video Animation**: Animates each keyframe into a 5-second clip using Seedance 1.5 Pro in 9:16 vertical format.
- **Local Video Assembly**: Downloads all clips locally and merges them using the `video-clip-mcp` MCP tool (requires ffmpeg).
- **TOS Hosting**: All intermediate and final assets are hosted on BytePlus TOS, returning a signed URL for easy sharing.
- **Revision Support**: The agent preserves context between turns — you can ask it to regenerate specific scenes without re-running the full workflow.

## Agent Capabilities

| Component | Description |
|-----------|-------------|
| **Director Agent** | [`agent.py`](agent.py) — Main orchestrator; coordinates all tools |
| **System Prompt** | [`prompts.py`](prompts.py) — Full workflow instructions and tool usage rules |
| **Custom Tools** | [`tools/`](tools/) — All project-specific tool implementations |
| **Vision Client** | [`utils/seed_client.py`](utils/seed_client.py) — HTTP client for BytePlus ModelArk Vision API (with retry) |
| **MCP Integration** | `@pickstar-2002/video-clip-mcp` — Local video stitching via ffmpeg |

### Tools

| Tool | Source | Description |
|------|--------|-------------|
| `download_tiktok_video` | custom | Downloads a TikTok video locally using yt-dlp |
| `upload_to_tos` | custom | Uploads a local file to TOS; returns a pre-signed URL |
| `analyze_reference_video` | custom | Sends video to vision model; returns structured JSON analysis |
| `analyze_product_image` | custom | Sends product image to vision model; returns product profile |
| `image_generate` | veadk built-in | Generates Seedream keyframes via `single_image_to_single` |
| `video_generate` | custom wrapper | Animates keyframes using Seedance; fixes `generate_audio=false` being dropped |
| `file_download` | custom | Batch-downloads remote files to local storage |
| `mergeVideos` | MCP | Stitches local video files together |
| `clipVideo` | MCP | Trims a local video clip |
| `getVideoInfo` | MCP | Reads duration/metadata of a local video |

> **Note on `video_generate` wrapper**: `tools/video_generate.py` is a custom wrapper around the veadk built-in to fix a bug where `generate_audio=False` is silently dropped. The built-in's `_should_disable_audio` converts `False` to `None`, causing the field to be omitted from the request — and Seedance generates audio by default when the field is absent. See [`video_generate_debug/`](../../video_generate_debug/) for a full reproduction.

## Quick Start

### Prerequisites

#### 1. Node.js + ffmpeg (required for video assembly)

```bash
# Install Node.js 18+ (https://nodejs.org/en)
# Verify:
node --version
npx --version

# Install ffmpeg (required by video-clip-mcp)
brew install ffmpeg        # macOS
# sudo apt install ffmpeg  # Ubuntu/Debian
```

The MCP tool (`@pickstar-2002/video-clip-mcp`) is launched automatically at runtime via `npx` — no manual installation needed for local use.

#### 2. BytePlus Credentials

- **AK/SK**: [BytePlus Console](https://console.byteplus.com) → Access Control → Users → Keys
- **ModelArk API Key**: [BytePlus ModelArk Console](https://console.byteplus.com/ark) → Create API Key
- **Enable models**:
  - Root agent: `deepseek-v3-2-251201`
  - Image generation: `seedream-4-5-251128` (or newer)
  - Video generation: `seedance-1-5-pro-251215` (or newer)
  - Vision analysis: `seed-2-0-mini-260215` (used by `seed_client.py`)

### Install Dependencies

```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

cd use-cases/tiktok_ref_video_gen

# Create virtual environment and install
uv venv --python 3.12
source .venv/bin/activate
uv sync
```

### Configure Credentials

Copy the example config and fill in your credentials:

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your AK/SK and API keys
```

**`config.yaml` fields:**

```yaml
byteplus:
  access_key: "<Your BytePlus Access Key>"
  secret_key: "<Your BytePlus Secret Key>"
  region: "ap-southeast-1"

model:
  agent:
    name: "deepseek-v3-2-251201"
    api_base: "https://ark.ap-southeast.bytepluses.com/api/v3/"
    api_key: "<Your Ark API Key>"
  video:
    name: "seedance-1-5-pro-251215"
    api_base: "https://ark.ap-southeast.bytepluses.com/api/v3/"
    api_key: "<Your Ark API Key>"
  image:
    name: "doubao-seedream-4-5-251128"
    api_base: "https://ark.ap-southeast.bytepluses.com/api/v3/"
    api_key: "<Your Ark API Key>"
```

You can also use environment variables instead of `config.yaml`:

```bash
export BYTEPLUS_ACCESS_KEY=<your_ak>
export BYTEPLUS_SECRET_KEY=<your_sk>
export DATABASE_TOS_BUCKET=agentkit-platform-<your_account_id>
export MODEL_AGENT_API_KEY=<your_ark_api_key>
export MODEL_IMAGE_API_KEY=<your_ark_api_key>
export MODEL_VIDEO_API_KEY=<your_ark_api_key>
```

**TOS Bucket:** The default bucket is `agentkit-platform-<your_account_id>` where `<your_account_id>` is your numeric BytePlus account ID (e.g., `agentkit-platform-3000087550`).

## Local Debugging

### Method 1: veadk web (Recommended)

`veadk web` provides a browser-based chat UI with full tool call and thought process visibility.

```bash
# Run from the parent directory (use-cases/) using the project venv's veadk
cd use-cases/
../use-cases/tiktok_ref_video_gen/.venv/bin/veadk web

# Open http://localhost:8000 in your browser
# Select the "tiktok_ref_video_gen" agent and start chatting
```

> **Important**: Run `veadk web` from the **parent** directory (`use-cases/`), not from inside `tiktok_ref_video_gen/`. VeADK scans subdirectories to discover agents.
>
> **Version pitfall**: If you have veadk installed globally via pyenv, `veadk web` may pick up an older version (e.g. 0.2.29) instead of the project's 0.5.25+. Always use the project venv's binary directly (`.venv/bin/veadk web`) or verify with `which veadk` that it points to the `.venv`.

### Method 2: Direct API

Start the agent server:

```bash
cd use-cases/tiktok_ref_video_gen
uv run agent.py
# Listens on http://0.0.0.0:8000 by default
```

#### Step 1: Create a Session

```bash
curl --request POST 'http://localhost:8000/apps/tiktok_ref_video_gen/users/u_123/sessions/s_001' \
  --header 'Content-Type: application/json'
```

#### Step 2: Send a Message

```bash
curl 'http://localhost:8000/run_sse' \
  --header 'Content-Type: application/json' \
  --data '{
    "appName": "tiktok_ref_video_gen",
    "userId": "u_123",
    "sessionId": "s_001",
    "newMessage": {
      "role": "user",
      "parts": [{
        "text": "Reference video: https://www.tiktok.com/@example/video/123\nProduct image: https://example.com/product.jpg\nInstructions: Energetic style, highlight the sole design"
      }]
    },
    "streaming": true
  }'
```

### Method 3: Test Client

```bash
# Edit client.py to set your reference URL and product image, then:
uv run client.py
```

### Example Prompt

```
Reference video: https://www.tiktok.com/@sneakerstore/video/7xxxxxxxxxxxxxxxxx
Product image: https://example.com/blue-running-shoes.jpg
Instructions: Keep it under 20 seconds, focus on the heel design, energetic upbeat style
```

**Expected workflow:**
1. Downloads and uploads reference TikTok video to TOS
2. Downloads and uploads product image to TOS
3. Analyzes reference video structure and style
4. Analyzes product for scene suggestions
5. Plans a 3–4 scene storyboard
6. Generates keyframe images (Seedream, reference-based)
7. Animates each keyframe into a 5s clip (Seedance)
8. Downloads all clips locally
9. Merges clips and uploads final video to TOS
10. Returns a signed URL for the final video

## AgentKit Cloud Deployment

### Step 0: Install AgentKit CLI

```bash
pip install 'agentkit-sdk-python>=0.5.1'
# or
uv pip install 'agentkit-sdk-python>=0.5.1'
```

### Step 1: Configure BytePlus Credentials

```bash
# Option A: Global config (recommended)
agentkit config --global --set byteplus.access_key=<your_ak>
agentkit config --global --set byteplus.secret_key=<your_sk>

# Option B: Environment variables
export BYTEPLUS_ACCESS_KEY=<your_ak>
export BYTEPLUS_SECRET_KEY=<your_sk>
```

### Step 2: Enter the Project Directory

```bash
cd use-cases/tiktok_ref_video_gen
```

### Step 3: Configure Deployment

```bash
agentkit config \
  --agent_name tiktok_ref_video_gen \
  --entry_point 'agent.py' \
  --cloud_provider byteplus \
  --region ap-southeast-1 \
  --runtime_envs DATABASE_TOS_BUCKET=agentkit-platform-<your_account_id> \
  --launch_type cloud
```

If you do not want to bundle API keys into the package, set them as runtime env vars/secrets in the AgentKit console or in `agentkit.yaml` instead of `config.yaml`:

```bash
# Set secrets via CLI
agentkit config --set runtime_envs.MODEL_AGENT_API_KEY=<your_key>
agentkit config --set runtime_envs.MODEL_IMAGE_API_KEY=<your_key>
agentkit config --set runtime_envs.MODEL_VIDEO_API_KEY=<your_key>
```

### Step 4: Pre-install video-clip-mcp at Build Time (Optional but Recommended)

To avoid slow `npx` downloads at runtime, pre-install the MCP package in the Docker image:

```bash
# Create the scripts directory and setup script
mkdir -p scripts
cat > scripts/setup.sh << 'EOF'
#!/bin/bash
echo "Installing @pickstar-2002/video-clip-mcp..."
npm install -g @pickstar-2002/video-clip-mcp@latest
EOF
chmod +x scripts/setup.sh
```

Then edit `agentkit.yaml` to include:

```yaml
docker_build:
  build_script: "scripts/setup.sh"
```

### Step 5: Deploy

```bash
agentkit launch
```

### Test the Deployed Agent

#### Via AgentKit Console

1. Open the [BytePlus AgentKit Console](https://console.byteplus.com/agentkit)
2. Go to **Runtime** and locate `tiktok_ref_video_gen`
3. Click the debug/chat entry to test interactively

#### Via CLI

```bash
agentkit invoke '{"prompt": "Reference video: https://www.tiktok.com/@x/video/123\nProduct image: https://example.com/product.jpg"}'
```

#### Via API

Get your runtime endpoint and API key from the AgentKit console, then:

```bash
# Create session
curl --request POST '<runtime_endpoint>/apps/tiktok_ref_video_gen/users/u_123/sessions/s_001' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: <your_api_key>'

# Send message
curl '<runtime_endpoint>/run_sse' \
  --header 'Authorization: <your_api_key>' \
  --header 'Content-Type: application/json' \
  --data '{
    "appName": "tiktok_ref_video_gen",
    "userId": "u_123",
    "sessionId": "s_001",
    "newMessage": {
      "role": "user",
      "parts": [{
        "text": "Reference video: https://www.tiktok.com/@x/video/123\nProduct image: https://example.com/product.jpg"
      }]
    },
    "streaming": false
  }'
```

## Directory Structure

```
tiktok_ref_video_gen/
├── agent.py                    # Director Agent — entry point and tool registration
├── prompts.py                  # Full system prompt with workflow instructions
├── client.py                   # Test client for local development
├── config.yaml.example         # Config template (copy to config.yaml)
├── pyproject.toml              # Project metadata and dependencies (uv)
├── requirements.txt            # Python dependencies (pip)
├── tools/
│   ├── __init__.py
│   ├── download_tiktok.py      # Download TikTok videos via yt-dlp
│   ├── upload_to_tos.py        # Upload files to TOS; return signed URL
│   ├── analyze_reference.py    # VLM analysis of reference video
│   ├── analyze_product.py      # VLM analysis of product image
│   ├── image_generate.py       # (unused) Custom wrapper kept as fallback
│   ├── video_generate.py       # Custom wrapper: Seedance with generate_audio fix
│   └── file_download.py        # Batch download remote files locally
├── utils/
│   └── seed_client.py          # BytePlus ModelArk Vision API client (with retry logic)
└── downloads/                  # Runtime download directory (auto-created)
```

## FAQ

**`npx` command not found**
- Install Node.js 18+ from https://nodejs.org/en and ensure `npx` is on your PATH.

**`ffprobe`/`ffmpeg` not found (MCP tool error)**
- The `video-clip-mcp` tool requires system ffmpeg. Install with:
  `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Linux)

**TOS upload / access errors**
- Verify `BYTEPLUS_ACCESS_KEY` and `BYTEPLUS_SECRET_KEY` are set correctly (BytePlus AK/SK).
- Check that `DATABASE_TOS_BUCKET` matches your actual bucket name including account ID.

**Reference image not applied to generated images**
- Ensure you are running veadk >= 0.5.25. Older versions (e.g. 0.2.29) silently drop the `image` parameter from the API request. Check with: `python -c "from veadk.version import VERSION; print(VERSION)"`
- If using `veadk web`, verify it picks up the correct version — pyenv shims may resolve to an older global install. Use the project venv's binary directly: `.venv/bin/veadk web`

**Generated video has Chinese audio**
- Audio generation is disabled by default (`generate_audio: false`). If you see Chinese audio, check that the agent is not overriding this default. Only set `generate_audio: true` if you explicitly want audio.

**`analyze_reference_video` times out**
- Long videos (>15s) can take 90–120s to analyze. The `seed_client.py` uses a 180s timeout with 3 retries. If it still fails, try a shorter reference video.

**`uv sync` fails**
- Ensure Python 3.12+ is installed: `python --version`
- Try: `uv sync --refresh`

## Related Resources

- [BytePlus AgentKit Console](https://console.byteplus.com/agentkit)
- [BytePlus ModelArk Console](https://console.byteplus.com/ark)
- [BytePlus TOS](https://www.byteplus.com/product/tos)
- [AgentKit SDK Documentation](https://volcengine.github.io/agentkit-sdk-python/)
- [VeADK Documentation](https://volcengine.github.io/veadk-python/)

## License

Apache License 2.0
