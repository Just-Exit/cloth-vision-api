from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloth_vision_api.adapters.outbound.database.base import JSON_VALUE, Base, utc_now

if TYPE_CHECKING:
    from cloth_vision_api.adapters.outbound.database.styling import (
        OutfitRow,
        SubscriptionRow,
        WearEventRow,
    )
    from cloth_vision_api.adapters.outbound.database.wardrobe import ClosetRow, ImportJobRow


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name="valid_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    auth_identities: Mapped[list[AuthIdentityRow]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshTokenRow]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped[UserProfileRow | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    preferences: Mapped[UserPreferenceRow | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    closets: Mapped[list[ClosetRow]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    import_jobs: Mapped[list[ImportJobRow]] = relationship(back_populates="user")
    outfits: Mapped[list[OutfitRow]] = relationship(back_populates="user")
    wear_events: Mapped[list[WearEventRow]] = relationship(back_populates="user")
    subscriptions: Mapped[list[SubscriptionRow]] = relationship(back_populates="user")


class AuthIdentityRow(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_auth_identity_provider_subject"),
        CheckConstraint(
            "provider IN ('local', 'apple', 'google', 'kakao')",
            name="valid_provider",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    subject: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[UserRow] = relationship(back_populates="auth_identities")


class RefreshTokenRow(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped[UserRow] = relationship(back_populates="refresh_tokens")
    replaced_by: Mapped[RefreshTokenRow | None] = relationship(remote_side="RefreshTokenRow.id")


class UserProfileRow(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "height_cm IS NULL OR (height_cm >= 80 AND height_cm <= 250)",
            name="valid_height_cm",
        ),
        CheckConstraint(
            "body_type IS NULL OR body_type IN ('straight', 'wave', 'natural')",
            name="valid_body_type",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    profile_image_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    gender_identity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    personal_colors: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[UserRow] = relationship(back_populates="profile")


class UserPreferenceRow(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    preferred_styles: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    disliked_styles: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    preferred_colors: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    fit_preferences: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    ai_settings: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    notification_settings: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped[UserRow] = relationship(back_populates="preferences")
