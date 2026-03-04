"""
Custom image generation wrapper.

Extends veadk's built-in image_generate to support the `guidance_scale` parameter,
which controls how strongly the output adheres to the reference image. The built-in
veadk 0.5.25 _build_request_body silently drops guidance_scale, making reference-based
generation (single_image_to_single) ineffective without this wrapper.
"""

import asyncio
import json
import logging

import httpx

from veadk.config import getenv, settings
from veadk.consts import DEFAULT_IMAGE_GENERATE_MODEL_API_BASE, DEFAULT_IMAGE_GENERATE_MODEL_NAME
from veadk.version import VERSION

logger = logging.getLogger(__name__)

API_KEY = getenv(
    "MODEL_IMAGE_API_KEY",
    getenv("MODEL_AGENT_API_KEY", settings.model.api_key),
)
API_BASE = getenv("MODEL_IMAGE_API_BASE", DEFAULT_IMAGE_GENERATE_MODEL_API_BASE).rstrip("/")


def _get_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "veadk-source": "veadk",
        "veadk-version": VERSION,
        "User-Agent": f"VeADK/{VERSION}",
    }


def _build_body(item: dict, model_name: str) -> dict:
    body = {
        "model": model_name,
        "prompt": item.get("prompt", ""),
    }
    if size := item.get("size"):
        body["size"] = size
    if (watermark := item.get("watermark")) is not None:
        body["watermark"] = watermark
    if image := item.get("image"):
        body["image"] = image
    if gs := item.get("guidance_scale"):
        body["guidance_scale"] = gs
    if seq := item.get("sequential_image_generation"):
        body["sequential_image_generation"] = seq
        if (max_img := item.get("max_images")) is not None:
            body["sequential_image_generation_options"] = {"max_images": max_img}
    if fmt := item.get("output_format"):
        body["output_format"] = fmt
    if rf := item.get("response_format"):
        body["response_format"] = rf
    return body


async def _call_api(item: dict, model_name: str, timeout: int = 600) -> dict:
    url = f"{API_BASE}/images/generations"
    body = _build_body(item, model_name)
    logger.info(
        f"[image_generate] POST {url}\nRequest body:\n{json.dumps(body, ensure_ascii=False, indent=2)}"
    )
    async with httpx.AsyncClient(timeout=float(timeout)) as client:
        response = await client.post(url, headers=_get_headers(), json=body)
        if response.status_code >= 400:
            logger.error(f"[image_generate] API error {response.status_code}: {response.text}")
        response.raise_for_status()
        return response.json()


async def image_generate(tasks: list[dict], tool_context, timeout: int = 600, model_name: str = None) -> dict:
    """Generate images using Seedream, with support for guidance_scale.

    The veadk built-in image_generate (0.5.25) does not pass guidance_scale to the API,
    making reference-based generation (single_image_to_single) produce weak or no adherence
    to the reference image. This wrapper fixes that by including guidance_scale in the request.

    Args:
        tasks: List of image generation task dicts. Each task supports:
            - task_type (str): "text_to_single", "single_image_to_single", etc.
            - prompt (str): Follow the pattern:
                "Based on the [product] in the reference image, [scene description]."
            - image (str): TOS URL of the reference/product image.
            - size (str): "1440x2560" for 9:16, "2048x2048" for 1:1, etc.
            - guidance_scale (float): Controls reference adherence strength. Try 3.5–7.0.
            - sequential_image_generation (str): "auto" to generate multiple variations.
            - max_images (int): Number of variations when sequential_image_generation="auto".

    Returns:
        {"status": "success", "success_list": [{"task_0_image_0": "<url>"}], "error_list": []}
    """
    model = model_name or getenv("MODEL_IMAGE_NAME", DEFAULT_IMAGE_GENERATE_MODEL_NAME)
    logger.info(f"[image_generate] Using model: {model}, {len(tasks)} task(s)")

    success_list = []
    error_list = []

    results = await asyncio.gather(
        *[_call_api(item, model, timeout) for item in tasks],
        return_exceptions=True,
    )

    for idx, res in enumerate(results):
        if isinstance(res, Exception):
            logger.error(f"[image_generate] Task {idx} exception: {res}")
            error_list.append(f"task_{idx}")
            continue

        data_list = res.get("data", [])
        if not data_list and "error" in res:
            logger.error(f"[image_generate] Task {idx} API error: {res['error']}")
            error_list.append(f"task_{idx}")
            continue

        for i, image_data in enumerate(data_list):
            name = f"task_{idx}_image_{i}"
            url = image_data.get("url")
            if url:
                success_list.append({name: url})
                tool_context.state[f"{name}_url"] = url
                logger.info(f"[image_generate] Task {idx} image {i}: {url[:80]}...")
            else:
                logger.error(f"[image_generate] Task {idx} image {i}: no URL in response")
                error_list.append(name)

    return {
        "status": "success" if success_list else "error",
        "success_list": success_list,
        "error_list": error_list,
    }
