from pydantic import BaseModel, Field


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geo: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
        description="ISO country code, e.g. AU",
    )
    offer_id: int = Field(gt=0)


class CampaignCreateResponse(BaseModel):
    id: int
    name: str
    alias: str | None = None
    domain_id: int | None = None
    group_id: int | None = None
    traffic_source_id: int | None = None
    google_stream_id: int | None = None
    offers_stream_id: int | None = None
    campaign_url: str | None = None


class OfferOut(BaseModel):
    id: int
    name: str
    state: str | None = None
    country: list[str] | None = None


class CampaignOut(BaseModel):
    id: int
    name: str
    alias: str | None = None
    domain_id: int | None = None
    group_id: int | None = None
    traffic_source_id: int | None = None
    domain: str | None = None
    group: str | None = None
    state: str | None = None


class LocalOfferOut(BaseModel):
    id: int
    keitaro_offer_id: int
    name: str
    share: int
    is_pinned: bool
    status: str


class LocalStreamOut(BaseModel):
    id: int
    campaign_id: int
    keitaro_stream_id: int
    name: str
    has_offers: bool
    is_dirty: bool
    offers: list[LocalOfferOut] = []


class AddOfferRequest(BaseModel):
    offer_id: int = Field(gt=0)


class PinOfferRequest(BaseModel):
    is_pinned: bool
    share: int | None = Field(default=None, ge=0, le=100)


class MetaItem(BaseModel):
    id: int
    name: str


