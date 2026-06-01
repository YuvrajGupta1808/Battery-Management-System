"""Tigris S3-compatible storage for remote CANary BMS wiki."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TigrisSettings:
    enabled: bool
    bucket: str
    prefix: str
    endpoint_url: str
    access_key_id: str | None
    secret_access_key: str | None
    region: str

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.access_key_id and self.secret_access_key)

    def object_key(self, relative: str) -> str:
        rel = relative.lstrip("/")
        base = self.prefix.rstrip("/")
        return f"{base}/{rel}" if base else rel


def get_tigris_settings() -> TigrisSettings:
    access = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("TIGRIS_STORAGE_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("TIGRIS_STORAGE_SECRET_ACCESS_KEY")
    endpoint = (
        os.getenv("AWS_ENDPOINT_URL")
        or os.getenv("AWS_ENDPOINT_URL_S3")
        or os.getenv("TIGRIS_STORAGE_ENDPOINT")
        or "https://t3.storage.dev"
    )
    enabled_raw = os.getenv("WORKBENCH_TIGRIS_ENABLED", "true").strip().lower()
    return TigrisSettings(
        enabled=enabled_raw not in {"0", "false", "no", "off"},
        bucket=os.getenv("TIGRIS_BUCKET", "canary-bms-knowledge"),
        prefix=os.getenv("TIGRIS_PREFIX", "dev/default"),
        endpoint_url=endpoint,
        access_key_id=access,
        secret_access_key=secret,
        region=os.getenv("AWS_REGION", "auto"),
    )


def mcp_env(settings: TigrisSettings) -> dict[str, str]:
    env: dict[str, str] = {}
    if settings.access_key_id:
        env["AWS_ACCESS_KEY_ID"] = settings.access_key_id
    if settings.secret_access_key:
        env["AWS_SECRET_ACCESS_KEY"] = settings.secret_access_key
    env["AWS_ENDPOINT_URL_S3"] = settings.endpoint_url
    env["AWS_REGION"] = settings.region
    return env


def s3_client(settings: TigrisSettings) -> Any:
    import boto3
    from botocore.config import Config

    if not settings.configured:
        raise RuntimeError("Tigris is not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name=settings.region,
        config=Config(s3={"addressing_style": "virtual"}),
    )


def ensure_bucket(settings: TigrisSettings) -> str:
    client = s3_client(settings)
    try:
        client.head_bucket(Bucket=settings.bucket)
    except Exception:
        client.create_bucket(Bucket=settings.bucket)
    return settings.bucket


def put_bytes(
    settings: TigrisSettings,
    relative_key: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
) -> str:
    bucket = ensure_bucket(settings)
    key = settings.object_key(relative_key)
    client = s3_client(settings)
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return key


def put_text(
    settings: TigrisSettings,
    relative_key: str,
    content: str,
    *,
    content_type: str = "text/markdown",
) -> str:
    bucket = ensure_bucket(settings)
    key = settings.object_key(relative_key)
    client = s3_client(settings)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType=content_type,
    )
    return key


def get_text(settings: TigrisSettings, relative_key: str) -> str | None:
    if not settings.configured:
        return None
    key = settings.object_key(relative_key)
    client = s3_client(settings)
    try:
        response = client.get_object(Bucket=settings.bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except Exception:
        return None


def list_prefix(settings: TigrisSettings, relative_prefix: str = "") -> list[str]:
    if not settings.configured:
        return []
    prefix = settings.object_key(relative_prefix)
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    client = s3_client(settings)
    keys: list[str] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": settings.bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        for obj in response.get("Contents", []):
            keys.append(str(obj["Key"]))
        if not response.get("IsTruncated"):
            break
        token = response.get("NextContinuationToken")
    return keys
