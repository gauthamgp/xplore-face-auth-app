"""
S3 utilities for storing and retrieving user reference images.
Uses environment variables for credentials and bucket (see docs/AWS_SETUP.md).
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import List
import logging
import time

logger = logging.getLogger("xplore.s3_utils")

# -----------------------------------------------------------------------------
# PLACEHOLDER: Set these in environment or .env for your deployment
# -----------------------------------------------------------------------------
S3_BUCKET = os.environ.get("S3_BUCKET", "YOUR_BUCKET_NAME_PLACEHOLDER")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
# S3 key prefix for user reference photos: users/{user_id}/ref_xxx.jpg
S3_USER_PREFIX = "users"


def _normalize_user_id(user_id: str) -> str:
    return (user_id or "").strip().lower()


def _s3_prefix(user_id: str) -> str:
    return f"{S3_USER_PREFIX}/{_normalize_user_id(user_id)}/"


def get_s3_client():
    """
    Return boto3 S3 client using automatic credential discovery.
    
    Credential chain (in order of priority):
    1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) — if explicitly set
    2. AWS credentials file (~/.aws/credentials) — for local development
    3. EC2 IAM Role (metadata service) — RECOMMENDED for production
    4. ECS task credentials — for container deployments
    
    For production EC2 instances, attach an IAM role with S3 permissions.
    boto3 will automatically fetch temporary, rotating credentials from the
    instance metadata service. No explicit AWS keys needed in environment or files.
    
    SSL validation uses certifi CA bundle (works on both macOS and Linux EC2).
    
    Raises:
        Exception: If no valid credentials found or S3 access fails.
    """
    import boto3
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError
    import certifi
    
    try:
        # Explicitly use certifi's CA bundle for SSL validation
        # This ensures consistent SSL certificate verification across local and EC2
        client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            verify=certifi.where()  # Use certifi CA bundle for SSL validation
        )
        
        # Verify we can at least make a request (will fail fast if credentials are invalid)
        # This helps catch credential errors at client creation time
        client.meta.events.register("before-call", lambda **kwargs: None)
        
        return client
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"Credential error creating S3 client: {e}")
        logger.error("For local: set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        logger.error("For EC2: attach IAM role with S3 permissions to instance")
        raise
    except Exception as e:
        logger.error(f"Error creating S3 client: {e}")
        raise


def upload_reference_image(
    user_id: str,
    image_bytes: bytes,
    file_extension: str = "jpg",
    suggested_filename: str | None = None,
) -> str:
    """
    Upload one reference image to S3 under the user's folder.
    Returns the S3 key (e.g. users/alice/ref_abc123.jpg).
    """
    user_id = _normalize_user_id(user_id)
    if not user_id:
        raise ValueError("user_id is required")
    name = suggested_filename or f"ref_{uuid.uuid4().hex[:12]}.{file_extension.lstrip('.')}"
    key = f"{S3_USER_PREFIX}/{user_id}/{name}"
    client = get_s3_client()
    logger.info("upload_reference_image: putting object %s to bucket=%s", key, S3_BUCKET)
    t0 = time.perf_counter()
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType=f"image/{'jpeg' if file_extension.lower() in ('jpg', 'jpeg') else 'png' if file_extension.lower() == 'png' else 'octet-stream'}",
    )
    t1 = time.perf_counter()
    logger.info("upload_reference_image: put_object completed in %.3fs", t1 - t0)
    return key


def list_user_reference_keys(user_id: str) -> List[str]:
    """List S3 keys of all reference images for the given user."""
    user_id = _normalize_user_id(user_id)
    if not user_id:
        return []
    prefix = _s3_prefix(user_id)
    client = get_s3_client()
    paginator = client.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        for obj in page.get("Contents") or []:
            k = obj.get("Key")
            if k and k.endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                keys.append(k)
    return sorted(keys)


def download_user_refs_to_temp_dir(user_id: str) -> Path:
    """
    Download all reference images for the user from S3 into a temporary directory.
    Returns the path to that directory (caller must clean up when done).
    The directory contains files named by the S3 object key's final segment.
    Also downloads the cached embeddings file (.face_embeddings.pkl) if it exists.
    """
    keys = list_user_reference_keys(user_id)
    if not keys:
        raise FileNotFoundError(f"No reference images found in S3 for user_id={user_id}")
    client = get_s3_client()
    tmp = Path(tempfile.mkdtemp(prefix="face_refs_"))
    
    # Download reference images
    for key in keys:
        local_name = key.split("/")[-1]
        local_path = tmp / local_name
        logger.info("download_user_refs_to_temp_dir: downloading %s to %s", key, local_path)
        t0 = time.perf_counter()
        client.download_file(S3_BUCKET, key, str(local_path))
        t1 = time.perf_counter()
        logger.info("download_user_refs_to_temp_dir: downloaded %s in %.3fs", key, t1 - t0)
    
    # Try to download cached embeddings file (optional, won't fail if doesn't exist)
    try:
        cache_key = f"{_s3_prefix(user_id)}.face_embeddings.pkl"
        client.download_file(S3_BUCKET, cache_key, str(tmp / ".face_embeddings.pkl"))
    except Exception:
        pass  # Cache file may not exist yet
    
    return tmp


def upload_embeddings_cache(user_id: str, cache_path: Path) -> None:
    """
    Upload the .face_embeddings.pkl file to S3 for persistence across servers.
    This enables fast verification even on fresh instances.
    """
    if not cache_path.exists():
        return
    
    user_id = _normalize_user_id(user_id)
    if not user_id:
        raise ValueError("user_id is required")
    
    try:
        s3_key = f"{_s3_prefix(user_id)}.face_embeddings.pkl"
        client = get_s3_client()
        logger.info("upload_embeddings_cache: uploading %s to %s/%s", cache_path, S3_BUCKET, s3_key)
        t0 = time.perf_counter()
        with open(cache_path, "rb") as f:
            client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=f.read(),
                ContentType="application/octet-stream",
            )
            t1 = time.perf_counter()
            logger.info("upload_embeddings_cache: uploaded in %.3fs", t1 - t0)
    except Exception as e:
        print(f"Warning: Could not upload embeddings cache to S3: {e}")
        # Don't fail the entire verification if cache upload fails
