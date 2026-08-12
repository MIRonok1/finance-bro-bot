import pytest

from app.config import Settings


def test_settings_parses_admin_ids(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    settings = Settings(bot_token="123:abc", admin_ids="1, 2 ,3")
    assert settings.admin_ids_set == {1, 2, 3}


def test_settings_rejects_empty_bot_token():
    with pytest.raises(ValueError):
        Settings(bot_token="   ", admin_ids="1")


def test_settings_rejects_empty_admin_ids():
    with pytest.raises(ValueError):
        Settings(bot_token="123:abc", admin_ids="")


def test_settings_rejects_non_numeric_admin_id():
    settings = Settings(bot_token="123:abc", admin_ids="1,not-a-number")
    with pytest.raises(ValueError):
        _ = settings.admin_ids_set


def test_settings_defaults():
    settings = Settings(bot_token="123:abc", admin_ids="1")
    assert settings.db_path == "/data/bot.db"
    assert settings.paywall_enabled is False
    assert settings.log_level == "INFO"
    assert settings.anthropic_api_key is None
