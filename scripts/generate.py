#!/usr/bin/env python3
"""Оффлайн-генерация вариаций вопросов через Anthropic API.

ВАЖНО (см. CLAUDE.md): LLM участвует ТОЛЬКО здесь, в админском CLI, и
никогда в рантайме бота. Берёт approved-вопрос как образец, просит модель
сделать N вариаций (другая формулировка, другие числа/дистракторы),
валидирует структуру каждой вариации и пишет их в БД со status='draft'.
Ни одна вариация не становится доступной пользователям, пока админ не
одобрит её через /review в боте (Веха 4).

Запуск:
    ANTHROPIC_API_KEY=... python scripts/generate.py --sample-id 3 --count 5
    python scripts/generate.py --sample-id 3 --count 5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
DEFAULT_DB_PATH = os.environ.get("DB_PATH", "/data/bot.db")

VALID_TYPES = {"mcq", "numeric", "open"}

# JSON Schema для structured outputs — модель обязана вернуть валидный
# по этой схеме JSON (см. output_config.format в Anthropic Messages API).
VARIATION_SCHEMA = {
    "type": "object",
    "properties": {
        "variations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["mcq", "numeric", "open"]},
                    "difficulty": {"type": "integer"},
                    "body": {"type": "string"},
                    "options": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["key", "text"],
                            "additionalProperties": False,
                        },
                    },
                    "correct_key": {"type": ["string", "null"]},
                    "correct_answer": {"type": ["string", "null"]},
                    "tolerance_pct": {"type": ["number", "null"]},
                    "explanation": {"type": "string"},
                },
                "required": [
                    "type",
                    "difficulty",
                    "body",
                    "options",
                    "correct_key",
                    "correct_answer",
                    "tolerance_pct",
                    "explanation",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["variations"],
    "additionalProperties": False,
}

SYSTEM_PROMPT_TEMPLATE = (
    "Ты помогаешь курировать банк вопросов для тренажёра подготовки к "
    "интервью в инвестбанкинг (DCF, мультипликаторы, LBO, accounting, M&A). "
    "Тебе дают образец approved-вопроса. Сделай {count} вариаций того же "
    "типа, темы и примерно того же уровня сложности: другая формулировка "
    "вопроса, другие числа (для numeric — обязательно пересчитай "
    "correct_answer под новые числа, не копируй старый ответ), другие "
    "дистракторы (для mcq). Правильный ответ должен быть математически и "
    "содержательно верным — это критично, ошибка здесь хуже, чем "
    "неудачная формулировка. Не выдумывай рыночные данные или «типичные» "
    "мультипликаторы — используй только внутреннюю логику финансовых "
    "формул и гипотетические числа, заданные в самом вопросе."
)


@dataclass
class SampleQuestion:
    id: int
    topic_id: int
    type: str
    difficulty: int
    body: str
    options_json: str | None
    correct_key: str | None
    correct_answer: str | None
    tolerance_pct: float | None
    explanation: str
    source: str | None


def fetch_sample(conn: sqlite3.Connection, question_id: int) -> SampleQuestion:
    row = conn.execute(
        "SELECT id, topic_id, type, difficulty, body, options_json, correct_key, "
        "correct_answer, tolerance_pct, explanation, source FROM questions "
        "WHERE id = ? AND status = 'approved'",
        (question_id,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"Вопрос id={question_id} не найден или не approved.")
    return SampleQuestion(*row)


def build_user_message(sample: SampleQuestion, count: int) -> str:
    payload = {
        "type": sample.type,
        "difficulty": sample.difficulty,
        "body": sample.body,
        "options": json.loads(sample.options_json) if sample.options_json else None,
        "correct_key": sample.correct_key,
        "correct_answer": sample.correct_answer,
        "tolerance_pct": sample.tolerance_pct,
        "explanation": sample.explanation,
    }
    return (
        f"Образец вопроса (JSON):\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        f"Сделай {count} вариаций."
    )


def validate_variation(v: dict) -> list[str]:
    """Возвращает список ошибок валидации (пустой список — вариация валидна).

    Это последний рубеж перед записью в БД: даже структурированный вывод
    модели может быть содержательно некорректным (например, correct_key,
    которого нет среди options), поэтому проверяем явно, а не доверяем
    вслепую."""
    errors: list[str] = []
    vtype = v.get("type")
    if vtype not in VALID_TYPES:
        errors.append(f"неизвестный type: {vtype!r}")
        return errors

    difficulty = v.get("difficulty")
    if (
        not isinstance(difficulty, int)
        or isinstance(difficulty, bool)
        or not (1 <= difficulty <= 5)
    ):
        errors.append(f"difficulty вне диапазона 1-5: {difficulty!r}")

    if not (v.get("body") or "").strip():
        errors.append("пустой body")
    if not (v.get("explanation") or "").strip():
        errors.append("пустой explanation")

    if vtype == "mcq":
        options = v.get("options")
        if not options or not isinstance(options, list) or len(options) < 2:
            errors.append("mcq требует options (минимум 2 варианта)")
        else:
            keys = {o.get("key") for o in options}
            if v.get("correct_key") not in keys:
                errors.append("correct_key не найден среди options")
    elif vtype == "numeric":
        if v.get("correct_answer") in (None, ""):
            errors.append("numeric требует correct_answer")
        if v.get("tolerance_pct") is None:
            errors.append("numeric требует tolerance_pct")
    else:  # open
        if v.get("correct_answer") in (None, ""):
            errors.append("open требует correct_answer (эталонный разбор)")

    return errors


def insert_draft(conn: sqlite3.Connection, topic_id: int, source: str, v: dict) -> int:
    options_json = json.dumps(v["options"], ensure_ascii=False) if v.get("options") else None
    cursor = conn.execute(
        """
        INSERT INTO questions
            (topic_id, type, difficulty, body, options_json, correct_key,
             correct_answer, tolerance_pct, explanation, source, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
        """,
        (
            topic_id,
            v["type"],
            v["difficulty"],
            v["body"],
            options_json,
            v.get("correct_key"),
            v.get("correct_answer"),
            v.get("tolerance_pct"),
            v["explanation"],
            source,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def call_claude(sample: SampleQuestion, count: int, model: str) -> dict:
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit(
            "Пакет anthropic не установлен. Установи dev-зависимости: "
            "pip install -r requirements-dev.txt"
        ) from exc

    client = anthropic.Anthropic()  # берёт ANTHROPIC_API_KEY из env
    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT_TEMPLATE.format(count=count),
        output_config={"format": {"type": "json_schema", "schema": VARIATION_SCHEMA}},
        messages=[{"role": "user", "content": build_user_message(sample, count)}],
    )
    if response.stop_reason == "refusal":
        raise SystemExit("Модель отказалась выполнить запрос (stop_reason=refusal).")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Генерирует вариации approved-вопроса через Claude и пишет их в "
            "БД со status='draft'. Ни одна вариация не идёт пользователям "
            "без ручного /review в боте."
        )
    )
    parser.add_argument(
        "--sample-id", type=int, required=True, help="id образца (status='approved')"
    )
    parser.add_argument(
        "--count", type=int, default=3, help="сколько вариаций сгенерировать (по умолчанию 3)"
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help=f"модель Claude (по умолчанию {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--db-path", default=DEFAULT_DB_PATH, help=f"путь к SQLite (по умолчанию {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="показать вариации, но не писать в БД"
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY не задан.")

    conn = sqlite3.connect(args.db_path)
    try:
        sample = fetch_sample(conn, args.sample_id)
        header = f"Образец #{sample.id} ({sample.type}, тема_id={sample.topic_id})"
        print(f"{header}: {sample.body[:80]}...")

        result = call_claude(sample, args.count, args.model)
        variations = result.get("variations", [])
        print(f"Получено вариаций: {len(variations)}")

        accepted, rejected = 0, 0
        for i, v in enumerate(variations, start=1):
            errors = validate_variation(v)
            if errors:
                rejected += 1
                print(f"  [{i}] ОТКЛОНЕНО: {'; '.join(errors)}")
                continue
            if args.dry_run:
                print(f"  [{i}] OK (dry-run, не записано): {v['body'][:80]}...")
            else:
                new_id = insert_draft(conn, sample.topic_id, f"generated_from_{sample.id}", v)
                print(f"  [{i}] OK -> questions.id={new_id} (status=draft)")
            accepted += 1

        print(f"\nИтого: принято {accepted}, отклонено {rejected}.")
        if not args.dry_run and accepted:
            print("Проверь черновики через /review в боте перед публикацией.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
