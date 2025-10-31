"""Utilities for loading screenshots from disk into OpenCV-friendly arrays."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class ScreenshotArtifacts:
    """Represents an image on disk and its numpy array representation."""

    path: Path
    image: np.ndarray


class ScreenshotLoader:
    """Loads screenshots from file paths or base64-encoded payloads."""

    def load_from_path(self, path: str | Path) -> ScreenshotArtifacts:
        path = Path(path)
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Unable to read screenshot at {path}")
        return ScreenshotArtifacts(path=path, image=image)

    def load_from_bytes(self, payload: bytes, *, output_path: Optional[Path] = None) -> ScreenshotArtifacts:
        array = np.frombuffer(payload, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image byte payload")
        if output_path is None:
            output_path = Path("outputs/screenshot.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), image)
        return ScreenshotArtifacts(path=output_path, image=image)

    def load_from_base64(self, data: str, *, output_path: Optional[Path] = None) -> ScreenshotArtifacts:
        raw = base64.b64decode(data)
        return self.load_from_bytes(raw, output_path=output_path)
