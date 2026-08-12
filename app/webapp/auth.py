"""Валидация Telegram Mini App initData.

Алгоритм — из официальной документации Telegram Bot API (Web Apps):
data-check-string из отсортированных пар "key=value" (кроме hash),
HMAC-SHA256(secret_key, data-check-string), где
secret_key = HMAC-SHA256("WebAppData", bot_token). Стабилен с 2022 года.

TODO: verify — не проверено вживую подписанными данными от настоящего
Telegram-клиента (в этой среде разработки нет доступа к Mini App рантайму).
Юнит-тесты подписывают тестовые данные тем же алгоритмом и проверяют
раунд-трип — это подтверждает самосогласованность реализации, но не
заменяет проверку с реальным initData после деплоя и регистрации в
BotFather.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

MAX_INIT_DATA_AGE_SECONDS = 24 * 60 * 60


@dataclass
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None


def _compute_hash(data_check_string: str, bot_token: str) -> str:
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


def validate_init_data(
    init_data: str, bot_token: str, max_age_seconds: int = MAX_INIT_DATA_AGE_SECONDS
) -> TelegramUser | None:
    """Проверяет подпись initData. Возвращает пользователя или None, если
    подпись неверна, данные устарели или обязательные поля отсутствуют."""
    if not init_data:
        return None

    data = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    expected_hash = _compute_hash(data_check_string, bot_token)
    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    try:
        auth_ts = int(data.get("auth_date", ""))
    except ValueError:
        return None
    if time.time() - auth_ts > max_age_seconds:
        return None

    user_json = data.get("user")
    if not user_json:
        return None
    try:
        user_payload = json.loads(user_json)
    except (json.JSONDecodeError, TypeError):
        return None

    user_id = user_payload.get("id")
    if user_id is None:
        return None

    return TelegramUser(
        id=int(user_id),
        first_name=user_payload.get("first_name", ""),
        last_name=user_payload.get("last_name"),
        username=user_payload.get("username"),
        photo_url=user_payload.get("photo_url"),
    )
