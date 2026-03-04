"""
Seed Client for BytePlus ModelArk Vision API (seed-2-0-mini) calls.
"""

import asyncio
import logging
import os
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

# Video analysis can take 60-120s for multi-second clips
_DEFAULT_TIMEOUT = 180.0
_MAX_RETRIES = 3
_RETRY_DELAYS = [5, 15, 30]  # seconds between retries


class SeedClient:
    """Client for interacting with Doubao Vision API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Initialize Doubao client.

        Args:
            api_key: API key for authentication
            api_base: Base URL for API
            model_name: Name of the model to use
        """
        self.api_key = api_key or os.getenv("MODEL_VISION_API_KEY")
        self.api_base = api_base or os.getenv(
            "MODEL_VISION_API_BASE", "https://ark.ap-southeast.bytepluses.com/api/v3/"
        )
        self.model_name = model_name or os.getenv("MODEL_VISION_NAME", "doubao-vision-pro-250815")

        if not self.api_key:
            raise ValueError("API key is required. Set MODEL_VISION_API_KEY environment variable.")

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Analyze an image using the Doubao Vision API.

        Args:
            image_url: URL of the image to analyze
            prompt: Analysis prompt/question
            system_prompt: Optional system prompt

        Returns:
            Analysis response text
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        return await self._call_api(messages)

    async def analyze_video(
        self,
        video_url: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Analyze a video using the Doubao Vision API.

        Args:
            video_url: URL of the video to analyze
            prompt: Analysis prompt/question
            system_prompt: Optional system prompt

        Returns:
            Analysis response text
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "video_url", "video_url": {"url": video_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        return await self._call_api(messages)

    async def _call_api(self, messages: List[dict]) -> str:
        """Call the Doubao API with retries on timeout.

        Args:
            messages: Message list for the API

        Returns:
            Response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        url = f"{self.api_base}chat/completions"

        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        f"Vision API timeout on attempt {attempt + 1}/{_MAX_RETRIES}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Vision API timed out after {_MAX_RETRIES} attempts: {e}")
            except httpx.HTTPStatusError as e:
                # Don't retry on HTTP errors (4xx/5xx) — they won't resolve with retries
                logger.error(f"Vision API HTTP error: {e.response.status_code} {e.response.text}")
                raise

        raise last_exc
