from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LocalStream(Base):
    """Local mirror of a Keitaro stream for draft editing."""

    __tablename__ = "local_streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    keitaro_stream_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    has_offers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    offers: Mapped[list["LocalOffer"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan", order_by="LocalOffer.id"
    )


class LocalOffer(Base):
    __tablename__ = "local_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("local_streams.id", ondelete="CASCADE"))
    keitaro_offer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    share: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    # active | removed

    stream: Mapped[LocalStream] = relationship(back_populates="offers")
