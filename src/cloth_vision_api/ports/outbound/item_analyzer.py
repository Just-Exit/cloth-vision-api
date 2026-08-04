from pathlib import Path
from typing import Protocol

from cloth_vision_core import AnalysisResult


class ItemAnalyzer(Protocol):
    def analyze(self, image_path: Path) -> AnalysisResult: ...
