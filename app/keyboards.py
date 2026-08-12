"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app import texts

CB_PORTFOLIO = "menu:portfolio"

# Фаза 4: квиз и устный счёт больше не хендлятся в чате — при заданном
# WEBAPP_URL кнопки меню открывают Mini App напрямую (web_app-кнопка,
# без callback_data). CB_MODULE_MOVED — фолбэк-заглушка на случай, если
# WEBAPP_URL не задан (например, до первого деплоя): вести пользователя
# нерабочей ссылкой нельзя, поэтому кнопка callback_data вместо web_app.
CB_MODULE_MOVED = "menu:module_moved"


def main_menu(webapp_url: str | None = None) -> InlineKeyboardMarkup:
    if webapp_url:
        theory_button = InlineKeyboardButton(
            text=texts.BTN_THEORY, web_app=WebAppInfo(url=f"{webapp_url}#/theory")
        )
        mental_math_button = InlineKeyboardButton(
            text=texts.BTN_MENTAL_MATH, web_app=WebAppInfo(url=f"{webapp_url}#/mental-math")
        )
    else:
        theory_button = InlineKeyboardButton(text=texts.BTN_THEORY, callback_data=CB_MODULE_MOVED)
        mental_math_button = InlineKeyboardButton(
            text=texts.BTN_MENTAL_MATH, callback_data=CB_MODULE_MOVED
        )

    rows = [
        [theory_button],
        [mental_math_button],
        [InlineKeyboardButton(text=texts.BTN_PORTFOLIO, callback_data=CB_PORTFOLIO)],
    ]
    # Кнопка "Открыть приложение" отдельно от двух выше — открывает Mini App
    # на стартовом экране (Профиль), а не на конкретном модуле.
    if webapp_url:
        rows.append(
            [InlineKeyboardButton(text=texts.BTN_WEBAPP, web_app=WebAppInfo(url=webapp_url))]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
