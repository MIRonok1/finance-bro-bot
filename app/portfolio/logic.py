"""Чистая логика симулятора портфеля: покупка/продажа/P&L. Никакого I/O —
только числа (int-копейки), поэтому легко и надёжно тестируется.

Деньги — целые копейки (int), никогда float (см. CLAUDE.md)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

INITIAL_CASH_KOPECKS = 100_000_000  # 1 000 000 ₽ виртуального капитала

# Лимит на одну сделку: не более 50% текущей стоимости портфеля за раз —
# простая защита от ставки «всё на одну акцию» (решение принято за вас,
# можно вынести в настройку позже).
MAX_ORDER_PCT_OF_EQUITY = Decimal("50")


class TradeError(Exception):
    """Базовая ошибка исполнения сделки — текст пригоден для показа пользователю."""


class InsufficientFunds(TradeError):
    pass


class InsufficientShares(TradeError):
    pass


class TradeLimitExceeded(TradeError):
    pass


def rub_to_kopecks(price_rub: Decimal) -> int:
    return int((price_rub * 100).to_integral_value(rounding=ROUND_HALF_UP))


def kopecks_to_rub(kopecks: int) -> Decimal:
    return Decimal(kopecks) / 100


@dataclass
class BuyResult:
    new_cash_kopecks: int
    new_quantity: int
    new_avg_price_kopecks: int
    cost_kopecks: int


@dataclass
class SellResult:
    new_cash_kopecks: int
    new_quantity: int
    proceeds_kopecks: int


def compute_buy(
    cash_kopecks: int,
    holding_quantity: int,
    holding_avg_price_kopecks: int,
    price_kopecks: int,
    quantity: int,
    total_equity_kopecks: int,
) -> BuyResult:
    if quantity <= 0:
        raise ValueError("quantity должно быть положительным")
    if price_kopecks <= 0:
        raise ValueError("price_kopecks должно быть положительным")

    cost = price_kopecks * quantity

    if total_equity_kopecks > 0:
        limit = (Decimal(total_equity_kopecks) * MAX_ORDER_PCT_OF_EQUITY / 100).to_integral_value(
            rounding=ROUND_HALF_UP
        )
        if Decimal(cost) > limit:
            raise TradeLimitExceeded(
                f"Сделка на {kopecks_to_rub(cost)}₽ превышает лимит "
                f"{MAX_ORDER_PCT_OF_EQUITY}% от портфеля ({kopecks_to_rub(int(limit))}₽)."
            )

    if cost > cash_kopecks:
        raise InsufficientFunds(
            f"Не хватает денег: нужно {kopecks_to_rub(cost)}₽, "
            f"доступно {kopecks_to_rub(cash_kopecks)}₽."
        )

    new_quantity = holding_quantity + quantity
    new_avg_price = (holding_avg_price_kopecks * holding_quantity + cost) // new_quantity

    return BuyResult(
        new_cash_kopecks=cash_kopecks - cost,
        new_quantity=new_quantity,
        new_avg_price_kopecks=new_avg_price,
        cost_kopecks=cost,
    )


def compute_sell(
    cash_kopecks: int,
    holding_quantity: int,
    price_kopecks: int,
    quantity: int,
) -> SellResult:
    if quantity <= 0:
        raise ValueError("quantity должно быть положительным")
    if price_kopecks <= 0:
        raise ValueError("price_kopecks должно быть положительным")
    if quantity > holding_quantity:
        raise InsufficientShares(
            f"В портфеле только {holding_quantity} шт., нельзя продать {quantity}."
        )

    proceeds = price_kopecks * quantity
    return SellResult(
        new_cash_kopecks=cash_kopecks + proceeds,
        new_quantity=holding_quantity - quantity,
        proceeds_kopecks=proceeds,
    )


def unrealized_pnl_kopecks(
    quantity: int, avg_price_kopecks: int, current_price_kopecks: int
) -> int:
    return (current_price_kopecks - avg_price_kopecks) * quantity


def total_equity_kopecks(cash_kopecks: int, holdings_value_kopecks: int) -> int:
    return cash_kopecks + holdings_value_kopecks


def pnl_pct(open_value: Decimal, current_value: Decimal) -> Decimal:
    """Изменение в % между открытием периода и текущим значением.
    Работает и для копеек портфеля, и для очков индекса — оба Decimal."""
    if open_value == 0:
        return Decimal(0)
    return (current_value - open_value) / open_value * 100
