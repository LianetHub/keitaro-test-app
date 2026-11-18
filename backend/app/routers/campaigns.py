from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    AddOfferRequest,
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignOut,
    LocalStreamOut,
    LocalOfferOut,
    PinOfferRequest,
)
from app.services import campaign_create, campaign_edit
from app.services.keitaro import KeitaroClient, KeitaroError

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _http_error(exc: KeitaroError) -> HTTPException:
    return HTTPException(status_code=exc.status_code or 502, detail=str(exc))


def _stream_out(stream) -> LocalStreamOut:
    return LocalStreamOut(
        id=stream.id,
        campaign_id=stream.campaign_id,
        keitaro_stream_id=stream.keitaro_stream_id,
        name=stream.name,
        has_offers=stream.has_offers,
        is_dirty=stream.is_dirty,
        offers=[
            LocalOfferOut(
                id=o.id,
                keitaro_offer_id=o.keitaro_offer_id,
                name=o.name,
                share=o.share,
                is_pinned=o.is_pinned,
                status=o.status,
            )
            for o in stream.offers
        ],
    )


@router.get("", response_model=list[CampaignOut])
def list_campaigns():
    try:
        with KeitaroClient() as client:
            campaigns = client.list_campaigns(limit=200)
        return [
            CampaignOut(
                id=c["id"],
                name=c.get("name") or "",
                alias=c.get("alias"),
                domain_id=c.get("domain_id"),
                group_id=c.get("group_id"),
                traffic_source_id=c.get("traffic_source_id"),
                domain=c.get("domain"),
                group=c.get("group"),
                state=c.get("state"),
            )
            for c in campaigns
        ]
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.post("", response_model=CampaignCreateResponse)
def create_campaign(payload: CampaignCreateRequest, db: Session = Depends(get_db)):
    try:
        return campaign_create.create_campaign_with_streams(db, payload)
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int):
    try:
        with KeitaroClient() as client:
            c = client.get_campaign(campaign_id)
        return CampaignOut(
            id=c["id"],
            name=c.get("name") or "",
            alias=c.get("alias"),
            domain_id=c.get("domain_id"),
            group_id=c.get("group_id"),
            traffic_source_id=c.get("traffic_source_id"),
            domain=c.get("domain"),
            group=c.get("group"),
            state=c.get("state"),
        )
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.post("/{campaign_id}/streams/fetch", response_model=list[LocalStreamOut])
def fetch_streams(campaign_id: int, db: Session = Depends(get_db)):
    try:
        streams = campaign_edit.fetch_streams(db, campaign_id)
        return [_stream_out(s) for s in streams]
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.get("/{campaign_id}/streams", response_model=list[LocalStreamOut])
def list_local_streams(campaign_id: int, db: Session = Depends(get_db)):
    streams = campaign_edit.get_local_streams(db, campaign_id)
    return [_stream_out(s) for s in streams]


@router.post("/streams/{stream_id}/offers", response_model=LocalStreamOut)
def add_offer(stream_id: int, payload: AddOfferRequest, db: Session = Depends(get_db)):
    try:
        return _stream_out(campaign_edit.add_offer(db, stream_id, payload.offer_id))
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.delete("/streams/{stream_id}/offers/{offer_id}", response_model=LocalStreamOut)
def remove_offer(stream_id: int, offer_id: int, db: Session = Depends(get_db)):
    try:
        return _stream_out(campaign_edit.remove_offer(db, stream_id, offer_id))
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.post("/streams/{stream_id}/offers/{offer_id}/bring-back", response_model=LocalStreamOut)
def bring_back(stream_id: int, offer_id: int, db: Session = Depends(get_db)):
    try:
        return _stream_out(campaign_edit.bring_back_offer(db, stream_id, offer_id))
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.post("/streams/{stream_id}/offers/{offer_id}/pin", response_model=LocalStreamOut)
def pin_offer(stream_id: int, offer_id: int, payload: PinOfferRequest, db: Session = Depends(get_db)):
    try:
        return _stream_out(
            campaign_edit.pin_offer(db, stream_id, offer_id, payload.is_pinned, payload.share)
        )
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.post("/streams/{stream_id}/push", response_model=LocalStreamOut)
def push_stream(stream_id: int, db: Session = Depends(get_db)):
    try:
        return _stream_out(campaign_edit.push_stream(db, stream_id))
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.post("/streams/{stream_id}/cancel", response_model=LocalStreamOut)
def cancel_stream(stream_id: int, db: Session = Depends(get_db)):
    try:
        return _stream_out(campaign_edit.cancel_stream(db, stream_id))
    except KeitaroError as exc:
        raise _http_error(exc) from exc
