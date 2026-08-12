"""Упрощённый SM-2 (SuperMemo 2) для интервального повторения вопросов.

Оригинальный SM-2 оценивает ответ по шкале качества 0-5. Наша проверка
ответа бинарна (верно/неверно), поэтому quality сведён к двум значениям —
это и есть то самое «упрощение», а формула интервалов и easiness factor
берутся из SM-2 без изменений.
"""

from __future__ import annotations

QUALITY_CORRECT = 5
QUALITY_INCORRECT = 2

MIN_EASINESS_FACTOR = 1.3
DEFAULT_EASINESS_FACTOR = 2.5


def sm2_update(
    easiness_factor: float, interval_days: int, repetitions: int, is_correct: bool
) -> tuple[float, int, int]:
    """Возвращает (новый EF, новый интервал в днях, новое число повторений)."""
    quality = QUALITY_CORRECT if is_correct else QUALITY_INCORRECT

    if quality >= 3:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = round(interval_days * easiness_factor)
        repetitions += 1
    else:
        repetitions = 0
        interval_days = 1

    easiness_factor = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if easiness_factor < MIN_EASINESS_FACTOR:
        easiness_factor = MIN_EASINESS_FACTOR

    return easiness_factor, interval_days, repetitions
