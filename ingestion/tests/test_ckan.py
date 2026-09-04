from __future__ import annotations

import pytest

from ingestion.ckan import CkanError, list_resources


class _FakeResponse:
    def __init__(self, status_code: int, body: dict[str, object]) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict[str, object]:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.requested_url: str | None = None

    def get(self, url: str, timeout: float) -> _FakeResponse:
        self.requested_url = url
        return self._response


def test_list_resources_parses_package_show() -> None:
    body = {
        "success": True,
        "result": {
            "resources": [
                {
                    "id": "abc-123",
                    "name": "Beneficios Emitidos junho 2026",
                    "format": "CSV",
                    "url": "https://s3/D.SDA.PDA.003.EMI.202606.CSV.ZIP",
                    "last_modified": "2026-07-10T12:00:00",
                },
                {
                    "id": "def-456",
                    "name": "Beneficios Emitidos julho 2026",
                    "format": "CSV",
                    "url": "https://s3/D.DLK.FRM.000.DADOSABERTOS.EMITIDOS_202607.zip",
                    "created": "2026-08-05T09:00:00",
                },
            ]
        },
    }
    session = _FakeSession(_FakeResponse(200, body))
    resources = list_resources(
        session, base_url="https://dadosabertos.inss.gov.br", package_id="inss-beneficios-emitidos"
    )
    assert len(resources) == 2
    assert resources[0].resource_id == "abc-123"
    assert resources[0].last_modified == "2026-07-10T12:00:00"
    assert resources[1].last_modified == "2026-08-05T09:00:00"
    assert session.requested_url == (
        "https://dadosabertos.inss.gov.br/api/3/action/package_show?id=inss-beneficios-emitidos"
    )


def test_list_resources_raises_on_unsuccessful_response() -> None:
    session = _FakeSession(_FakeResponse(200, {"success": False}))
    with pytest.raises(CkanError):
        list_resources(session, base_url="https://x", package_id="missing")
