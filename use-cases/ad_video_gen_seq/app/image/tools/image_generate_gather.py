# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import urllib.parse
from typing import Any, Dict

import requests
from google.adk.tools import ToolContext
from veadk.tools.builtin_tools.image_generate import (
    image_generate as image_generate_builtin,
)
from veadk.utils.logger import get_logger

logger = get_logger(__name__)


def _extract_image_url(value: str) -> str | None:
    text = value.strip().strip("`'\"，, ")
    match = re.search(r"https?://[^\s`'\"，,]+", text)
    if match:
        return match.group(0).rstrip("`'\"，,。)")
    if text.startswith("data:"):
        return text
    return None


def _is_supported_image_input(value: str) -> bool:
    parsed = urllib.parse.urlparse(value.strip())
    return parsed.scheme in {"http", "https", "data"} and bool(
        parsed.netloc or parsed.scheme == "data"
    )


def _is_reachable_image_url(value: str) -> bool:
    if value.startswith("data:"):
        return True
    try:
        response = requests.head(value, timeout=5, allow_redirects=True)
        return response.status_code < 400
    except Exception as e:
        logger.warning(f"Skip unreachable image reference URL: {value}, error={e}")
        return False


def _clean_image_input(value: Any):
    if isinstance(value, str):
        url = _extract_image_url(value)
        if url and _is_supported_image_input(url) and _is_reachable_image_url(url):
            return url
        logger.warning(f"Drop invalid image reference: {value}")
        return None
    if isinstance(value, list):
        cleaned = [
            cleaned_item
            for item in value
            if isinstance(item, str)
            if (cleaned_item := _clean_image_input(item))
        ]
        return cleaned or None
    return None


def _downgrade_to_text_task_if_no_image(task: dict):
    task_type = task.get("task_type", "")
    if "image" not in task and isinstance(task_type, str) and "image_to" in task_type:
        task["task_type"] = "text_to_single"


async def image_generate(tasks: list[dict], tool_context: ToolContext) -> Dict:
    """Generate images with Seedream 4.5.

    Commit batch image generation requests via tasks.

    Args:
        tasks (list[dict]):
            A list of image-generation tasks. Each task is a dict.
    Per-task schema
    ---------------
    Required:
        - task_type (str):
            One of:
              * "multi_image_to_group"   # multi-image to image group
              * "single_image_to_group"  # single-image to image group
              * "text_to_group"          # text to image group
              * "multi_image_to_single"  # multi-image to single image
              * "single_image_to_single" # single-image to single image
              * "text_to_single"         # text to single image
        - prompt (str)
            Text description of the desired image(s). Chinese or English are both accepted.
            Note: do not put phrases like `generate X images` in the prompt field; use the `max_images` field to control the number of images generated.
    Optional:
        - size (str)
            Specify the size of the generated image:
                    - 1:1   -> 2048x2048
                    - 4:3   -> 2384x1728
                    - 3:4   -> 1728x2304
                    - 16:9  -> 2560x1440
                    - 9:16  -> 1440x2560
            Default: "2048x2048"
        - watermark (bool)
            Add watermark. Default: true.
        - image (str | list[str])   # (corresponds to the reference field)
            Reference image(s) as URL or Base64.
            * For "single image" tasks: pass a string (exactly 1 image).
            * For "image group" tasks: pass an array (2-10 images).
        - sequential_image_generation (str)
            Controls whether to generate an "image group". Default: "disabled".
            * To generate a group: must be set to "auto".
        - max_images (int)
            Only effective when generating a group. Controls how many images the model can generate.
    Model behavior (how the mode is inferred from parameters)
    ---------------------------------
    1) Text to single image: no image provided and (S not set or S="disabled") -> 1 image.
    2) Text to image group: no image provided and S="auto" -> group, count controlled by max_images.
    3) Single-image to single image: image=string and (S not set or S="disabled") -> 1 image.
    4) Single-image to image group: image=string and S="auto" -> group, count <= 14.
    5) Multi-image to single image: image=array (2-10) and (S not set or S="disabled") -> 1 image.
    6) Multi-image to image group: image=array (2-10) and S="auto" -> group, total must be <= 15.
    Return result
    --------
        Dict with generation summary.
        Example:
        {
            "status": "success",
            "success_list": [
                {"image_name": "url"}
            ],
            "error_list": ["image_name"]
        }
    Notes:
    - Image-group tasks require sequential_image_generation="auto".
    - For size, 2048x2048 or a standard ratio from the table is recommended to ensure generation quality.
    """
    logger.debug(f"image_generate_gather tasks: {tasks}")
    new_tasks = []
    task_origin_info = []  # Stores (original_task_index, sub_index_within_group)

    for original_idx, task in enumerate(tasks):
        task_type = task.get("task_type", "")
        num_images = int(task.get("max_images") or 1)
        is_group_task = task_type in {
            "single_image_to_group",
            "text_to_group",
            "multi_image_to_group",
        } or num_images > 1

        if is_group_task:
            base_task_type = task_type.replace("_group", "_single")
            for i in range(num_images):
                new_task = task.copy()
                new_task["task_type"] = base_task_type
                new_task.pop("sequential_image_generation", None)
                new_task.pop("max_images", None)
                new_tasks.append(new_task)
                task_origin_info.append((original_idx, i))
        else:
            new_tasks.append(task.copy())
            task_origin_info.append((original_idx, 0))

    for task in new_tasks:
        # Guard against the prompt containing "N images" (or the Chinese equivalent)
        # phrasing, which makes the model render a single image as a 4-grid or 6-grid
        # composite instead of N separate images.
        if "prompt" in task and isinstance(task["prompt"], str):
            # Match Arabic and Chinese numerals, in both English and Chinese phrasing.
            task["prompt"] = re.sub(
                r"[\d一二三四五六七八九十百千万]+\s*(?:images?|pictures?|pics?|photos?|张图片)",
                "image",
                task["prompt"],
                flags=re.IGNORECASE,
            )
        task["watermark"] = False

        # Handling the reference field: The model often incorrectly uses reference instead of image
        # Priority: image > reference
        if "reference" in task:
            if "image" not in task or not task.get("image"):
                task["image"] = task["reference"]
            task.pop("reference", None)

        if "image" in task:
            cleaned_image = _clean_image_input(task["image"])
            if cleaned_image:
                task["image"] = cleaned_image
            else:
                task.pop("image", None)

        _downgrade_to_text_task_if_no_image(task)

        # BytePlus image models used here do not support group-generation params.
        # This wrapper fans out max_images into independent single-image tasks.
        task.pop("sequential_image_generation", None)
        task.pop("max_images", None)

        aspect_ratio_map = {
            "1:1": "2048x2048",
            "4:3": "2384x1728",
            "3:4": "1728x2304",
            "16:9": "2560x1440",
            "9:16": "1440x2560",
            "3:2": "2496x1664",
            "2:3": "1664x2496",
            "21:9": "3024x1296",
        }
        if "size" in task and task["size"] in aspect_ratio_map:
            task["size"] = aspect_ratio_map[task["size"]]

    # Call the underlying image_generate function with the flattened list of tasks
    logger.debug(f"image_generate_gather new_tasks: {new_tasks}")
    raw_result = await image_generate_builtin(new_tasks, tool_context)
    logger.debug(f"image_generate_gather raw_result: {raw_result}")

    # Remap the results to match the original task structure
    remapped_success = []
    remapped_errors = set()

    for success_item in raw_result.get("success_list", []):
        for key, url in success_item.items():
            # Key is like 'task_{idx}_image_{i}'
            match = re.match(r"task_(\d+)_image_(\d+)", key)
            if not match:
                continue

            new_task_idx = int(match.group(1))
            if new_task_idx >= len(task_origin_info):
                continue

            original_idx, original_sub_idx = task_origin_info[new_task_idx]
            new_key = f"task_{original_idx}_image_{original_sub_idx}"
            remapped_success.append({new_key: url})

    for error_item in raw_result.get("error_list", []):
        # Error item is like 'task_{idx}'
        match = re.match(r"task_(\d+)", error_item)
        if match:
            new_task_idx = int(match.group(1))
            if new_task_idx < len(task_origin_info):
                original_idx, _ = task_origin_info[new_task_idx]
                remapped_errors.add(f"task_{original_idx}")
            else:
                remapped_errors.add(error_item)  # Keep original error if mapping fails
        else:
            remapped_errors.add(error_item)
    logger.debug(f"image_generate_gather remapped_success: {remapped_success}")
    logger.debug(f"image_generate_gather remapped_errors: {remapped_errors}")

    result = {
        "status": raw_result.get("status"),
        "success_list": remapped_success,
        "error_list": list(remapped_errors),
    }
    return result
