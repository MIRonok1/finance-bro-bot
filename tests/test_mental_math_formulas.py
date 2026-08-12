from decimal import Decimal

import pytest

from app.mental_math.formulas import (
    cagr_pct,
    dilution_pct,
    margin_delta_pp,
    margin_pct,
    npv,
    percent_of,
    reverse_ev_ebitda,
)

D = Decimal


@pytest.mark.parametrize(
    "base, pct, expected",
    [
        (D(100), D(10), D(10)),
        (D(200), D(25), D(50)),
        (D(50), D(50), D(25)),
        (D(1000), D(1), D(10)),
        (D(80), D("12.5"), D(10)),
        (D(37), D(50), D("18.5")),
        (D(0), D(20), D(0)),
        (D(100), D(0), D(0)),
        (D(250), D(4), D(10)),
        (D(60), D(150), D(90)),
        (D(1_500_000), D(10), D(150_000)),
    ],
)
def test_percent_of(base, pct, expected):
    assert percent_of(base, pct) == expected


@pytest.mark.parametrize(
    "ev, multiple, expected",
    [
        (D(400), D(8), D(50)),
        (D(1200), D(8), D(150)),
        (D(1000), D(10), D(100)),
        (D(560), D(8), D(70)),
        (D(100), D(5), D(20)),
        (D(750), D("7.5"), D(100)),
        (D(999), D(3), D(333)),
        (D(45), D(9), D(5)),
        (D(10), D(2), D(5)),
        (D(1), D(1), D(1)),
    ],
)
def test_reverse_ev_ebitda(ev, multiple, expected):
    assert reverse_ev_ebitda(ev, multiple) == expected


@pytest.mark.parametrize(
    "revenue, profit, expected",
    [
        (D(200), D(80), D(40)),
        (D(100), D(10), D(10)),
        (D(50), D(25), D(50)),
        (D(1000), D(150), D("15")),
        (D(400), D(0), D(0)),
        (D(100), D(100), D(100)),
        (D(250), D(-50), D(-20)),
        (D(80), D(4), D(5)),
        (D(300), D(90), D(30)),
        (D(1), D(1), D(100)),
    ],
)
def test_margin_pct(revenue, profit, expected):
    assert margin_pct(revenue, profit) == expected


@pytest.mark.parametrize(
    "revenue1, profit1, revenue2, profit2, expected_delta",
    [
        (D(200), D(80), D(220), D(110), D(10)),
        (D(100), D(10), D(100), D(20), D(10)),
        (D(100), D(20), D(100), D(10), D(-10)),
        (D(500), D(100), D(500), D(100), D(0)),
        (D(1000), D(300), D(1200), D(420), D(5)),
        (D(200), D(40), D(200), D(60), D(10)),
        (D(400), D(100), D(400), D(100), D(0)),
        (D(50), D(5), D(50), D(10), D(10)),
        (D(300), D(30), D(300), D(45), D(5)),
        (D(1000), D(500), D(1000), D(0), D(-50)),
    ],
)
def test_margin_delta_pp(revenue1, profit1, revenue2, profit2, expected_delta):
    assert margin_delta_pp(revenue1, profit1, revenue2, profit2) == expected_delta


@pytest.mark.parametrize(
    "old_shares, new_shares, expected",
    [
        (D(80), D(20), D(20)),
        (D(100), D(0), D(0)),
        (D(90), D(10), D(10)),
        (D(75), D(25), D(25)),
        (D(60), D(40), D(40)),
        (D(95), D(5), D(5)),
        (D(50), D(50), D(50)),
        (D(150), D(50), D(25)),
        (D(9), D(1), D(10)),
        (D(999), D(1), D("0.1")),
    ],
)
def test_dilution_pct(old_shares, new_shares, expected):
    assert dilution_pct(old_shares, new_shares) == expected


@pytest.mark.parametrize(
    "rate_pct, cashflows, expected",
    [
        (D(10), [D(-100), D(110)], D(0)),
        (D(0), [D(-50), D(20), D(30)], D(0)),
        (D(25), [D(-100), D(125)], D(0)),
        (D(100), [D(-100), D(200)], D(0)),
        (D(10), [D(-1000), D(550), D(605)], D(0)),
        (D(20), [D(-100), D(60), D(72)], D(0)),
        (D(0), [D(-100), D(100)], D(0)),
        (D(50), [D(-90), D(135)], D(0)),
        (D(10), [D(100)], D(100)),
        (D(10), [D(-100), D(110), D(0)], D(0)),
        (D(10), [D(100), D(110), D(121)], D(300)),
    ],
)
def test_npv(rate_pct, cashflows, expected):
    assert npv(rate_pct, cashflows) == expected


@pytest.mark.parametrize(
    "begin, end, years, expected",
    [
        (D(100), D("121"), 2, D(10)),
        (D(100), D("133.1"), 3, D(10)),
        (D(100), D(100), 1, D(0)),
        (D(100), D(200), 1, D(100)),
        (D(1000), D(1210), 2, D(10)),
        (D(50), D("60.5"), 2, D(10)),
        (D(100), D(110), 1, D(10)),
        (D(200), D(242), 2, D(10)),
        (D(100), D("146.41"), 4, D(10)),
        (D(100), D(90), 1, D(-10)),
    ],
)
def test_cagr_pct(begin, end, years, expected):
    assert cagr_pct(begin, end, years) == expected
