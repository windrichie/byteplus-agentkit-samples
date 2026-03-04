"""
TikTok Reference Product Video Generator - Director Agent

Main entry point for generating TikTok product videos based on reference videos.
"""

import logging
import os
import sys
from pathlib import Path

from agentkit.apps import AgentkitAgentServerApp
from dotenv import load_dotenv
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioConnectionParams,
    StdioServerParameters,
)
from veadk import Agent
from veadk.memory.short_term_memory import ShortTermMemory

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompts import DIRECTOR_AGENT_PROMPT
from tools.analyze_product import analyze_product_image
from tools.analyze_reference import analyze_reference_video
from tools.download_tiktok import download_tiktok_video
from tools.file_download import file_download
from tools.image_generate import image_generate  # custom wrapper: adds guidance_scale support missing from veadk built-in
from tools.upload_to_tos import upload_to_tos
from veadk.tools.builtin_tools.video_generate import video_generate

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model configuration from environment variables
MODEL_CONFIG = {
    "agent": {
        "name": os.getenv("MODEL_AGENT_NAME", "deepseek-v3-2-251201"),
        "api_base": os.getenv("MODEL_AGENT_API_BASE", "https://ark.ap-southeast.byteplus.com/api/v3/"),
        "api_key": os.getenv("MODEL_AGENT_API_KEY"),
    },
}

# Configure MCP tool for video stitching (video-clip-mcp)
server_parameters = StdioServerParameters(
    command="npx",
    args=["@pickstar-2002/video-clip-mcp@latest"],
)
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=server_parameters, timeout=600.0
    ),
    errlog=None,
)

# Create Director Agent
# Built-in tools: image_generate, video_generate (VeADK)
# Custom tools: download_tiktok_video, upload_to_tos, analyze_reference_video, analyze_product_image
# MCP toolset: video-clip-mcp (merge_videos, clip_video, add_audio)
root_agent = Agent(
    name="tiktok_ref_video_gen",
    # name="tiktokref_video_director",
    description=(
        "Director agent for generating TikTok product videos based on "
        "reference videos, product images, and user customization instructions."
    ),
    instruction=DIRECTOR_AGENT_PROMPT,
    model_name=MODEL_CONFIG["agent"]["name"],
    model_api_base=MODEL_CONFIG["agent"]["api_base"],
    model_api_key=MODEL_CONFIG["agent"]["api_key"],
    tools=[
        download_tiktok_video,
        file_download,
        upload_to_tos,
        image_generate,
        video_generate,
        analyze_reference_video,
        analyze_product_image,
        mcp_toolset,  # MCP toolset for video stitching
    ],
)

# Setup memory and app
short_term_memory = ShortTermMemory(backend="local")

agent_server_app = AgentkitAgentServerApp(
    agent=root_agent,
    short_term_memory=short_term_memory,
)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    agent_server_app.run(host="0.0.0.0", port=port)
