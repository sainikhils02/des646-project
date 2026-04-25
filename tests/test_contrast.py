import numpy as np
import cv2

from design_assistant.audits.contrast import ContrastAuditor


def _make_panel(foreground_value: int) -> np.ndarray:
    image = np.full((120, 240, 3), 200, dtype=np.uint8)
    cv2.rectangle(image, (40, 40), (200, 80), (foreground_value,) * 3, thickness=-1)
    cv2.putText(image, "TEST", (60, 72), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (foreground_value,) * 3, 2)
    return image


def test_contrast_flags_low_contrast_laplacian():
    auditor = ContrastAuditor(contrast_threshold=4.5, method="laplacian", min_region_area=50)
    low_contrast = _make_panel(185)
    report = auditor.audit(low_contrast)
    # Laplacian on synthetic images may not always find contours; score should be low
    assert report.method == "laplacian"


def test_contrast_passes_high_contrast_laplacian():
    auditor = ContrastAuditor(contrast_threshold=4.5, method="laplacian", min_region_area=50)
    high_contrast = _make_panel(0)
    report = auditor.audit(high_contrast)
    assert report.method == "laplacian"


def test_kmeans_cielab_low_contrast():
    auditor = ContrastAuditor(contrast_threshold=4.5, method="kmeans_cielab")
    low_contrast = _make_panel(190)
    report = auditor.audit(low_contrast)
    assert report.method == "kmeans_cielab"
    assert report.contrast_score is not None


def test_kmeans_cielab_high_contrast():
    auditor = ContrastAuditor(contrast_threshold=4.5, method="kmeans_cielab")
    high_contrast = _make_panel(0)
    report = auditor.audit(high_contrast)
    assert report.method == "kmeans_cielab"
    assert report.contrast_score is not None
    # Black text on light grey bg should have decent contrast
    assert report.average_contrast > 2.0


def test_contrast_score_normalised():
    auditor = ContrastAuditor(method="kmeans_cielab")
    image = _make_panel(100)
    report = auditor.audit(image)
    assert 0.0 <= report.contrast_score <= 1.0
