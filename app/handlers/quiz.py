"""FSM-флоу модуля «Теория и кейсы»: тема -> сложность -> сессия -> результат."""

from __future__ import annotations

import logging
import uuid

import aiosqlite
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.config import Settings
from app.db import touch_daily_streak
from app.keyboards import CB_THEORY, main_menu
from app.payments.gate import check_and_consume
from app.payments.plans import FREE_DAILY_TASKS
from app.quiz import repo
from app.quiz.keyboards import (
    CB_BACK_TO_MENU,
    CB_DIFF,
    CB_MCQ,
    CB_NEXT,
    CB_OPEN_RATE,
    CB_TOPIC,
    DIFF_ANY,
    back_to_menu_keyboard,
    difficulty_keyboard,
    mcq_keyboard,
    next_keyboard,
    open_rating_keyboard,
    topics_keyboard,
)
from app.quiz.logic import grade_mcq, grade_numeric, grade_open

logger = logging.getLogger(__name__)

router = Router(name="quiz")


class QuizStates(StatesGroup):
    choosing_topic = State()
    choosing_difficulty = State()
    in_session = State()
    awaiting_open_rating = State()


@router.callback_query(F.data == CB_THEORY)
async def start_quiz(
    callback: CallbackQuery, db: aiosqlite.Connection, settings: Settings, state: FSMContext
) -> None:
    allowed = await check_and_consume(db, callback.from_user.id, settings)
    await callback.answer()
    if not allowed:
        await callback.message.answer(texts.PAYWALL_LIMIT_REACHED.format(limit=FREE_DAILY_TASKS))
        return

    topics = await repo.list_topics(db)
    await callback.message.answer(texts.QUIZ_CHOOSE_TOPIC, reply_markup=topics_keyboard(topics))
    await state.set_state(QuizStates.choosing_topic)


@router.callback_query(QuizStates.choosing_topic, F.data.startswith(f"{CB_TOPIC}:"))
async def on_topic_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    topic_id = int(callback.data.split(":")[-1])
    await state.update_data(topic_id=topic_id)
    await callback.answer()
    await callback.message.answer(texts.QUIZ_CHOOSE_DIFFICULTY, reply_markup=difficulty_keyboard())
    await state.set_state(QuizStates.choosing_difficulty)


@router.callback_query(QuizStates.choosing_difficulty, F.data.startswith(f"{CB_DIFF}:"))
async def on_difficulty_chosen(
    callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext
) -> None:
    raw = callback.data.split(":")[-1]
    difficulty = None if raw == DIFF_ANY else int(raw)
    data = await state.get_data()
    topic_id = data["topic_id"]

    question_ids = await repo.pick_session_question_ids(db, topic_id, difficulty)
    await callback.answer()

    if not question_ids:
        await callback.message.answer(texts.QUIZ_NO_QUESTIONS, reply_markup=difficulty_keyboard())
        return

    session_id = uuid.uuid4().hex
    await state.update_data(
        question_ids=question_ids,
        index=0,
        session_id=session_id,
        correct_count=0,
    )
    await state.set_state(QuizStates.in_session)
    await _send_question(callback.message, db, state)


async def _send_question(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    data = await state.get_data()
    question_ids: list[int] = data["question_ids"]
    index: int = data["index"]
    question_id = question_ids[index]

    question = await repo.get_question(db, question_id)
    if question is None:
        # Вопрос сняли с публикации между выбором и показом — пропускаем без штрафа.
        await _advance(message, db, state)
        return

    topic = await repo.get_topic(db, question.topic_id)
    header = texts.QUIZ_QUESTION_HEADER.format(
        i=index + 1,
        n=len(question_ids),
        topic=topic.title if topic else "?",
        difficulty=question.difficulty,
    )
    body = f"{header}\n\n{question.body}"

    if question.type == "mcq":
        await message.answer(body, reply_markup=mcq_keyboard(question))
    elif question.type == "numeric":
        await message.answer(body + texts.QUIZ_NUMERIC_HINT)
    else:
        await message.answer(body + texts.QUIZ_OPEN_HINT)


@router.callback_query(QuizStates.in_session, F.data.startswith(f"{CB_MCQ}:"))
async def on_mcq_answered(
    callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext
) -> None:
    chosen_key = callback.data.split(":")[-1]
    data = await state.get_data()
    question_id = data["question_ids"][data["index"]]

    question = await repo.get_question(db, question_id)
    await callback.answer()
    if question is None:
        await _advance(callback.message, db, state)
        return

    is_correct = grade_mcq(question, chosen_key)
    await repo.record_attempt(
        db, callback.from_user.id, question.id, data["session_id"], chosen_key, is_correct
    )
    await repo.upsert_review_after_attempt(db, callback.from_user.id, question.id, is_correct)
    await touch_daily_streak(db, callback.from_user.id)
    if is_correct:
        await state.update_data(correct_count=data["correct_count"] + 1)

    result_text = texts.QUIZ_CORRECT if is_correct else texts.QUIZ_INCORRECT
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"{result_text}\n{texts.QUIZ_YOUR_ANSWER.format(answer=chosen_key)}\n\n"
        f"{texts.QUIZ_EXPLANATION.format(explanation=question.explanation)}",
        reply_markup=next_keyboard(),
    )


@router.message(QuizStates.in_session)
async def on_free_text_answer(
    message: Message, db: aiosqlite.Connection, state: FSMContext
) -> None:
    data = await state.get_data()
    question_id = data["question_ids"][data["index"]]
    question = await repo.get_question(db, question_id)
    if question is None or question.type == "mcq":
        return

    raw_answer = message.text or ""

    if question.type == "numeric":
        is_correct, parsed = grade_numeric(question, raw_answer)
        if parsed is None:
            await message.answer(texts.QUIZ_COULD_NOT_PARSE)
            return
        await repo.record_attempt(
            db, message.from_user.id, question.id, data["session_id"], raw_answer, is_correct
        )
        await repo.upsert_review_after_attempt(db, message.from_user.id, question.id, is_correct)
        await touch_daily_streak(db, message.from_user.id)
        if is_correct:
            await state.update_data(correct_count=data["correct_count"] + 1)
        result_text = texts.QUIZ_CORRECT if is_correct else texts.QUIZ_INCORRECT
        await message.answer(
            f"{result_text}\n{texts.QUIZ_YOUR_ANSWER.format(answer=raw_answer)}\n\n"
            f"{texts.QUIZ_EXPLANATION.format(explanation=question.explanation)}",
            reply_markup=next_keyboard(),
        )
    else:  # open
        await state.update_data(pending_open_answer=raw_answer)
        await message.answer(
            f"{texts.QUIZ_EXPLANATION.format(explanation=question.explanation)}\n\n"
            f"{texts.QUIZ_RATE_YOURSELF}",
            reply_markup=open_rating_keyboard(),
        )
        await state.set_state(QuizStates.awaiting_open_rating)


@router.callback_query(QuizStates.awaiting_open_rating, F.data.startswith(f"{CB_OPEN_RATE}:"))
async def on_open_rated(
    callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext
) -> None:
    rating = callback.data.split(":")[-1]
    is_correct = grade_open(rating)
    data = await state.get_data()
    question_id = data["question_ids"][data["index"]]

    await repo.record_attempt(
        db,
        callback.from_user.id,
        question_id,
        data["session_id"],
        data.get("pending_open_answer"),
        is_correct,
    )
    await repo.upsert_review_after_attempt(db, callback.from_user.id, question_id, is_correct)
    await touch_daily_streak(db, callback.from_user.id)
    if is_correct:
        await state.update_data(correct_count=data["correct_count"] + 1)

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(QuizStates.in_session)
    await _advance(callback.message, db, state)


@router.callback_query(QuizStates.in_session, F.data == CB_NEXT)
async def on_next(callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext) -> None:
    await callback.answer()
    await _advance(callback.message, db, state)


async def _advance(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    data = await state.get_data()
    index = data["index"] + 1
    question_ids = data["question_ids"]

    if index >= len(question_ids):
        await message.answer(
            texts.QUIZ_SESSION_DONE.format(correct=data["correct_count"], total=len(question_ids)),
            reply_markup=back_to_menu_keyboard(),
        )
        await state.clear()
        return

    await state.update_data(index=index)
    await _send_question(message, db, state)


@router.callback_query(F.data == CB_BACK_TO_MENU)
async def on_back_to_menu(callback: CallbackQuery, settings: Settings, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await callback.message.answer(texts.START_GREETING, reply_markup=main_menu(settings.webapp_url))
