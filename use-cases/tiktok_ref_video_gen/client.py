"""
Test client for TikTok Reference Product Video Generator.

This script allows local testing of the video generation workflow.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from veadk import Runner
from veadk.memory.short_term_memory import ShortTermMemory

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent import root_agent

# Load environment variables
load_dotenv()

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for testing."""
    app_name = "tiktok_video_gen"
    user_id = "test_user"
    session_id = "test_session"

    short_term_memory = ShortTermMemory(backend="local")
    runner = Runner(
        agent = root_agent,
        short_term_memory = short_term_memory,
        app_name = app_name,
        user_id = user_id,
    )

    print("=" * 60)
    print("TikTok Reference Product Video Generator - Test Client")
    print("=" * 60)

    # Example workflow
    user_message = """
    Hello! I'd like to generate a TikTok product video. This is the reference video: https://www.tiktok.com/@thefashionjogger/video/7611569702044847382 . This is the product image: https://media.istockphoto.com/id/1350560575/photo/pair-of-blue-running-sneakers-on-white-background-isolated.jpg?s=612x612&w=0&k=20&c=A3w_a9q3Gz-tWkQL6K00xu7UHdN5LLZefzPDp-wNkSU=
    """

    print("\nSending request:\n" + user_message + "\n")

    response = await runner.run(
        messages = user_message,
        session_id = session_id,
    )

    print("\n" + "=" * 60)
    print("Response:")
    print("=" * 60)
    print(response)
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
