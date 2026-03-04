"""
TOS file upload tool for TikTok reference video generation.
Uploads files to BytePlus TOS object storage and returns signed access URL.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import tos
from tos import HttpMethodType

logger = logging.getLogger(__name__)


def upload_to_tos(
    file_path: str,
    object_key: Optional[str] = None,
    expires: int = 604800,
) -> str:
    """
    Upload a file to TOS object storage and return a signed accessible URL.

    Args:
        file_path: Local file path
        object_key: Object storage key name; if empty, uses the filename
        expires: Signed URL validity period (seconds), defaults to 7 days

    Returns:
        str: Signed TOS URL that can be accessed directly

    Environment variables required:
        VOLCENGINE_ACCESS_KEY: Volcano Engine access key
        VOLCENGINE_SECRET_KEY: Volcano Engine secret key
        DATABASE_TOS_BUCKET: TOS bucket name
        DATABASE_TOS_REGION: TOS region

    Example:
        >>> url = upload_to_tos("./video.mp4")
        >>> print(url)
        https://bucket.tos-ap-southeast-1.bytepluses.com/video.mp4?X-Tos-Signature=...
    """
    # Load configuration from config.yaml or environment variables
    access_key = os.getenv("VOLCENGINE_ACCESS_KEY")
    secret_key = os.getenv("VOLCENGINE_SECRET_KEY")
    bucket_name = os.getenv("DATABASE_TOS_BUCKET")
    region = os.getenv("DATABASE_TOS_REGION", "ap-southeast-1")

    if not all([access_key, secret_key, bucket_name]):
        raise ValueError(
            "Missing required environment variables: VOLCENGINE_ACCESS_KEY, "
            "VOLCENGINE_SECRET_KEY, DATABASE_TOS_BUCKET"
        )

    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")

    if not os.path.isfile(file_path):
        raise ValueError(f"Path is not a file: {file_path}")

    # Auto-generate object_key (using filename)
    if not object_key:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        object_key = f"tiktok-video-gen/{timestamp}_{filename}"

    client = None
    try:
        # Initialize TOS client
        endpoint = f"tos-{region}.bytepluses.com"
        client = tos.TosClientV2(
            ak=access_key,
            sk=secret_key,
            endpoint=endpoint,
            region=region,
        )

        logger.info(f"Uploading {file_path} to {bucket_name}/{object_key}")

        # Upload file
        result = client.put_object_from_file(
            bucket=bucket_name,
            key=object_key,
            file_path=file_path,
        )

        logger.info(f"File uploaded successfully! ETag: {result.etag}")

        # Generate signed URL
        signed_url_output = client.pre_signed_url(
            http_method=HttpMethodType.Http_Method_Get,
            bucket=bucket_name,
            key=object_key,
            expires=expires,
        )

        signed_url = signed_url_output.signed_url
        logger.info(f"Signed URL generated (valid for {expires} seconds)")

        return signed_url

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise
    finally:
        if client:
            client.close()
