import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from app.webapp.auth import validate_init_data

BOT_TOKEN = "123456:fake-test-token"


def _sign(data: dict) -> str:
    """Подписывает данные тем же алгоритмом, что и validate_init_data —
    единственный способ сгенерировать валидный initData без реального
    Telegram-клиента (см. TODO: verify в app/webapp/auth.py)."""
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    data = dict(data)
    data["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def _valid_init_data(user_id: int = 1, **overrides) -> str:
    user = {"id": user_id, "first_name": "Dima", "username": "dima"}
    user.update(overrides.pop("user_overrides", {}))
    payload = {"auth_date": str(int(time.time())), "user": json.dumps(user)}
    payload.update(overrides)
    return _sign(payload)


def test_valid_init_data_returns_user():
    init_data = _valid_init_data(user_id=42)
    user = validate_init_data(init_data, BOT_TOKEN)
    assert user is not None
    assert user.id == 42
    assert user.first_name == "Dima"
    assert user.username == "dima"


def test_tampered_hash_rejected():
    init_data = _valid_init_data()
    tampered = init_data[:-1] + ("0" if init_data[-1] != "0" else "1")
    assert validate_init_data(tampered, BOT_TOKEN) is None


def test_wrong_bot_token_rejected():
    init_data = _valid_init_data()
    assert validate_init_data(init_data, "different:token") is None


def test_missing_hash_rejected():
    payload = {"auth_date": str(int(time.time())), "user": json.dumps({"id": 1})}
    init_data = urlencode(payload)  # без hash вообще
    assert validate_init_data(init_data, BOT_TOKEN) is None


def test_empty_init_data_rejected():
    assert validate_init_data("", BOT_TOKEN) is None


def test_stale_auth_date_rejected():
    old_auth_date = str(int(time.time()) - 999_999)
    init_data = _valid_init_data(auth_date=old_auth_date)
    assert validate_init_data(init_data, BOT_TOKEN, max_age_seconds=86400) is None


def test_fresh_auth_date_within_custom_max_age_accepted():
    init_data = _valid_init_data()
    assert validate_init_data(init_data, BOT_TOKEN, max_age_seconds=60) is not None


def test_missing_user_field_rejected():
    payload = {"auth_date": str(int(time.time()))}
    init_data = _sign(payload)
    assert validate_init_data(init_data, BOT_TOKEN) is None


def test_malformed_user_json_rejected():
    payload = {"auth_date": str(int(time.time())), "user": "{not json"}
    init_data = _sign(payload)
    assert validate_init_data(init_data, BOT_TOKEN) is None


def test_user_without_id_rejected():
    payload = {"auth_date": str(int(time.time())), "user": json.dumps({"first_name": "X"})}
    init_data = _sign(payload)
    assert validate_init_data(init_data, BOT_TOKEN) is None


def test_optional_fields_default_to_none():
    payload = {"auth_date": str(int(time.time())), "user": json.dumps({"id": 7})}
    init_data = _sign(payload)
    user = validate_init_data(init_data, BOT_TOKEN)
    assert user is not None
    assert user.id == 7
    assert user.last_name is None
    assert user.username is None
    assert user.photo_url is None
