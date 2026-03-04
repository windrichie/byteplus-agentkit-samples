"""
Tool for downloading TikTok videos using yt-dlp.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path to import existing download_tiktok
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)


async def download_tiktok_video(
    tool_context,
    url: str,
    out_dir: Optional[str] = None,
) -> str:
    """Download a TikTok video locally for analysis and processing.

    Args:
        url: TikTok video URL
        out_dir: Output directory (default: "downloads")

    Returns:
        JSON string containing download result:
        {
          "status": "success" | "error",
          "local_path": str,
          "url": str,
          "title": str,
          "error": str (if failed)
        }

    Example:
        >>> result = await download_tiktok_video(
        ...     tool_context,
        ...     url="https://www.tvmatrix.com/video/123"
        ... )
        >>> data = json.loads(result)
        >>> print(data["local_path"])
        downloads/video_title [123].mp4
    """
    # Set default output directory
    if out_dir is None:
        out_dir = "downloads"

    # Create output directory
    os.makedirs(out_dir, exist_ok=True)
    output_template = os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s")

    try:
        import yt_dlp
    except ImportError:
        error_msg = "yt-dlp package is not installed. Please install it with: pip install yt-dlp"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "error": error_msg,
            "url": url
        })

    try:
        ydl_opts = {
            "format": "bv*+ba/b",
            "outtmpl": output_template,
            "restrictfilenames": True,
            "quiet": False,
            "noprogress": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading TikTok video: {url}")
            info = ydl.extract_info(url, download=True)

            # Get the local file path
            local_path = ydl.prepare_filename(info)

            if not os.path.exists(local_path):
                # Try to find the file in the output directory
                # The actual filename might be different due to sanitize
                filename = f"{info.get('title', '')} [{info.get('id', '')}].mp4"
                local_path = os.path.join(out_dir, filename)

                if not os.path.exists(local_path):
                    # List files in directory as fallback
                    files = [f for f in os.listdir(out_dir) if f.endswith('.mp4')]
                    if files:
                        local_path = os.path.join(out_dir, files[-1])  # Most recent

            result = {
                "status": "success",
                "local_path": os.path.abspath(local_path),
                "url": url,
                "title": info.get("title", ""),
                "id": info.get("id", ""),
                "duration": info.get("duration", 0),
                "description": info.get("description", ""),
            }

            logger.info(f"TikTok video downloaded successfully: {local_path}")
            return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Failed to download TikTok video: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "url": url
        }, indent=2)
