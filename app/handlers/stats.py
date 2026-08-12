"""/stats — сводная статистика: темы квиза, mental math, дневная серия,
вопросы на повторение (упрощённый SM-2) с возможностью сразу их пройти."""

from __future__ import annotations

import uuid

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.db import get_daily_streak
from app.handlers.quiz import QuizStates, _send_question
from app.mental_math import repo as mm_repo
from app.quiz import repo as quiz_repo
from app.quiz.keyboards import CB_START_REVIEW, review_keyboard

router = Router(name="stats")


def _render_stats(
    topic_rows: list[tuple[str, int, int]],
    mm_best: int,
    mm_total: int,
    mm_correct: int,
    daily_streak: int,
    due_count: int,
) -> str:
    lines = [texts.STATS_HEADER, "", texts.STATS_QUIZ_HEADER]
    if not topic_rows:
        lines.append(texts.STATS_NO_QUIZ_ATTEMPTS)
    else:
        for title, total, correct in topic_rows:
            pct = round(correct / total * 100) if total else 0
            marker = texts.STATS_WEAK_MARKER if quiz_repo.is_weak_topic(total, correct) else ""
            lines.append(
                texts.STATS_TOPIC_LINE.format(
                    title=title, correct=correct, total=total, pct=pct, weak_marker=marker
                )
            )

    lines += ["", texts.STATS_MENTAL_MATH_HEADER]
    if mm_total == 0:
        lines.append(texts.STATS_NO_MENTAL_MATH)
    else:
        mm_pct = round(mm_correct / mm_total * 100)
        lines.append(
            texts.STATS_MENTAL_MATH_LINE.format(
                total=mm_total, correct=mm_correct, pct=mm_pct, best=mm_best
            )
        )

    lines += ["", texts.STATS_DAILY_STREAK.format(streak=daily_streak)]
    lines.append(texts.STATS_DUE_REVIEW.format(count=due_count))
    return "\n".join(lines)


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: aiosqlite.Connection) -> None:
    user_id = message.from_user.id
    topic_rows = await quiz_repo.topic_stats(db, user_id)
    mm_best, mm_total, mm_correct = await mm_repo.get_stats(db, user_id)
    daily_streak = await get_daily_streak(db, user_id)
    due_count = await quiz_repo.count_due_questions(db, user_id)

    text = _render_stats(topic_rows, mm_best, mm_total, mm_correct, daily_streak, due_count)
    kb = review_keyboard() if due_count else None
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == CB_START_REVIEW)
async def on_start_review(
    callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext
) -> None:
    due_ids = await quiz_repo.get_due_question_ids(db, callback.from_user.id)
    await callback.answer()

    if not due_ids:
        await callback.message.answer(texts.STATS_NOTHING_TO_REVIEW)
        return

    session_id = uuid.uuid4().hex
    await state.update_data(
        question_ids=due_ids,
        index=0,
        session_id=session_id,
        correct_count=0,
    )
    await state.set_state(QuizStates.in_session)
    await _send_question(callback.message, db, state)
