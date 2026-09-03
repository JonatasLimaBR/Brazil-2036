from __future__ import annotations

import hashlib
import json

from ingestion.raw import write_raw

DATA = b"UF;ANO;VALOR\r\nAC;2015;4.245.948.557,36\r\n"


class FakeBlob:
    def __init__(self, store: dict[str, bytes], name: str) -> None:
        self._store = store
        self._name = name
        self.uploads = 0

    def exists(self) -> bool:
        return self._name in self._store

    def upload_from_string(
        self, data: bytes | str, *, content_type: str, if_generation_match: int
    ) -> None:
        assert if_generation_match == 0
        self.uploads += 1
        self._store[self._name] = data if isinstance(data, bytes) else data.encode()


class FakeBucket:
    def __init__(self, store: dict[str, bytes]) -> None:
        self._store = store
        self.blobs: list[FakeBlob] = []

    def blob(self, name: str) -> FakeBlob:
        blob = FakeBlob(self._store, name)
        self.blobs.append(blob)
        return blob


class FakeStorage:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
        self.bucket_obj = FakeBucket(self.store)

    def bucket(self, name: str) -> FakeBucket:
        return self.bucket_obj


def test_write_raw_creates_object_and_manifest() -> None:
    storage = FakeStorage()
    sha = hashlib.sha256(DATA).hexdigest()

    result = write_raw(
        storage,
        bucket_name="proj-raw",
        prefix="divida_estados",
        data=DATA,
        source_uri="https://example.test/divida.csv",
        http_status=200,
    )

    assert result.created is True
    assert result.content_sha256 == sha
    assert result.uri == f"gs://proj-raw/divida_estados/{sha}.csv"
    assert f"divida_estados/{sha}.csv" in storage.store
    manifest = json.loads(storage.store[f"divida_estados/{sha}.manifest.json"])
    assert manifest["content_sha256"] == sha
    assert manifest["bytes"] == len(DATA)
    assert manifest["http_status"] == 200


def test_write_raw_is_immutable_on_second_call() -> None:
    storage = FakeStorage()
    first = write_raw(
        storage,
        bucket_name="proj-raw",
        prefix="divida_estados",
        data=DATA,
        source_uri="u",
        http_status=200,
    )
    before = dict(storage.store)

    second = write_raw(
        storage,
        bucket_name="proj-raw",
        prefix="divida_estados",
        data=DATA,
        source_uri="u",
        http_status=200,
    )

    assert second.created is False
    assert storage.store == before
    assert second.content_sha256 == first.content_sha256
