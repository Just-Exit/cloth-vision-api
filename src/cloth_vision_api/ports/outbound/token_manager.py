from typing import Protocol
from uuid import UUID


class TokenManager(Protocol):
    def create_access_token(self, user_id: UUID) -> tuple[str, int]: ...
    def decode_user_id(self, token: str) -> UUID: ...
