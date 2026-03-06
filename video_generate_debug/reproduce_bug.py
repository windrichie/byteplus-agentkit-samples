"""
Live reproduction of the veadk-python 0.5.25 video_generate bug:
generate_audio=False is silently dropped from the API request body.

This script calls through veadk's actual internal functions — the same code path
that the agent uses — to demonstrate that passing generate_audio=False in the
params has no effect on the resulting video.

Setup:
    cp .env.example .env   # fill in your API key
    pip install veadk-python httpx python-dotenv
    python reproduce_bug.py
"""

import asyncio
import json
import os

from dotenv import load_dotenv

load_dotenv()

# Must be set before importing veadk (it reads env at import time)
API_KEY = os.environ["MODEL_VIDEO_API_KEY"]
MODEL = os.environ.get("MODEL_VIDEO_NAME", "doubao-seedance-1-5-pro-251215")


async def main():
    from veadk.version import VERSION
    from veadk.tools.builtin_tools.video_generate import (
        VideoGenerationConfig,
        _build_request_body,
        _create_video_task,
        _get_task_status,
        _parse_item_to_config,
        _should_disable_audio,
    )

    print(f"veadk-python version: {VERSION}")
    print(f"Model: {MODEL}")
    print("=" * 60)

    # ── This is what the agent passes to video_generate ──────────────
    params = {
        "video_name": "test_video.mp4",
        "prompt": (
            "A pair of blue running shoes rotating slowly on a clean "
            "white studio surface, soft directional lighting."
        ),
        "ratio": "9:16",
        "duration": 5,
        "resolution": "720p",
        "generate_audio": False,  # <-- explicitly set to False
    }

    print(f"\n[Input] Agent passes generate_audio = {params['generate_audio']!r}")

    # ── Step 1: Parse params through veadk's _parse_item_to_config ───
    config: VideoGenerationConfig = _parse_item_to_config(params)
    print(f"\n[Step 1] _parse_item_to_config → config.generate_audio = {config.generate_audio!r}")

    # ── Step 2: Show what _should_disable_audio does to False ────────
    audio_result = _should_disable_audio(MODEL, config.generate_audio)
    print(f"[Step 2] _should_disable_audio(model, False) → {audio_result!r}")
    if audio_result is None:
        print("         ⚠️  False was converted to None!")

    # ── Step 3: Show the actual request body veadk builds ────────────
    body = _build_request_body(params["prompt"], config, MODEL)
    print(f"\n[Step 3] _build_request_body produces:")
    # Print body without the content array (too verbose)
    display_body = {k: v for k, v in body.items() if k != "content"}
    print(f"         {json.dumps(display_body, indent=2)}")
    print(f"\n         'generate_audio' in body: {'generate_audio' in body}")
    if "generate_audio" not in body:
        print("         ⚠️  generate_audio is MISSING from the request body.")
        print("         Seedance will use its default → audio WILL be generated.")

    # ── Step 4: Actually submit the task via veadk's _create_video_task ──
    print(f"\n[Step 4] Submitting video task via veadk's _create_video_task...")
    task_data = await _create_video_task(params["prompt"], config, MODEL)
    task_id = task_data["id"]
    print(f"         Task ID: {task_id}")

    # ── Step 5: Poll via veadk's _get_task_status ────────────────────
    print(f"\n[Step 5] Polling via veadk's _get_task_status", end="", flush=True)
    while True:
        await asyncio.sleep(10)
        result = await _get_task_status(task_id)
        status = result.get("status")
        if status == "succeeded":
            video_url = result["content"]["video_url"]
            print(f" done.")
            break
        elif status == "failed":
            print(f" FAILED: {result.get('error')}")
            return
        print(".", end="", flush=True)

    # ── Result ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"""
The agent passed:              generate_audio = False
veadk sent to the API:         generate_audio field ABSENT
Seedance default when absent:  generate audio = True

Video URL (open to verify audio is present):
  {video_url}

Expected: video should be silent (no audio track)
Actual:   video has audio
""")


if __name__ == "__main__":
    asyncio.run(main())
