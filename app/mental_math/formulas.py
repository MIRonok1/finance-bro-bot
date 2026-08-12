"""Чистые формулы mental math. Никакого LLM, никакой рандомизации — только
вычисление правильного ответа по явным параметрам. Эти функции покрыты
юнит-тестами напрямую (см. CLAUDE.md: «формулы покрыты юнит-тестами»).

Деньги/проценты — Decimal, не float. Единственное исключение — CAGR: n-й
корень не выражается точно через Decimal (нет общего nth-root), поэтому для
него используется временный мост через float внутри одной операции; ни один
денежный показатель как float не хранится и не сравнивается.
"""

from __future__ import annotations

from decimal import Decimal


def percent_of(base: Decimal, pct: Decimal) -> Decimal:
    """Сколько составляет pct% от base."""
    return base * pct / Decimal(100)


def reverse_ev_ebitda(ev: Decimal, multiple: Decimal) -> Decimal:
    """EBITDA по известным EV и мультипликатору EV/EBITDA."""
    return ev / multiple


def margin_pct(revenue: Decimal, profit: Decimal) -> Decimal:
    """Маржа (в %) = прибыль / выручка × 100."""
    return profit / revenue * Decimal(100)


def margin_delta_pp(
    revenue1: Decimal, profit1: Decimal, revenue2: Decimal, profit2: Decimal
) -> Decimal:
    """Изменение маржи между двумя периодами, в процентных пунктах."""
    return margin_pct(revenue2, profit2) - margin_pct(revenue1, profit1)


def dilution_pct(old_shares: Decimal, new_shares: Decimal) -> Decimal:
    """На сколько % размывается доля существующих акционеров при выпуске
    new_shares новых акций поверх old_shares существующих."""
    return new_shares / (old_shares + new_shares) * Decimal(100)


def npv(rate_pct: Decimal, cashflows: list[Decimal]) -> Decimal:
    """NPV списка денежных потоков, cashflows[0] — поток в момент t=0
    (обычно отрицательная инвестиция), cashflows[i] дисконтируется на i лет.
    Дисконтирование по целой степени — считается точно в Decimal."""
    rate = Decimal(1) + rate_pct / Decimal(100)
    total = Decimal(0)
    for t, cf in enumerate(cashflows):
        total += cf / (rate**t)
    return total


def cagr_pct(begin: Decimal, end: Decimal, years: int) -> Decimal:
    """CAGR (в %) = (end/begin)^(1/years) − 1, ×100.

    n-й корень считается через float-мост (Decimal не умеет произвольный
    корень), результат сразу переводится обратно в Decimal и округляется
    до 2 знаков — сам begin/end остаются Decimal на всём пути до этой точки.
    """
    ratio = float(end) / float(begin)
    growth = ratio ** (1 / years) - 1
    return Decimal(str(round(growth * 100, 2)))
