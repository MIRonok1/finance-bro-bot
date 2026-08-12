import pytest

from app.config import Settings

# _env_file=None отключает подхват настоящего .env разработчика (см.
# app/config.py: env_file=".env") — без этого тесты незаметно ловят
# значения из локального .env вместо кодовых дефолтов/явных kwargs.


def test_settings_parses_admin_ids(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    settings = Settings(bot_token="123:abc", admin_ids="1, 2 ,3", _env_file=None)
    assert settings.admin_ids_set == {1, 2, 3}


def test_settings_rejects_empty_bot_token():
    with pytest.raises(ValueError):
        Settings(bot_token="   ", admin_ids="1", _env_file=None)


def test_settings_rejects_empty_admin_ids():
    with pytest.raises(ValueError):
        Settings(bot_token="123:abc", admin_ids="", _env_file=None)


def test_settings_rejects_non_numeric_admin_id():
    settings = Settings(bot_token="123:abc", admin_ids="1,not-a-number", _env_file=None)
    with pytest.raises(ValueError):
        _ = settings.admin_ids_set


def test_settings_defaults():
    settings = Settings(bot_token="123:abc", admin_ids="1", _env_file=None)
    assert settings.db_path == "/data/bot.db"
    assert settings.paywall_enabled is False
    assert settings.log_level == "INFO"
    assert settings.anthropic_api_key is None
