"""FSM-флоу модуля «Быстрый счёт»: сложность -> бесконечная сессия с таймером,
стриком и рейтингом по скорости, чекпоинты каждые 10 задач."""

from __future__ import annotations

import logging
import time
from decimal import Decimal

import aiosqlite
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.config import Settings
from app.db import touch_daily_streak
from app.keyboards import CB_MENTAL_MATH, main_menu
from app.mental_math import repo as mm_repo
from app.mental_math.answer_check import parse_answer
from app.mental_math.engine import Task
from app.mental_math.generators import fmt_decimal, random_task
from app.mental_math.keyboards import (
    CB_BACK_TO_MENU,
    CB_CONTINUE,
    CB_DIFF,
    CB_FINISH,
    CB_STOP,
    back_to_menu_keyboard,
    checkpoint_keyboard,
    difficulty_keyboard,
    stop_keyboard,
)
from app.payments.gate import check_and_consume
from app.payments.plans import FREE_DAILY_TASKS
from app.quiz.answer_parser import is_within_tolerance

logger = logging.getLogger(__name__)

router = Router(name="mental_math")

CHECKPOINT_EVERY = 10
FAST_THRESHOLD_S = 5
NORMAL_THRESHOLD_S = 15


class MentalMathStates(StatesGroup):
    choosing_difficulty = State()
    in_session = State()


def _serialize_task(task: Task) -> dict:
    return {
        "kind": task.kind,
        "answer": str(task.answer),
        "tolerance_pct": task.tolerance_pct,
        "explanation": task.explanation,
    }


def _speed_label(elapsed_s: float) -> str:
    s = f"{elapsed_s:.1f}"
    if elapsed_s < FAST_THRESHOLD_S:
        return texts.MM_SPEED_FAST.format(s=s)
    if elapsed_s < NORMAL_THRESHOLD_S:
        return texts.MM_SPEED_NORMAL.format(s=s)
    return texts.MM_SPEED_SLOW.format(s=s)


@router.callback_query(F.data == CB_MENTAL_MATH)
async def start_mental_math(
    callback: CallbackQuery, db: aiosqlite.Connection, settings: Settings, state: FSMContext
) -> None:
    allowed = await check_and_consume(db, callback.from_user.id, settings)
    await callback.answer()
    if not allowed:
        await callback.message.answer(texts.PAYWALL_LIMIT_REACHED.format(limit=FREE_DAILY_TASKS))
        return

    await callback.message.answer(texts.MM_CHOOSE_DIFFICULTY, reply_markup=difficulty_keyboard())
    await state.set_state(MentalMathStates.choosing_difficulty)


@router.callback_query(MentalMathStates.choosing_difficulty, F.data.startswith(f"{CB_DIFF}:"))
async def on_difficulty_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    difficulty = int(callback.data.split(":")[-1])
    await state.update_data(
        difficulty=difficulty, streak=0, session_best_streak=0, total=0, correct=0
    )
    await callback.answer()
    await state.set_state(MentalMathStates.in_session)
    await _send_task(callback.message, state)


async def _send_task(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    task = random_task(data["difficulty"])
    await state.update_data(current_task=_serialize_task(task), started_at=time.monotonic())
    await message.answer(task.prompt, reply_markup=stop_keyboard())


@router.message(MentalMathStates.in_session)
async def on_answer(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    data = await state.get_data()
    current = data.get("current_task")
    if not current:
        return

    elapsed_s = time.monotonic() - data["started_at"]
    raw_answer = message.text or ""
    parsed = parse_answer(raw_answer)
    if parsed is None:
        await message.answer(texts.MM_COULD_NOT_PARSE)
        return

    correct_value = Decimal(current["answer"])
    is_correct = is_within_tolerance(parsed, correct_value, current["tolerance_pct"])

    streak = data["streak"] + 1 if is_correct else 0
    session_best_streak = max(data["session_best_streak"], streak)
    total = data["total"] + 1
    correct_count = data["correct"] + (1 if is_correct else 0)

    await mm_repo.record_attempt(
        db,
        message.from_user.id,
        current["kind"],
        data["difficulty"],
        is_correct,
        int(elapsed_s * 1000),
    )
    best_streak, _, _ = await mm_repo.update_stats(db, message.from_user.id, is_correct, streak)
    await touch_daily_streak(db, message.from_user.id)

    await state.update_data(
        streak=streak,
        session_best_streak=session_best_streak,
        total=total,
        correct=correct_count,
        current_task=None,
    )

    lines = [
        texts.MM_CORRECT if is_correct else texts.MM_INCORRECT,
        texts.MM_YOUR_ANSWER.format(answer=raw_answer),
    ]
    if not is_correct:
        lines.append(texts.MM_CORRECT_ANSWER.format(answer=fmt_decimal(correct_value)))
    lines.append(current["explanation"])
    lines.append(f"{_speed_label(elapsed_s)} · {texts.MM_STREAK.format(streak=streak)}")
    await message.answer("\n".join(lines))

    if total % CHECKPOINT_EVERY == 0:
        await message.answer(
            texts.MM_CHECKPOINT.format(total=total, correct=correct_count, best_streak=best_streak),
            reply_markup=checkpoint_keyboard(),
        )
        return

    await _send_task(message, state)


@router.callback_query(MentalMathStates.in_session, F.data == CB_STOP)
async def on_stop(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _finish_session(callback.message, state)


@router.callback_query(F.data == CB_CONTINUE)
async def on_continue(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(MentalMathStates.in_session)
    await _send_task(callback.message, state)


@router.callback_query(F.data == CB_FINISH)
async def on_finish(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _finish_session(callback.message, state)


async def _finish_session(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    total = data.get("total", 0)
    correct = data.get("correct", 0)
    pct = round(correct / total * 100) if total else 0
    await message.answer(
        texts.MM_SESSION_DONE.format(
            total=total, correct=correct, pct=pct, best_streak=data.get("session_best_streak", 0)
        ),
        reply_markup=back_to_menu_keyboard(),
    )
    await state.clear()


@router.callback_query(F.data == CB_BACK_TO_MENU)
async def on_back_to_menu(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer(texts.START_GREETING, reply_markup=main_menu(settings.webapp_url))
