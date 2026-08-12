from decimal import Decimal

import pytest

from app.portfolio.logic import (
    InsufficientFunds,
    InsufficientShares,
    TradeLimitExceeded,
    compute_buy,
    compute_sell,
    kopecks_to_rub,
    pnl_pct,
    rub_to_kopecks,
    total_equity_kopecks,
    unrealized_pnl_kopecks,
)


def test_rub_to_kopecks_and_back():
    assert rub_to_kopecks(Decimal("285.5")) == 28550
    assert kopecks_to_rub(28550) == Decimal("285.5")


def test_rub_to_kopecks_rounds_half_up():
    assert rub_to_kopecks(Decimal("1.005")) == 101  # 100.5 -> round half up -> 101


def test_compute_buy_first_purchase():
    result = compute_buy(
        cash_kopecks=100_000_00,
        holding_quantity=0,
        holding_avg_price_kopecks=0,
        price_kopecks=1000_00,
        quantity=10,
        total_equity_kopecks=100_000_00,
    )
    assert result.cost_kopecks == 10_000_00
    assert result.new_cash_kopecks == 90_000_00
    assert result.new_quantity == 10
    assert result.new_avg_price_kopecks == 1000_00


def test_compute_buy_averages_price_on_second_purchase():
    # уже держим 10 акций по 1000₽, докупаем 10 по 2000₽ -> средняя 1500₽
    result = compute_buy(
        cash_kopecks=1_000_000_00,
        holding_quantity=10,
        holding_avg_price_kopecks=1000_00,
        price_kopecks=2000_00,
        quantity=10,
        total_equity_kopecks=1_000_000_00,
    )
    assert result.new_quantity == 20
    assert result.new_avg_price_kopecks == 1500_00


def test_compute_buy_raises_on_insufficient_funds():
    # equity большое (в основном в других бумагах), поэтому лимит на сделку
    # не мешает — но свободных денег на покупку всё равно не хватает.
    with pytest.raises(InsufficientFunds):
        compute_buy(
            cash_kopecks=100_00,
            holding_quantity=0,
            holding_avg_price_kopecks=0,
            price_kopecks=1000_00,
            quantity=1,
            total_equity_kopecks=100_000_00,
        )


def test_compute_buy_raises_on_trade_limit():
    # лимит 50% от equity; пытаемся потратить 60%
    with pytest.raises(TradeLimitExceeded):
        compute_buy(
            cash_kopecks=1_000_000_00,
            holding_quantity=0,
            holding_avg_price_kopecks=0,
            price_kopecks=600_000_00,
            quantity=1,
            total_equity_kopecks=1_000_000_00,
        )


def test_compute_buy_allows_exactly_at_limit():
    result = compute_buy(
        cash_kopecks=1_000_000_00,
        holding_quantity=0,
        holding_avg_price_kopecks=0,
        price_kopecks=500_000_00,
        quantity=1,
        total_equity_kopecks=1_000_000_00,
    )
    assert result.cost_kopecks == 500_000_00


@pytest.mark.parametrize("quantity", [0, -1, -100])
def test_compute_buy_rejects_non_positive_quantity(quantity):
    with pytest.raises(ValueError):
        compute_buy(
            cash_kopecks=100_000_00,
            holding_quantity=0,
            holding_avg_price_kopecks=0,
            price_kopecks=100_00,
            quantity=quantity,
            total_equity_kopecks=100_000_00,
        )


def test_compute_sell_full_position():
    result = compute_sell(
        cash_kopecks=90_000_00, holding_quantity=10, price_kopecks=1200_00, quantity=10
    )
    assert result.proceeds_kopecks == 12_000_00
    assert result.new_cash_kopecks == 102_000_00
    assert result.new_quantity == 0


def test_compute_sell_partial_position():
    result = compute_sell(cash_kopecks=0, holding_quantity=10, price_kopecks=1000_00, quantity=4)
    assert result.new_quantity == 6
    assert result.new_cash_kopecks == 4000_00


def test_compute_sell_raises_when_selling_more_than_held():
    with pytest.raises(InsufficientShares):
        compute_sell(cash_kopecks=0, holding_quantity=5, price_kopecks=100_00, quantity=6)


@pytest.mark.parametrize("quantity", [0, -1])
def test_compute_sell_rejects_non_positive_quantity(quantity):
    with pytest.raises(ValueError):
        compute_sell(cash_kopecks=0, holding_quantity=10, price_kopecks=100_00, quantity=quantity)


def test_unrealized_pnl_positive_and_negative():
    assert (
        unrealized_pnl_kopecks(
            quantity=10, avg_price_kopecks=1000_00, current_price_kopecks=1200_00
        )
        == 2000_00
    )
    assert (
        unrealized_pnl_kopecks(
            quantity=10, avg_price_kopecks=1200_00, current_price_kopecks=1000_00
        )
        == -2000_00
    )
    assert (
        unrealized_pnl_kopecks(
            quantity=10, avg_price_kopecks=1000_00, current_price_kopecks=1000_00
        )
        == 0
    )


def test_total_equity_kopecks():
    assert (
        total_equity_kopecks(cash_kopecks=50_000_00, holdings_value_kopecks=30_000_00) == 80_000_00
    )


@pytest.mark.parametrize(
    "open_value, current_value, expected",
    [
        (Decimal(1000), Decimal(1100), Decimal(10)),
        (Decimal(1000), Decimal(900), Decimal(-10)),
        (Decimal(1000), Decimal(1000), Decimal(0)),
        (Decimal(0), Decimal(1000), Decimal(0)),  # деление на ноль -> 0, не exception
    ],
)
def test_pnl_pct(open_value, current_value, expected):
    assert pnl_pct(open_value, current_value) == expected
