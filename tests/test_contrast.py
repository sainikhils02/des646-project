import numpy as np
import cv2

from design_assistant.audits.contrast import ContrastAuditor


def _make_panel(foreground_value: int) -> np.ndarray:
    image = np.full((120, 240, 3), 200, dtype=np.uint8)
    cv2.rectangle(image, (40, 40), (200, 80), (foreground_value,) * 3, thickness=-1)
    cv2.putText(image, "TEST", (60, 72), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (foreground_value,) * 3, 2)
    return image


def test_contrast_flags_low_contrast():
    auditor = ContrastAuditor(contrast_threshold=4.5)
    low_contrast = _make_panel(185)
    report = auditor.audit(low_contrast)
    assert report.violations, "Expected at least one contrast violation"


def test_contrast_passes_high_contrast():
    auditor = ContrastAuditor(contrast_threshold=4.5)
    high_contrast = _make_panel(0)
    report = auditor.audit(high_contrast)
    assert report.average_contrast >= 4.5
