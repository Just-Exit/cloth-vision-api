from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


class LocalImageStorage:
    _allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, item_id: UUID, filename: str, stream: BinaryIO) -> str:
        extension = Path(filename or "").suffix.lower()
        if extension not in self._allowed_extensions:
            extension = ".img"
        key = f"{item_id}/original{extension}"
        destination = self.path_for(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            shutil.copyfileobj(stream, output)
        return key

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("invalid storage key")
        return path

    def delete(self, key: str) -> None:
        path = self.path_for(key)
        if path.exists():
            path.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass
