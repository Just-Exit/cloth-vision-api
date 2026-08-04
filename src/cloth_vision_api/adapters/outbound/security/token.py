from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError

from cloth_vision_api.application.errors import UnauthorizedError


class JwtTokenManager:
    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_access_token(self, user_id: UUID) -> tuple[str, int]:
        expires_in = self.expire_minutes * 60
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(user_id),
                "iat": now,
                "exp": now + timedelta(seconds=expires_in),
                "type": "access",
            },
            self.secret_key,
            algorithm=self.algorithm,
        )
        return token, expires_in

    def decode_user_id(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["sub", "exp", "type"]},
            )
            if payload["type"] != "access":
                raise UnauthorizedError("유효하지 않은 토큰 유형입니다.")
            return UUID(payload["sub"])
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise UnauthorizedError("유효하지 않거나 만료된 토큰입니다.") from exc
