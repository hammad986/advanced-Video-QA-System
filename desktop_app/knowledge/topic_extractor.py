from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TopicResult:
    title: str
    confidence: float


class TopicExtractor:
    TOPIC_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("Introduction", ("introduction", "overview", "what is", "let's take a look", "in this video")),
        ("Machine Learning Basics", ("machine learning", "learning algorithm", "supervised learning", "unsupervised learning")),
        ("Neural Networks", ("neural network", "deep learning", "hidden layer", "activation")),
        ("Model Evaluation", ("evaluation", "test set", "validation", "accuracy", "precision", "recall")),
        ("Training Process", ("training", "gradient", "loss", "optimize", "fit the model")),
        ("Data Preparation", ("data preparation", "features", "labels", "dataset", "cleaning")),
        ("Practical Advice", ("practical advice", "apply", "real-world", "success", "problems")),
    )

    def extract(self, text: str) -> TopicResult:
        lowered = text.lower()
        best_title = ""
        best_score = 0
        for title, keywords in self.TOPIC_RULES:
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score > best_score:
                best_title = title
                best_score = score
        if best_title:
            return TopicResult(best_title, min(0.95, 0.65 + (best_score * 0.1)))
        return TopicResult(self._fallback_title(text), 0.55)

    def _fallback_title(self, text: str) -> str:
        words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
        stopwords = {"the", "and", "for", "with", "that", "this", "from", "you", "are", "was", "were"}
        meaningful = [word for word in words if word.lower() not in stopwords]
        if not meaningful:
            return "Transcript Segment"
        return " ".join(meaningful[:4]).title()

