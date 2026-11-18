from fastapi import APIRouter, HTTPException, Query

from app.schemas import MetaItem, OfferOut
from app.services.keitaro import KeitaroClient, KeitaroError

router = APIRouter(prefix="/api/meta", tags=["meta"])


def _http_error(exc: KeitaroError) -> HTTPException:
    return HTTPException(status_code=exc.status_code or 502, detail=str(exc))


@router.get("/offers", response_model=list[OfferOut])
def list_offers(q: str | None = Query(default=None), limit: int = Query(default=100, le=500)):
    try:
        with KeitaroClient() as client:
            offers = client.list_offers(limit=500)
        if q:
            needle = q.lower()
            offers = [
                o
                for o in offers
                if needle in str(o.get("name", "")).lower() or needle in str(o.get("id"))
            ]
        offers = offers[:limit]
        return [
            OfferOut(
                id=o["id"],
                name=o.get("name") or str(o["id"]),
                state=o.get("state"),
                country=o.get("country"),
            )
            for o in offers
        ]
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.get("/domains", response_model=list[MetaItem])
def list_domains():
    try:
        with KeitaroClient() as client:
            items = client.list_domains()
        return [MetaItem(id=i["id"], name=i.get("name") or str(i["id"])) for i in items]
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.get("/groups", response_model=list[MetaItem])
def list_groups():
    try:
        with KeitaroClient() as client:
            items = client.list_groups("campaigns")
        return [MetaItem(id=i["id"], name=i.get("name") or str(i["id"])) for i in items]
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.get("/traffic-sources", response_model=list[MetaItem])
def list_sources():
    try:
        with KeitaroClient() as client:
            items = client.list_traffic_sources()
        return [MetaItem(id=i["id"], name=i.get("name") or str(i["id"])) for i in items]
    except KeitaroError as exc:
        raise _http_error(exc) from exc


@router.get("/health")
def keitaro_health():
    try:
        with KeitaroClient() as client:
            domains = client.list_domains()
        return {"ok": True, "domains": len(domains)}
    except KeitaroError as exc:
        raise _http_error(exc) from exc
