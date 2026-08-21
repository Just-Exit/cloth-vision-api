from uuid import UUID

from cloth_vision_core import Category
from sqlalchemy import delete, select

from cloth_vision_api.adapters.outbound.database.orm import ClosetRow, FashionItemRow
from cloth_vision_api.adapters.outbound.database.repositories.base import SqlAlchemyRepositoryBase
from cloth_vision_api.domain.models import Closet, FashionItem, ItemStatus


def _closet(row: ClosetRow) -> Closet:
    return Closet(
        user_id=UUID(row.user_id),
        name=row.name,
        id=UUID(row.id),
        created_at=row.created_at,
    )


def _item(row: FashionItemRow) -> FashionItem:
    return FashionItem(
        closet_id=UUID(row.closet_id),
        display_name=row.display_name,
        category=Category(row.category),
        subcategory=row.subcategory,
        status=ItemStatus(row.analysis_status),
        image_key=row.image_key,
        color_hex=row.color_hex,
        color_name=row.color_name,
        colors=list(row.colors or []),
        materials=list(row.materials or []),
        style_tags=list(row.style_tags or []),
        season_tags=list(row.season_tags or []),
        confidence=row.confidence,
        user_attributes=dict(row.user_attributes or {}),
        id=UUID(row.id),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyWardrobeRepository(SqlAlchemyRepositoryBase):
    def add_closet(self, closet: Closet) -> Closet:
        with self._session() as session:
            session.add(
                ClosetRow(
                    id=str(closet.id),
                    user_id=str(closet.user_id),
                    name=closet.name,
                    created_at=closet.created_at,
                    updated_at=closet.created_at,
                )
            )
        return closet

    def get_closet(self, closet_id: UUID) -> Closet | None:
        with self._session() as session:
            row = session.get(ClosetRow, str(closet_id))
            return _closet(row) if row else None

    def list_closets(self, user_id: UUID) -> list[Closet]:
        with self._session() as session:
            rows = session.scalars(
                select(ClosetRow)
                .where(ClosetRow.user_id == str(user_id))
                .order_by(ClosetRow.created_at)
            )
            return [_closet(row) for row in rows]

    def add_item(self, item: FashionItem) -> FashionItem:
        with self._session() as session:
            session.add(self._item_row(item))
        return item

    def get_item(self, item_id: UUID) -> FashionItem | None:
        with self._session() as session:
            row = session.get(FashionItemRow, str(item_id))
            return _item(row) if row else None

    def list_items(self, closet_id: UUID) -> list[FashionItem]:
        with self._session() as session:
            rows = session.scalars(
                select(FashionItemRow)
                .where(FashionItemRow.closet_id == str(closet_id))
                .order_by(FashionItemRow.created_at.desc())
            )
            return [_item(row) for row in rows]

    def save_item(self, item: FashionItem) -> FashionItem:
        with self._session() as session:
            row = session.get(FashionItemRow, str(item.id))
            if not row:
                raise ValueError("item does not exist")
            values = self._item_values(item)
            for key, value in values.items():
                setattr(row, key, value)
        return item

    def delete_item(self, item_id: UUID) -> bool:
        with self._session() as session:
            result = session.execute(
                delete(FashionItemRow).where(FashionItemRow.id == str(item_id))
            )
            return bool(result.rowcount)

    @staticmethod
    def _item_values(item: FashionItem) -> dict:
        return {
            "closet_id": str(item.closet_id),
            "display_name": item.display_name,
            "category": item.category.value,
            "subcategory": item.subcategory,
            "analysis_status": item.status.value,
            "image_key": item.image_key,
            "color_hex": item.color_hex,
            "color_name": item.color_name,
            "colors": item.colors,
            "materials": item.materials,
            "style_tags": item.style_tags,
            "season_tags": item.season_tags,
            "confidence": item.confidence,
            "user_attributes": item.user_attributes,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    @classmethod
    def _item_row(cls, item: FashionItem) -> FashionItemRow:
        return FashionItemRow(id=str(item.id), **cls._item_values(item))
