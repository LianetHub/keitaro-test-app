from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import LocalOffer, LocalStream, OperationLog
from app.services.keitaro import KeitaroClient, KeitaroError
from app.services.weights import ShareError, redistribute_shares


def _snapshot_offers(offers: list[LocalOffer]) -> str:
    data = [
        {
            "keitaro_offer_id": o.keitaro_offer_id,
            "name": o.name,
            "share": o.share,
            "is_pinned": o.is_pinned,
            "status": o.status,
        }
        for o in offers
    ]
    return json.dumps(data, ensure_ascii=False)


def _stream_query(db: Session):
    return select(LocalStream).options(selectinload(LocalStream.offers))


def fetch_streams(db: Session, campaign_id: int) -> list[LocalStream]:
    """Pull streams from Keitaro. A dirty local draft is left untouched."""
    with KeitaroClient() as client:
        remote_streams = client.list_campaign_streams(campaign_id)
        offer_cache: dict[int, str] = {}

        def offer_name(offer_id: int) -> str:
            if offer_id not in offer_cache:
                try:
                    offer_cache[offer_id] = client.get_offer(offer_id).get("name") or str(offer_id)
                except KeitaroError:
                    offer_cache[offer_id] = str(offer_id)
            return offer_cache[offer_id]

        seen_stream_ids: set[int] = set()

        for remote in remote_streams:
            stream_id = int(remote["id"])
            seen_stream_ids.add(stream_id)
            remote_offers = remote.get("offers") or []
            schema = remote.get("schema")
            has_offers = bool(remote_offers) or schema == "landings"

            local = db.scalar(
                select(LocalStream).where(LocalStream.keitaro_stream_id == stream_id)
            )
            if local is None:
                local = LocalStream(
                    campaign_id=campaign_id,
                    keitaro_stream_id=stream_id,
                    name=remote.get("name") or f"Stream {stream_id}",
                    has_offers=has_offers,
                    is_dirty=False,
                )
                db.add(local)
                db.flush()
            else:
                local.campaign_id = campaign_id

            if local.is_dirty:
                continue

            local.name = remote.get("name") or local.name

            if not remote_offers and schema != "landings":
                local.has_offers = False
                local.is_dirty = False
                local.offers.clear()
                local.published_snapshot = "[]"
                continue

            local.has_offers = True
            remote_by_id = {int(o["offer_id"]): o for o in remote_offers}
            existing = {o.keitaro_offer_id: o for o in local.offers}

            for offer_id, offer in list(existing.items()):
                if offer_id not in remote_by_id:
                    offer.status = "removed"
                    offer.share = 0
                    offer.is_pinned = False

            for offer_id, remote_offer in remote_by_id.items():
                if offer_id in existing:
                    offer = existing[offer_id]
                    offer.status = "active"
                    offer.share = int(remote_offer.get("share") or 0)
                    offer.name = offer_name(offer_id)
                    offer.is_pinned = False
                else:
                    local.offers.append(
                        LocalOffer(
                            keitaro_offer_id=offer_id,
                            name=offer_name(offer_id),
                            share=int(remote_offer.get("share") or 0),
                            is_pinned=False,
                            status="active",
                        )
                    )

            local.is_dirty = False
            local.published_snapshot = _snapshot_offers(
                [o for o in local.offers if o.status == "active"]
            )

        for stream in db.scalars(
            select(LocalStream).where(LocalStream.campaign_id == campaign_id)
        ).all():
            if stream.keitaro_stream_id not in seen_stream_ids:
                db.delete(stream)

        db.commit()
        streams = db.scalars(
            _stream_query(db).where(LocalStream.campaign_id == campaign_id)
        ).all()
        return list(streams)


def get_local_streams(db: Session, campaign_id: int) -> list[LocalStream]:
    return list(
        db.scalars(_stream_query(db).where(LocalStream.campaign_id == campaign_id)).all()
    )


def _get_offer_stream(db: Session, stream_id: int) -> LocalStream:
    stream = db.scalar(_stream_query(db).where(LocalStream.id == stream_id))
    if stream is None:
        raise KeitaroError("Stream not found in local DB. Fetch streams first.", 404)
    if not stream.has_offers:
        raise KeitaroError("This stream has no offers schema", 400)
    return stream


def _recalculate(stream: LocalStream) -> None:
    payload = [
        {
            "ref": offer,
            "share": offer.share,
            "is_pinned": offer.is_pinned,
            "status": offer.status,
        }
        for offer in stream.offers
    ]
    try:
        redistribute_shares(payload)
    except ShareError as exc:
        raise KeitaroError(str(exc), 400) from exc
    for item in payload:
        item["ref"].share = item["share"]
    stream.is_dirty = True


def add_offer(db: Session, stream_id: int, offer_id: int) -> LocalStream:
    stream = _get_offer_stream(db, stream_id)
    existing = next((o for o in stream.offers if o.keitaro_offer_id == offer_id), None)
    if existing and existing.status == "active":
        raise KeitaroError("Offer already in stream", 400)

    with KeitaroClient() as client:
        offer = client.get_offer(offer_id)
        name = offer.get("name") or str(offer_id)

    if existing:
        existing.status = "active"
        existing.name = name
        existing.is_pinned = False
    else:
        stream.offers.append(
            LocalOffer(
                keitaro_offer_id=offer_id,
                name=name,
                share=0,
                is_pinned=False,
                status="active",
            )
        )

    _recalculate(stream)
    db.commit()
    db.refresh(stream)
    return _get_offer_stream(db, stream_id)


def remove_offer(db: Session, stream_id: int, local_offer_id: int) -> LocalStream:
    stream = _get_offer_stream(db, stream_id)
    offer = next((o for o in stream.offers if o.id == local_offer_id), None)
    if offer is None:
        raise KeitaroError("Offer not found", 404)
    offer.status = "removed"
    offer.share = 0
    offer.is_pinned = False
    _recalculate(stream)
    db.commit()
    return _get_offer_stream(db, stream_id)


def bring_back_offer(db: Session, stream_id: int, local_offer_id: int) -> LocalStream:
    stream = _get_offer_stream(db, stream_id)
    offer = next((o for o in stream.offers if o.id == local_offer_id), None)
    if offer is None:
        raise KeitaroError("Offer not found", 404)
    offer.status = "active"
    offer.is_pinned = False
    _recalculate(stream)
    db.commit()
    return _get_offer_stream(db, stream_id)


def pin_offer(
    db: Session,
    stream_id: int,
    local_offer_id: int,
    is_pinned: bool,
    share: int | None = None,
) -> LocalStream:
    stream = _get_offer_stream(db, stream_id)
    offer = next((o for o in stream.offers if o.id == local_offer_id), None)
    if offer is None:
        raise KeitaroError("Offer not found", 404)
    if offer.status != "active":
        raise KeitaroError("Cannot pin a removed offer", 400)

    offer.is_pinned = is_pinned
    if is_pinned and share is not None:
        offer.share = share
    _recalculate(stream)
    db.commit()
    return _get_offer_stream(db, stream_id)


def cancel_stream(db: Session, stream_id: int) -> LocalStream:
    stream = _get_offer_stream(db, stream_id)
    snapshot = json.loads(stream.published_snapshot or "[]")
    stream.offers.clear()
    db.flush()
    for item in snapshot:
        stream.offers.append(
            LocalOffer(
                keitaro_offer_id=item["keitaro_offer_id"],
                name=item.get("name") or str(item["keitaro_offer_id"]),
                share=int(item.get("share") or 0),
                is_pinned=bool(item.get("is_pinned")),
                status=item.get("status") or "active",
            )
        )
    stream.is_dirty = False
    db.commit()
    return _get_offer_stream(db, stream_id)


_SERVER_KEYS = {"id", "stream_id", "created_at", "updated_at", "oid"}


def stream_update_body(remote: dict, offers: list[dict]) -> dict:
    """Keep the stream Keitaro returned and replace offers.

    Drop only server-side ids. Filters, landings and the rest stay as they were.
    """

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if key not in _SERVER_KEYS}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    body = clean(remote)
    body["offers"] = offers
    return body


def push_stream(db: Session, stream_id: int) -> LocalStream:
    stream = _get_offer_stream(db, stream_id)
    active = [o for o in stream.offers if o.status == "active"]
    if not active or sum(o.share for o in active) != 100:
        raise KeitaroError("Сумма долей активных офферов должна быть 100%", 400)
    payload_offers = [
        {
            "offer_id": o.keitaro_offer_id,
            "share": o.share,
            "state": "active",
        }
        for o in active
    ]

    with KeitaroClient() as client:
        remote = client.get_stream(stream.keitaro_stream_id)
        client.update_stream(
            stream.keitaro_stream_id,
            stream_update_body(remote, payload_offers),
        )

    # Drop removed offers from local after successful push
    stream.offers[:] = [o for o in stream.offers if o.status == "active"]
    stream.is_dirty = False
    stream.published_snapshot = _snapshot_offers(list(stream.offers))

    db.add(
        OperationLog(
            action="push_stream",
            details=json.dumps(
                {
                    "campaign_id": stream.campaign_id,
                    "stream_id": stream.keitaro_stream_id,
                    "offers": payload_offers,
                },
                ensure_ascii=False,
            ),
        )
    )
    db.commit()
    return _get_offer_stream(db, stream_id)
