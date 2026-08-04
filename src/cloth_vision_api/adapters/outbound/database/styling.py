from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloth_vision_api.adapters.outbound.database.base import JSON_VALUE, Base, utc_now

if TYPE_CHECKING:
    from cloth_vision_api.adapters.outbound.database.identity import UserRow
    from cloth_vision_api.adapters.outbound.database.wardrobe import FashionItemRow


class OutfitRow(Base):
    __tablename__ = "outfits"
    __table_args__ = (
        CheckConstraint("source IN ('ai', 'user')", name="valid_source"),
        CheckConstraint(
            "status IN ('draft', 'recommended', 'accepted', 'archived')",
            name="valid_status",
        ),
        CheckConstraint(
            "overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 100)",
            name="valid_overall_score",
        ),
        Index("ix_outfits_user_scheduled", "user_id", "scheduled_for"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(20), default="ai")
    status: Mapped[str] = mapped_column(String(30), default="recommended")
    scheduled_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    occasion: Mapped[str | None] = mapped_column(String(80), nullable=True)
    weather_snapshot: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    preference_snapshot: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_breakdown: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    recommendation_reasons: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    stylist_tip: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_version: Mapped[str] = mapped_column(String(40))
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[UserRow] = relationship(back_populates="outfits")
    item_links: Mapped[list[OutfitItemRow]] = relationship(
        back_populates="outfit", cascade="all, delete-orphan"
    )
    feedback: Mapped[list[OutfitFeedbackRow]] = relationship(
        back_populates="outfit", cascade="all, delete-orphan"
    )
    wear_events: Mapped[list[WearEventRow]] = relationship(back_populates="outfit")


class OutfitItemRow(Base):
    __tablename__ = "outfit_items"
    __table_args__ = (
        CheckConstraint(
            "role IN ('top', 'bottom', 'outer', 'shoes', 'accessory')",
            name="valid_role",
        ),
        CheckConstraint("position >= 0", name="nonnegative_position"),
    )

    outfit_id: Mapped[str] = mapped_column(
        ForeignKey("outfits.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[str] = mapped_column(
        ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(30))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    outfit: Mapped[OutfitRow] = relationship(back_populates="item_links")
    item: Mapped[FashionItemRow] = relationship(back_populates="outfit_links")


class OutfitFeedbackRow(Base):
    __tablename__ = "outfit_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "outfit_id", name="uq_outfit_feedback_user_outfit"),
        CheckConstraint("feedback_type IN ('like', 'dislike')", name="valid_feedback_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    outfit_id: Mapped[str] = mapped_column(ForeignKey("outfits.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    feedback_type: Mapped[str] = mapped_column(String(20))
    reason_tags: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    outfit: Mapped[OutfitRow] = relationship(back_populates="feedback")


class WearEventRow(Base):
    __tablename__ = "wear_events"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_wear_events_user_idempotency"),
        Index("ix_wear_events_user_worn", "user_id", "worn_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    outfit_id: Mapped[str] = mapped_column(
        ForeignKey("outfits.id", ondelete="RESTRICT"), index=True
    )
    worn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    weather_snapshot: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    occasion: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[UserRow] = relationship(back_populates="wear_events")
    outfit: Mapped[OutfitRow] = relationship(back_populates="wear_events")
    review: Mapped[OutfitReviewRow | None] = relationship(
        back_populates="wear_event", cascade="all, delete-orphan", uselist=False
    )


class OutfitReviewRow(Base):
    __tablename__ = "outfit_reviews"
    __table_args__ = (CheckConstraint("rating >= 1 AND rating <= 5", name="valid_rating"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    wear_event_id: Mapped[str] = mapped_column(
        ForeignKey("wear_events.id", ondelete="CASCADE"), unique=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    quick_tags: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    wear_event: Mapped[WearEventRow] = relationship(back_populates="review")


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_subscription_id", name="uq_subscriptions_provider_external"
        ),
        CheckConstraint(
            "status IN ('trialing', 'active', 'past_due', 'cancelled', 'expired')",
            name="valid_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    external_subscription_id: Mapped[str] = mapped_column(String(160))
    plan: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30))
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[UserRow] = relationship(back_populates="subscriptions")
