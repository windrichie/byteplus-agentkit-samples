"""
Tool for analyzing product images using BytePlus ModelArk Vision API.
"""

import logging
import os
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from utils.seed_client import SeedClient

logger = logging.getLogger(__name__)

# Analysis prompt for product images
PRODUCT_ANALYSIS_PROMPT = """
You are analyzing a product image to extract information needed for creating a TikTok product video.
Your output will be used in two ways:
1. As a reference description embedded directly in image generation prompts (Seedream model)
2. To help plan which scenes from a reference video can be adapted for this product

Return a concise JSON response with exactly these fields:

{
  "product_name": "Short natural-language name for the product as it will appear in image generation prompts, e.g. 'running shoes', 'face serum bottle', 'wireless headphones'. Used directly in: 'Based on the [product_name] in the reference image...'",
  "key_brand_detail": "Only if there is ONE standout brand-identity element that must be visible in every shot (e.g. 'gold cap and brand label', 'Nike swoosh logo', 'holographic packaging'). Leave empty string if no such element exists.",
  "content_type": "Category of product (e.g. footwear, apparel, electronics, cosmetics, food)",
  "suggested_scene_angles": ["3-5 specific camera angles or shots that best showcase this product type — these become storyboard scene ideas"],
  "suggested_setting": "One ideal background/environment for this product (e.g. minimalist dark studio floor, white marble surface, outdoor urban pavement)",
  "adaptation_notes": "One or two sentences on how a reference video's shots can be adapted for this product — what to keep the same (pacing, lighting style) and what to change (subject, setting)"
}

Be concise. Each field should be brief and directly usable.
"""


async def analyze_product_image(
    tool_context: ToolContext,
    image_url: str,
    system_prompt: Optional[str] = PRODUCT_ANALYSIS_PROMPT,
) -> str:
    """Analyze a product image to extract visual attributes and presentation style.

    Args:
        image_url: URL of product image to analyze
        system_prompt: Optional custom analysis prompt

    Returns:
        Structured JSON analysis of product

    Environment variables required:
        MODEL_VISION_API_KEY: Doubao Vision API key
        MODEL_VISION_API_BASE: API base URL
        MODEL_VISION_NAME: Vision model name
    """
    logger.info(f"Analyzing product image: {image_url}")

    try:
        client = SeedClient()

        analysis = await client.analyze_image(
            image_url=image_url,
            prompt="Please analyze this product image according to the structure defined above.",
            system_prompt=system_prompt,
        )

        logger.info("Product image analysis completed successfully")
        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze product image: {e}")
        raise
