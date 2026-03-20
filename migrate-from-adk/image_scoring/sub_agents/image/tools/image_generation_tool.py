import urllib.request

from google.adk.tools.tool_context import ToolContext
from google.genai import types
from veadk.tools.builtin_tools.image_generate import image_generate as veadk_image_generate

import config


def _extract_first_url(result: dict | None) -> str | None:
    if not isinstance(result, dict):
        return None
    for key in ("image_url", "url", "image"):
        value = result.get(key)
        if isinstance(value, str):
            return value
    success_list = result.get("success_list")
    if isinstance(success_list, list):
        for item in success_list:
            if isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, str):
                        return value
                    if isinstance(value, list):
                        for nested in value:
                            if isinstance(nested, str):
                                return nested
    return None


def _download_image(image_url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(image_url) as response:
            return response.read()
    except Exception:
        return None


async def generate_images(imagen_prompt: str, tool_context: ToolContext) -> dict:
    tasks = [
        {
            "task_type": config.IMAGE_TASK_TYPE,
            "prompt": imagen_prompt,
            "size": config.IMAGE_SIZE,
        }
    ]
    result = await veadk_image_generate(
        tasks=tasks,
        tool_context=tool_context,
    )
    image_url = _extract_first_url(result)
    if not image_url:
        return {
            "status": "error",
            "message": "Image generation succeeded but no image URL was found.",
            "raw_result": result,
        }

    counter = str(tool_context.state.get("loop_iteration", 0))
    artifact_name = f"generated_image_{counter}.png"
    tool_context.state["generated_image_url_" + counter] = image_url
    tool_context.state["last_generated_image_url"] = image_url

    image_bytes = _download_image(image_url)
    if image_bytes:
        report_artifact = types.Part.from_bytes(
            data=image_bytes, mime_type="image/png"
        )
        await tool_context.save_artifact(artifact_name, report_artifact)

    return {
        "status": "success",
        "message": "Image generated.",
        "artifact_name": artifact_name,
        "image_url": image_url,
    }
