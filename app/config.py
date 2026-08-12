"""Конфигурация приложения из переменных окружения.

Обязательные переменные (BOT_TOKEN, ADMIN_IDS) валидируются на старте.
Если их нет или они пустые — приложение должно упасть с понятным
сообщением, а не стартовать с бракованным конфигом.
"""

from __future__ import annotations

import sys

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    admin_ids: str  # "123,456" -> парсится в set[int] через .admin_ids_set
    db_path: str = "/data/bot.db"
    anthropic_api_key: str | None = None
    paywall_enabled: bool = False
    log_level: str = "INFO"

    # --- Mini App (Фаза 3) ---
    # Публичный HTTPS-адрес, по которому Telegram открывает Mini App. Пока
    # не задан — кнопка запуска в боте скрыта, сервер всё равно поднимается
    # (чтобы можно было проверить /healthz и получить сам адрес от Netrun).
    webapp_url: str | None = None
    # PORT — частый конвенционный env var у PaaS-платформ (Netrun в их числе,
    # предположительно): если задан, имеет приоритет над WEBAPP_PORT.
    webapp_port: int = 8080
    port: int | None = None

    @property
    def effective_webapp_port(self) -> int:
        return self.port if self.port is not None else self.webapp_port

    @field_validator("bot_token")
    @classmethod
    def _bot_token_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("BOT_TOKEN пуст. Возьми токен у @BotFather и задай его в env.")
        return v.strip()

    @field_validator("admin_ids")
    @classmethod
    def _admin_ids_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ADMIN_IDS пуст. Укажи хотя бы один Telegram user id через запятую.")
        return v.strip()

    @property
    def admin_ids_set(self) -> set[int]:
        result: set[int] = set()
        for chunk in self.admin_ids.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                result.add(int(chunk))
            except ValueError as exc:
                raise ValueError(f"ADMIN_IDS содержит нечисловое значение: {chunk!r}") from exc
        if not result:
            raise ValueError("ADMIN_IDS не содержит ни одного валидного id.")
        return result


def load_settings() -> Settings:
    """Загружает конфиг или падает с внятным сообщением в stderr."""
    try:
        settings = Settings()  # type: ignore[call-arg]
        # Триггерим парсинг admin_ids_set сразу, чтобы упасть на старте,
        # а не при первом обращении к списку админов.
        _ = settings.admin_ids_set
        return settings
    except Exception as exc:  # noqa: BLE001 — здесь осознанно ловим всё
        print(f"[config] Не удалось загрузить конфигурацию: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
