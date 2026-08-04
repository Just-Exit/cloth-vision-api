from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from cloth_vision_core import Category
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from cloth_vision_api.adapters.outbound.database.orm import (
    AuthIdentityRow,
    ClosetRow,
    FashionItemRow,
    UserRow,
)
from cloth_vision_api.domain.models import (
    AuthIdentity,
    AuthProvider,
    Closet,
    FashionItem,
    ItemStatus,
    User,
)


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_database_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    _enable_sqlite_foreign_keys(engine)
    return engine


def _user(row: UserRow) -> User:
    return User(email=row.email, nickname=row.nickname, id=UUID(row.id), created_at=row.created_at)


def _closet(row: ClosetRow) -> Closet:
    return Closet(
        user_id=UUID(row.user_id),
        name=row.name,
        id=UUID(row.id),
        created_at=row.created_at,
    )


def _auth_identity(row: AuthIdentityRow) -> AuthIdentity:
    return AuthIdentity(
        user_id=UUID(row.user_id),
        provider=AuthProvider(row.provider),
        subject=row.subject,
        password_hash=row.password_hash,
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
        style_tags=list(row.style_tags or []),
        season_tags=list(row.season_tags or []),
        confidence=row.confidence,
        user_attributes=dict(row.user_attributes or {}),
        id=UUID(row.id),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_database_engine(database_url)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def add_user(self, user: User) -> User:
        with self._session() as session:
            session.add(
                UserRow(
                    id=str(user.id),
                    email=user.email,
                    nickname=user.nickname,
                    created_at=user.created_at,
                    updated_at=user.created_at,
                )
            )
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError("duplicate email") from exc
        return user

    def get_user(self, user_id: UUID) -> User | None:
        with self._session() as session:
            row = session.get(UserRow, str(user_id))
            return _user(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        with self._session() as session:
            row = session.scalar(select(UserRow).where(UserRow.email == email))
            return _user(row) if row else None

    def add_auth_identity(self, identity: AuthIdentity) -> AuthIdentity:
        with self._session() as session:
            session.add(
                AuthIdentityRow(
                    id=str(identity.id),
                    user_id=str(identity.user_id),
                    provider=identity.provider.value,
                    subject=identity.subject,
                    password_hash=identity.password_hash,
                    created_at=identity.created_at,
                )
            )
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError("duplicate auth identity") from exc
        return identity

    def get_auth_identity(self, provider: str, subject: str) -> AuthIdentity | None:
        with self._session() as session:
            row = session.scalar(
                select(AuthIdentityRow).where(
                    AuthIdentityRow.provider == provider,
                    AuthIdentityRow.subject == subject,
                )
            )
            return _auth_identity(row) if row else None

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
