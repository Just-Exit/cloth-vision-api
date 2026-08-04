from __future__ import annotations

from uuid import UUID

from cloth_vision_api.application.errors import ConflictError, UnauthorizedError
from cloth_vision_api.domain.models import AuthIdentity, AuthProvider, User
from cloth_vision_api.ports.outbound import PasswordManager, Repository, TokenManager


class AuthService:
    def __init__(
        self,
        repository: Repository,
        password_manager: PasswordManager,
        token_manager: TokenManager,
    ) -> None:
        self.repository = repository
        self.password_manager = password_manager
        self.token_manager = token_manager

    def signup(self, email: str, password: str, nickname: str) -> tuple[User, str, int]:
        normalized_email = email.strip().lower()
        if self.repository.get_user_by_email(normalized_email):
            raise ConflictError("이미 사용 중인 이메일입니다.")

        user = self.repository.add_user(User(email=normalized_email, nickname=nickname))
        identity = AuthIdentity(
            user_id=user.id,
            provider=AuthProvider.LOCAL,
            subject=normalized_email,
            password_hash=self.password_manager.hash(password),
        )
        self.repository.add_auth_identity(identity)
        token, expires_in = self.token_manager.create_access_token(user.id)
        return user, token, expires_in

    def login(self, email: str, password: str) -> tuple[User, str, int]:
        normalized_email = email.strip().lower()
        identity = self.repository.get_auth_identity(AuthProvider.LOCAL.value, normalized_email)
        if (
            not identity
            or not identity.password_hash
            or not self.password_manager.verify(password, identity.password_hash)
        ):
            raise UnauthorizedError("이메일 또는 비밀번호가 올바르지 않습니다.")
        user = self.repository.get_user(identity.user_id)
        if not user:
            raise UnauthorizedError("사용자 계정을 찾을 수 없습니다.")
        token, expires_in = self.token_manager.create_access_token(user.id)
        return user, token, expires_in

    def user_from_token(self, token: str) -> User:
        user_id = self.token_manager.decode_user_id(token)
        user = self.repository.get_user(user_id)
        if not user:
            raise UnauthorizedError("유효하지 않은 인증 정보입니다.")
        return user

    def get_user(self, user_id: UUID) -> User:
        user = self.repository.get_user(user_id)
        if not user:
            raise UnauthorizedError("사용자 계정을 찾을 수 없습니다.")
        return user
