"""Генераторы задач mental math: рандомизируют параметры и передают их в
чистые формулы (app/mental_math/formulas.py) — эти формулы, а не человек и
не LLM, вычисляют правильный ответ. Модель здесь не участвует нигде.

rng — необязательный источник случайности (по умолчанию модуль `random`);
позволяет тестам передавать `random.Random(seed)` для детерминизма.
"""

from __future__ import annotations

import random as _random
from decimal import Decimal

from app.mental_math import formulas
from app.mental_math.engine import Task

RandomLike = _random.Random


def fmt_decimal(value: Decimal) -> str:
    """Человекочитаемое форматирование Decimal: без экспоненты и лишних нулей."""
    if value == value.to_integral_value():
        return str(value.to_integral_value())
    s = format(value.quantize(Decimal("0.01")), "f")
    return s.rstrip("0").rstrip(".")


def generate_percent_of_number(difficulty: int, rng: RandomLike | None = None) -> Task:
    rng = rng or _random
    if difficulty <= 2:
        pct = Decimal(rng.choice([5, 10, 15, 20, 25, 50]))
        base = Decimal(rng.randint(2, 50) * 10)
    elif difficulty <= 4:
        pct = Decimal(rng.choice([12, 18, 22, 35, 40, 60, 70, 85]))
        base = Decimal(rng.randint(50, 5000))
    else:
        pct = Decimal(rng.randint(1, 990)) / Decimal(10)
        base = Decimal(rng.randint(1000, 999_999)) / Decimal(10)

    answer = formulas.percent_of(base, pct)
    p, b, a = fmt_decimal(pct), fmt_decimal(base), fmt_decimal(answer)
    prompt = f"Сколько будет {p}% от {b}?"
    explanation = f"{p}% от {b} = {b} × {p} / 100 = {a}."
    return Task(
        kind="percent_of_number",
        prompt=prompt,
        answer=answer,
        tolerance_pct=1,
        explanation=explanation,
    )


def generate_reverse_ev_ebitda(difficulty: int, rng: RandomLike | None = None) -> Task:
    rng = rng or _random
    if difficulty <= 2:
        multiple = Decimal(rng.choice([4, 5, 6, 8, 10]))
        ebitda = Decimal(rng.randint(5, 200))
    elif difficulty <= 4:
        multiple = Decimal(rng.choice([65, 75, 85, 95])) / Decimal(10)
        ebitda = Decimal(rng.randint(20, 900))
    else:
        multiple = Decimal(rng.randint(30, 150)) / Decimal(10)
        ebitda = Decimal(rng.randint(10, 5000))

    ev = ebitda * multiple
    answer = formulas.reverse_ev_ebitda(ev, multiple)
    e, m, a = fmt_decimal(ev), fmt_decimal(multiple), fmt_decimal(answer)
    prompt = f"EV = ${e}m, мультипликатор EV/EBITDA = {m}x. Чему равна EBITDA (в $m)?"
    explanation = f"EBITDA = EV / мультипликатор = {e} / {m} = {a} млн $."
    return Task(
        kind="reverse_ev_ebitda",
        prompt=prompt,
        answer=answer,
        tolerance_pct=1,
        explanation=explanation,
    )


def generate_cagr(difficulty: int, rng: RandomLike | None = None) -> Task:
    rng = rng or _random
    if difficulty <= 2:
        years = 2
        rate = Decimal(rng.choice(["0.05", "0.10", "0.15", "0.20"]))
    elif difficulty <= 4:
        years = 3
        rate = Decimal(rng.choice(["0.05", "0.08", "0.10", "0.12"]))
    else:
        years = 4
        rate = Decimal(rng.choice(["0.06", "0.09", "0.11", "0.14"]))

    begin = Decimal(rng.randint(10, 500)) * 10
    end = begin * (Decimal(1) + rate) ** years
    answer = formulas.cagr_pct(begin, end, years)
    prompt = (
        f"Выручка выросла с ${fmt_decimal(begin)}m до ${fmt_decimal(end)}m за {years} года. "
        f"Посчитай CAGR (в %, округли до десятых)."
    )
    explanation = (
        f"CAGR = (Конец/Начало)^(1/{years}) − 1 = "
        f"({fmt_decimal(end)}/{fmt_decimal(begin)})^(1/{years}) − 1 ≈ {fmt_decimal(answer)}%."
    )
    return Task(kind="cagr", prompt=prompt, answer=answer, tolerance_pct=5, explanation=explanation)


def generate_margin_delta(difficulty: int, rng: RandomLike | None = None) -> Task:
    rng = rng or _random
    if difficulty <= 2:
        revenue = Decimal(rng.randint(10, 100)) * 10
        margin1 = Decimal(rng.choice([10, 20, 30, 40, 50]))
        delta = Decimal(rng.choice([-10, -5, 5, 10, 15]))
    elif difficulty <= 4:
        revenue = Decimal(rng.randint(50, 2000))
        margin1 = Decimal(rng.choice([12, 18, 22, 27, 33]))
        delta = Decimal(rng.choice([-8, -3, 3, 7, 11]))
    else:
        revenue = Decimal(rng.randint(100, 50_000))
        margin1 = Decimal(rng.randint(50, 450)) / Decimal(10)
        delta = Decimal(rng.choice([-75, -45, 35, 65, 95])) / Decimal(10)

    margin2 = margin1 + delta
    profit1 = formulas.percent_of(revenue, margin1)
    profit2 = formulas.percent_of(revenue, margin2)
    answer = formulas.margin_delta_pp(revenue, profit1, revenue, profit2)

    rv, p1, p2 = fmt_decimal(revenue), fmt_decimal(profit1), fmt_decimal(profit2)
    m1, m2, a = fmt_decimal(margin1), fmt_decimal(margin2), fmt_decimal(answer)
    prompt = (
        f"Год 1: выручка ${rv}m, прибыль ${p1}m. Год 2: выручка ${rv}m, прибыль ${p2}m. "
        f"На сколько п.п. изменилась маржа?"
    )
    explanation = (
        f"Маржа год1 = {p1}/{rv} × 100 = {m1}%. Маржа год2 = {p2}/{rv} × 100 = {m2}%. "
        f"Дельта = {m2} − {m1} = {a} п.п."
    )
    return Task(
        kind="margin_delta",
        prompt=prompt,
        answer=answer,
        tolerance_pct=15,
        explanation=explanation,
    )


def generate_dilution(difficulty: int, rng: RandomLike | None = None) -> Task:
    rng = rng or _random
    if difficulty <= 2:
        old = Decimal(rng.choice([80, 90, 75, 60, 50]))
        new = Decimal(rng.choice([20, 10, 25, 40, 50]))
    elif difficulty <= 4:
        old = Decimal(rng.randint(50, 500))
        new = Decimal(rng.randint(10, 200))
    else:
        old = Decimal(rng.randint(500, 50_000))
        new = Decimal(rng.randint(50, 20_000))

    answer = formulas.dilution_pct(old, new)
    o, n, a = fmt_decimal(old), fmt_decimal(new), fmt_decimal(answer)
    prompt = (
        f"У компании было {o}m акций. Выпустили ещё {n}m новых акций. "
        f"На сколько % размылась доля существующих акционеров?"
    )
    explanation = f"Доля новых акций = {n} / ({o} + {n}) × 100 = {a}%."
    return Task(
        kind="dilution", prompt=prompt, answer=answer, tolerance_pct=2, explanation=explanation
    )


def generate_npv(difficulty: int, rng: RandomLike | None = None) -> Task:
    rng = rng or _random
    if difficulty <= 2:
        years = 2
        rate = Decimal(rng.choice([10, 20, 25]))
    elif difficulty <= 4:
        years = 3
        rate = Decimal(rng.choice([10, 15, 20]))
    else:
        years = 3
        rate = Decimal(rng.choice([8, 12, 18]))

    investment = Decimal(rng.randint(2, 20)) * 50
    rate_mult = Decimal(1) + rate / Decimal(100)

    cashflows = [-investment]
    for t in range(1, years + 1):
        pv_component = Decimal(rng.randint(2, 20)) * 10
        raw_cf = (pv_component * rate_mult**t).quantize(Decimal("1"))
        cashflows.append(raw_cf)

    answer = formulas.npv(rate, cashflows)
    cf_text = ", ".join(
        f"год {i}: ${fmt_decimal(cf)}m" for i, cf in enumerate(cashflows[1:], start=1)
    )
    prompt = (
        f"Инвестиция сегодня: −${fmt_decimal(investment)}m. Денежные потоки — {cf_text}. "
        f"Ставка дисконтирования {fmt_decimal(rate)}%. Посчитай NPV (в $m)."
    )
    explanation = (
        f"NPV = сумма CFt / (1+r)^t по каждому году минус инвестиция ≈ {fmt_decimal(answer)} млн $."
    )
    return Task(kind="npv", prompt=prompt, answer=answer, tolerance_pct=8, explanation=explanation)


TASK_GENERATORS = {
    "percent_of_number": generate_percent_of_number,
    "reverse_ev_ebitda": generate_reverse_ev_ebitda,
    "cagr": generate_cagr,
    "margin_delta": generate_margin_delta,
    "dilution": generate_dilution,
    "npv": generate_npv,
}


def generate_task(kind: str, difficulty: int, rng: RandomLike | None = None) -> Task:
    return TASK_GENERATORS[kind](difficulty, rng)


def random_task(difficulty: int, rng: RandomLike | None = None) -> Task:
    rng = rng or _random
    kind = rng.choice(list(TASK_GENERATORS))
    return generate_task(kind, difficulty, rng)
