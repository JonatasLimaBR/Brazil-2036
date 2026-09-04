from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class HttpResponseLike(Protocol):
    status_code: int

    def json(self) -> dict[str, object]: ...

    def raise_for_status(self) -> None: ...


class HttpGet(Protocol):
    def get(self, url: str, timeout: float) -> HttpResponseLike: ...


@dataclass(frozen=True)
class CkanResource:
    resource_id: str
    name: str
    format: str
    url: str
    last_modified: str | None


class CkanError(RuntimeError):
    pass


def list_resources(
    session: HttpGet, *, base_url: str, package_id: str, timeout: float = 30.0
) -> list[CkanResource]:
    url = f"{base_url.rstrip('/')}/api/3/action/package_show?id={package_id}"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    if not body.get("success"):
        raise CkanError(f"CKAN package_show failed for {package_id!r}")
    result = body.get("result")
    if not isinstance(result, dict):
        raise CkanError(f"CKAN package_show returned no result for {package_id!r}")
    resources = result.get("resources", [])
    return [
        CkanResource(
            resource_id=str(r["id"]),
            name=str(r["name"]),
            format=str(r.get("format", "")),
            url=str(r["url"]),
            last_modified=r.get("last_modified") or r.get("created"),
        )
        for r in resources
    ]
