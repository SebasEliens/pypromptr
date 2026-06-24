# Design: S3Prompts

## Motivation

Object storage is the natural home for prompts in cloud-native stacks. S3-compatible APIs (AWS S3, Cloudflare R2, MinIO, GCS via interop) mean one implementation covers most teams. Use cases:

- Prompts deployed as objects, updated via CI without redeploying the application
- Multi-environment setups: `prompts/prod/`, `prompts/staging/` prefixes in one bucket
- Access control via IAM/bucket policies, no separate auth system needed

## Optional dependency

```bash
pip install pypromptr[s3]
# adds: boto3
```

## Interface

```python
from pypromptr.s3_source import S3Prompts

source = S3Prompts(
    bucket="my-prompts-bucket",
    prefix="prompts/",           # key prefix to scope; default: ""
    extension=".md",             # object key suffix to match; default: ".md"
    endpoint_url=None,           # override for R2, MinIO, GCS, etc.; default: AWS
    region_name=None,            # AWS region; default: from env/config
)
```

Credentials follow the standard boto3 chain: env vars (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`), `~/.aws/credentials`, instance profile, etc. No credential parameters on the constructor.

## Behaviour

### `keys() -> list[str]`
Lists objects under `prefix` with the given `extension` via `ListObjectsV2`. Returns keys stripped of prefix and extension. Called at init.

### `get_prompt(key: str) -> PromptLike`
Fetches `{prefix}{key}{extension}` via `GetObject`. Parses frontmatter + body the same way as `FilePrompts`. Raises `KeyError(key)` on `NoSuchKey` (404); all other S3 errors propagate.

## Compatibility

The same class works for any S3-compatible store by setting `endpoint_url`:

| Store | `endpoint_url` |
|-------|---------------|
| AWS S3 | `None` (default) |
| Cloudflare R2 | `https://<account>.r2.cloudflarestorage.com` |
| MinIO | `http://localhost:9000` |
| GCS (interop) | `https://storage.googleapis.com` |

## Notes

- `keys()` requires `ListObjectsV2` permission in addition to `GetObject`.
- For large buckets, `keys()` paginates automatically via the boto3 paginator.
- No file-watcher; prompt updates are picked up on next process start (or registry reconstruction).
- Omit `keys()` implementation if the source is used purely for resolution and listing is not needed — `S3Prompts` could be split into `S3Prompts` (no `keys()`) and `EnumerableS3Prompts` (with `keys()`), but a single class with both is simpler.

## Example

```python
from pypromptr import PromptRegistry
from pypromptr.s3_source import S3Prompts

# AWS S3
registry = PromptRegistry(S3Prompts("my-bucket", prefix="prompts/prod/"))

# Cloudflare R2
registry = PromptRegistry(
    S3Prompts("my-bucket", endpoint_url="https://<account>.r2.cloudflarestorage.com")
)

rendered = registry.get("welcome", name="Alice")
```
