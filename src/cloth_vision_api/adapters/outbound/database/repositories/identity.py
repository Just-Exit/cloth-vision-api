from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from cloth_vision_api.adapters.outbound.database.orm import AuthIdentityRow, UserRow
from cloth_vision_api.adapters.outbound.database.repositories.base import SqlAlchemyRepositoryBase
from cloth_vision_api.domain.models import AuthIdentity, AuthProvider, User


def _user(row: UserRow) -> User:
    return User(email=row.email, nickname=row.nickname, id=UUID(row.id), created_at=row.created_at)


def _auth_identity(row: AuthIdentityRow) -> AuthIdentity:
    return AuthIdentity(
        user_id=UUID(row.user_id),
        provider=AuthProvider(row.provider),
        subject=row.subject,
        password_hash=row.password_hash,
        id=UUID(row.id),
        created_at=row.created_at,
    )


class SqlAlchemyIdentityRepository(SqlAlchemyRepositoryBase):
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
