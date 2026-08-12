"""Проверка ответа пользователя на задачу mental math.

Переиспользует парсер чисел из модуля квиза — формат ответа тот же
('1,5', '1.5', '1 500 000', '1.5 млрд', '1,5bn').
"""

from __future__ import annotations

from decimal import Decimal

from app.mental_math.engine import Task
from app.quiz.answer_parser import is_within_tolerance, parse_numeric_answer


def check_answer(task: Task, raw_answer: str) -> bool:
    parsed = parse_numeric_answer(raw_answer)
    if parsed is None:
        return False
    return is_within_tolerance(parsed, task.answer, task.tolerance_pct)


def parse_answer(raw_answer: str) -> Decimal | None:
    return parse_numeric_answer(raw_answer)
