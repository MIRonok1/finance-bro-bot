"""Планы подписки, оплачиваемые Telegram Stars (валюта XTR).

Решение принято за тебя (MVP): один план и один лимит бесплатных задач в
день — оба легко расширить/поменять позже, не трогая остальной пейволл."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    code: str
    title: str
    description: str
    stars_price: int
    duration_days: int


MONTHLY_PLAN = Plan(
    code="monthly",
    title="Finance bro Pro — 1 месяц",
    description="Безлимитный доступ к «Теория и кейсы» и «Быстрый счёт» на 30 дней.",
    stars_price=100,
    duration_days=30,
)

PLANS: dict[str, Plan] = {MONTHLY_PLAN.code: MONTHLY_PLAN}

# Сколько бесплатных сессий (квиз/mental math) в день доступно без подписки,
# пока PAYWALL_ENABLED=true.
FREE_DAILY_TASKS = 5
