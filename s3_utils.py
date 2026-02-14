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

# -----------------------------------------------------------------------------
# PLACEHOLDER: Set these in environment or .env for your deployment
# -----------------------------------------------------------------------------
S3_BUCKET = os.environ.get("S3_BUCKET", "YOUR_BUCKET_NAME_PLACEHOLDER")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
# Optional: if not set, boto3 uses default credential chain (env, ~/.aws/credentials, IAM role)
# AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
# AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

# S3 key prefix for user reference photos: users/{user_id}/ref_xxx.jpg
S3_USER_PREFIX = "users"


def _normalize_user_id(user_id: str) -> str:
    return (user_id or "").strip().lower()


def _s3_prefix(user_id: str) -> str:
    return f"{S3_USER_PREFIX}/{_normalize_user_id(user_id)}/"


def get_s3_client():
    """Return boto3 S3 client using env credentials (or default chain)."""
    import boto3
    kwargs = {"region_name": AWS_REGION}
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        kwargs["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID")
        kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
    return boto3.client("s3", **kwargs)


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
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=image_bytes,
        ContentType=f"image/{'jpeg' if file_extension.lower() in ('jpg', 'jpeg') else 'png' if file_extension.lower() == 'png' else 'octet-stream'}",
    )
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
        client.download_file(S3_BUCKET, key, str(local_path))
    
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
        with open(cache_path, "rb") as f:
            client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=f.read(),
                ContentType="application/octet-stream",
            )
    except Exception as e:
        print(f"Warning: Could not upload embeddings cache to S3: {e}")
        # Don't fail the entire verification if cache upload fails
