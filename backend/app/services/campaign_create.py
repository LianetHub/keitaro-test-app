from __future__ import annotations

import json
import secrets
import re

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import OperationLog
from app.schemas import CampaignCreateRequest, CampaignCreateResponse
from app.services.keitaro import KeitaroClient, KeitaroError


def _make_alias(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")[:24] or "camp"
    return f"{slug}-{secrets.token_hex(4)}"


def _pick_id(
    configured: int | None,
    items: list[dict],
    label: str,
    *,
    prefer_name: str | None = None,
) -> int:
    if configured:
        return configured
    if not items:
        raise KeitaroError(f"No {label} found in Keitaro. Create one in admin or set it in .env")
    if prefer_name:
        needle = prefer_name.lower()
        for item in items:
            if needle in str(item.get("name", "")).lower():
                return int(item["id"])
    return int(items[0]["id"])


def resolve_campaign_defaults(client: KeitaroClient, settings: Settings) -> dict[str, int]:
    domain_id = _pick_id(settings.keitaro_domain_id, client.list_domains(), "domains")
    group_id = _pick_id(
        settings.keitaro_group_id,
        client.list_groups("campaigns"),
        "campaign groups",
        prefer_name="fortest",
    )
    source_id = _pick_id(
        settings.keitaro_traffic_source_id,
        client.list_traffic_sources(),
        "traffic sources",
        prefer_name="fortest",
    )
    return {
        "domain_id": domain_id,
        "group_id": group_id,
        "traffic_source_id": source_id,
    }


def create_campaign_with_streams(
    db: Session,
    payload: CampaignCreateRequest,
    settings: Settings | None = None,
) -> CampaignCreateResponse:
    settings = settings or get_settings()
    geo = payload.geo.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", geo):
        raise KeitaroError("Гео-код должен быть из двух латинских букв, например AU", 400)

    with KeitaroClient(settings) as client:
        offer = client.get_offer(payload.offer_id)
        defaults = resolve_campaign_defaults(client, settings)

        campaign_id: int | None = None
        try:
            campaign = client.create_campaign(
                {
                    "name": payload.name,
                    "alias": _make_alias(payload.name),
                    "type": "position",
                    "domain_id": defaults["domain_id"],
                    "group_id": defaults["group_id"],
                    "traffic_source_id": defaults["traffic_source_id"],
                }
            )
            campaign_id = int(campaign["id"])

            google_stream = client.create_stream(
                {
                    "campaign_id": campaign_id,
                    "name": "Google",
                    "type": "regular",
                    "position": 1,
                    "schema": "redirect",
                    "action_type": "http",
                    "action_payload": "https://www.google.com",
                    "collect_clicks": True,
                    "filter_or": False,
                    "filters": [
                        {
                            "name": "country",
                            "mode": "accept",
                            "payload": [geo],
                        }
                    ],
                    "offers": [],
                    "landings": [],
                }
            )

            offers_stream = client.create_stream(
                {
                    "campaign_id": campaign_id,
                    "name": "Offers",
                    "type": "regular",
                    "position": 2,
                    "schema": "landings",
                    "action_type": "http",
                    "action_payload": "",
                    "collect_clicks": True,
                    "filter_or": False,
                    "filters": [],
                    "landings": [],
                    "offers": [
                        {
                            "offer_id": payload.offer_id,
                            "share": 100,
                            "state": "active",
                        }
                    ],
                }
            )
        except KeitaroError as exc:
            if campaign_id is not None:
                try:
                    client.delete_campaign(campaign_id)
                except KeitaroError as cleanup_exc:
                    raise KeitaroError(
                        f"{exc}. Кампания #{campaign_id} осталась в Keitaro: {cleanup_exc}",
                        exc.status_code,
                    ) from exc
            raise

        domain = next((d for d in client.list_domains() if d["id"] == defaults["domain_id"]), None)
        alias = campaign.get("alias")
        campaign_url = None
        if domain and alias:
            host = domain.get("name", "").rstrip("/")
            campaign_url = f"https://{host}/{alias}"

        db.add(
            OperationLog(
                action="create_campaign",
                details=json.dumps(
                    {
                        "campaign_id": campaign_id,
                        "name": payload.name,
                        "geo": geo,
                        "offer_id": payload.offer_id,
                        "offer_name": offer.get("name"),
                        "defaults": defaults,
                    },
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()

        return CampaignCreateResponse(
            id=campaign_id,
            name=campaign.get("name", payload.name),
            alias=alias,
            domain_id=defaults["domain_id"],
            group_id=defaults["group_id"],
            traffic_source_id=defaults["traffic_source_id"],
            google_stream_id=google_stream.get("id"),
            offers_stream_id=offers_stream.get("id"),
            campaign_url=campaign_url,
        )
