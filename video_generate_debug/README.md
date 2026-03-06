# Bug Report: `video_generate` — `generate_audio=False` is silently dropped

**Package:** `veadk-python`
**Affected version:** `0.5.27` (latest as of 2026-03-06)
**Severity:** Medium — a documented parameter has no effect, leading to unexpected audio in all generated videos

---

## Summary

Passing `generate_audio=False` to `video_generate` has no effect. Seedance 1.5 Pro always generates audio regardless of the value set, because the parameter is silently dropped before the API request is sent.

---

## Steps to Reproduce

```bash
cp .env.example .env
# Fill in your Ark API key in .env

pip install veadk-python httpx python-dotenv
python reproduce_bug.py
```

The script calls through **veadk's actual internal functions** — the same code path that the agent uses at runtime:

1. Builds a params dict with `generate_audio: false` (same as what the agent passes)
2. Parses it through veadk's `_parse_item_to_config()` → shows `config.generate_audio = False` ✓
3. Passes it through `_should_disable_audio()` → shows `False` is converted to `None` ✗
4. Builds the request body via `_build_request_body()` → shows `generate_audio` field is **absent**
5. Submits the task via veadk's `_create_video_task()` → actually sends the buggy body to the API
6. Polls via veadk's `_get_task_status()` → returns a video URL

Opening the returned video URL confirms: the video has audio despite `generate_audio=False` being set.

---

## Root Cause

The bug is in `_should_disable_audio()` in `veadk/tools/builtin_tools/video_generate.py`:

```python
# veadk 0.5.25 — line 133
def _should_disable_audio(
    model_name: str, generate_audio: Optional[bool]
) -> Optional[bool]:
    if generate_audio is False:
        return None          # ← BUG: should return False, not None
    if model_name.startswith("doubao-seedance-1-0") and generate_audio:
        ...
        return None
    return generate_audio
```

This return value is then used in `_build_request_body()`:

```python
# line 175
generate_audio = _should_disable_audio(model_name, config.generate_audio)
if generate_audio is not None:       # ← None check causes False to be skipped
    body["generate_audio"] = generate_audio
```

**The result:** `generate_audio=False` is treated identically to `generate_audio=None` (not set). The field is never included in the request body. Since Seedance 1.5 Pro generates audio by default when the field is absent, audio is always produced.

| Value passed | `_should_disable_audio` returns | Field in request body | Audio generated? |
|---|---|---|---|
| `True` | `True` | ✅ `"generate_audio": true` | Yes |
| `False` | `None` ← bug | ❌ field absent | **Yes (unexpected)** |
| `None` (not set) | `None` | ❌ field absent | Yes (expected default) |

---

## Expected Behaviour

When `generate_audio=False` is passed, the request body should contain `"generate_audio": false`, and the generated video should have no audio track.

---

## Proposed Fix

A one-line change in `video_generate.py`:

```python
def _should_disable_audio(
    model_name: str, generate_audio: Optional[bool]
) -> Optional[bool]:
    if generate_audio is False:
-       return None
+       return False
    ...
```

With this fix, `False` is no longer converted to `None`, so `_build_request_body()` will correctly include `"generate_audio": false` in the body.

---

## Workaround

Until a fix is released, call `_build_request_body` manually and add the field explicitly, or use the following minimal wrapper:

```python
async def video_generate_fixed(params, tool_context, **kwargs):
    # Patch: add generate_audio to body before API call
    from veadk.tools.builtin_tools.video_generate import (
        VideoGenerationConfig, _build_content, _get_headers
    )
    from veadk.config import getenv
    from veadk.consts import DEFAULT_VIDEO_MODEL_API_BASE
    import httpx

    API_BASE = getenv("MODEL_VIDEO_API_BASE", DEFAULT_VIDEO_MODEL_API_BASE).rstrip("/")

    for item in params:
        config = VideoGenerationConfig(**{k: item.get(k) for k in VideoGenerationConfig.__dataclass_fields__})
        body = {
            "model": kwargs.get("model_name", "doubao-seedance-1-5-pro-251215"),
            "content": _build_content(item["prompt"], config),
        }
        if config.generate_audio is not None:   # correctly includes False
            body["generate_audio"] = config.generate_audio
        # ... submit body to API
```
