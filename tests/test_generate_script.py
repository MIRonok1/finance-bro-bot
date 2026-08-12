import json
import sqlite3

import pytest

from app.db import _discover_migrations
from scripts.generate import (
    build_user_message,
    fetch_sample,
    insert_draft,
    validate_variation,
)


def _sync_conn_from_migrations() -> sqlite3.Connection:
    """scripts/generate.py использует синхронный sqlite3 (админский CLI,
    не рантайм бота), поэтому применяем те же .sql-миграции синхронным
    драйвером вместо асинхронного app.db.apply_migrations."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for _version, path in _discover_migrations():
        conn.executescript(path.read_text(encoding="utf-8"))
    return conn


@pytest.fixture
def seeded_conn():
    conn = _sync_conn_from_migrations()
    yield conn
    conn.close()


def test_fetch_sample_returns_approved_question(seeded_conn):
    sample = fetch_sample(seeded_conn, 1)
    assert sample.id == 1
    assert sample.type in {"mcq", "numeric", "open"}


def test_fetch_sample_raises_on_missing_question(seeded_conn):
    with pytest.raises(SystemExit):
        fetch_sample(seeded_conn, 999999)


def test_build_user_message_includes_sample_body(seeded_conn):
    sample = fetch_sample(seeded_conn, 1)
    message = build_user_message(sample, count=5)
    assert sample.body in message
    assert "5 вариаций" in message


# --- validate_variation: критично для корректности контента ---

VALID_MCQ = {
    "type": "mcq",
    "difficulty": 2,
    "body": "Что из перечисленного?",
    "options": [{"key": "A", "text": "один"}, {"key": "B", "text": "два"}],
    "correct_key": "A",
    "correct_answer": None,
    "tolerance_pct": None,
    "explanation": "потому что",
}

VALID_NUMERIC = {
    "type": "numeric",
    "difficulty": 2,
    "body": "Посчитай EV/EBITDA.",
    "options": None,
    "correct_key": None,
    "correct_answer": "8",
    "tolerance_pct": 1,
    "explanation": "1200/150=8",
}

VALID_OPEN = {
    "type": "open",
    "difficulty": 3,
    "body": "Объясни разницу.",
    "options": None,
    "correct_key": None,
    "correct_answer": "Развёрнутый разбор.",
    "tolerance_pct": None,
    "explanation": "Развёрнутый разбор.",
}


@pytest.mark.parametrize("valid", [VALID_MCQ, VALID_NUMERIC, VALID_OPEN])
def test_validate_variation_accepts_well_formed(valid):
    assert validate_variation(valid) == []


def test_validate_variation_rejects_unknown_type():
    v = {**VALID_OPEN, "type": "essay"}
    errors = validate_variation(v)
    assert any("type" in e for e in errors)


@pytest.mark.parametrize("difficulty", [0, 6, -1, "два", None, True])
def test_validate_variation_rejects_bad_difficulty(difficulty):
    v = {**VALID_OPEN, "difficulty": difficulty}
    errors = validate_variation(v)
    assert any("difficulty" in e for e in errors)


def test_validate_variation_rejects_empty_body():
    v = {**VALID_OPEN, "body": "   "}
    assert any("body" in e for e in validate_variation(v))


def test_validate_variation_mcq_requires_two_options():
    v = {**VALID_MCQ, "options": [{"key": "A", "text": "один"}]}
    assert any("options" in e for e in validate_variation(v))


def test_validate_variation_mcq_correct_key_must_exist_in_options():
    v = {**VALID_MCQ, "correct_key": "Z"}
    assert any("correct_key" in e for e in validate_variation(v))


def test_validate_variation_numeric_requires_correct_answer():
    v = {**VALID_NUMERIC, "correct_answer": None}
    assert any("correct_answer" in e for e in validate_variation(v))


def test_validate_variation_numeric_requires_tolerance():
    v = {**VALID_NUMERIC, "tolerance_pct": None}
    assert any("tolerance_pct" in e for e in validate_variation(v))


def test_validate_variation_open_requires_correct_answer():
    v = {**VALID_OPEN, "correct_answer": None}
    assert any("correct_answer" in e for e in validate_variation(v))


# --- insert_draft: всегда status='draft', никогда сразу approved ---


def test_insert_draft_writes_status_draft(seeded_conn):
    new_id = insert_draft(seeded_conn, topic_id=1, source="test", v=VALID_MCQ)
    row = seeded_conn.execute(
        "SELECT status, type, options_json FROM questions WHERE id = ?", (new_id,)
    ).fetchone()
    assert row["status"] == "draft"
    assert row["type"] == "mcq"
    assert json.loads(row["options_json"]) == VALID_MCQ["options"]


def test_insert_draft_does_not_affect_approved_count(seeded_conn):
    before = seeded_conn.execute(
        "SELECT COUNT(*) FROM questions WHERE status='approved'"
    ).fetchone()[0]
    insert_draft(seeded_conn, topic_id=1, source="test", v=VALID_OPEN)
    after = seeded_conn.execute(
        "SELECT COUNT(*) FROM questions WHERE status='approved'"
    ).fetchone()[0]
    assert before == after
