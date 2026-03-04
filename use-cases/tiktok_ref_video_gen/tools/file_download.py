"""
Tool for downloading files from URLs to local storage.
Used to download generated video/image URLs so MCP tools can process them locally.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlparse

import requests

logger = logging.getLogger(__name__)


def file_download(
    url: List[str],
    save_dir: Optional[str] = None,
    filename: Optional[List[str]] = None,
) -> List[str]:
    """
    Batch download files from URLs to local storage.

    Use this tool to download generated video or image files from remote URLs
    to local paths, so that MCP video tools (merge_videos, clip_video, add_audio)
    can process them.

    Args:
        url: List of file URLs to download
        save_dir: Save directory, defaults to "downloads"
        filename: Optional list of filenames; if None, extracted from URLs

    Returns:
        List[str]: List of absolute paths to downloaded files

    Examples:
        # Download generated scene videos before merging
        paths = file_download(url=[
            "https://example.com/scene_1.mp4",
            "https://example.com/scene_2.mp4",
        ])
        # Then use merge_videos with the returned local paths
    """
    if not isinstance(url, list):
        raise ValueError("url parameter must be a list")

    if save_dir is None:
        save_dir = os.getenv("DOWNLOAD_DIR", "downloads")

    if filename is None:
        filenames = [None] * len(url)
    elif isinstance(filename, list):
        if len(filename) != len(url):
            raise ValueError(
                f"filename list length ({len(filename)}) must match url list length ({len(url)})"
            )
        filenames = filename
    else:
        raise ValueError("filename must be a list or None")

    downloaded_paths = []
    for url_item, filename_item in zip(url, filenames):
        path = _download_single_file(url_item, save_dir, filename_item)
        downloaded_paths.append(path)

    return downloaded_paths


def _download_single_file(
    url: str, save_dir: str, filename: Optional[str] = None
) -> str:
    """Download a single file from a URL."""
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    if filename is None:
        parsed_url = urlparse(url)
        filename = unquote(os.path.basename(parsed_url.path))
        if not filename or filename == "/":
            filename = "downloaded_file"

    full_path = save_path / filename

    # Avoid overwriting existing files
    counter = 1
    original_stem = full_path.stem
    original_suffix = full_path.suffix
    while full_path.exists():
        filename = f"{original_stem}_{counter}{original_suffix}"
        full_path = save_path / filename
        counter += 1

    try:
        logger.info(f"Downloading {url} -> {full_path}")
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        with open(full_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info(f"Downloaded successfully: {full_path.absolute()}")
        return str(full_path.absolute())

    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Download failed for {url}: {e}")
    except IOError as e:
        raise IOError(f"Write file failed: {e}")
