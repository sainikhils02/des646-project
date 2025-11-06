"""Contrast auditing powered by OpenCV."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class ContrastViolation:
    """Represents a detected or validated low-contrast region."""

    bbox: Optional[Tuple[int, int, int, int]] = None
    contrast_ratio: Optional[float] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        data: dict = {
            "contrast_ratio": self.contrast_ratio,
        }
        if self.bbox:
            x, y, w, h = self.bbox
            data["bbox"] = {"x": x, "y": y, "width": w, "height": h}
        if self.description:
            data["description"] = self.description
        return data


@dataclass(frozen=True)
class ContrastReport:
    """Summary of contrast measurements."""

    average_contrast: float
    violations: List[ContrastViolation]

    def to_dict(self) -> dict:
        return {
            "average_contrast": self.average_contrast,
            "violations": [violation.to_dict() for violation in self.violations],
        }


class ContrastAuditor:
    """Detects low-contrast text-like regions using simple heuristics."""

    def __init__(
        self,
        *,
        min_region_area: int = 200,
        contrast_threshold: float = 4.5,
        padding: int = 4,
    ) -> None:
        self.min_region_area = min_region_area
        self.contrast_threshold = contrast_threshold
        self.padding = padding

    def audit(self, image: np.ndarray) -> ContrastReport:
        if image is None or image.size == 0:
            raise ValueError("Empty image provided for contrast audit")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        normalized = gray.astype("float32") / 255.0
        blur = cv2.GaussianBlur(normalized, (5, 5), 0)
        gradients = cv2.Laplacian(blur, cv2.CV_32F)
        magnitude = cv2.convertScaleAbs(gradients)
        _, thresh = cv2.threshold(magnitude, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        violations: List[ContrastViolation] = []
        contrast_samples: List[float] = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h < self.min_region_area:
                continue

            roi = image[y : y + h, x : x + w]
            bg = self._extract_background(image, x, y, w, h)
            if roi.size == 0 or bg.size == 0:
                continue

            fg_luminance = self._relative_luminance(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
            bg_luminance = self._relative_luminance(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB))

            if fg_luminance is None or bg_luminance is None:
                continue

            l1, l2 = max(fg_luminance, bg_luminance), min(fg_luminance, bg_luminance)
            contrast_ratio = (l1 + 0.05) / (l2 + 0.05)
            contrast_samples.append(contrast_ratio)

            if contrast_ratio < self.contrast_threshold:
                violations.append(ContrastViolation(bbox=(x, y, w, h), contrast_ratio=contrast_ratio))

        average_contrast = float(np.mean(contrast_samples)) if contrast_samples else 0.0
        return ContrastReport(average_contrast=average_contrast, violations=violations)

    def _extract_background(self, image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
        pad = self.padding
        y1 = max(y - pad, 0)
        y2 = min(y + h + pad, image.shape[0])
        x1 = max(x - pad, 0)
        x2 = min(x + w + pad, image.shape[1])
        region = image[y1:y2, x1:x2]
        mask = np.ones(region.shape[:2], dtype=np.uint8) * 255
        mask[pad : pad + h, pad : pad + w] = 0
        fg_removed = cv2.inpaint(region, mask, 3, cv2.INPAINT_TELEA)
        return fg_removed

    def _relative_luminance(self, rgb: np.ndarray) -> Optional[float]:
        if rgb.size == 0:
            return None
        normalized = rgb.astype("float32") / 255.0
        coefficients = np.array([0.2126, 0.7152, 0.0722], dtype="float32")
        luminance = normalized @ coefficients
        if luminance.size == 0:
            return None
        return float(np.mean(luminance))
