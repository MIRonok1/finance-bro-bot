"""/review — админский флоу проверки черновиков вопросов: approve / edit /
reject. Ни один draft не попадает пользователям, пока не станет approved
(см. CLAUDE.md)."""

from __future__ import annotations

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import texts
from app.admin import repo as admin_repo
from app.admin.keyboards import CB_APPROVE, CB_EDIT, CB_REJECT, CB_SKIP, review_keyboard
from app.config import Settings
from app.handlers.filters import not_a_command

logger = logging.getLogger(__name__)

router = Router(name="review")


class ReviewStates(StatesGroup):
    reviewing = State()
    editing_body = State()


@router.message(Command("review"))
async def cmd_review(
    message: Message, db: aiosqlite.Connection, settings: Settings, state: FSMContext
) -> None:
    user = message.from_user
    if not user or user.id not in settings.admin_ids_set:
        await message.answer(texts.ADMIN_ACCESS_DENIED)
        return

    draft_ids = await admin_repo.list_draft_ids(db)
    if not draft_ids:
        await message.answer(texts.REVIEW_NO_DRAFTS)
        return

    await state.update_data(draft_ids=draft_ids, index=0)
    await state.set_state(ReviewStates.reviewing)
    await _show_current_draft(message, db, state)


async def _show_current_draft(
    message: Message, db: aiosqlite.Connection, state: FSMContext
) -> None:
    data = await state.get_data()
    ids: list[int] = data["draft_ids"]
    index: int = data["index"]

    if index >= len(ids):
        await message.answer(texts.REVIEW_DONE)
        await state.clear()
        return

    question = await admin_repo.get_any_question(db, ids[index])
    if question is None:
        # Вопрос могли удалить/изменить статус вручную между шагами — пропускаем.
        await state.update_data(index=index + 1)
        await _show_current_draft(message, db, state)
        return

    text = texts.REVIEW_CARD.format(
        i=index + 1,
        n=len(ids),
        id=question.id,
        type=question.type,
        difficulty=question.difficulty,
        body=question.body,
        explanation=question.explanation,
    )
    await message.answer(text, reply_markup=review_keyboard())


async def _act_and_advance(
    callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext, new_status: str
) -> None:
    data = await state.get_data()
    ids: list[int] = data["draft_ids"]
    question_id = ids[data["index"]]

    await admin_repo.set_status(db, question_id, new_status)
    await callback.answer(texts.REVIEW_STATUS_SET.format(status=new_status))
    await state.update_data(index=data["index"] + 1)
    await _show_current_draft(callback.message, db, state)


@router.callback_query(ReviewStates.reviewing, F.data == CB_APPROVE)
async def on_approve(callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext) -> None:
    await _act_and_advance(callback, db, state, "approved")


@router.callback_query(ReviewStates.reviewing, F.data == CB_REJECT)
async def on_reject(callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext) -> None:
    await _act_and_advance(callback, db, state, "rejected")


@router.callback_query(ReviewStates.reviewing, F.data == CB_SKIP)
async def on_skip(callback: CallbackQuery, db: aiosqlite.Connection, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.update_data(index=data["index"] + 1)
    await _show_current_draft(callback.message, db, state)


@router.callback_query(ReviewStates.reviewing, F.data == CB_EDIT)
async def on_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.answer(texts.REVIEW_SEND_NEW_BODY)
    await state.set_state(ReviewStates.editing_body)


@router.message(ReviewStates.editing_body, not_a_command)
async def on_new_body(message: Message, db: aiosqlite.Connection, state: FSMContext) -> None:
    new_body = (message.text or "").strip()
    if not new_body:
        await message.answer(texts.REVIEW_SEND_NEW_BODY)
        return

    data = await state.get_data()
    question_id = data["draft_ids"][data["index"]]
    await admin_repo.update_body(db, question_id, new_body)
    await message.answer(texts.REVIEW_BODY_UPDATED)

    await state.set_state(ReviewStates.reviewing)
    await _show_current_draft(message, db, state)
