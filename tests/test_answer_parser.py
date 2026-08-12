from decimal import Decimal

import pytest

from app.quiz.answer_parser import is_within_tolerance, parse_numeric_answer


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1,5", Decimal("1.5")),
        ("1.5", Decimal("1.5")),
        ("1 500 000", Decimal("1500000")),
        ("1.5 млрд", Decimal("1.5e9")),
        ("1,5bn", Decimal("1.5e9")),
        ("1.5 млн", Decimal("1.5e6")),
        ("10", Decimal("10")),
        ("-3.2", Decimal("-3.2")),
        ("+3.2", Decimal("3.2")),
        ("12%", Decimal("12")),
        ("2.04", Decimal("2.04")),
        ("40", Decimal("40")),
        ("410", Decimal("410")),
        ("1020", Decimal("1020")),
        ("8", Decimal("8")),
        ("1.5к", Decimal("1500")),
    ],
)
def test_parse_numeric_answer_valid(raw, expected):
    assert parse_numeric_answer(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "abc", "не число", None, "1.2.3"])
def test_parse_numeric_answer_invalid(raw):
    assert parse_numeric_answer(raw) is None


def test_is_within_tolerance_exact_match():
    assert is_within_tolerance(Decimal("10"), Decimal("10"), 1)


def test_is_within_tolerance_within_range():
    assert is_within_tolerance(Decimal("10.05"), Decimal("10"), 1)


def test_is_within_tolerance_outside_range():
    assert not is_within_tolerance(Decimal("10.5"), Decimal("10"), 1)


def test_is_within_tolerance_zero_correct_value_uses_absolute():
    assert is_within_tolerance(Decimal("0.5"), Decimal("0"), 1)
    assert not is_within_tolerance(Decimal("2"), Decimal("0"), 1)
