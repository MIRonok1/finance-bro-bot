"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app import texts

# callback_data модулей — стабильные строки, на них будут завязаны
# будущие хендлеры (Веха 1+).
CB_THEORY = "menu:theory"
CB_MENTAL_MATH = "menu:mental_math"
CB_PORTFOLIO = "menu:portfolio"


def main_menu(webapp_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=texts.BTN_THEORY, callback_data=CB_THEORY)],
        [InlineKeyboardButton(text=texts.BTN_MENTAL_MATH, callback_data=CB_MENTAL_MATH)],
        [InlineKeyboardButton(text=texts.BTN_PORTFOLIO, callback_data=CB_PORTFOLIO)],
    ]
    # web_app-кнопка требует непустого https-URL — без WEBAPP_URL просто не
    # показываем её, чтобы не давать пользователю нерабочую ссылку.
    if webapp_url:
        rows.append(
            [InlineKeyboardButton(text=texts.BTN_WEBAPP, web_app=WebAppInfo(url=webapp_url))]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
