from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloth_vision_api.adapters.outbound.database.base import JSON_VALUE, Base, utc_now

if TYPE_CHECKING:
    from cloth_vision_api.adapters.outbound.database.identity import UserRow
    from cloth_vision_api.adapters.outbound.database.styling import OutfitItemRow


class ClosetRow(Base):
    __tablename__ = "closets"
    __table_args__ = (
        Index(
            "uq_closets_default_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default = 1"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    is_default: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[UserRow] = relationship(back_populates="closets")
    items: Mapped[list[FashionItemRow]] = relationship(
        back_populates="closet", cascade="all, delete-orphan"
    )
    import_jobs: Mapped[list[ImportJobRow]] = relationship(back_populates="closet")


class ImportJobRow(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('shopping_screenshot', 'ootd')",
            name="valid_source_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="valid_status",
        ),
        CheckConstraint("detected_item_count >= 0", name="nonnegative_detected_count"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    closet_id: Mapped[str] = mapped_column(ForeignKey("closets.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_key: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    detected_item_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[UserRow] = relationship(back_populates="import_jobs")
    closet: Mapped[ClosetRow] = relationship(back_populates="import_jobs")
    items: Mapped[list[FashionItemRow]] = relationship(back_populates="import_job")


class FashionItemRow(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint(
            "analysis_status IN ('processing', 'ready', 'failed')",
            name="valid_analysis_status",
        ),
        CheckConstraint(
            "lifecycle_status IN ('active', 'archived', 'donated', 'sold', 'discarded')",
            name="valid_lifecycle_status",
        ),
        CheckConstraint(
            "source_type IN ('camera', 'manual', 'shopping_screenshot', 'ootd')",
            name="valid_source_type",
        ),
        CheckConstraint("purchase_price IS NULL OR purchase_price >= 0", name="valid_price"),
        CheckConstraint("wear_count >= 0", name="nonnegative_wear_count"),
        Index("ix_items_closet_created", "closet_id", "created_at"),
        Index("ix_items_closet_category_created", "closet_id", "category", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    closet_id: Mapped[str] = mapped_column(ForeignKey("closets.id", ondelete="CASCADE"), index=True)
    import_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    collection_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(60), nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(30), default="processing", index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="manual")

    # Compatibility bridge until all image reads move to item_images.
    image_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    color_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    colors: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    materials: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    style_tags: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    season_tags: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_attributes: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)

    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    acquired_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    donated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_worn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wear_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    closet: Mapped[ClosetRow] = relationship(back_populates="items")
    import_job: Mapped[ImportJobRow | None] = relationship(back_populates="items")
    images: Mapped[list[ItemImageRow]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    analysis_jobs: Mapped[list[AnalysisJobRow]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    analyses: Mapped[list[ItemAnalysisRow]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    outfit_links: Mapped[list[OutfitItemRow]] = relationship(back_populates="item")


class ItemImageRow(Base):
    __tablename__ = "item_images"
    __table_args__ = (
        CheckConstraint(
            "image_type IN ('original', 'mask', 'transparent', 'normalized', 'thumbnail')",
            name="valid_image_type",
        ),
        CheckConstraint("width > 0 AND height > 0", name="positive_dimensions"),
        CheckConstraint("byte_size > 0", name="positive_byte_size"),
        UniqueConstraint("item_id", "image_type", name="uq_item_images_item_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    image_type: Mapped[str] = mapped_column(String(30))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(80))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    item: Mapped[FashionItemRow] = relationship(back_populates="images")


class AnalysisJobRow(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="valid_status",
        ),
        CheckConstraint("attempt > 0", name="positive_attempt"),
        UniqueConstraint("item_id", "attempt", name="uq_analysis_jobs_item_attempt"),
        Index("ix_analysis_jobs_status_queued", "status", "queued_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pipeline_version: Mapped[str] = mapped_column(String(40))
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    item: Mapped[FashionItemRow] = relationship(back_populates="analysis_jobs")
    analysis: Mapped[ItemAnalysisRow | None] = relationship(
        back_populates="analysis_job", cascade="all, delete-orphan", uselist=False
    )


class ItemAnalysisRow(Base):
    __tablename__ = "item_analyses"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="valid_confidence",
        ),
        Index("ix_item_analyses_item_created", "item_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    analysis_job_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), unique=True
    )
    model_name: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(80))
    pipeline_version: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(30))
    subcategory: Mapped[str | None] = mapped_column(String(60), nullable=True)
    materials: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    colors: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    style_tags: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    season_tags: Mapped[list] = mapped_column(JSON_VALUE, default=list)
    attributes: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_result: Mapped[dict] = mapped_column(JSON_VALUE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    item: Mapped[FashionItemRow] = relationship(back_populates="analyses")
    analysis_job: Mapped[AnalysisJobRow] = relationship(back_populates="analysis")
