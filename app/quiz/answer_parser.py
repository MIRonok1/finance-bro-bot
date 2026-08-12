"""Парсинг числовых ответов пользователя и сверка с допуском.

Правило из CLAUDE.md: числовые ответы сверяются с допуском (tolerance_pct),
а не на равенство. Парсер принимает '1,5', '1.5', '1 500 000', '1.5 млрд',
'1,5bn'. Деньги/проценты в этом модуле — Decimal, не float.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

# Суффиксы-множители, отсортированные по убыванию длины при поиске —
# чтобы 'млрд' не спутать с 'м' и т.п.
_MULTIPLIERS: dict[str, Decimal] = {
    "трлн": Decimal("1e12"),
    "trillion": Decimal("1e12"),
    "млрд": Decimal("1e9"),
    "billion": Decimal("1e9"),
    "bn": Decimal("1e9"),
    "млн": Decimal("1e6"),
    "million": Decimal("1e6"),
    "mm": Decimal("1e6"),
    "m": Decimal("1e6"),
    "тыс": Decimal("1e3"),
    "к": Decimal("1e3"),  # кириллическая "к" (тысяча), напр. "1.5к"
    "k": Decimal("1e3"),
}
_SUFFIXES_BY_LENGTH = sorted(_MULTIPLIERS, key=len, reverse=True)


def parse_numeric_answer(raw: str) -> Decimal | None:
    """Парсит текст ответа в Decimal или возвращает None, если не удалось."""
    if raw is None:
        return None
    s = raw.strip().lower().replace("\xa0", " ")
    if not s:
        return None

    negative = s.startswith("-")
    if negative:
        s = s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()

    s = s.replace("%", "").strip()

    multiplier = Decimal(1)
    for suffix in _SUFFIXES_BY_LENGTH:
        if s.endswith(suffix):
            candidate = s[: -len(suffix)].strip()
            # не отрезаем суффикс, если после этого не осталось цифр
            # (например слово "million" целиком без числа перед ним)
            if candidate and any(ch.isdigit() for ch in candidate):
                s = candidate
                multiplier = _MULTIPLIERS[suffix]
                break

    s = s.replace(" ", "")
    s = s.replace(",", ".")

    if s.count(".") > 1:
        return None
    if not s or not any(ch.isdigit() for ch in s):
        return None

    try:
        value = Decimal(s)
    except InvalidOperation:
        return None

    value *= multiplier
    if negative:
        value = -value
    return value


def is_within_tolerance(user_value: Decimal, correct_value: Decimal, tolerance_pct: float) -> bool:
    """Сверяет число с допуском в процентах от правильного ответа.

    Если правильный ответ равен нулю, допуск трактуется как абсолютный
    (в единицах ответа), иначе деление на ноль было бы некорректным.
    """
    tolerance = Decimal(str(tolerance_pct))
    if correct_value == 0:
        return abs(user_value) <= tolerance
    diff_pct = abs(user_value - correct_value) / abs(correct_value) * 100
    return diff_pct <= tolerance
