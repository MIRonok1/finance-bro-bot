"""Фаза 4: квиз/устный счёт в чате больше нет — main_menu() и кнопка
повторения в /stats должны либо вести прямо в Mini App (web_app-кнопка),
либо, если WEBAPP_URL не задан, показывать фолбэк без нерабочей ссылки."""

from app.handlers.stats import _review_keyboard
from app.keyboards import CB_MODULE_MOVED, CB_PORTFOLIO, main_menu


def test_main_menu_without_webapp_url_uses_fallback_callbacks():
    kb = main_menu(None)
    buttons = [row[0] for row in kb.inline_keyboard]

    theory, mental_math, portfolio = buttons
    assert theory.web_app is None
    assert theory.callback_data == CB_MODULE_MOVED
    assert mental_math.web_app is None
    assert mental_math.callback_data == CB_MODULE_MOVED
    assert portfolio.callback_data == CB_PORTFOLIO

    # без WEBAPP_URL нет и отдельной кнопки "Открыть приложение"
    assert len(kb.inline_keyboard) == 3


def test_main_menu_with_webapp_url_deep_links_into_app():
    kb = main_menu("https://example.netrun.io")
    theory, mental_math, portfolio, webapp = [row[0] for row in kb.inline_keyboard]

    assert theory.callback_data is None
    assert theory.web_app.url == "https://example.netrun.io#/theory"
    assert mental_math.callback_data is None
    assert mental_math.web_app.url == "https://example.netrun.io#/mental-math"
    assert portfolio.callback_data == CB_PORTFOLIO  # портфель не переехал
    assert webapp.web_app.url == "https://example.netrun.io"


def test_review_keyboard_deep_links_to_review_mode():
    kb = _review_keyboard("https://example.netrun.io")
    button = kb.inline_keyboard[0][0]
    assert button.web_app.url == "https://example.netrun.io#/theory/play?mode=review"
