"""Object storage — AWS S3 (replaces Emergent object storage).

Required env vars:
  AWS_ACCESS_KEY_ID      — IAM key with s3:GetObject / s3:PutObject
  AWS_SECRET_ACCESS_KEY  — corresponding secret
  AWS_REGION             — bucket region (default: us-east-1)
  S3_BUCKET_NAME         — target bucket name

Optional:
  S3_ENDPOINT_URL        — S3-compatible endpoint (MinIO, Supabase Storage, etc.)
"""
import os
import uuid
from typing import Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

APP_NAME = "synaptiq"

_s3_client = None


def _client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    kwargs: dict = {
        "aws_access_key_id":     os.environ.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "region_name":           os.environ.get("AWS_REGION", "us-east-1"),
    }
    endpoint = os.environ.get("S3_ENDPOINT_URL", "").strip()
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def _bucket() -> str:
    name = os.environ.get("S3_BUCKET_NAME", "").strip()
    if not name:
        raise RuntimeError("S3_BUCKET_NAME not configured")
    return name


def init_storage() -> str:
    """Verify bucket is accessible at startup. Idempotent."""
    c = _client()
    b = _bucket()
    c.head_bucket(Bucket=b)
    return b


def put_object(path: str, data: bytes, content_type: str) -> dict:
    try:
        _client().put_object(
            Bucket=_bucket(),
            Key=path,
            Body=data,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 put failed: {exc}") from exc
    return {"path": path}


def get_object(path: str) -> Tuple[bytes, str]:
    try:
        resp = _client().get_object(Bucket=_bucket(), Key=path)
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 get failed: {exc}") from exc
    content_type = resp.get("ContentType") or "application/octet-stream"
    return resp["Body"].read(), content_type


def build_path(user_id: str, ext: str) -> str:
    return f"{APP_NAME}/uploads/{user_id}/{uuid.uuid4().hex}.{ext.lstrip('.').lower()}"
