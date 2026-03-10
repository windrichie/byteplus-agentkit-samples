"""
Custom video generation wrapper.

Fixes a bug in veadk's built-in video_generate where passing
`generate_audio: false` is silently dropped. The built-in `_should_disable_audio`
returns None when generate_audio=False, and the request body builder skips None
values — so the field is never sent to the API. Since Seedance generates audio by
default when the field is absent, passing generate_audio=false has no effect.

This wrapper is fully self-contained — no imports from veadk's internal
video_generate module — to avoid version compatibility issues.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

import httpx

from veadk.config import getenv, settings
from veadk.consts import DEFAULT_VIDEO_MODEL_API_BASE, DEFAULT_VIDEO_MODEL_NAME
from veadk.version import VERSION

logger = logging.getLogger(__name__)

API_KEY = getenv(
    "MODEL_VIDEO_API_KEY",
    getenv("MODEL_AGENT_API_KEY", settings.model.api_key),
)
API_BASE = getenv("MODEL_VIDEO_API_BASE", DEFAULT_VIDEO_MODEL_API_BASE).rstrip("/")


def _get_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "veadk-source": "veadk",
        "veadk-version": VERSION,
        "User-Agent": f"VeADK/{VERSION}",
    }


def _build_content(prompt: str, item: dict) -> list:
    content = [{"type": "text", "text": prompt}]

    if first_frame := item.get("first_frame"):
        content.append({"type": "image_url", "image_url": {"url": first_frame}, "role": "first_frame"})

    if last_frame := item.get("last_frame"):
        content.append({"type": "image_url", "image_url": {"url": last_frame}, "role": "last_frame"})

    for ref in item.get("reference_images", []):
        content.append({"type": "image_url", "image_url": {"url": ref}, "role": "reference_image"})

    for ref in item.get("reference_videos", []):
        content.append({"type": "video_url", "video_url": {"url": ref}, "role": "reference_video"})

    for ref in item.get("reference_audios", []):
        content.append({"type": "audio_url", "audio_url": {"url": ref}, "role": "reference_audio"})

    return content


def _build_request_body(item: dict, model_name: str) -> dict:
    prompt = item.get("prompt", "")
    body = {
        "model": model_name,
        "content": _build_content(prompt, item),
    }

    # Fix: pass generate_audio explicitly when False, not just when True
    generate_audio = item.get("generate_audio")
    if generate_audio is not None:
        body["generate_audio"] = generate_audio

    if (ratio := item.get("ratio")) is not None:
        body["ratio"] = ratio
    if (duration := item.get("duration")) is not None:
        body["duration"] = duration
    if (resolution := item.get("resolution")) is not None:
        body["resolution"] = resolution
    if (frames := item.get("frames")) is not None:
        body["frames"] = frames
    if (camera_fixed := item.get("camera_fixed")) is not None:
        body["camera_fixed"] = camera_fixed
    if (seed := item.get("seed")) is not None:
        body["seed"] = seed
    if (watermark := item.get("watermark")) is not None:
        body["watermark"] = watermark

    return body


async def _create_task(item: dict, model_name: str) -> dict:
    url = f"{API_BASE}/contents/generations/tasks"
    body = _build_request_body(item, model_name)
    logger.info(f"[video_generate] POST {url}\nRequest body:\n{json.dumps(body, ensure_ascii=False, indent=2)}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=_get_headers(), json=body)
        if response.status_code >= 400:
            logger.error(f"[video_generate] API error {response.status_code}: {response.text}")
        response.raise_for_status()
        return response.json()


async def _get_task_status(task_id: str) -> dict:
    url = f"{API_BASE}/contents/generations/tasks/{task_id}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, headers=_get_headers())
        response.raise_for_status()
        return response.json()


async def video_generate(
    params: list,
    tool_context,
    batch_size: int = 10,
    max_wait_seconds: int = 1200,
    model_name: str = None,
) -> Dict:
    """Generate videos using Seedance, with generate_audio=false correctly respected.

    The veadk built-in video_generate drops generate_audio=false from the
    API request body, causing Seedance to always produce audio. This wrapper fixes
    that by explicitly including generate_audio in the body when it is set.

    Args:
        params: List of video generation task dicts. Each task supports:
            - video_name (str): Output file identifier.
            - prompt (str): Scene description.
            - first_frame (str): URL of the keyframe image to animate.
            - last_frame (str): URL of the last frame image.
            - reference_images (list[str]): Reference image URLs.
            - reference_videos (list[str]): Reference video URLs.
            - reference_audios (list[str]): Reference audio URLs.
            - ratio (str): "9:16" for vertical TikTok format.
            - duration (int): Clip length in seconds (4–12 for Seedance 1.5 Pro).
            - resolution (str): "720p" or "1080p".
            - generate_audio (bool): False to disable audio.
            - camera_fixed (bool): True to lock camera movement.
            - seed (int): Random seed for reproducibility.
            - watermark (bool): Whether to add watermark.
        tool_context: ADK tool context.
        batch_size: Number of videos per batch. Default 10.
        max_wait_seconds: Max polling time per batch. Default 1200.
        model_name: Override model name.

    Returns:
        {"status": "success", "success_list": [{"video_name": "<url>"}], ...}
    """
    if model_name is None:
        model_name = getenv("MODEL_VIDEO_NAME", DEFAULT_VIDEO_MODEL_NAME)

    logger.info(f"[video_generate] Using model: {model_name}, {len(params)} task(s)")

    success_list = []
    error_list = []
    error_details = []
    pending_list = []

    for start_idx in range(0, len(params), batch_size):
        batch = params[start_idx: start_idx + batch_size]

        # Submit tasks
        task_map = {}
        for item in batch:
            video_name = item["video_name"]
            try:
                task_data = await _create_task(item, model_name)
                task_id = task_data.get("id")
                if task_id:
                    task_map[task_id] = {
                        "video_name": video_name,
                        "execution_expires_after": task_data.get("execution_expires_after"),
                    }
                    logger.info(f"[video_generate] Task created: {task_id} for {video_name}")
            except httpx.HTTPStatusError as e:
                error_text = e.response.text if e.response else str(e)
                logger.error(f"[video_generate] HTTP error for {video_name}: {error_text}")
                error_list.append(video_name)
                try:
                    error_details.append({"video_name": video_name, "error": json.loads(error_text)})
                except Exception:
                    error_details.append({"video_name": video_name, "error": error_text})
            except Exception as e:
                logger.error(f"[video_generate] Failed to create task for {video_name}: {e}")
                error_list.append(video_name)
                error_details.append({"video_name": video_name, "error": str(e)})

        # Poll for results
        poll_count = 0
        max_polls = max_wait_seconds // 10

        while task_map and poll_count < max_polls:
            completed = []
            for task_id, info in list(task_map.items()):
                video_name = info["video_name"]
                try:
                    result = await _get_task_status(task_id)
                    status = result.get("status")
                    if status == "succeeded":
                        video_url = result.get("content", {}).get("video_url")
                        tool_context.state[f"{video_name}_video_url"] = video_url
                        success_list.append({video_name: video_url})
                        completed.append(task_id)
                        logger.info(f"[video_generate] {video_name} completed: {video_url[:80]}...")
                    elif status == "failed":
                        error_info = result.get("error")
                        error_list.append(video_name)
                        error_details.append({"video_name": video_name, "error": error_info})
                        completed.append(task_id)
                        logger.error(f"[video_generate] {video_name} failed: {error_info}")
                except Exception as e:
                    logger.error(f"[video_generate] Error polling {task_id}: {e}")

            for task_id in completed:
                task_map.pop(task_id, None)

            if not task_map:
                break

            await asyncio.sleep(10)
            poll_count += 1

        for task_id, info in task_map.items():
            pending_list.append({
                "video_name": info["video_name"],
                "task_id": task_id,
                "execution_expires_after": info["execution_expires_after"],
                "message": f"Task still running. Use video_task_query('{task_id}') to check status later.",
            })

    if success_list and not error_list and not pending_list:
        status = "success"
    elif success_list:
        status = "partial_success"
    else:
        status = "error"

    return {
        "status": status,
        "success_list": success_list,
        "error_list": error_list,
        "error_details": error_details,
        "pending_list": pending_list,
    }
