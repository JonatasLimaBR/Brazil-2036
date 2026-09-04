from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol


class Blob(Protocol):
    def exists(self) -> bool: ...

    def upload_from_string(
        self, data: bytes | str, *, content_type: str, if_generation_match: int
    ) -> None: ...


class Bucket(Protocol):
    def blob(self, name: str) -> Blob: ...


class StorageClient(Protocol):
    def bucket(self, name: str) -> Bucket: ...


@dataclass(frozen=True)
class RawObject:
    uri: str
    manifest_uri: str
    content_sha256: str
    created: bool
    manifest: dict[str, Any]


def write_raw(
    client: StorageClient,
    *,
    bucket_name: str,
    prefix: str,
    data: bytes,
    source_uri: str,
    http_status: int,
    file_ext: str = "csv",
) -> RawObject:
    content_sha256 = hashlib.sha256(data).hexdigest()
    bucket = client.bucket(bucket_name)

    object_name = f"{prefix}/{content_sha256}.{file_ext}"
    manifest_name = f"{prefix}/{content_sha256}.manifest.json"

    blob = bucket.blob(object_name)
    created = not blob.exists()
    if created:
        blob.upload_from_string(data, content_type="text/csv", if_generation_match=0)

    manifest = {
        "source_uri": source_uri,
        "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
        "http_status": http_status,
        "bytes": len(data),
        "content_sha256": content_sha256,
    }
    manifest_blob = bucket.blob(manifest_name)
    if not manifest_blob.exists():
        manifest_blob.upload_from_string(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            content_type="application/json",
            if_generation_match=0,
        )

    return RawObject(
        uri=f"gs://{bucket_name}/{object_name}",
        manifest_uri=f"gs://{bucket_name}/{manifest_name}",
        content_sha256=content_sha256,
        created=created,
        manifest=manifest,
    )
