import random
from decimal import Decimal

import pytest

from app.mental_math.answer_check import check_answer
from app.mental_math.generators import TASK_GENERATORS, generate_task, random_task

ALL_KINDS = list(TASK_GENERATORS)


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
def test_generate_task_produces_well_formed_task(kind, difficulty):
    rng = random.Random(f"{kind}-{difficulty}")
    for _ in range(20):
        task = generate_task(kind, difficulty, rng)
        assert task.kind == kind
        assert task.prompt.strip()
        assert task.explanation.strip()
        assert task.tolerance_pct > 0
        assert isinstance(task.answer, Decimal)


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_generated_answer_is_self_consistent(kind):
    """Ответ, который сам генератор считает верным, должен проходить проверку
    допуска, если пользователь введёт его же (в т.ч. с округлением до 2 знаков)."""
    rng = random.Random(f"consistency-{kind}")
    for _ in range(30):
        task = generate_task(kind, 3, rng)
        rounded = task.answer.quantize(Decimal("0.01"))
        assert check_answer(task, str(rounded))


def test_generate_task_is_deterministic_with_seeded_rng():
    task1 = generate_task("percent_of_number", 2, random.Random(42))
    task2 = generate_task("percent_of_number", 2, random.Random(42))
    assert task1 == task2


def test_random_task_picks_from_all_kinds():
    rng = random.Random(1)
    seen = {random_task(3, rng).kind for _ in range(100)}
    assert seen == set(ALL_KINDS)


def test_unknown_kind_raises():
    with pytest.raises(KeyError):
        generate_task("nonexistent", 1)
