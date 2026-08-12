"""Клавиатуры для админского /review."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CB_PREFIX = "review"
CB_APPROVE = f"{CB_PREFIX}:approve"
CB_REJECT = f"{CB_PREFIX}:reject"
CB_EDIT = f"{CB_PREFIX}:edit"
CB_SKIP = f"{CB_PREFIX}:skip"


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=CB_APPROVE),
                InlineKeyboardButton(text="✏️ Править", callback_data=CB_EDIT),
            ],
            [
                InlineKeyboardButton(text="❌ Отклонить", callback_data=CB_REJECT),
                InlineKeyboardButton(text="⏭ Пропустить", callback_data=CB_SKIP),
            ],
        ]
    )
