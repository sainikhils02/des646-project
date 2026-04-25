"""Contrast auditing powered by OpenCV with CIELAB + KMeans segmentation."""
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
    method: str = "laplacian"           # "laplacian" | "kmeans_cielab"
    contrast_score: Optional[float] = None  # normalised [0,1] score for DFS

    def to_dict(self) -> dict:
        return {
            "average_contrast": self.average_contrast,
            "violations": [violation.to_dict() for violation in self.violations],
            "method": self.method,
            "contrast_score": self.contrast_score,
        }


class ContrastAuditor:
    """Detects low-contrast text-like regions using multiple methods.

    Methods
    -------
    ``laplacian`` (default, original):
        Uses Laplacian edge detection to find text-like contours, then
        computes luminance contrast ratios per bounding box.

    ``kmeans_cielab``:
        Converts to CIELAB colour space, runs KMeans (k=3) to cluster
        foreground/background regions, and computes contrast between
        cluster centroids.
    """

    def __init__(
        self,
        *,
        min_region_area: int = 200,
        contrast_threshold: float = 4.5,
        padding: int = 4,
        method: str = "laplacian",
        n_clusters: int = 3,
    ) -> None:
        self.min_region_area = min_region_area
        self.contrast_threshold = contrast_threshold
        self.padding = padding
        self.method = method
        self.n_clusters = n_clusters

    def audit(self, image: np.ndarray) -> ContrastReport:
        if image is None or image.size == 0:
            raise ValueError("Empty image provided for contrast audit")

        if self.method == "kmeans_cielab":
            return self._audit_kmeans_cielab(image)
        return self._audit_laplacian(image)

    # ------------------------------------------------------------------
    # KMeans + CIELAB method
    # ------------------------------------------------------------------

    def _audit_kmeans_cielab(self, image: np.ndarray) -> ContrastReport:
        """Segment via KMeans in CIELAB and compute contrast between clusters."""
        # Downscale for performance (max 800px wide)
        scale = 1.0
        if image.shape[1] > 800:
            scale = 800.0 / image.shape[1]
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2Lab)
        pixels = lab.reshape(-1, 3).astype(np.float32)

        # KMeans clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0)
        _, labels, centroids = cv2.kmeans(
            pixels, self.n_clusters, None, criteria, 10, cv2.KMEANS_PP_CENTERS
        )
        labels = labels.flatten()

        # Convert centroids back to BGR for luminance calculation
        centroids_bgr = []
        for c in centroids:
            lab_pixel = np.array([[c]], dtype=np.float32)
            bgr_pixel = cv2.cvtColor(lab_pixel.astype(np.uint8), cv2.COLOR_Lab2BGR)
            centroids_bgr.append(bgr_pixel[0, 0])

        # Compute pairwise contrast ratios between centroids
        violations: List[ContrastViolation] = []
        contrast_ratios: List[float] = []

        for i in range(len(centroids_bgr)):
            for j in range(i + 1, len(centroids_bgr)):
                lum_i = self._srgb_relative_luminance(centroids_bgr[i])
                lum_j = self._srgb_relative_luminance(centroids_bgr[j])

                l1, l2 = max(lum_i, lum_j), min(lum_i, lum_j)
                ratio = (l1 + 0.05) / (l2 + 0.05)
                contrast_ratios.append(ratio)

                if ratio < self.contrast_threshold:
                    # Find spatial regions where these two clusters are adjacent
                    label_map = labels.reshape(image.shape[:2])
                    region_bboxes = self._find_cluster_boundary_regions(label_map, i, j, scale)
                    for bbox in region_bboxes[:3]:  # limit per pair
                        violations.append(ContrastViolation(
                            bbox=bbox,
                            contrast_ratio=round(ratio, 2),
                            description=f"Low contrast between colour clusters: {ratio:.2f}:1 "
                                        f"(WCAG AA requires {self.contrast_threshold}:1)",
                        ))

        avg_contrast = float(np.mean(contrast_ratios)) if contrast_ratios else 0.0

        # Normalise to [0,1] score
        # 21:1 is the maximum possible contrast (black/white)
        contrast_score = min(1.0, avg_contrast / 21.0)
        # Also penalise for violations
        if violations:
            violation_penalty = len(violations) / 10.0  # 10 violations = max penalty
            contrast_score = max(0.0, contrast_score - violation_penalty)

        return ContrastReport(
            average_contrast=avg_contrast,
            violations=violations,
            method="kmeans_cielab",
            contrast_score=max(0.0, min(1.0, contrast_score)),
        )

    def _find_cluster_boundary_regions(
        self, label_map: np.ndarray, cluster_a: int, cluster_b: int, scale: float
    ) -> List[Tuple[int, int, int, int]]:
        """Find bounding boxes where two clusters share a boundary."""
        h, w = label_map.shape
        boundary = np.zeros((h, w), dtype=np.uint8)

        mask_a = (label_map == cluster_a).astype(np.uint8)
        mask_b = (label_map == cluster_b).astype(np.uint8)

        # Dilate each mask and find overlap (boundary region)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated_a = cv2.dilate(mask_a, kernel, iterations=1)
        dilated_b = cv2.dilate(mask_b, kernel, iterations=1)
        boundary = cv2.bitwise_and(dilated_a, dilated_b)

        contours, _ = cv2.findContours(boundary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bboxes: List[Tuple[int, int, int, int]] = []
        for contour in contours:
            x, y, bw, bh = cv2.boundingRect(contour)
            if bw * bh >= self.min_region_area:
                # Scale back to original image coordinates
                inv = 1.0 / scale if scale > 0 else 1.0
                bboxes.append((int(x * inv), int(y * inv), int(bw * inv), int(bh * inv)))
        return bboxes

    @staticmethod
    def _srgb_relative_luminance(bgr: np.ndarray) -> float:
        """WCAG 2.1 relative luminance from a BGR pixel."""
        rgb = bgr[::-1].astype(np.float64) / 255.0
        linearised = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        return float(0.2126 * linearised[0] + 0.7152 * linearised[1] + 0.0722 * linearised[2])

    # ------------------------------------------------------------------
    # Original Laplacian method
    # ------------------------------------------------------------------

    def _audit_laplacian(self, image: np.ndarray) -> ContrastReport:
        """Original Laplacian edge-based contrast detection."""
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

        # Compute normalised score
        contrast_score = min(1.0, average_contrast / 21.0)
        if violations:
            violation_penalty = len(violations) / 10.0
            contrast_score = max(0.0, contrast_score - violation_penalty)

        return ContrastReport(
            average_contrast=average_contrast,
            violations=violations,
            method="laplacian",
            contrast_score=max(0.0, min(1.0, contrast_score)),
        )

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
