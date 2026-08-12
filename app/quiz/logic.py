"""Оценка ответа пользователя по типу вопроса."""

from __future__ import annotations

from decimal import Decimal

from app.quiz.answer_parser import is_within_tolerance, parse_numeric_answer
from app.quiz.repo import Question


def grade_mcq(question: Question, chosen_key: str) -> bool:
    return question.correct_key is not None and chosen_key == question.correct_key


def grade_numeric(question: Question, raw_answer: str) -> tuple[bool, Decimal | None]:
    """Возвращает (is_correct, распарсенное_значение_или_None)."""
    parsed = parse_numeric_answer(raw_answer)
    if parsed is None or question.correct_answer is None or question.tolerance_pct is None:
        return False, parsed
    correct_value = parse_numeric_answer(question.correct_answer)
    if correct_value is None:
        return False, parsed
    return is_within_tolerance(parsed, correct_value, question.tolerance_pct), parsed


# Самооценка для open-вопросов: пользователь читает эталонный разбор и сам
# отмечает, насколько его ответ совпал. Засчитываем как верный только
# честный "Верно" — иначе легко обмануть собственную статистику, но это и
# не экзамен, а тренажёр, так что выбор оставляем пользователю.
OPEN_SELF_RATINGS = {
    "correct": True,
    "partial": False,
    "incorrect": False,
}


def grade_open(rating: str) -> bool:
    return OPEN_SELF_RATINGS.get(rating, False)
