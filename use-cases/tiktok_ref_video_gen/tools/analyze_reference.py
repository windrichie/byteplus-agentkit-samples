"""
Tool for analyzing TikTok reference videos using BytePlus ModelArk Vision API.
"""

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from utils.seed_client import SeedClient

logger = logging.getLogger(__name__)

# Analysis prompt for reference video
REFERENCE_ANALYSIS_PROMPT = """
Analyze this TikTok reference video and provide a structured breakdown of its elements.
Focus on what makes it effective for showcasing products.

Provide a JSON response with these fields:
{
  "structure": {
    "total_duration": "estimated duration in seconds",
    "scene_count": "number of distinct scenes",
    "scenes": [
      {
        "scene_number": 1,
        "description": "what happens in this scene",
        "duration": "duration in seconds",
        "purpose": "what this scene achieves"
      }
    ]
  },
  "pacing": {
    "tempo": "fast/medium/slow",
    "cuts_per_minute": "estimated number of cuts",
    "rhythm": "description of the flow"
  },
  "camera": {
    "movements": ["list of movements like zoom in, pan right, static"],
    "shot_types": ["types like close-up, medium, wide"],
    "angles": ["angles like eye-level, low angle, overhead"]
  },
  "lighting": {
    "type": "type of lighting (natural, studio, dramatic, etc.)",
    "mood": "overall mood conveyed",
    "highlights": "key lighting techniques observed"
  },
  "transitions": {
    "type": "how scenes connect (cuts, fades, wipes, etc.)",
    "timing": "transition timing description"
  },
  "hook_strategy": {
    "first_3_seconds": "what grabs attention immediately",
    "engagement_triggers": ["list of techniques used"]
  },
  "visual_style": {
    "color_palette": "main colors used",
    "tone": "overall visual tone",
    "aesthetic": "style description"
  },
  "audio_cues": {
    "music_style": "style of music (if visible)",
    "beat_timing": "how visuals sync with audio"
  }
}
"""


async def analyze_reference_video(
    tool_context: ToolContext,
    video_url: str,
    system_prompt: Optional[str] = REFERENCE_ANALYSIS_PROMPT,
) -> str:
    """Analyze a TikTok reference video to extract structure, style, and pacing.

    Args:
        video_url: URL of the reference video to analyze
        system_prompt: Optional custom analysis prompt

    Returns:
        Structured JSON analysis of the reference video

    Environment variables required:
        MODEL_VISION_API_KEY: Doubao Vision API key
        MODEL_VISION_API_BASE: API base URL
        MODEL_VISION_NAME: Vision model name
    """
    logger.info(f"Analyzing reference video: {video_url}")

    try:
        client = SeedClient()

        analysis = await client.analyze_video(
            video_url=video_url,
            prompt="Please analyze this TikTok video according to the structure defined above.",
            system_prompt=system_prompt,
        )

        logger.info("Reference video analysis completed successfully")
        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze reference video: {e}")
        raise
