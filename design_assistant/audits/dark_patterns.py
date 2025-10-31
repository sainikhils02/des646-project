"""Detection of dark patterns using transformer models or keyword heuristics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    from transformers import pipeline
except ImportError:  # pragma: no cover - optional dependency
    pipeline = None


@dataclass(frozen=True)
class DarkPatternFlag:
    """Represents a suspected dark pattern segment."""

    label: str
    score: float
    text: str

    def to_dict(self) -> dict:
        return {"label": self.label, "score": self.score, "text": self.text}


@dataclass(frozen=True)
class DarkPatternReport:
    """Summary of NLP-based dark pattern detections."""

    score: float
    flags: List[DarkPatternFlag]
    raw_outputs: Optional[List[dict]]

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "flags": [flag.to_dict() for flag in self.flags],
            "raw_outputs": self.raw_outputs,
        }


class DarkPatternAuditor:
    """Uses transformers or heuristics to detect ethical UX violations."""

    def __init__(
        self,
        model_name_or_path: str = "",
        *,
        threshold: float = 0.5,
        labels: Optional[List[str]] = None,
    ) -> None:
        self.threshold = threshold
        self.labels = labels or ["Urgency", "Confirm-shaming", "Misdirection"]
        self._classifier = self._build_classifier(model_name_or_path)
        self._keyword_map = self._default_keyword_map()

    def audit(self, text: str) -> DarkPatternReport:
        if not text.strip():
            return DarkPatternReport(score=1.0, flags=[], raw_outputs=None)

        sentences = self._split_text(text)
        flags: List[DarkPatternFlag] = []
        raw_outputs: List[dict] = []

        if self._classifier is not None:
            for sentence in sentences:
                result = self._classifier(sentence)
                top = result[0]
                raw_outputs.append({"sentence": sentence, **top})
                label = top["label"].replace("LABEL_", "").strip()
                score = float(top.get("score", 0.0))
                if label in self.labels and score >= self.threshold:
                    flags.append(DarkPatternFlag(label=label, score=score, text=sentence))
        else:
            for sentence in sentences:
                label, score = self._heuristic_score(sentence)
                if label:
                    flags.append(DarkPatternFlag(label=label, score=score, text=sentence))

        violation_ratio = len(flags) / max(len(sentences), 1)
        ethical_score = max(0.0, 1.0 - violation_ratio)
        return DarkPatternReport(score=ethical_score, flags=flags, raw_outputs=raw_outputs or None)

    def _split_text(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _build_classifier(self, model_name_or_path: str):
        if pipeline is None:
            return None
        target = model_name_or_path or "distilbert-base-uncased-finetuned-sst-2-english"
        try:
            return pipeline("text-classification", model=target)
        except Exception:
            return None

    def _heuristic_score(self, sentence: str) -> tuple[str, float]:
        sentence_lower = sentence.lower()
        for label, keywords in self._keyword_map.items():
            hits = sum(keyword in sentence_lower for keyword in keywords)
            if hits:
                score = min(0.9, 0.4 + 0.2 * hits)
                return label, score
        return "", 0.0

    def _default_keyword_map(self) -> Dict[str, List[str]]:
        return {
            "Urgency": ["last chance", "limited time", "hurry", "expires soon"],
            "Confirm-shaming": ["are you sure", "don't miss", "you'll regret"],
            "Misdirection": ["preselected", "default", "hidden fee", "sneak"],
        }
