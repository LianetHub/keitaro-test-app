from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings, get_settings


class KeitaroError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class KeitaroClient:
    """Thin wrapper around Keitaro Admin API v1."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if not self.settings.keitaro_api_key:
            raise KeitaroError("KEITARO_API_KEY is not set. Put it into .env")

        self._client = httpx.Client(
            base_url=self.settings.keitaro_api_base,
            headers={
                "Api-Key": self.settings.keitaro_api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                # Cloudflare on the tracker blocks default Python UA
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
            timeout=60.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> KeitaroClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        try:
            data = response.json() if response.content else None
        except ValueError:
            data = response.text

        if response.status_code >= 400:
            message = data.get("error") if isinstance(data, dict) else str(data)
            raise KeitaroError(str(message or response.text), response.status_code, data)
        return data

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json: dict | None = None) -> Any:
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict | None = None) -> Any:
        return self._request("PUT", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    # ---- resources ----

    def list_campaigns(self, limit: int = 100) -> list[dict]:
        return self.get("/campaigns", params={"limit": limit})

    def get_campaign(self, campaign_id: int) -> dict:
        return self.get(f"/campaigns/{campaign_id}")

    def create_campaign(self, payload: dict) -> dict:
        return self.post("/campaigns", json=payload)

    def delete_campaign(self, campaign_id: int) -> Any:
        return self.delete(f"/campaigns/{campaign_id}")

    def list_campaign_streams(self, campaign_id: int) -> list[dict]:
        return self.get(f"/campaigns/{campaign_id}/streams")

    def create_stream(self, payload: dict) -> dict:
        return self.post("/streams", json=payload)

    def update_stream(self, stream_id: int, payload: dict) -> dict:
        return self.put(f"/streams/{stream_id}", json=payload)

    def get_stream(self, stream_id: int) -> dict:
        return self.get(f"/streams/{stream_id}")

    def list_offers(self, limit: int = 500) -> list[dict]:
        return self.get("/offers", params={"limit": limit})

    def get_offer(self, offer_id: int) -> dict:
        return self.get(f"/offers/{offer_id}")

    def list_domains(self) -> list[dict]:
        return self.get("/domains")

    def list_groups(self, group_type: str = "campaigns") -> list[dict]:
        return self.get("/groups", params={"type": group_type})

    def list_traffic_sources(self) -> list[dict]:
        return self.get("/traffic_sources")
