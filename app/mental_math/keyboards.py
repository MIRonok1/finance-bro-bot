"""Клавиатуры модуля «Быстрый счёт»."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app import texts

CB_PREFIX = "mm"
CB_DIFF = f"{CB_PREFIX}:diff"
CB_STOP = f"{CB_PREFIX}:stop"
CB_CONTINUE = f"{CB_PREFIX}:continue"
CB_FINISH = f"{CB_PREFIX}:finish"
CB_BACK_TO_MENU = f"{CB_PREFIX}:back"


def difficulty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(d), callback_data=f"{CB_DIFF}:{d}") for d in range(1, 6)]
        ]
    )


def stop_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=texts.MM_STOP_BUTTON, callback_data=CB_STOP)]]
    )


def checkpoint_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.MM_CONTINUE, callback_data=CB_CONTINUE),
                InlineKeyboardButton(text=texts.MM_FINISH, callback_data=CB_FINISH),
            ]
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.MM_BACK_TO_MENU, callback_data=CB_BACK_TO_MENU)]
        ]
    )
