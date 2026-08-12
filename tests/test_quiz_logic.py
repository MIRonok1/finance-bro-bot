from app.quiz.logic import grade_mcq, grade_numeric, grade_open
from app.quiz.repo import Question


def _question(**overrides) -> Question:
    base = dict(
        id=1,
        topic_id=1,
        type="mcq",
        difficulty=2,
        body="body",
        options_json=None,
        correct_key=None,
        correct_answer=None,
        tolerance_pct=None,
        explanation="explanation",
        source=None,
        status="approved",
    )
    base.update(overrides)
    return Question(**base)


def test_grade_mcq_correct():
    q = _question(type="mcq", correct_key="A")
    assert grade_mcq(q, "A") is True


def test_grade_mcq_incorrect():
    q = _question(type="mcq", correct_key="A")
    assert grade_mcq(q, "B") is False


def test_grade_numeric_within_tolerance():
    q = _question(type="numeric", correct_answer="10", tolerance_pct=1)
    is_correct, parsed = grade_numeric(q, "10,05")
    assert is_correct is True
    assert parsed is not None


def test_grade_numeric_outside_tolerance():
    q = _question(type="numeric", correct_answer="10", tolerance_pct=1)
    is_correct, _ = grade_numeric(q, "12")
    assert is_correct is False


def test_grade_numeric_unparseable_answer():
    q = _question(type="numeric", correct_answer="10", tolerance_pct=1)
    is_correct, parsed = grade_numeric(q, "не число")
    assert is_correct is False
    assert parsed is None


def test_grade_open_ratings():
    assert grade_open("correct") is True
    assert grade_open("partial") is False
    assert grade_open("incorrect") is False
    assert grade_open("garbage") is False
