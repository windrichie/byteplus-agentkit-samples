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
"""
TOS file upload utility
Provides functionality to upload files to Volcano Engine TOS object storage and returns a signed access URL
Implemented using the tos library directly
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import tos
from tos import HttpMethodType

# Current directory
sys.path.append(str(Path(__file__).resolve().parent))
# Parent directory
sys.path.append(str(Path(__file__).resolve().parent.parent))
from veadk.auth.veauth.utils import get_credential_from_vefaas_iam
try:
    from ..consts import DEFAULT_BUCKET, DEFAULT_REGION
except ImportError:
    from consts import DEFAULT_BUCKET, DEFAULT_REGION


logger = logging.getLogger(__name__)


def upload_file_to_tos(
    file_path: str,
    bucket_name: Optional[str] = None,
    object_key: Optional[str] = None,
    region: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    session_token: Optional[str] = None,
    expires: int = 604800,  # 7-day validity
) -> Optional[str]:
    """
    Upload a file to TOS object storage and return a signed accessible URL

    Args:
        file_path: Local file path
        bucket_name: TOS bucket name, defaults to "aaa-bbb-ccc-ddd"
        object_key: Object storage key name; if empty, uses the filename
        region: TOS region, defaults to cn-beijing
        ak: Access Key; if empty, reads from environment variables
        sk: Secret Key; if empty, reads from environment variables
        expires: Signed URL validity period (seconds), defaults to 7 days (604800 seconds)

    Returns:
        str: Signed TOS URL that can be accessed directly
        None: Returns None if upload fails

    Environment variables required:
        VOLCENGINE_ACCESS_KEY: Volcano Engine access key
        VOLCENGINE_SECRET_KEY: Volcano Engine secret key

    Usage example:
        >>> url = upload_file_to_tos("./video.mp4")
        >>> print(url)
        https://bucket.tos-cn-beijing.volces.com/video.mp4?X-Tos-Signature=...
    """

    if bucket_name is None:
        bucket_name = os.getenv("DATABASE_TOS_BUCKET")
        if bucket_name is None:
            bucket_name = DEFAULT_BUCKET
            logger.warning(
                "bucket_name is not provided in env, using default bucket name: %s",
                bucket_name,
            )
        else:
            logger.info("Using bucket_name from env: %s", bucket_name)
    if region is None:
        region = os.getenv("DATABASE_TOS_REGION")
        if region is None:
            region = DEFAULT_REGION
            logger.warning(
                "region is not provided in env, using default region: %s", region
            )
        else:
            logger.info("Using region from env: %s", region)

    # Check if file exists
    if not os.path.exists(file_path):
        msg = f"ERROR: File does not exist: {file_path}"
        logger.error(msg)
        return msg

    if not os.path.isfile(file_path):
        msg = f"ERROR: Path is not a file: {file_path}"
        logger.error(msg)
        return msg

    # Retrieve STS from IAM Role
    access_key = os.getenv("VOLCENGINE_ACCESS_KEY")
    secret_key = os.getenv("VOLCENGINE_SECRET_KEY")
    session_token = ""

    if not (access_key and secret_key):
        try:
            cred = get_credential_from_vefaas_iam()
            access_key = cred.access_key_id
            secret_key = cred.secret_access_key
            session_token = cred.session_token
        except Exception as e:
            msg = f"ERROR: Missing VOLCENGINE_ACCESS_KEY/VOLCENGINE_SECRET_KEY and failed to load VeFaaS IAM credentials: {e}"
            logger.error(msg)
            return msg

    if not access_key or not secret_key:
        msg = "ERROR: VOLCENGINE_ACCESS_KEY and VOLCENGINE_SECRET_KEY are not provided (and IAM Role is not configured)."
        logger.error(msg)
        return msg

    # Auto-generate object_key (using filename)
    if not object_key:
        # Combine timestamp and original filename to avoid overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        object_key = f"upload/{filename}_{timestamp}"

    # Create TOS client
    client = None
    try:
        # Initialize TOS client
        endpoint = f"tos-{region}.bytepluses.com"
        client = tos.TosClientV2(
            ak=access_key,
            sk=secret_key,
            security_token=session_token,
            endpoint=endpoint,
            region=region,
        )

        logger.info(f"Starting file upload: {file_path}")
        logger.info(f"Target Bucket: {bucket_name}")
        logger.info(f"Object Key: {object_key}")

        # Ensure bucket exists (create if not)
        try:
            client.head_bucket(bucket_name)
            logger.info(f"Bucket {bucket_name} already exists")
        except tos.exceptions.TosServerError as e:
            if e.status_code == 404:
                logger.info(f"Bucket {bucket_name} does not exist, creating...")
            else:
                raise e

        # Upload file
        result = client.put_object_from_file(
            bucket=bucket_name, key=object_key, file_path=file_path
        )

        logger.info("File uploaded successfully!")
        logger.info(f"ETag: {result.etag}")
        logger.info(f"Request ID: {result.request_id}")

        # Generate signed URL
        signed_url_output = client.pre_signed_url(
            http_method=HttpMethodType.Http_Method_Get,
            bucket=bucket_name,
            key=object_key,
            expires=expires,
        )

        signed_url = signed_url_output.signed_url
        logger.info(f"Signed URL generated successfully (valid for {expires} seconds)")
        logger.info(f"Access URL: {signed_url}")

        return signed_url

    except tos.exceptions.TosClientError as e:
        msg = f"ERROR: TOS client error: {e}"
        logger.exception(msg)
        return msg
    except tos.exceptions.TosServerError as e:
        msg = (
            f"ERROR: TOS server error: status_code={e.status_code}, code={e.code}, message={e.message}"
        )
        logger.exception(msg)
        return msg
    except Exception as e:
        msg = f"ERROR: File upload failed: {e}"
        logger.exception(msg)
        return msg
    finally:
        # Close client
        if client:
            client.close()


# Example usage
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("TOS file upload test")
    logger.info("=" * 60)

    # Test file path
    test_file = "./hujiahuwei_complete.mp4"

    if os.path.exists(test_file):
        logger.info(f"\nTest file found: {test_file}")
        file_size = os.path.getsize(test_file) / (1024 * 1024)  # MB
        logger.info(f"File size: {file_size:.2f} MB")

        logger.info("\n" + "=" * 60)
        logger.info("Starting upload...")
        logger.info("=" * 60)

        # Call upload function
        url = upload_file_to_tos(
            file_path=test_file,
            bucket_name=os.getenv(
                "DATABASE_TOS_BUCKET", DEFAULT_BUCKET
            ),  # You can change to your bucket name
            # object_key="test_video.mp4",  # Optional: specify object key
            region=os.getenv(
                "DATABASE_TOS_REGION", DEFAULT_REGION
            ),  # You can change to your region
            expires=604800,  # 7-day validity
        )

        logger.info("\n" + "=" * 60)
        if url:
            logger.info("✅ Upload successful!")
            logger.info(f"📎 Access URL: {url}")
            logger.info(
                "\nTip: URL is valid for 7 days and can be accessed directly in a browser"
            )
        else:
            logger.info("❌ Upload failed")
            logger.info("\nPlease check:")
            logger.info(
                "1. Whether environment variables VOLCENGINE_ACCESS_KEY and VOLCENGINE_SECRET_KEY are set"
            )
            logger.info("2. Whether network connection is normal")
            logger.info("3. Whether account permissions are sufficient")
        logger.info("=" * 60)
    else:
        logger.info(f"\n❌ Test file does not exist: {test_file}")
        logger.info(
            "\nPlease ensure the test file exists, or modify the test_file variable in the code to point to a valid file path"
        )
        logger.info("\nUsage:")
        logger.info("  from tool.tos_upload import upload_file_to_tos")
        logger.info('  url = upload_file_to_tos("your_file.mp4")')
        logger.info("  print(url)")
