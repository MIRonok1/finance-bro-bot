"""Task — единый результат генератора mental math."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Task:
    kind: str
    prompt: str
    answer: Decimal
    tolerance_pct: float
    explanation: str
