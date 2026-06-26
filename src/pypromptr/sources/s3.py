"""S3Prompts: PromptSource that fetches prompts from S3-compatible object storage. Requires pip install pypromptr[s3]."""

from __future__ import annotations

from typing import Protocol

from pypromptr._parsing import parse_prompt_text
from pypromptr.prompts import MessagesPrompt, SimplePrompt


class BucketAdapter(Protocol):
    """Port for S3-compatible object storage. Implement to swap out boto3 in tests."""

    def list_keys(self) -> list[str]:
        """Return all prompt keys (prefix/extension already stripped)."""
        ...

    def get_object(self, key: str) -> str:
        """Return raw content for key. Raises KeyError if missing."""
        ...


class FakeBucketAdapter:
    """Test double: in-memory dict of key → raw content."""

    def __init__(self, objects: dict[str, str]) -> None:
        self._objects = dict(objects)

    def list_keys(self) -> list[str]:
        return list(self._objects.keys())

    def get_object(self, key: str) -> str:
        if key not in self._objects:
            raise KeyError(key)
        return self._objects[key]


class Boto3BucketAdapter:
    """Real adapter using boto3. Requires pip install pypromptr[s3]."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        extension: str = ".md",
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix
        self._extension = extension
        self._endpoint_url = endpoint_url
        self._region_name = region_name

    def _client(self):
        try:
            import boto3
        except ImportError as e:
            raise ImportError("Install S3 support with: pip install pypromptr[s3]") from e
        kwargs: dict = {}
        if self._endpoint_url is not None:
            kwargs["endpoint_url"] = self._endpoint_url
        if self._region_name is not None:
            kwargs["region_name"] = self._region_name
        return boto3.client("s3", **kwargs)

    def list_keys(self) -> list[str]:
        client = self._client()
        paginator = client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._prefix):
            for obj in page.get("Contents", []):
                k = obj["Key"]
                if k.endswith(self._extension):
                    # Strip prefix and extension
                    stripped = k[len(self._prefix):]
                    stripped = stripped[: -len(self._extension)]
                    keys.append(stripped)
        return keys

    def get_object(self, key: str) -> str:
        client = self._client()
        object_key = f"{self._prefix}{key}{self._extension}"
        try:
            response = client.get_object(Bucket=self._bucket, Key=object_key)
            return response["Body"].read().decode("utf-8")
        except client.exceptions.NoSuchKey:
            raise KeyError(key)
        except Exception as e:
            # Handle ClientError with NoSuchKey error code
            if hasattr(e, "response") and e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise KeyError(key)
            raise


class S3Prompts:
    """PromptSource that lists and fetches prompts from S3-compatible object storage (lazy)."""

    def __init__(
        self,
        bucket: str = "",
        prefix: str = "",
        extension: str = ".md",
        endpoint_url: str | None = None,
        region_name: str | None = None,
        *,
        adapter: BucketAdapter | None = None,
    ) -> None:
        if adapter is not None:
            self._adapter: BucketAdapter = adapter
        else:
            self._adapter = Boto3BucketAdapter(
                bucket=bucket,
                prefix=prefix,
                extension=extension,
                endpoint_url=endpoint_url,
                region_name=region_name,
            )

    def keys(self) -> list[str]:
        """Return all prompt keys from the bucket (prefix/extension stripped)."""
        return self._adapter.list_keys()

    def get_prompt(self, key: str) -> SimplePrompt | MessagesPrompt:
        """Fetch and parse the prompt for key. Raises KeyError if object not found."""
        raw = self._adapter.get_object(key)
        return parse_prompt_text(raw)
