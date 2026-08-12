"""Клавиатуры квиза."""

from __future__ import annotations

import json

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app import texts
from app.quiz.repo import Question, Topic

CB_PREFIX = "quiz"
CB_TOPIC = f"{CB_PREFIX}:topic"
CB_DIFF = f"{CB_PREFIX}:diff"
CB_MCQ = f"{CB_PREFIX}:mcq"
CB_OPEN_RATE = f"{CB_PREFIX}:rate"
CB_NEXT = f"{CB_PREFIX}:next"
CB_BACK_TO_MENU = f"{CB_PREFIX}:back"
CB_START_REVIEW = f"{CB_PREFIX}:review"

DIFF_ANY = "any"


def topics_keyboard(topics: list[Topic]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t.title, callback_data=f"{CB_TOPIC}:{t.id}")] for t in topics
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def difficulty_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=str(d), callback_data=f"{CB_DIFF}:{d}") for d in range(1, 6)],
        [InlineKeyboardButton(text=texts.QUIZ_DIFF_ANY, callback_data=f"{CB_DIFF}:{DIFF_ANY}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def mcq_keyboard(question: Question) -> InlineKeyboardMarkup:
    options = json.loads(question.options_json) if question.options_json else []
    rows = [
        [
            InlineKeyboardButton(
                text=f"{o['key']}. {o['text']}", callback_data=f"{CB_MCQ}:{o['key']}"
            )
        ]
        for o in options
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def open_rating_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.QUIZ_RATE_CORRECT, callback_data=f"{CB_OPEN_RATE}:correct"
                ),
                InlineKeyboardButton(
                    text=texts.QUIZ_RATE_PARTIAL, callback_data=f"{CB_OPEN_RATE}:partial"
                ),
                InlineKeyboardButton(
                    text=texts.QUIZ_RATE_INCORRECT, callback_data=f"{CB_OPEN_RATE}:incorrect"
                ),
            ]
        ]
    )


def next_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=texts.QUIZ_NEXT, callback_data=CB_NEXT)]]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.QUIZ_BACK_TO_MENU, callback_data=CB_BACK_TO_MENU)]
        ]
    )


def review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.STATS_START_REVIEW_BUTTON, callback_data=CB_START_REVIEW
                )
            ]
        ]
    )
