"""/stats — сводная статистика: темы квиза, mental math, дневная серия,
вопросы на повторение (упрощённый SM-2) со ссылкой пройти их в Mini App.

Само повторение (как и весь квиз/устный счёт) теперь проходит только в
Mini App (Фаза 4) — здесь только текстовая сводка + кнопка-переход."""

from __future__ import annotations

import aiosqlite
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app import texts
from app.config import Settings
from app.db import get_daily_streak
from app.mental_math import repo as mm_repo
from app.quiz import repo as quiz_repo

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


def _review_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.STATS_START_REVIEW_BUTTON,
                    web_app=WebAppInfo(url=f"{webapp_url}#/theory/play?mode=review"),
                )
            ]
        ]
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: aiosqlite.Connection, settings: Settings) -> None:
    user_id = message.from_user.id
    topic_rows = await quiz_repo.topic_stats(db, user_id)
    mm_best, mm_total, mm_correct = await mm_repo.get_stats(db, user_id)
    daily_streak = await get_daily_streak(db, user_id)
    due_count = await quiz_repo.count_due_questions(db, user_id)

    text = _render_stats(topic_rows, mm_best, mm_total, mm_correct, daily_streak, due_count)

    kb = None
    if due_count and settings.webapp_url:
        kb = _review_keyboard(settings.webapp_url)
    elif due_count:
        text += "\n" + texts.REVIEW_NEEDS_WEBAPP

    await message.answer(text, reply_markup=kb)
